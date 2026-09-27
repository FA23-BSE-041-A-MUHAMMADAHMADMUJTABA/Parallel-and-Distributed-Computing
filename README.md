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
└── lab3/                                    # Lab 03: Multi-Threaded Socket Server
    ├── server.py                            # Multi-Threaded TCP Server with Locks
    ├── client.py                            # Interactive Continuous TCP Client
    ├── concept.txt                          # Concise Concepts Guide (Roman Urdu)
    ├── working.txt                          # Line-by-Line Code & Architecture Guide
    ├── ss/                                  # Output Terminal Screenshots
    │   ├── server.PNG                       # Server Multi-Client Terminal Log
    │   ├── client1.PNG                      # Client 1 Interactive Session
    │   └── client2.PNG                      # Client 2 Concurrent Session
    └── README.md                            # Lab 03 Detailed Report & Screenshots
```

---

## ⚙️ Quick Start & Execution

### Prerequisites
- Python 3.8+ installed ([python.org](https://www.python.org/))
- No external libraries required (built entirely with standard library `socket` and `threading`).

### 1. Clone the Repository
```bash
git clone https://github.com/FA23-BSE-041-A-MUHAMMADAHMADMUJTABA/Parallel-and-Distributed-Computing.git
cd Parallel-and-Distributed-Computing
```

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
*Both clients will be handled concurrently by separate worker threads on the server!*

---

## 🛠️ Technologies & Concepts

- **Programming Language:** Python 3.13
- **Network Protocol:** TCP/IP (Transmission Control Protocol, `SOCK_STREAM`)
- **Concurrency Model:** Multi-Threading (`threading.Thread`)
- **Synchronization Primitives:** Mutex Locks (`threading.Lock`, `.acquire()`, `.release()`)
- **Operating Systems:** Windows / POSIX Compliant Sockets

---

<p align="center">
  <i>Developed for CSC-334: Parallel and Distributed Computing • Department of Computer Science</i>
</p>