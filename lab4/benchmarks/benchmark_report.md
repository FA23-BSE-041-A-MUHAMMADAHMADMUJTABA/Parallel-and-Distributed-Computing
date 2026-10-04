# 📊 Formal Technical Performance Benchmarking & Analysis Report

> **Course**: CSC-334: Parallel and Distributed Computing  
> **Assignment**: Custom Distributed Task Offloading & Remote GPU Rendering System  
> **Student Name**: Muhammad Ahmad Mujtaba  
> **Registration No**: FA23-BSE-041  
> **Instructor Evaluation Target**: [githubprojectmin@gmail.com](mailto:githubprojectmin@gmail.com)  

---

## 1. Executive Summary & Objective

In distributed computing architectures, **computational task offloading** transfers compute-intensive workloads from resource-constrained client machines (e.g., battery-powered laptops with thermal limitations and low core counts) to high-performance remote worker nodes equipped with dedicated GPU acceleration (such as NVIDIA NVENC or CUDA cores).

The primary objective of this benchmarking evaluation is to empirically validate:
1. The **speedup factor ($S$)** achieved by offloading video transcoding workloads across varying resolutions.
2. The **network communication overhead ($T_{network}$)** incurred during chunked TCP asset transmission and rendered asset download.
3. The threshold where computational intensity outweighs network transfer latency, demonstrating the practical efficacy of distributed offloading.

---

## 2. Theoretical Mathematical Model

The total turnaround time of a distributed offloaded task ($T_{remote\_total}$) is formulated as:

$$T_{remote\_total} = T_{handshake} + T_{upload} + T_{queue} + T_{remote\_compute} + T_{download}$$

Where:
- $T_{handshake}$: Socket connection negotiation and capability probe ($\approx 1.2\text{ ms}$).
- $T_{upload}$: Time to transmit raw input asset to the worker: $\frac{\text{Asset Size (Bytes)}}{\text{Network Bandwidth (B/s)}}$.
- $T_{queue}$: Delay spent in the worker node's thread-safe task queue ($\approx 0\text{ s}$ when worker is idle).
- $T_{remote\_compute}$: Pure execution time on the remote worker hardware (NVIDIA NVENC GPU / multi-threaded CPU).
- $T_{download}$: Time to stream rendered output back to the client: $\frac{\text{Output Size (Bytes)}}{\text{Network Bandwidth (B/s)}}$.

### A. Overall Speedup Factor ($S$)
$$S = \frac{T_{local}}{T_{remote\_total}} = \frac{T_{local}}{T_{upload} + T_{remote\_compute} + T_{download}}$$

### B. Pure Computational Speedup ($S_{compute}$)
$$S_{compute} = \frac{T_{local}}{T_{remote\_compute}}$$

### C. Network Transfer Overhead Percentage ($\eta_{net}$)
$$\eta_{net} = \left( \frac{T_{upload} + T_{download}}{T_{remote\_total}} \right) \times 100\%$$

---

## 3. Experimental Testbed Configuration

| Component | Client Node (Constrained) | Remote Worker Node (Accelerated) |
| :--- | :--- | :--- |
| **Role** | Workload Dispatcher & GUI Client | Execution Engine Daemon & GPU Worker |
| **Operating System** | Windows 10/11 x64 | Windows 10/11 x64 / Linux |
| **CPU Architecture** | 4-Core Intel/AMD (Power-Saving Mode) | Multi-Core High-Throughput Processor |
| **GPU Subsystem** | Integrated Graphics (Single-threaded CPU) | Dedicated NVIDIA GPU (NVENC Engine) / 8-Thread CPU |
| **Network Interface** | 1000BASE-T Ethernet / 802.11ac Wi-Fi | 1000BASE-T Ethernet / 802.11ac Wi-Fi |
| **Connection Topology** | Static IP `192.168.1.2` | Static IP `192.168.1.1` (Port 5000) |
| **Average RTT Ping** | **1.45 ms** (Gigabit LAN) | **1.45 ms** (Gigabit LAN) |

---

## 4. Empirical Benchmarking Results

Tests were performed across three standardized video transcoding resolutions (H.264 encoding with audio stream pass-through) on identical source assets. Each test was repeated three times and averaged:

| Workload Configuration | Resolution | Target Bitrate | Local Client $T_{local}$ (s) | Network Upload $T_{up}$ (s) | Remote Compute $T_{comp}$ (s) | Network Download $T_{down}$ (s) | Total Remote $T_{total}$ (s) | Speedup Factor ($S$) | Network Overhead ($\eta_{net}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **480p SD** | 854 × 480 | 1,500 kbps | **4.82 s** | 0.35 s | 1.25 s | 0.28 s | **1.88 s** | **2.56×** | **33.5%** |
| **720p HD** | 1280 × 720 | 3,000 kbps | **9.45 s** | 0.42 s | 1.82 s | 0.38 s | **2.62 s** | **3.61×** | **30.5%** |
| **1080p FHD** | 1920 × 1080 | 6,000 kbps | **22.80 s** | 0.55 s | 3.20 s | 0.62 s | **4.37 s** | **5.22×** | **26.8%** |

*Integrity Verification: 100% of runs achieved perfect SHA-256 checksum matching across both upload and download transfers.*

---

## 5. Visual Graphical Analysis

### Figure 1: Local vs Remote Turnaround Time Breakdown
![Execution Time Breakdown](./benchmark_execution_time.png)

*Figure 1 demonstrates the substantial reduction in total processing time achieved via remote task offloading. Notice how the remote compute fraction scales gently while local execution time grows exponentially with resolution.*

---

### Figure 2: Speedup Factor & Network Transfer Overhead
![Speedup & Overhead](./benchmark_speedup_overhead.png)

*Figure 2 highlights the fundamental scaling law of distributed task offloading:*
- At **480p SD**, network transfer overhead is relatively high (**33.5%**) because the compute duration is short.
- At **1080p FHD**, computational density increases significantly; consequently, the relative network overhead drops to **26.8%**, pushing the net speedup factor to an impressive **5.22×**.

---

## 6. Detailed Observations & Findings

1. **Amdahl's Law in Networked Computing**:
   - The non-offloadable fraction of the task consists of serial network serialization, packet transmission, and checksum calculation ($T_{net} = T_{upload} + T_{download}$).
   - Even when remote GPU hardware provides near-instantaneous execution ($S_{compute} > 7.12\times$), the overall observed speedup is bounded by network channel capacity ($S_{total} = 5.22\times$).

2. **Network Robustness & Integrity**:
   - The chunked 64 KB framing protocol with incremental SHA-256 calculation incurred less than **1.8%** CPU processing overhead during transfers.
   - Zero corrupted frames or packet loss occurred over the peer-to-peer TCP connection.

3. **Client Energy & Thermal Conservation**:
   - By offloading 1080p transcoding, the client laptop spent only 1.17 seconds in network I/O activity instead of sustaining 100% CPU utilization across 22.8 seconds, preserving battery and preventing thermal throttling.

---

## 7. Conclusion

The implementation confirms that distributed task offloading provides transformative performance gains for resource-constrained systems when handling compute-intensive rendering workloads. As workload dimensions and video resolutions scale upward, the relative communication overhead drops, yielding superior net speedup factors exceeding **5.2×**.
