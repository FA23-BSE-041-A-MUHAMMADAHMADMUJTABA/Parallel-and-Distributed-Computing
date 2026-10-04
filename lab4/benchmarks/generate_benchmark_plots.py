"""
================================================================================
CSC-334: Parallel and Distributed Computing
Lab 4: Custom Distributed Task Offloading & Remote GPU Rendering System
Module: benchmarks/generate_benchmark_plots.py
Description: Generates publication-quality charts for Task 5 Performance Analysis.
================================================================================
"""

import os
import sys
import json
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for automated image saving
import matplotlib.pyplot as plt
import numpy as np


def generate_plots_from_data(data: dict, output_dir: str):
    """
    Renders two high-resolution analytical plots:
    1. Execution Time Breakdown (Local vs Remote Stacks)
    2. Speedup Factor & Network Overhead vs Resolution
    """
    os.makedirs(output_dir, exist_ok=True)
    records = data["records"]

    labels = [r["configuration"] for r in records]
    t_local = [r["t_local_sec"] for r in records]
    t_upload = [r["t_upload_sec"] for r in records]
    t_compute = [r["t_remote_compute_sec"] for r in records]
    t_download = [r["t_download_sec"] for r in records]
    t_remote_total = [r["t_remote_total_sec"] for r in records]
    speedups = [r["speedup_factor"] for r in records]
    overheads = [r["network_overhead_pct"] for r in records]

    # Set modern visual style
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.size"] = 10

    # ==========================================================
    # CHART 1: Comparative Execution Time Breakdown (Grouped/Stacked)
    # ==========================================================
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
    x = np.arange(len(labels))
    width = 0.35

    # Bar 1: Local
    bars1 = ax.bar(x - width/2, t_local, width, label="Local Client Execution (T_local)", color="#ef4444", edgecolor="#991b1b")

    # Bar 2: Remote Stacked (Upload + Compute + Download)
    bars_up = ax.bar(x + width/2, t_upload, width, label="Network Upload (T_upload)", color="#3b82f6", edgecolor="#1d4ed8")
    bars_comp = ax.bar(x + width/2, t_compute, width, bottom=t_upload, label="Remote Engine Compute (T_remote)", color="#10b981", edgecolor="#047857")
    bottom_dl = [u + c for u, c in zip(t_upload, t_compute)]
    bars_dl = ax.bar(x + width/2, t_download, width, bottom=bottom_dl, label="Network Download (T_download)", color="#f59e0b", edgecolor="#b45309")

    # Add value labels on top of bars
    for i, v in enumerate(t_local):
        ax.text(i - width/2, v + 0.1, f"{v:.2f}s", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#991b1b")
    for i, v in enumerate(t_remote_total):
        ax.text(i + width/2, v + 0.1, f"{v:.2f}s", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#065f46")

    ax.set_title("CSC-334: Local Client vs Remote Offloading Turnaround Time", fontsize=13, fontweight="bold", pad=14)
    ax.set_xlabel("Workload Resolution / Configuration", fontweight="bold", labelpad=8)
    ax.set_ylabel("Turnaround Time (Seconds) - Lower is Better", fontweight="bold", labelpad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontweight="bold")
    ax.legend(frameon=True, facecolor="#f8fafc", loc="upper left")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    plot1_path = os.path.join(output_dir, "benchmark_execution_time.png")
    plt.tight_layout()
    plt.savefig(plot1_path)
    plt.close()

    # ==========================================================
    # CHART 2: Speedup Factor & Network Overhead Dual Plot
    # ==========================================================
    fig, ax1 = plt.subplots(figsize=(9, 5.5), dpi=300)

    color_speedup = "#8b5cf6"
    color_overhead = "#f97316"

    ax1.set_title("CSC-334: Speedup Factor vs Network Transfer Overhead", fontsize=13, fontweight="bold", pad=14)
    ax1.set_xlabel("Workload Resolution / Configuration", fontweight="bold", labelpad=8)
    ax1.set_ylabel("Speedup Factor (S = T_local / T_remote)", color=color_speedup, fontweight="bold", labelpad=8)
    
    line1 = ax1.plot(labels, speedups, marker="o", markersize=8, linewidth=2.5, color=color_speedup, label="Speedup Factor (x)")
    for i, txt in enumerate(speedups):
        ax1.annotate(f"{txt:.2f}x", (labels[i], speedups[i]), textcoords="offset points", xytext=(0, 10), ha="center", fontweight="bold", color=color_speedup)
    
    ax1.tick_params(axis="y", labelcolor=color_speedup)
    ax1.set_ylim(0, max(speedups) * 1.35 if speedups else 5)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Second axis for Overhead %
    ax2 = ax1.twinx()
    ax2.set_ylabel("Network Overhead (%)", color=color_overhead, fontweight="bold", labelpad=8)
    line2 = ax2.plot(labels, overheads, marker="s", markersize=8, linewidth=2.5, linestyle="--", color=color_overhead, label="Network Overhead (%)")
    for i, txt in enumerate(overheads):
        ax2.annotate(f"{txt:.1f}%", (labels[i], overheads[i]), textcoords="offset points", xytext=(0, -18), ha="center", fontweight="bold", color=color_overhead)
    
    ax2.tick_params(axis="y", labelcolor=color_overhead)
    ax2.set_ylim(0, 100)

    lines = line1 + line2
    labels_legend = [l.get_label() for l in lines]
    ax1.legend(lines, labels_legend, loc="upper right", frameon=True, facecolor="#f8fafc")

    plot2_path = os.path.join(output_dir, "benchmark_speedup_overhead.png")
    plt.tight_layout()
    plt.savefig(plot2_path)
    plt.close()

    return plot1_path, plot2_path


if __name__ == "__main__":
    benchmark_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(benchmark_dir, "benchmark_data.json")

    # Default synthetic sample data if no benchmark run yet
    sample_data = {
        "timestamp": "2026-10-04 15:30:00",
        "worker_hostname": "DESKTOP-WORKER-GPU",
        "worker_acceleration": "NVIDIA NVENC (Hardware Acceleration Active)",
        "latency_rtt_ms": 1.45,
        "average_speedup": 3.85,
        "average_network_overhead_pct": 18.2,
        "records": [
            {
                "configuration": "480p SD",
                "resolution": "854x480",
                "bitrate": "1500k",
                "t_local_sec": 4.82,
                "t_upload_sec": 0.35,
                "t_remote_compute_sec": 1.25,
                "t_download_sec": 0.28,
                "t_remote_total_sec": 1.88,
                "network_overhead_sec": 0.63,
                "network_overhead_pct": 33.5,
                "speedup_factor": 2.56,
                "compute_speedup": 3.86,
                "checksum_verified": True,
                "engine": "NVIDIA NVENC (GPU)"
            },
            {
                "configuration": "720p HD",
                "resolution": "1280x720",
                "bitrate": "3000k",
                "t_local_sec": 9.45,
                "t_upload_sec": 0.42,
                "t_remote_compute_sec": 1.82,
                "t_download_sec": 0.38,
                "t_remote_total_sec": 2.62,
                "network_overhead_sec": 0.80,
                "network_overhead_pct": 30.5,
                "speedup_factor": 3.61,
                "compute_speedup": 5.19,
                "checksum_verified": True,
                "engine": "NVIDIA NVENC (GPU)"
            },
            {
                "configuration": "1080p FHD",
                "resolution": "1920x1080",
                "bitrate": "6000k",
                "t_local_sec": 22.80,
                "t_upload_sec": 0.55,
                "t_remote_compute_sec": 3.20,
                "t_download_sec": 0.62,
                "t_remote_total_sec": 4.37,
                "network_overhead_sec": 1.17,
                "network_overhead_pct": 26.8,
                "speedup_factor": 5.22,
                "compute_speedup": 7.12,
                "checksum_verified": True,
                "engine": "NVIDIA NVENC (GPU)"
            }
        ]
    }

    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            sample_data = json.load(f)

    p1, p2 = generate_plots_from_data(sample_data, benchmark_dir)
    print(f"Generated: {p1}")
    print(f"Generated: {p2}")
