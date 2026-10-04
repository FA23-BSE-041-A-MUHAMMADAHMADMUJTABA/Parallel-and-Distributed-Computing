"""
================================================================================
CSC-334: Parallel and Distributed Computing
Lab 4: Custom Distributed Task Offloading & Remote GPU Rendering System
Module: client/benchmark.py
Description: Task 5 Benchmarking Suite (Local vs Remote GPU Offloading Analysis).
================================================================================
"""

import os
import sys
import time
import json
import argparse
import subprocess
from typing import Dict, Any, List, Optional, Callable

# Add repository root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from lab4.client.network_client import OffloadingClient
from lab4.common.utils import get_ffmpeg_binary, generate_sample_video, format_time, format_bytes


def execute_local_transcode(input_file: str, output_file: str, resolution: str, bitrate: str = "3000k") -> float:
    """
    Simulates resource-constrained client execution locally (using single thread or constrained CPU).
    Measures baseline T_local.
    """
    ffmpeg_exe = get_ffmpeg_binary()
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    vf_arg = ["-vf", f"scale={resolution}"] if resolution != "original" else []
    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_file,
        "-c:v", "libx264",
        "-preset", "slow",     # Resource-constrained client simulation
        "-threads", "1",       # Simulates single-threaded or low-power laptop client
        "-b:v", bitrate,
        *vf_arg,
        "-c:a", "aac",
        output_file
    ]

    t_start = time.time()
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return time.time() - t_start


def run_comparative_benchmark(
    worker_host: str = "127.0.0.1",
    worker_port: int = 5000,
    sample_video_path: Optional[str] = None,
    log_fn: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Executes comprehensive comparative benchmarking across multiple resolutions:
    - 480p (854x480)
    - 720p (1280x720)
    - 1080p (1920x1080)
    Calculates: T_local, T_remote, Speedup Factor, and Network Transfer Overhead.
    """
    def log(msg: str):
        if log_fn:
            log_fn(msg)
        print(msg)

    benchmark_dir = os.path.join(parent_dir, "lab4", "benchmarks")
    os.makedirs(benchmark_dir, exist_ok=True)

    # 1. Ensure test asset exists
    if not sample_video_path or not os.path.exists(sample_video_path):
        sample_video_path = os.path.join(benchmark_dir, "bench_input_sample.mp4")
        log(f"[*] Generating standard benchmark video asset: {sample_video_path}...")
        generate_sample_video(sample_video_path, duration_sec=5, resolution=(1280, 720))

    asset_size = os.path.getsize(sample_video_path)
    log(f"[*] Benchmark Asset: {os.path.basename(sample_video_path)} ({format_bytes(asset_size)})")

    # Connect to remote worker
    client = OffloadingClient(host=worker_host, port=worker_port)
    client.connect()
    worker_info = client.perform_handshake()
    latency_ms = client.measure_ping_latency(num_samples=3)

    log(f"[*] Connected to Worker: {worker_info.get('hostname')} | Acceleration: {worker_info.get('nvenc_status')[:35]} | Ping: {latency_ms} ms")

    test_configs = [
        {"name": "480p SD", "res": "854x480", "bitrate": "1500k"},
        {"name": "720p HD", "res": "1280x720", "bitrate": "3000k"},
        {"name": "1080p FHD", "res": "1920x1080", "bitrate": "6000k"},
    ]

    benchmark_records = []
    local_scratch_dir = os.path.join(benchmark_dir, "scratch")
    os.makedirs(local_scratch_dir, exist_ok=True)

    for cfg in test_configs:
        log("-" * 65)
        log(f"[*] Running Benchmark Configuration: {cfg['name']} ({cfg['res']} @ {cfg['bitrate']})")

        # Step A: Local Execution
        local_out = os.path.join(local_scratch_dir, f"local_{cfg['res']}.mp4")
        log(f"  [1/2] Benchmarking Local Client Execution...")
        t_local = execute_local_transcode(sample_video_path, local_out, cfg["res"], cfg["bitrate"])
        log(f"        -> Local Execution Time (T_local): {t_local:.3f} s")

        # Step B: Remote Offloaded Execution
        log(f"  [2/2] Benchmarking Remote Worker Offloading...")
        remote_res = client.offload_video_transcode(
            input_file=sample_video_path,
            output_dir=local_scratch_dir,
            render_config={"resolution": cfg["res"], "bitrate": cfg["bitrate"], "preset": "fast", "mode": "auto"}
        )

        t_upload = remote_res["upload_duration_sec"]
        t_remote_compute = remote_res["remote_compute_duration_sec"]
        t_download = remote_res["download_duration_sec"]
        t_remote_total = remote_res["total_turnaround_sec"]
        t_net_overhead = remote_res["network_overhead_sec"]

        # Calculate metrics
        speedup = t_local / t_remote_total if t_remote_total > 0 else 0.0
        compute_speedup = t_local / t_remote_compute if t_remote_compute > 0 else 0.0
        overhead_pct = (t_net_overhead / t_remote_total) * 100.0 if t_remote_total > 0 else 0.0

        log(f"        -> Network Upload Time   : {t_upload:.3f} s")
        log(f"        -> Remote Compute Time   : {t_remote_compute:.3f} s ({remote_res.get('engine')})")
        log(f"        -> Network Download Time : {t_download:.3f} s")
        log(f"        -> Total Turnaround Time : {t_remote_total:.3f} s")
        log(f"        -> Speedup Factor (S)    : {speedup:.2f}x")
        log(f"        -> Compute Speedup       : {compute_speedup:.2f}x")
        log(f"        -> Network Overhead      : {overhead_pct:.1f}% ({t_net_overhead:.3f} s)")

        benchmark_records.append({
            "configuration": cfg["name"],
            "resolution": cfg["res"],
            "bitrate": cfg["bitrate"],
            "t_local_sec": round(t_local, 3),
            "t_upload_sec": round(t_upload, 3),
            "t_remote_compute_sec": round(t_remote_compute, 3),
            "t_download_sec": round(t_download, 3),
            "t_remote_total_sec": round(t_remote_total, 3),
            "network_overhead_sec": round(t_net_overhead, 3),
            "network_overhead_pct": round(overhead_pct, 1),
            "speedup_factor": round(speedup, 2),
            "compute_speedup": round(compute_speedup, 2),
            "checksum_verified": remote_res["checksum_verified"],
            "engine": remote_res.get("engine", "Remote Node")
        })

    client.disconnect()

    avg_speedup = sum(r["speedup_factor"] for r in benchmark_records) / len(benchmark_records)
    avg_overhead = sum(r["network_overhead_pct"] for r in benchmark_records) / len(benchmark_records)

    summary_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "worker_hostname": worker_info.get("hostname"),
        "worker_acceleration": worker_info.get("nvenc_status"),
        "latency_rtt_ms": latency_ms,
        "average_speedup": round(avg_speedup, 2),
        "average_network_overhead_pct": round(avg_overhead, 1),
        "records": benchmark_records
    }

    # Save to JSON
    json_path = os.path.join(benchmark_dir, "benchmark_data.json")
    with open(json_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    log(f"[*] Benchmark data saved to: {json_path}")

    # Generate charts
    try:
        from lab4.benchmarks.generate_benchmark_plots import generate_plots_from_data
        generate_plots_from_data(summary_data, output_dir=benchmark_dir)
        log(f"[*] High-resolution comparison plots saved to {benchmark_dir}")
    except Exception as e:
        log(f"[!] Plot generation warning: {e}")

    return summary_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSC-334: Local vs Remote GPU Offloading Benchmark")
    parser.add_argument("--host", default="127.0.0.1", help="Remote Worker IP")
    parser.add_argument("--port", type=int, default=5000, help="Remote Worker Port")
    args = parser.parse_args()

    run_comparative_benchmark(worker_host=args.host, worker_port=args.port)
