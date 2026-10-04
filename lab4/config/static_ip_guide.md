# 🌐 Static IP & Peer-to-Peer LAN / Wi-Fi Configuration Guide

> **Course**: CSC-334: Parallel and Distributed Computing  
> **Lab Module**: Lab 04 — Task Offloading & Remote GPU Rendering System  
> **Author**: Muhammad Ahmad Mujtaba (FA23-BSE-041)

---

## 📌 1. Overview & Network Topology

In a distributed task-offloading architecture, predictable network latency and direct addressability are essential. This guide explains how to establish a direct, high-bandwidth connection between the **Resource-Constrained Client Laptop** and the **Remote Worker GPU Node**.

```text
+-----------------------+                         +-----------------------+
|     CLIENT LAPTOP     |                         |  REMOTE WORKER NODE   |
| (CustomTkinter GUI)   |                         |  (FFmpeg NVENC / CUDA)|
|                       |  Direct CAT6 Ethernet   |                       |
| Static IP:            | <=====================> | Static IP:            |
|    192.168.1.2        |  or Dedicated Wi-Fi     |    192.168.1.1        |
| Subnet: 255.255.255.0 |                         | Subnet: 255.255.255.0 |
| Gateway: 192.168.1.1  |                         | Listening Port: 5000  |
+-----------------------+                         +-----------------------+
```

---

## 🔌 2. Physical Connection Options

1. **Direct Peer-to-Peer Ethernet Cable (Recommended)**:
   - Connect an RJ-45 Cat5e/Cat6 patch cable directly between the Ethernet ports of both computers.
   - Modern Gigabit Network Interface Cards (NICs) support **Auto-MDIX**, which automatically eliminates the need for special crossover cables.
   - Bandwidth: **1000 Mbps (1 Gbps) Full Duplex** — delivers ultra-low latency (< 0.5 ms) and maximum file transfer throughput.

2. **Dedicated Wi-Fi Subnet / Mobile Hotspot**:
   - Both machines connect to the same Wi-Fi router or one laptop broadcasts a Windows Mobile Hotspot.
   - Bandwidth: 50–300 Mbps, Latency: ~2–8 ms.

---

## 🖥️ 3. Windows Configuration (Step-by-Step)

### A. Configuring the Server (Remote Worker Node)
1. Press `Win + R`, type `ncpa.cpl`, and press **Enter** (opens Network Connections).
2. Right-click your Ethernet adapter (or Wi-Fi adapter) and select **Properties**.
3. Highlight **Internet Protocol Version 4 (TCP/IPv4)** and click **Properties**.
4. Choose **"Use the following IP address"**:
   - **IP address**: `192.168.1.1`
   - **Subnet mask**: `255.255.255.0`
   - **Default gateway**: *Leave empty* (or `192.168.1.1`)
5. Click **OK**, then **Close**.

### B. Configuring the Client Laptop
1. Follow the same steps (`Win + R` -> `ncpa.cpl`).
2. Right-click the Client's Ethernet / Wi-Fi adapter -> **Properties** -> **IPv4 Properties**.
3. Choose **"Use the following IP address"**:
   - **IP address**: `192.168.1.2`
   - **Subnet mask**: `255.255.255.0`
   - **Default gateway**: `192.168.1.1`
4. Click **OK**, then **Close**.

---

## 🛡️ 4. Windows Firewall Configuration (Port 5000)

By default, Windows Defender Firewall may block unsolicited inbound connections on port 5000. Run the following command in an **Elevated PowerShell** (Run as Administrator) on the **Server Node**:

```powershell
New-NetFirewallRule -DisplayName "CSC334_GPU_Worker_Port5000" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

Alternatively, allow Python through the firewall via Windows Security settings.

---

## 🐧 5. Linux / Ubuntu Server Configuration (Optional)

If your remote worker node runs Ubuntu or Debian:

```bash
# Assign static IP to interface (e.g. eth0 or enp3s0)
sudo ip addr add 192.168.1.1/24 dev eth0
sudo ip link set dev eth0 up

# Allow port 5000 in UFW firewall
sudo ufw allow 5000/tcp
```

---

## 🔍 6. Connection Verification & Ping Test

Before launching the GUI application, test network connectivity from the client's terminal:

```cmd
ping 192.168.1.1
```

**Expected Successful Output**:
```text
Pinging 192.168.1.1 with 32 bytes of data:
Reply from 192.168.1.1: bytes=32 time<1ms TTL=128
Reply from 192.168.1.1: bytes=32 time<1ms TTL=128
Reply from 192.168.1.1: bytes=32 time<1ms TTL=128

Ping statistics for 192.168.1.1:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 0ms, Maximum = 0ms, Average = 0ms
```

Once ping succeeds, launch the **Remote Worker Daemon** on the server, open the **Client GUI** on the laptop, enter `192.168.1.1`, and click **"Handshake & Ping"**!
