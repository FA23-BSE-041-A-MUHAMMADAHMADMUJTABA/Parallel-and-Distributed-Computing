# 🚀 Parallel and Distributed Computing (CSC-334)

<p align="center">
  <img src="https://img.shields.io/badge/Course-CSC--334%20Parallel%20%26%20Distributed%20Computing-blue?style=for-the-badge&logo=codeforces" alt="Course Badge"/>
  <img src="https://img.shields.io/badge/Language-Python%203.x-yellow?style=for-the-badge&logo=python" alt="Python Badge"/>
  <img src="https://img.shields.io/badge/Networking-TCP%20%2F%20IP%20Sockets-brightgreen?style=for-the-badge&logo=wireshark" alt="Sockets Badge"/>
  <img src="https://img.shields.io/badge/Concurrency-Multi--Threading-orange?style=for-the-badge&logo=speedtest" alt="Concurrency Badge"/>
</p>

---

## 👨‍💻 Student Profile

| Field | Details |
| :--- | :--- |
| **Student Name** | **Muhammad Ahmad Mujtaba** |
| **Registration No** | **FA23-BSE-041** |
| **Class & Section** | **BSE 7A (Software Engineering)** |
| **Department** | **Computer Science & Software Engineering** |
| **Course Title** | **Parallel and Distributed Computing (CSC-334)** |
| **Instructor / Lab Manual** | SP24 Version 2.0 |

---

## 📖 Repository Overview

This repository contains the practical laboratory implementations, conceptual guides, and execution traces for **Parallel and Distributed Computing (CSC-334)**. The labs focus on low-level network communication, socket architecture, concurrent programming, and synchronization mechanisms using Python.

---

## 🗂️ Lab Modules & Index

| Lab | Title & Focus | Key Concepts & Techniques | Directory | Status |
| :---: | :--- | :--- | :---: | :---: |
| **Lab 02** | **Socket Programming: Variable-Length Framing** | • TCP Byte-Stream Nature<br>• Head-of-Line Blocking Solution<br>• Length-Prefix Framing (`zfill(3)`)<br>• Custom `recvall()` implementation | [📂 `lab2/`](./lab2/) | ✅ Completed |
| **Lab 03** | **Multi-Threaded TCP Server & Client** | • Multi-Threading via `threading.Thread`<br>• Simultaneous Multi-Client Handling<br>• Thread Synchronization (`threading.Lock`)<br>• Explicit `acquire()` & `release()`<br>• Real-time Thread/IP/Port Terminal Output | [📂 `lab3/`](./lab3/) | ✅ Completed |
| **Lab 04** | **Custom Distributed Task Offloading & Remote GPU Rendering** | • Peer-to-Peer LAN / Wi-Fi Offloading<br>• Binary+JSON Socket Protocol & Ping Check<br>• FFmpeg NVENC (GPU) & CUDA Compute Daemon<br>• CustomTkinter Desktop Client GUI<br>• Real-Time Progress Streaming & SHA-256 Verification<br>• Empirical Benchmarking, Speedup & Overhead Analysis | [📂 `lab4/`](./lab4/) | ✅ Completed (100/100) |

---

## 🔬 Lab Highlights

### 🔹 [Lab 02: Variable Length Message Framing](./lab2/)
- **Problem**: Solved the default 16-character fixed-length buffer limitation in naive TCP sockets.
- **Framing Protocol**: Implemented a 3-digit length prefix header using `.zfill(3)` allowing payload sizes up to 255 bytes.
- **Reliable Reception**: Engineered a `recvall()` function to guarantee exact byte reception across variable chunk arrivals.

### 🔹 [Lab 03: Multi-Threaded TCP Server with Synchronization](./lab3/)
- **Architecture**: Decoupled the **Main Listener Thread** from connection handling by dynamically spawning a dedicated **Worker Thread** for each incoming client.
- **Synchronization & Mutex**: Utilized `threading.Lock()` with explicit `.acquire()` and `.release()` in `safe_print()` and state management routines to eliminate race conditions.
- **Continuous Two-Way Exchange**: Enabled persistent, interactive duplex communication with graceful shutdown upon receiving termination signals (`exit`/`quit`).
- **Live Output Trace & Verification**: Complete terminal output screenshots included demonstrating concurrent multi-client sessions.

### 🔹 [Lab 04: Custom Distributed Task Offloading & Remote GPU Rendering](./lab4/)
- **Task 1: Networking & Handshake Setup (20 Marks)**: Peer-to-peer static IP configuration (`192.168.1.1` server, `192.168.1.2` client), framed handshake protocol (`MAGIC = b"DC"`), server capability discovery (CPU/GPU/NVENC), and real-time RTT latency ping probe.
- **Task 2: Remote GPU Execution Engine Daemon (25 Marks)**: Background worker daemon executing FFmpeg NVENC hardware acceleration (`-c:v h264_nvenc`) with intelligent CPU multi-threading fallback (`libx264`) and CUDA / NumPy parallel matrix tensor compute workloads.
- **Task 3: Client Desktop GUI Application (25 Marks)**: Modern CustomTkinter dark-mode desktop interface featuring IP configuration, real-time connection status card, video asset picker & synthetic HD generator, customizable render parameters (Resolution, Bitrate, Preset, Mode), and integrated live log console.
- **Task 4: Real-Time Progress Tracking & Network Robustness (15 Marks)**: Real-time asynchronous streaming of transcode progress (percentage, FPS, speed multiplier, ETA), 64KB chunked file streaming, and end-to-end SHA-256 cryptographic checksum integrity verification.
- **Task 5: Performance Benchmarking & Analysis Report (15 Marks)**: Automated comparative suite measuring local vs remote offloading across 480p, 720p, and 1080p, computing speedup factors ($S > 5.2\times$), network overhead ($\eta_{net} \approx 26.8\%$), and generating publication-quality analytical plots.

#### 🎬 Lab 04 Live Execution Demonstration
<p align="center">
  <img src="./lab4/ss/demo.gif" alt="Lab 04 Live Execution Demo" width="850"/>
</p>
<p align="center">
  <i>Real-Time Distributed Task Offloading: Handshake, Asset Upload, Progress Streaming, Remote Transcoding, Download & SHA-256 Verification (<a href="./lab4/ss/demo.mp4">Watch Full HD Video</a>)</i>
</p>

---

## 📂 Project Directory Structure

```text
Parallel-and-Distributed-Computing/
│
├── CSC-334_ P&DC_Lab manual_SP24_V2.0.pdf   # Official Course Lab Manual
├── README.md                                # Root Repository Documentation
│
├── lab2/                                    # Lab 02: Socket Variable-Length Framing
│   ├── TCPserver.py                         # Length-Prefix Frame Receiver Server
│   ├── TCPclient.py                         # Length-Padded Message Sender Client
│   ├── task1_client_length_padding.py       # Task 1 sub-module
│   ├── task2_client_prep_msg.py             # Task 2 sub-module
│   ├── task3_client_send.py                 # Task 3 sub-module
│   ├── task4_server_receive.py              # Task 4 sub-module
│   ├── concept_and_working.txt              # In-depth Roman Urdu & English Guide
│   ├── screenshot_server_output.png         # Terminal Output Screenshot
│   └── screenshot_client_output.png         # Terminal Output Screenshot
│
├── lab3/                                    # Lab 03: Multi-Threaded Socket Server
│   ├── server.py                            # Multi-Threaded TCP Server with Locks
│   ├── client.py                            # Interactive Continuous TCP Client
│   ├── concept.txt                          # Concise Concepts Guide (Roman Urdu)
│   ├── working.txt                          # Line-by-Line Code & Architecture Guide
│   ├── ss/                                  # Output Terminal Screenshots
│   │   ├── server.PNG                       # Server Multi-Client Terminal Log
│   │   ├── client1.PNG                      # Client 1 Interactive Session
│   │   └── client2.PNG                      # Client 2 Concurrent Session
│   └── README.md                            # Lab 03 Detailed Report & Screenshots
│
└── lab4/                                    # Lab 04: Custom Distributed Task Offloading & Remote GPU Rendering (100 Marks)
    ├── README.md                            # Lab 04 Master Documentation & Architecture Guide
    ├── concept.txt                          # Concise Concepts & Architecture Guide (Roman Urdu & English)
    ├── working.txt                          # Line-by-Line Code & Module Working Guide
    ├── requirements.txt                     # Dependencies (customtkinter, opencv, matplotlib)
    ├── client/                              # Client Desktop Application Subsystem
    │   ├── client_gui.py                    # CustomTkinter Modern Desktop GUI
    │   ├── network_client.py                # Client Socket Layer, Handshake, Streamer & Checksum
    │   └── benchmark.py                     # Local vs Remote Performance Benchmarking Suite
    ├── server/                              # Server Worker Daemon Subsystem
    │   ├── server_daemon.py                 # Remote Worker Daemon Entrypoint
    │   ├── network_server.py                # Multi-Threaded Socket Listener & Progress Streamer
    │   ├── execution_engine.py              # FFmpeg NVENC GPU & Parallel Matrix Compute Engine
    │   └── task_queue.py                    # Thread-Safe Task Queue Manager
    ├── common/                              # Shared Protocol & Network Utilities
    │   ├── protocol.py                      # Framed Binary+JSON Protocol (Magic Bytes 'DC')
    │   └── utils.py                         # SHA-256 Hasher, System Capability Prober & Video Gen
    ├── config/                              # Network Topology & Guides
    │   ├── network_config.json              # Static IP & Buffer Specifications
    │   └── static_ip_guide.md               # Peer-to-Peer LAN / Wi-Fi Configuration Guide
    ├── ss/                                  # Live Execution Screenshots & Real Demo Recordings
    │   ├── demo.mp4                         # Full High-Definition Live System Execution Video
    │   ├── demo.gif                         # Animated Live Demonstration Preview GIF
    │   ├── client_gui_initial.PNG           # Client GUI Launch Window (Disconnected)
    │   ├── client_gui_handshake.PNG         # Worker Online, Latency Ping & Spec Discovery
    │   ├── client_gui_progress.PNG          # Real-Time Progress Streaming (FPS, Speed & ETA)
    │   ├── client_gui_completed.PNG         # Finished Offload & SHA-256 Verified Badge
    │   └── server_terminal_execution.PNG    # Remote Server Daemon Terminal Execution Trace
    └── benchmarks/                          # Benchmarking Data & Visual Analysis
        ├── benchmark_report.md              # Formal Technical Performance Analysis Report
        ├── generate_benchmark_plots.py      # Matplotlib Analytical Chart Generator
        ├── benchmark_data.json              # Empirical Benchmarking Records
        ├── benchmark_execution_time.png     # Chart 1: Turnaround Time Comparison
        └── benchmark_speedup_overhead.png   # Chart 2: Speedup vs Network Overhead
```

---

## ⚙️ Quick Start & Execution

### Prerequisites
- Python 3.8+ installed ([python.org](https://www.python.org/))
- For Lab 04 dependencies:
  ```bash
  pip install -r lab4/requirements.txt
  ```

---

### 1. Running Lab 04 (Distributed Task Offloading & Remote GPU Rendering)

#### Step A: Launch the Remote Worker Daemon (Server Node)
```bash
python lab4/server/server_daemon.py --host 0.0.0.0 --port 5000
```

#### Step B: Launch the Client Desktop GUI (Client Laptop)
```bash
python lab4/client/client_gui.py
```
- Click **"⚡ Handshake & Ping"** to verify connection and inspect remote hardware specs.
- Click **"🎬 Gen Asset"** to generate an HD test video (or browse your own video).
- Click **"🚀 Offload Task to Remote Worker"** to stream the job, view real-time progress percentages, and download verified output.
- Click **"📈 Benchmark (Local vs Remote)"** to run the comparative performance suite.

---

### 2. Running Lab 03 (Multi-Threaded Server & Concurrent Clients)
1. **Start the Multi-Threaded Server:**
   ```bash
   cd lab3
   python server.py
   ```
2. **Launch First Client (Terminal 2):**
   ```bash
   cd lab3
   python client.py
   ```
3. **Launch Second Client (Terminal 3):**
   ```bash
   cd lab3
   python client.py
   ```

---

## 🛠️ Technologies & Concepts

- **Programming Language:** Python 3.13
- **Network Protocol:** TCP/IP (Transmission Control Protocol, `SOCK_STREAM`), Custom Framed Binary+JSON Protocol
- **Concurrency Model:** Multi-Threading (`threading.Thread`), Thread-Safe Queues (`queue.Queue`)
- **Synchronization Primitives:** Mutex Locks (`threading.Lock`, `.acquire()`, `.release()`)
- **GPU Acceleration:** FFmpeg NVENC (`h264_nvenc`), CUDA / High-Performance Parallel BLAS Matrix Compute
- **Integrity Validation:** SHA-256 End-to-End Cryptographic Checksums
- **Client GUI:** CustomTkinter (Modern Dark-Mode Desktop GUI)
- **Benchmarking & Visualization:** Matplotlib, NumPy, Empirical Amdahl Scaling Analysis
- **Operating Systems:** Windows / POSIX Compliant Sockets

---

## 👥 Instructor Collaborator Requirement
As required by the assignment guidelines, the following instructor email account has been added as a collaborator:
- **Collaborator:** `githubprojectmin@gmail.com`

---

<p align="center">
  <i>Developed for CSC-334: Parallel and Distributed Computing • Department of Computer Science & Software Engineering</i>
</p>