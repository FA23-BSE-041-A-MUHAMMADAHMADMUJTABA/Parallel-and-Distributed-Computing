"""
================================================================================
CSC-334: Parallel and Distributed Computing
Lab 4: Custom Distributed Task Offloading & Remote GPU Rendering System
Module: server/network_server.py
Description: Multi-threaded Network Listener, Protocol Handler & File Streamer.
================================================================================
"""

import os
import time
import socket
import select
import hashlib
import threading
from typing import Dict, Any, Optional

from ..common.protocol import (
    MsgType, send_packet, send_json, read_packet, read_json,
    CHUNK_SIZE, SOCKET_TIMEOUT, PROTOCOL_VERSION
)
from ..common.utils import compute_sha256, format_bytes, detect_system_capabilities
from .task_queue import TaskQueueManager, TaskItem, TaskStatus
from .execution_engine import RemoteExecutionEngine


class RemoteWorkerServer:
    """
    Core Server Daemon that listens for client connections, processes handshakes,
    streams files with checksum verification, and executes tasks on remote GPU/CPU.
    """
    def __init__(self, host: str = "0.0.0.0", port: int = 5000, storage_dir: str = "server_storage"):
        self.host = host
        self.port = port
        self.storage_dir = os.path.abspath(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)

        self.queue_manager = TaskQueueManager()
        self.engine = RemoteExecutionEngine()
        self.sys_info = detect_system_capabilities()

        self._server_sock: Optional[socket.socket] = None
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()
        self.active_clients = 0

    def start(self) -> None:
        """Starts the server listener and worker thread pool."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(10)
        self._server_sock.settimeout(1.0)  # Non-blocking accept check for clean shutdown

        print("=" * 70)
        print("  REMOTE GPU EXECUTION ENGINE DAEMON (CSC-334)")
        print("=" * 70)
        print(f"[*] Bound to Address       : {self.host}:{self.port}")
        print(f"[*] Storage Directory      : {self.storage_dir}")
        print(f"[*] Node Hostname          : {self.sys_info['hostname']}")
        print(f"[*] Platform OS            : {self.sys_info['os']}")
        print(f"[*] CPU Cores              : {self.sys_info['cpu_count']}")
        print(f"[*] GPU/NVENC Acceleration : {self.sys_info['nvenc_status']}")
        print(f"[*] Protocol Version       : {PROTOCOL_VERSION}")
        print("=" * 70)
        print("[*] Worker daemon listening for incoming client offload tasks...")

        # Start background task queue execution thread
        worker_thread = threading.Thread(target=self._queue_worker_loop, daemon=True)
        worker_thread.start()

        try:
            while not self._shutdown_event.is_set():
                try:
                    client_sock, client_addr = self._server_sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                with self._lock:
                    self.active_clients += 1
                
                print(f"[+] Incoming connection from client: {client_addr[0]}:{client_addr[1]}")
                handler_thread = threading.Thread(
                    target=self._handle_client_connection,
                    args=(client_sock, client_addr),
                    daemon=True
                )
                handler_thread.start()
        finally:
            self.stop()

    def stop(self) -> None:
        """Gracefully shuts down the server daemon."""
        self._shutdown_event.set()
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
        print("[-] Remote Worker Server Daemon stopped gracefully.")

    def _handle_client_connection(self, sock: socket.socket, addr: tuple) -> None:
        """Handles an interactive client session."""
        sock.settimeout(None)  # Keep persistent connection alive for interactive GUI
        try:
            while not self._shutdown_event.is_set():
                try:
                    msg_type, payload = read_packet(sock)
                except (socket.timeout, ConnectionResetError, EOFError):
                    break

                # 1. TASK 1: Robust Handshake Protocol
                if msg_type == MsgType.HANDSHAKE_SYN:
                    import json
                    client_meta = json.loads(payload.decode("utf-8")) if payload else {}
                    print(f"  [HANDSHAKE] Client {addr[0]} connected with Client ID: {client_meta.get('client_id', 'unknown')}")
                    
                    ack_data = {
                        "status": "READY",
                        "server_time": time.time(),
                        "hostname": self.sys_info["hostname"],
                        "os": self.sys_info["os"],
                        "cpu_count": self.sys_info["cpu_count"],
                        "nvenc_available": self.sys_info["nvenc_available"],
                        "nvenc_status": self.sys_info["nvenc_status"],
                        "cuda_available": self.sys_info["cuda_available"],
                        "queue_size": self.queue_manager.get_queue_size(),
                        "protocol_version": PROTOCOL_VERSION
                    }
                    send_json(sock, MsgType.HANDSHAKE_ACK, ack_data)

                # 2. TASK 1: Initial Latency / Ping Check
                elif msg_type == MsgType.PING_REQ:
                    import json
                    ping_data = json.loads(payload.decode("utf-8")) if payload else {}
                    pong_data = {
                        "client_send_time": ping_data.get("client_timestamp", time.time()),
                        "server_receive_time": time.time(),
                        "active_workers": self.queue_manager.get_active_count()
                    }
                    send_json(sock, MsgType.PONG_RESP, pong_data)

                # 3. TASK 2 & 4: Job Submission & Secure Asset Streaming
                elif msg_type == MsgType.JOB_SUBMIT:
                    self._process_job_submission(sock, payload, addr)

                # 4. TASK 4: Download Processed Output
                elif msg_type == MsgType.DOWNLOAD_REQ:
                    self._process_download_request(sock, payload)

                # 5. Cancel Request
                elif msg_type == MsgType.CANCEL_REQ:
                    import json
                    req = json.loads(payload.decode("utf-8")) if payload else {}
                    task_id = req.get("task_id", "")
                    cancelled = self.queue_manager.cancel_task(task_id)
                    send_json(sock, MsgType.JOB_RESULT, {"task_id": task_id, "status": "CANCELLED" if cancelled else "NOT_FOUND"})

                else:
                    print(f"[!] Unknown message type received: {msg_type!r}")

        except Exception as e:
            print(f"[!] Error handling client {addr}: {e}")
        finally:
            with self._lock:
                self.active_clients = max(0, self.active_clients - 1)
            try:
                sock.close()
            except Exception:
                pass
            print(f"[-] Client {addr[0]}:{addr[1]} disconnected.")

    def _process_job_submission(self, sock: socket.socket, payload: bytes, addr: tuple) -> None:
        """Receives asset file, validates SHA-256 checksum, and schedules task."""
        import json
        meta = json.loads(payload.decode("utf-8"))
        task_id = meta["task_id"]
        task_type = meta["task_type"]
        file_name = meta.get("file_name", f"{task_id}.dat")
        expected_size = meta.get("file_size", 0)
        expected_sha256 = meta.get("sha256", "")
        config = meta.get("config", {})

        print(f"\n[JOB SUBMIT] Task ID: {task_id} ({task_type}) from {addr[0]}")
        print(f"  Asset File: {file_name} ({format_bytes(expected_size)})")

        input_path = os.path.join(self.storage_dir, f"in_{task_id}_{os.path.basename(file_name)}")
        
        # Acknowledge job submission
        send_json(sock, MsgType.JOB_ACCEPTED, {"task_id": task_id, "status": "READY_FOR_UPLOAD"})

        # Stream incoming asset file chunks if file size > 0
        if expected_size > 0:
            received_bytes = 0
            hasher = hashlib.sha256()

            with open(input_path, "wb") as f:
                while True:
                    chunk_type, chunk_data = read_packet(sock)
                    if chunk_type == MsgType.FILE_CHUNK:
                        f.write(chunk_data)
                        hasher.update(chunk_data)
                        received_bytes += len(chunk_data)
                    elif chunk_type == MsgType.FILE_EOF:
                        break
                    else:
                        raise ValueError(f"Unexpected chunk type during upload: {chunk_type!r}")

            computed_sha256 = hasher.hexdigest()
            print(f"  Upload Complete. Computed SHA-256: {computed_sha256[:12]}...")

            # TASK 4: File Integrity Verification Checksum
            if expected_sha256 and computed_sha256.lower() != expected_sha256.lower():
                print(f"[!] CHECKSUM MISMATCH for {file_name}! Expected: {expected_sha256}, Got: {computed_sha256}")
                send_json(sock, MsgType.ERROR, {"error": "Checksum verification failed. Corrupted transfer."})
                if os.path.exists(input_path):
                    os.remove(input_path)
                return
            else:
                print(f"  [INTEGRITY] SHA-256 checksum verified successfully!")
        else:
            input_path = ""

        # Prepare output path
        out_ext = ".mp4" if task_type == "video_transcode" else ".json"
        output_path = os.path.join(self.storage_dir, f"out_{task_id}{out_ext}")

        task_item = TaskItem(task_id, task_type, config, input_path, output_path)
        task_item.client_socket = sock

        # Add to Task Queue
        self.queue_manager.submit_task(task_item)

        # Directly monitor execution on this socket channel
        self._stream_task_execution(task_item, sock)

    def _stream_task_execution(self, task: TaskItem, sock: socket.socket) -> None:
        """Executes task and streams real-time progress directly to client socket."""
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()

        def progress_callback(percent: float, fps: float, speed: str, eta: float, status_text: str):
            task.progress_percent = percent
            task.current_fps = fps
            task.speed_multiplier = speed
            progress_packet = {
                "task_id": task.task_id,
                "percent": round(percent, 1),
                "fps": round(fps, 1),
                "speed": speed,
                "eta_seconds": round(eta, 1),
                "status": status_text
            }
            try:
                send_json(sock, MsgType.PROGRESS, progress_packet)
            except Exception:
                pass

        try:
            if task.task_type == "video_transcode":
                res = self.engine.execute_video_transcode(
                    task.input_path,
                    task.output_path,
                    task.config,
                    progress_callback=progress_callback,
                    check_cancelled=lambda: task.is_cancelled
                )
            elif task.task_type == "cuda_compute":
                matrix_size = task.config.get("matrix_size", 1024)
                iterations = task.config.get("iterations", 10)
                res = self.engine.execute_cuda_compute(
                    matrix_size,
                    iterations,
                    task.output_path,
                    progress_callback=progress_callback,
                    check_cancelled=lambda: task.is_cancelled
                )
            else:
                res = {"success": False, "error": f"Unknown task type: {task.task_type}"}

            task.end_time = time.time()
            task.execution_duration = task.end_time - task.start_time

            if res.get("success"):
                task.status = TaskStatus.COMPLETED
                output_size = os.path.getsize(task.output_path) if os.path.exists(task.output_path) else 0
                output_sha256 = compute_sha256(task.output_path) if output_size > 0 else ""

                result_payload = {
                    "task_id": task.task_id,
                    "status": "COMPLETED",
                    "engine": res.get("engine", "Default"),
                    "duration_sec": round(task.execution_duration, 3),
                    "output_file_name": os.path.basename(task.output_path),
                    "output_size_bytes": output_size,
                    "output_sha256": output_sha256,
                    "metrics": res
                }
                print(f"[JOB COMPLETE] Task {task.task_id} completed in {task.execution_duration:.2f}s using {res.get('engine')}")
                send_json(sock, MsgType.JOB_RESULT, result_payload)
            else:
                task.status = TaskStatus.FAILED
                task.error_message = res.get("error", "Unknown execution error")
                print(f"[JOB FAILED] Task {task.task_id}: {task.error_message}")
                send_json(sock, MsgType.ERROR, {"task_id": task.task_id, "error": task.error_message})

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            print(f"[JOB EXCEPTION] Task {task.task_id}: {e}")
            send_json(sock, MsgType.ERROR, {"task_id": task.task_id, "error": str(e)})

    def _process_download_request(self, sock: socket.socket, payload: bytes) -> None:
        """Streams rendered output file back to client in chunks with SHA-256 validation."""
        import json
        req = json.loads(payload.decode("utf-8"))
        task_id = req.get("task_id", "")
        file_name = req.get("file_name", "")

        file_path = os.path.join(self.storage_dir, file_name)
        if not os.path.exists(file_path):
            send_json(sock, MsgType.ERROR, {"error": "File not found on server"})
            return

        file_size = os.path.getsize(file_path)
        sha256 = compute_sha256(file_path)
        print(f"[DOWNLOAD] Streaming {file_name} ({format_bytes(file_size)}) to client...")

        # Send download metadata header
        send_json(sock, MsgType.JOB_ACCEPTED, {"file_name": file_name, "file_size": file_size, "sha256": sha256})

        # Stream chunks
        with open(file_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                send_packet(sock, MsgType.FILE_CHUNK, chunk)

        # Send EOF
        send_packet(sock, MsgType.FILE_EOF, sha256.encode("utf-8"))
        print(f"[DOWNLOAD COMPLETE] Successfully streamed {file_name} with SHA-256 verification.")

    def _queue_worker_loop(self) -> None:
        """Background worker thread loop for task queue execution."""
        while not self._shutdown_event.is_set():
            task = self.queue_manager.get_task(timeout=1.0)
            if task:
                self.queue_manager.task_done()
