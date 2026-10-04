"""
================================================================================
CSC-334: Parallel and Distributed Computing
Lab 4: Custom Distributed Task Offloading & Remote GPU Rendering System
Module: client/network_client.py
Description: Robust Network Client handling handshake, ping, streaming & checksums.
================================================================================
"""

import os
import sys
import time
import socket
import hashlib
import uuid
from typing import Dict, Any, Tuple, Optional, Callable

from ..common.protocol import (
    MsgType, send_packet, send_json, read_packet, read_json,
    CHUNK_SIZE, SOCKET_TIMEOUT, PROTOCOL_VERSION
)
from ..common.utils import compute_sha256, format_bytes


class OffloadingClient:
    """
    Client-side communication manager:
    - Task 1: Performs handshake and ping latency check with remote worker.
    - Task 4: Chunked file streaming with SHA-256 verification and progress streaming.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port
        self.client_id = f"client_{uuid.uuid4().hex[:8]}"
        self.sock: Optional[socket.socket] = None
        self.worker_info: Dict[str, Any] = {}
        self.is_connected = False

    def connect(self, timeout: float = 5.0) -> bool:
        """Establishes TCP connection to the remote worker node."""
        self.disconnect()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(timeout)
            self.sock.connect((self.host, self.port))
            self.is_connected = True
            return True
        except Exception as e:
            self.disconnect()
            raise ConnectionError(f"Could not connect to Remote Worker at {self.host}:{self.port} -> {e}")

    def disconnect(self) -> None:
        """Closes the socket connection safely."""
        self.is_connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def perform_handshake(self) -> Dict[str, Any]:
        """
        TASK 1: Handshake Protocol
        Sends client info, verifies worker protocol version, and retrieves worker capabilities.
        """
        if not self.is_connected or not self.sock:
            self.connect()

        handshake_payload = {
            "client_id": self.client_id,
            "protocol_version": PROTOCOL_VERSION,
            "timestamp": time.time()
        }
        send_json(self.sock, MsgType.HANDSHAKE_SYN, handshake_payload)

        msg_type, ack_data = read_json(self.sock)
        if msg_type != MsgType.HANDSHAKE_ACK:
            raise ValueError(f"Handshake failed. Expected HANDSHAKE_ACK, got {msg_type!r}")

        self.worker_info = ack_data
        return ack_data

    def measure_ping_latency(self, num_samples: int = 3) -> float:
        """
        TASK 1: Latency / Ping Check
        Calculates average round-trip time (RTT) in milliseconds.
        """
        if not self.is_connected or not self.sock:
            self.connect()

        latencies = []
        for _ in range(num_samples):
            t_start = time.time()
            send_json(self.sock, MsgType.PING_REQ, {"client_timestamp": t_start})
            msg_type, pong = read_json(self.sock)
            if msg_type == MsgType.PONG_RESP:
                rtt = (time.time() - t_start) * 1000.0  # ms
                latencies.append(rtt)
            time.sleep(0.05)

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        return round(avg_latency, 2)

    def offload_video_transcode(
        self,
        input_file: str,
        output_dir: str,
        render_config: Dict[str, Any],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        TASK 2 & 4: Submits video transcoding task to remote GPU worker.
        Transfers asset with SHA-256 verification, receives progress, downloads output.
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")

        file_size = os.path.getsize(input_file)
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        # Calculate SHA-256 for transmission integrity verification
        if progress_callback:
            progress_callback({"status": "Computing SHA-256 input checksum...", "percent": 0.0})
        input_sha256 = compute_sha256(input_file)

        if not self.is_connected or not self.sock:
            self.connect()
            self.perform_handshake()

        # 1. Submit Job Metadata
        if progress_callback:
            progress_callback({"status": "Submitting job configuration to remote worker...", "percent": 0.0})

        job_meta = {
            "task_id": task_id,
            "task_type": "video_transcode",
            "file_name": os.path.basename(input_file),
            "file_size": file_size,
            "sha256": input_sha256,
            "config": render_config
        }
        try:
            send_json(self.sock, MsgType.JOB_SUBMIT, job_meta)
        except (OSError, ConnectionError):
            self.connect()
            self.perform_handshake()
            send_json(self.sock, MsgType.JOB_SUBMIT, job_meta)

        # Wait for worker acceptance
        msg_type, ack = read_json(self.sock)
        if msg_type != MsgType.JOB_ACCEPTED:
            raise ConnectionError(f"Worker did not accept job: {ack}")

        # 2. Stream File Asset to Worker
        upload_start = time.time()
        sent_bytes = 0
        with open(input_file, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                if cancel_check and cancel_check():
                    send_json(self.sock, MsgType.CANCEL_REQ, {"task_id": task_id})
                    raise InterruptedError("Job cancelled by user.")
                
                send_packet(self.sock, MsgType.FILE_CHUNK, chunk)
                sent_bytes += len(chunk)
                upload_pct = (sent_bytes / file_size) * 100.0
                if progress_callback and sent_bytes % (CHUNK_SIZE * 4) == 0:
                    speed = (sent_bytes / (time.time() - upload_start + 0.001)) / (1024 * 1024)
                    progress_callback({
                        "status": f"Uploading asset ({format_bytes(sent_bytes)}/{format_bytes(file_size)}) @ {speed:.2f} MB/s",
                        "percent": upload_pct,
                        "upload_progress": upload_pct
                    })

        send_packet(self.sock, MsgType.FILE_EOF, input_sha256.encode("utf-8"))
        upload_duration = time.time() - upload_start

        # 3. Stream Real-Time Progress from Worker
        remote_compute_start = time.time()
        result_payload = None

        while True:
            if cancel_check and cancel_check():
                send_json(self.sock, MsgType.CANCEL_REQ, {"task_id": task_id})
                raise InterruptedError("Job cancelled by user.")

            msg_type, payload = read_packet(self.sock)

            if msg_type == MsgType.PROGRESS:
                import json
                prog_data = json.loads(payload.decode("utf-8"))
                if progress_callback:
                    progress_callback(prog_data)

            elif msg_type == MsgType.JOB_RESULT:
                import json
                result_payload = json.loads(payload.decode("utf-8"))
                break

            elif msg_type == MsgType.ERROR:
                import json
                err_data = json.loads(payload.decode("utf-8"))
                raise RuntimeError(f"Remote Worker Execution Error: {err_data.get('error')}")

            else:
                pass

        remote_compute_duration = time.time() - remote_compute_start

        # 4. Download Rendered Output File with Checksum Validation
        out_filename = result_payload.get("output_file_name", f"output_{task_id}.mp4")
        expected_out_size = result_payload.get("output_size_bytes", 0)
        expected_out_sha256 = result_payload.get("output_sha256", "")
        download_start = time.time()

        os.makedirs(output_dir, exist_ok=True)
        local_output_path = os.path.join(output_dir, out_filename)

        if progress_callback:
            progress_callback({"status": "Downloading rendered asset from worker node...", "percent": 100.0})

        send_json(self.sock, MsgType.DOWNLOAD_REQ, {"task_id": task_id, "file_name": out_filename})

        # Read download acceptance
        msg_type, dl_ack = read_json(self.sock)
        recv_bytes = 0
        hasher = hashlib.sha256()

        with open(local_output_path, "wb") as f:
            while True:
                c_type, c_data = read_packet(self.sock)
                if c_type == MsgType.FILE_CHUNK:
                    f.write(c_data)
                    hasher.update(c_data)
                    recv_bytes += len(c_data)
                elif c_type == MsgType.FILE_EOF:
                    break

        download_duration = time.time() - download_start
        computed_out_sha256 = hasher.hexdigest()

        # Validate download integrity
        checksum_verified = (computed_out_sha256.lower() == expected_out_sha256.lower()) if expected_out_sha256 else True

        total_turnaround_time = upload_duration + remote_compute_duration + download_duration
        network_overhead_time = upload_duration + download_duration

        return {
            "success": True,
            "task_id": task_id,
            "engine": result_payload.get("engine", "Remote Worker"),
            "local_output_path": local_output_path,
            "input_file_size": file_size,
            "output_file_size": os.path.getsize(local_output_path),
            "upload_duration_sec": round(upload_duration, 3),
            "remote_compute_duration_sec": round(remote_compute_duration, 3),
            "download_duration_sec": round(download_duration, 3),
            "network_overhead_sec": round(network_overhead_time, 3),
            "total_turnaround_sec": round(total_turnaround_time, 3),
            "input_sha256": input_sha256,
            "output_sha256": computed_out_sha256,
            "checksum_verified": checksum_verified
        }

    def offload_cuda_compute(
        self,
        matrix_size: int,
        iterations: int,
        output_dir: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Submits a parallel matrix tensor compute workload to remote worker."""
        task_id = f"cuda_{uuid.uuid4().hex[:8]}"
        job_meta = {
            "task_id": task_id,
            "task_type": "cuda_compute",
            "file_name": "",
            "file_size": 0,
            "sha256": "",
            "config": {"matrix_size": matrix_size, "iterations": iterations}
        }
        send_json(self.sock, MsgType.JOB_SUBMIT, job_meta)

        msg_type, ack = read_json(self.sock)
        if msg_type != MsgType.JOB_ACCEPTED:
            raise ConnectionError(f"Job rejected: {ack}")

        start_time = time.time()
        result_payload = None

        while True:
            msg_type, payload = read_packet(self.sock)
            if msg_type == MsgType.PROGRESS:
                import json
                prog_data = json.loads(payload.decode("utf-8"))
                if progress_callback:
                    progress_callback(prog_data)
            elif msg_type == MsgType.JOB_RESULT:
                import json
                result_payload = json.loads(payload.decode("utf-8"))
                break
            elif msg_type == MsgType.ERROR:
                import json
                err = json.loads(payload.decode("utf-8"))
                raise RuntimeError(err.get("error"))

        total_time = time.time() - start_time
        return {
            "success": True,
            "task_id": task_id,
            "total_turnaround_sec": round(total_time, 3),
            "result_payload": result_payload
        }
