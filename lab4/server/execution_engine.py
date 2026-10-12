"""
================================================================================
CSC-334: Parallel and Distributed Computing
Lab 4: Custom Distributed Task Offloading & Remote GPU Rendering System
Module: server/execution_engine.py
Description: Hardware-accelerated GPU & Multi-Threaded Execution Engine.
================================================================================
"""

import os
import re
import sys
import time
import json
import subprocess
from typing import Dict, Any, Callable, Optional

# Local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from utils import get_ffmpeg_binary, detect_system_capabilities, compute_sha256, format_bytes
except ImportError:
    from .utils import get_ffmpeg_binary, detect_system_capabilities, compute_sha256, format_bytes


class RemoteExecutionEngine:
    """
    Executes heavy offloaded computational and rendering workloads:
    - GPU-accelerated video rendering via FFmpeg NVENC (with CPU libx264 fallback)
    - Full execution logging saved to disk and streamed to client
    - CUDA / Parallel Matrix Tensor Compute workloads
    - Custom multi-stage scientific / project script execution
    """
    def __init__(self):
        self.sys_info = detect_system_capabilities()
        self.ffmpeg_exe = get_ffmpeg_binary()
        self.nvenc_available = self.sys_info.get("nvenc_available", False)

    def execute_video_transcode(
        self,
        input_path: str,
        output_path: str,
        config: Dict[str, Any],
        progress_callback: Optional[Callable[[float, float, str, float, str], None]] = None,
        check_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Transcodes video asset using NVENC hardware acceleration if supported,
        falling back to multi-threaded CPU libx264.
        Streams real-time progress percentages and generates a detailed server render log.
        """
        start_time = time.time()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        log_path = output_path.rsplit(".", 1)[0] + "_render_log.txt"

        log_events = []
        def log_event(text: str):
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            entry = f"[{timestamp}] {text}"
            log_events.append(entry)

        log_event("=" * 70)
        log_event("CSC-334: REMOTE VIDEO RENDERING ENGINE EXECUTION LOG")
        log_event("=" * 70)
        log_event(f"Server Node Hostname : {self.sys_info.get('hostname', 'Unknown')}")
        log_event(f"Operating System     : {self.sys_info.get('os', 'Unknown')}")
        log_event(f"CPU Physical / Logic : {self.sys_info.get('cpu_count', 'Unknown')} Cores")
        log_event(f"GPU / NVENC Hardware : {self.sys_info.get('nvenc_status', 'N/A')}")
        log_event(f"FFmpeg Binary Path   : {self.ffmpeg_exe}")
        log_event("-" * 70)

        # 1. Probe input video duration & specs
        duration = self._probe_video_duration(input_path)
        if duration <= 0:
            duration = 10.0  # Fallback duration estimate

        in_size = os.path.getsize(input_path) if os.path.exists(input_path) else 0
        in_sha256 = compute_sha256(input_path) if in_size > 0 else "N/A"
        log_event(f"Input Video Source   : {input_path}")
        log_event(f"Input File Size      : {format_bytes(in_size)} ({in_size:,} bytes)")
        log_event(f"Input SHA-256 Hash   : {in_sha256}")
        log_event(f"Probed Video Duration: {duration:.2f} seconds")

        # 2. Extract configuration parameters
        resolution = config.get("resolution", "original")  # e.g. "1920x1080", "1280x720"
        bitrate = config.get("bitrate", "3000k")
        preset = config.get("preset", "fast")
        force_mode = config.get("mode", "auto")  # "auto", "nvenc", "cpu"
        filter_effect = config.get("filter", "none")
        fps_val = str(config.get("fps", "original"))

        log_event("-" * 70)
        log_event("RENDER CONFIGURATION PARAMETERS:")
        log_event(f"• Target Resolution  : {resolution}")
        log_event(f"• Target Bitrate     : {bitrate}")
        log_event(f"• Encoding Preset    : {preset}")
        log_event(f"• Acceleration Mode  : {force_mode}")
        log_event(f"• Visual Filter      : {filter_effect}")
        log_event(f"• Target Frame Rate  : {fps_val}")

        # Determine codec
        use_nvenc = False
        if force_mode == "nvenc" or (force_mode == "auto" and self.nvenc_available):
            use_nvenc = True
            codec = "h264_nvenc"
            nvenc_preset = "p4" if preset in ["medium", "default"] else ("p1" if preset == "ultrafast" else "p5")
            encoder_args = ["-c:v", codec, "-preset", nvenc_preset, "-b:v", str(bitrate)]
        else:
            codec = "libx264"
            encoder_args = ["-c:v", codec, "-preset", preset, "-b:v", str(bitrate), "-threads", str(self.sys_info["cpu_count"])]

        # Video filter options & creative editing effects
        vf_filters = []
        if resolution != "original" and "x" in resolution:
            vf_filters.append(f"scale={resolution}")

        if filter_effect == "grayscale":
            vf_filters.append("format=gray")
        elif filter_effect == "sepia":
            vf_filters.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        elif filter_effect == "mirror":
            vf_filters.append("hflip")
        elif filter_effect == "blur":
            vf_filters.append("boxblur=5:1")
        elif filter_effect == "speed_2x":
            vf_filters.append("setpts=0.5*PTS")

        vf_args = []
        if vf_filters:
            vf_args = ["-vf", ",".join(vf_filters)]

        if fps_val != "original":
            clean_fps = fps_val.replace(" fps", "").strip()
            vf_args.extend(["-r", clean_fps])

        cmd = [
            self.ffmpeg_exe, "-y",
            "-loglevel", "error",
            "-i", input_path,
            *encoder_args,
            *vf_args,
            "-c:a", "aac", "-b:a", "128k",
            "-progress", "pipe:1",
            "-nostats",
            output_path
        ]

        acceleration_label = "NVIDIA NVENC (GPU Hardware)" if use_nvenc else "Multi-Threaded CPU (libx264)"
        log_event(f"Assigned Engine      : {acceleration_label}")
        log_event(f"FFmpeg Shell Command : {' '.join(cmd)}")
        log_event("-" * 70)
        log_event("ENCODING EXECUTION TIMELINE & PROGRESS STREAM:")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        current_fps = 0.0
        current_speed = "1.0x"
        last_logged_pct = -10.0

        try:
            for line in process.stdout:
                if check_cancelled and check_cancelled():
                    process.kill()
                    log_event("[ABORT] Rendering cancelled by client request.")
                    self._save_log_file(log_path, log_events)
                    return {"success": False, "error": "Task cancelled by client"}

                line = line.strip()
                if not line:
                    continue

                if line.startswith("fps="):
                    try:
                        current_fps = float(line.split("=")[1])
                    except ValueError:
                        pass
                elif line.startswith("speed="):
                    current_speed = line.split("=")[1].strip()
                elif line.startswith("out_time_us="):
                    try:
                        time_us = int(line.split("=")[1])
                        out_time_sec = time_us / 1_000_000.0
                        percent = min(99.0, (out_time_sec / duration) * 100.0)
                        speed_mult = float(current_speed.replace("x", "")) if "x" in current_speed and current_speed != "N/A" and float(current_speed.replace("x", "") or 1) > 0 else 1.0
                        eta = max(0.0, (duration - out_time_sec) / speed_mult)

                        if percent - last_logged_pct >= 10.0 or percent >= 98.0:
                            log_event(f"Progress: {percent:5.1f}% | Encoded: {out_time_sec:5.1f}s / {duration:5.1f}s | Speed: {current_speed} | FPS: {current_fps:4.1f} | ETA: {eta:4.1f}s")
                            last_logged_pct = percent

                        if progress_callback:
                            progress_callback(
                                percent,
                                current_fps,
                                current_speed,
                                eta,
                                f"Rendering with {acceleration_label} [{percent:.1f}%]"
                            )
                    except (ValueError, ZeroDivisionError):
                        pass
                elif line == "progress=end":
                    log_event("Progress: 100.0% | FFmpeg reported stream completion.")
                    if progress_callback:
                        progress_callback(100.0, current_fps, current_speed, 0.0, "Encoding Complete")

            process.wait()
        except Exception as e:
            process.kill()
            log_event(f"[EXCEPTION] Runtime error during encoding: {e}")
            self._save_log_file(log_path, log_events)
            raise e

        stderr_out = ""
        if process.stderr:
            try:
                stderr_out = process.stderr.read()
            except Exception:
                stderr_out = ""

        # Auto fallback if NVENC fails
        if process.returncode != 0 and use_nvenc:
            if "Cannot load nvcuda.dll" in stderr_out or "Error while opening encoder" in stderr_out or "Unknown encoder" in stderr_out:
                log_event("[WARNING] NVENC hardware encoder unavailable. Switching to Multi-threaded CPU fallback...")
                if progress_callback:
                    progress_callback(0.0, 0.0, "1.0x", 0.0, "NVENC unavailable on host. Retrying with CPU fallback...")
                config["mode"] = "cpu"
                return self.execute_video_transcode(input_path, output_path, config, progress_callback, check_cancelled)
            else:
                log_event(f"[ERROR] FFmpeg error: {stderr_out}")
                self._save_log_file(log_path, log_events)
                return {"success": False, "error": f"FFmpeg error: {stderr_out[:200] if stderr_out else 'Encoding failed'}"}

        if process.returncode != 0:
            log_event(f"[ERROR] Process exited with code {process.returncode}: {stderr_out}")
            self._save_log_file(log_path, log_events)
            return {"success": False, "error": f"FFmpeg execution failed (code {process.returncode}): {stderr_out[:200] if stderr_out else 'Execution error'}"}

        total_duration = time.time() - start_time
        out_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        out_sha256 = compute_sha256(output_path) if out_size > 0 else "N/A"
        compression_ratio = ((in_size - out_size) / in_size * 100.0) if in_size > 0 else 0.0

        log_event("-" * 70)
        log_event("RENDER EXECUTION RESULTS & INTEGRITY METRICS:")
        log_event(f"• Execution Status   : SUCCESS (Return Code 0)")
        log_event(f"• Render Duration    : {total_duration:.3f} seconds")
        log_event(f"• Average Speed Factor: {current_speed}")
        log_event(f"• Output File Path   : {output_path}")
        log_event(f"• Output File Size   : {format_bytes(out_size)} ({out_size:,} bytes)")
        log_event(f"• Size Delta Ratio   : {compression_ratio:+.1f}%")
        log_event(f"• Output SHA-256 Hash: {out_sha256}")
        log_event("=" * 70)
        log_event("END OF LOG - Video asset rendered and verified for transmission back to client.")
        log_event("=" * 70)

        logs_content = "\n".join(log_events)
        self._save_log_file(log_path, log_events)

        return {
            "success": True,
            "engine": acceleration_label,
            "duration": total_duration,
            "resolution": resolution,
            "bitrate": bitrate,
            "output_size": out_size,
            "output_sha256": out_sha256,
            "log_path": log_path,
            "log_file_name": os.path.basename(log_path),
            "logs_text": logs_content
        }

    def _save_log_file(self, log_path: str, lines: list):
        """Writes execution events list to disk log file."""
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass

    def execute_cuda_compute(
        self,
        matrix_size: int,
        iterations: int,
        output_path: str,
        progress_callback: Optional[Callable[[float, float, str, float, str], None]] = None,
        check_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """Executes intensive parallel matrix tensor computations."""
        import numpy as np

        start_time = time.time()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        engine_name = "CPU Parallel NumPy (BLAS Optimized)"
        use_torch = False
        torch_mod = None
        try:
            import importlib
            torch_mod = importlib.import_module("torch")
            if hasattr(torch_mod, "cuda") and torch_mod.cuda.is_available():
                engine_name = f"NVIDIA CUDA GPU ({torch_mod.cuda.get_device_name(0)})"
                use_torch = True
        except Exception:
            use_torch = False
            torch_mod = None

        results = []
        for i in range(iterations):
            if check_cancelled and check_cancelled():
                return {"success": False, "error": "Task cancelled by client"}

            iter_start = time.time()
            if use_torch and torch_mod is not None:
                a = torch_mod.randn(matrix_size, matrix_size, device="cuda")
                b = torch_mod.randn(matrix_size, matrix_size, device="cuda")
                c = torch_mod.matmul(a, b)
                trace_val = float(torch_mod.trace(c).cpu())
            else:
                a = np.random.randn(matrix_size, matrix_size).astype(np.float32)
                b = np.random.randn(matrix_size, matrix_size).astype(np.float32)
                c = np.dot(a, b)
                trace_val = float(np.trace(c))

            iter_time = time.time() - iter_start
            gflops = (2.0 * (matrix_size ** 3)) / (iter_time * 1e9) if iter_time > 0 else 0
            results.append({"iteration": i + 1, "trace": trace_val, "gflops": round(gflops, 2), "duration_sec": iter_time})

            percent = ((i + 1) / iterations) * 100.0
            eta = (iterations - (i + 1)) * iter_time

            if progress_callback:
                progress_callback(
                    percent,
                    float(i + 1),
                    f"{gflops:.1f} GFLOPS",
                    eta,
                    f"Computing ({engine_name}) - Iter {i+1}/{iterations} [{percent:.1f}%]"
                )

        total_duration = time.time() - start_time
        summary = {
            "task_type": "cuda_compute",
            "engine": engine_name,
            "matrix_dimension": f"{matrix_size}x{matrix_size}",
            "iterations": iterations,
            "total_execution_time": total_duration,
            "average_gflops": sum(r["gflops"] for r in results) / len(results) if results else 0,
            "iteration_metrics": results
        }
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

        return {
            "success": True,
            "engine": engine_name,
            "duration": total_duration,
            "gflops": summary["average_gflops"],
            "output_size": os.path.getsize(output_path)
        }

    def _probe_video_duration(self, video_path: str) -> float:
        """Extracts exact video duration in seconds using ffprobe or OpenCV."""
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            if fps > 0 and frames > 0:
                return frames / fps
        except Exception:
            pass

        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.returncode == 0:
                return float(res.stdout.strip())
        except Exception:
            pass

        return 10.0

    def execute_custom_script(
        self,
        script_path: str,
        output_path: str,
        config: Dict[str, Any],
        progress_callback: Optional[Callable[[float, float, str, float, str], None]] = None,
        check_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """Executes an offloaded custom Python project script."""
        start_time = time.time()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if not os.path.exists(script_path):
            return {"success": False, "error": f"Script not found: {script_path}"}

        cmd = [sys.executable, script_path, output_path]
        extra_args = config.get("args", [])
        if isinstance(extra_args, list):
            cmd.extend([str(a) for a in extra_args])

        engine_name = f"Remote Server CPU Compute ({self.sys_info.get('hostname', 'Server')} - {self.sys_info.get('cpu_count', 4)} Cores)"
        if progress_callback:
            progress_callback(5.0, 0.0, "1.0x", 0.0, f"Spawning worker process on {self.sys_info.get('hostname')}...")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        all_logs = []
        current_pct = 5.0
        line_count = 0

        try:
            for line in process.stdout:
                if check_cancelled and check_cancelled():
                    process.kill()
                    return {"success": False, "error": "Task cancelled by client."}

                clean_line = line.strip()
                if not clean_line:
                    continue
                all_logs.append(clean_line)
                line_count += 1

                if "[PROGRESS]" in clean_line:
                    try:
                        part = clean_line.split("[PROGRESS]")[1].strip()
                        pct_str, desc = part.split("% - ")
                        current_pct = float(pct_str)
                        if progress_callback:
                            progress_callback(current_pct, float(line_count), "Active", 0.0, desc)
                    except Exception:
                        if progress_callback:
                            progress_callback(current_pct, float(line_count), "Active", 0.0, clean_line)
                else:
                    current_pct = min(92.0, current_pct + 1.5)
                    if progress_callback:
                        progress_callback(current_pct, float(line_count), "Active", 0.0, clean_line[:60])

            process.wait()
        except Exception as e:
            process.kill()
            return {"success": False, "error": f"Process execution error: {e}"}

        total_duration = time.time() - start_time

        if process.returncode != 0:
            err_summary = "\n".join(all_logs[-10:]) if all_logs else f"Exited with code {process.returncode}"
            return {"success": False, "error": f"Script failed (exit code {process.returncode}): {err_summary}"}

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            summary_data = {
                "task_type": "custom_script",
                "engine": engine_name,
                "script_name": os.path.basename(script_path),
                "duration_seconds": round(total_duration, 3),
                "lines_processed": line_count,
                "execution_stdout": all_logs
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2)

        if progress_callback:
            progress_callback(100.0, float(line_count), "Done", 0.0, "Script Completed Successfully")

        return {
            "success": True,
            "engine": engine_name,
            "duration": total_duration,
            "output_size": os.path.getsize(output_path) if os.path.exists(output_path) else 0,
            "lines_output": line_count
        }
