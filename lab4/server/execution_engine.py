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
try:
    from ..common.utils import get_ffmpeg_binary, detect_system_capabilities
except (ImportError, ValueError):
    from lab4.common.utils import get_ffmpeg_binary, detect_system_capabilities


class RemoteExecutionEngine:
    """
    Executes heavy offloaded computational and rendering workloads:
    - GPU-accelerated video rendering via FFmpeg NVENC (with CPU libx264 fallback)
    - CUDA / Parallel Matrix Tensor Compute workloads
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
        Streams real-time progress percentages and stats.
        """
        start_time = time.time()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 1. Probe input video duration & specs
        duration = self._probe_video_duration(input_path)
        if duration <= 0:
            duration = 10.0  # Fallback duration estimate

        # 2. Extract configuration parameters
        resolution = config.get("resolution", "original")  # e.g. "1920x1080", "1280x720", "854x480"
        bitrate = config.get("bitrate", "3000k")
        preset = config.get("preset", "fast")
        force_mode = config.get("mode", "auto")  # "auto", "nvenc", "cpu"

        # Determine codec
        use_nvenc = False
        if force_mode == "nvenc" or (force_mode == "auto" and self.nvenc_available):
            use_nvenc = True
            codec = "h264_nvenc"
            # Map presets for NVENC if needed (p1 to p7 or standard)
            nvenc_preset = "p4" if preset in ["medium", "default"] else ("p1" if preset == "ultrafast" else "p5")
            encoder_args = ["-c:v", codec, "-preset", nvenc_preset, "-b:v", str(bitrate)]
        else:
            codec = "libx264"
            encoder_args = ["-c:v", codec, "-preset", preset, "-b:v", str(bitrate), "-threads", str(self.sys_info["cpu_count"])]

        # Video filter options
        vf_args = []
        if resolution != "original" and "x" in resolution:
            vf_args = ["-vf", f"scale={resolution}"]

        # Build FFmpeg command with progress pipe
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

        acceleration_label = "NVIDIA NVENC (GPU)" if use_nvenc else "Multi-Threaded CPU (libx264)"

        # Spawn FFmpeg process with stderr=subprocess.PIPE to capture error diagnostics safely
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
        out_time_ms = 0

        # Read progress output line-by-line
        try:
            for line in process.stdout:
                if check_cancelled and check_cancelled():
                    process.kill()
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
                        eta = max(0.0, (duration - out_time_sec) / (float(current_speed.replace("x", "")) if "x" in current_speed and current_speed != "N/A" and float(current_speed.replace("x", "") or 1) > 0 else 1.0))
                        
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
                    if progress_callback:
                        progress_callback(100.0, current_fps, current_speed, 0.0, "Encoding Complete")

            process.wait()
        except Exception as e:
            process.kill()
            raise e

        # Safely read stderr diagnostic if available
        stderr_out = ""
        if process.stderr:
            try:
                stderr_out = process.stderr.read()
            except Exception:
                stderr_out = ""

        # If NVENC failed because host lacks GPU, retry automatically with CPU fallback
        if process.returncode != 0 and use_nvenc:
            if "Cannot load nvcuda.dll" in stderr_out or "Error while opening encoder" in stderr_out or "Unknown encoder" in stderr_out:
                if progress_callback:
                    progress_callback(0.0, 0.0, "1.0x", 0.0, "NVENC unavailable on host. Retrying with CPU fallback...")
                config["mode"] = "cpu"
                return self.execute_video_transcode(input_path, output_path, config, progress_callback, check_cancelled)
            else:
                return {"success": False, "error": f"FFmpeg error: {stderr_out[:200] if stderr_out else 'Encoding failed'}"}

        if process.returncode != 0:
            return {"success": False, "error": f"FFmpeg execution failed (code {process.returncode}): {stderr_out[:200] if stderr_out else 'Execution error'}"}

        total_duration = time.time() - start_time
        return {
            "success": True,
            "engine": acceleration_label,
            "duration": total_duration,
            "resolution": resolution,
            "bitrate": bitrate,
            "output_size": os.path.getsize(output_path) if os.path.exists(output_path) else 0
        }

    def execute_cuda_compute(
        self,
        matrix_size: int,
        iterations: int,
        output_path: str,
        progress_callback: Optional[Callable[[float, float, str, float, str], None]] = None,
        check_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes intensive parallel matrix tensor computations (Monte Carlo / Matrix SVD / Multiplication).
        Uses PyTorch CUDA when available, with optimized vectorized NumPy parallel fallback.
        """
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
                # GPU Tensor Matrix Multiplication
                a = torch_mod.randn(matrix_size, matrix_size, device="cuda")
                b = torch_mod.randn(matrix_size, matrix_size, device="cuda")
                c = torch_mod.matmul(a, b)
                trace_val = float(torch_mod.trace(c).cpu())
            else:
                # High-performance NumPy Matrix Multiplication
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
        
        # Write computation summary to output file
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

        # Fallback ffprobe command
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
        """
        Executes an offloaded custom Python project script or heavy computation workload
        on this remote worker node using server CPU cores & memory.
        Streams real-time console stdout directly back to the client.
        """
        start_time = time.time()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if not os.path.exists(script_path):
            return {"success": False, "error": f"Script not found: {script_path}"}

        # Build execution command using current Python interpreter
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

                # Parse standardized [PROGRESS] markers if script outputs them
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
                    # Incrementally bump progress up to 90% for general scripts
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

        # If output file wasn't created by script itself, write stdout summary
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
