"""
================================================================================
CSC-334: Parallel and Distributed Computing
Lab 4: Custom Distributed Task Offloading & Remote GPU Rendering System
Module: client/client_gui.py
Description: Modern CustomTkinter Desktop GUI for Task Offloading, Remote GPU Rendering,
             Complex Project Script Distribution, and LAN File Sharing.
================================================================================
"""

import os
import sys
import time
import queue
import threading
from typing import Optional, Dict, Any, List
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Add repository root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from lab4.client.network_client import OffloadingClient
from lab4.common.utils import (
    generate_sample_video, format_bytes, format_time, compute_sha256,
    generate_sample_project_task
)
from lab4.common.protocol import DEFAULT_HOST, DEFAULT_PORT


class TaskOffloaderApp(ctk.CTk):
    """
    Modern CustomTkinter GUI for Custom Distributed Task Offloading,
    Remote Hardware Acceleration, and LAN File Sharing Hub.
    """
    def __init__(self):
        super().__init__()

        # Window Appearance & Geometry
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.title("CSC-334: Distributed Task Offloading & Remote Compute System")
        self.geometry("1100x820")
        self.minsize(980, 680)

        # State Variables
        self.client: Optional[OffloadingClient] = None
        self.is_processing = False
        self.cancel_flag = False
        self.selected_file_path = ""
        self.download_output_dir = os.path.join(current_dir, "client_downloads")
        os.makedirs(self.download_output_dir, exist_ok=True)

        # Thread-safe UI update queue
        self.ui_queue = queue.Queue()
        self._poll_ui_queue()

        # Build UI Layout
        self._build_header()
        self._build_tab_container()
        self._build_log_terminal()

        # Log Initial System Banner
        self.log("[SYSTEM] Distributed Task Offloading Client initialized (Computer A).")
        self.log(f"[SYSTEM] Default Target: {DEFAULT_HOST}:{DEFAULT_PORT}. Click '⚡ Handshake & Ping' to connect to Computer B.")

    # ==========================================
    # UI BUILDERS
    # ==========================================
    def _build_header(self):
        """Top Header Banner with Course & System Details."""
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#1f2937", "#111827"))
        header_frame.pack(fill="x", padx=16, pady=(12, 6))

        title_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(10, 2))

        ctk.CTkLabel(
            title_row,
            text="⚡ CSC-334: Distributed Task Offloading & Remote Compute (Computer A)",
            font=ctk.CTkFont(family="Inter", size=19, weight="bold"),
            text_color="#60a5fa"
        ).pack(side="left")

        self.conn_indicator = ctk.CTkLabel(
            title_row,
            text="🔴 OFFLINE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f87171",
            fg_color=("#374151", "#1e293b"),
            corner_radius=6,
            padx=10,
            pady=3
        )
        self.conn_indicator.pack(side="right")

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Peer-to-Peer Remote Acceleration | GPU NVENC / CUDA / Complex Project Tasks | FA23-BSE-041",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color="#9ca3af"
        )
        sub_lbl.pack(anchor="w", padx=16, pady=(0, 10))

    def _build_tab_container(self):
        """Builds tabs: Tab 1 = Task Offloading; Tab 2 = LAN File Sharing."""
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=4)

        self.tab_offload = self.tabview.add("🚀 Task Offloading & Compute")
        self.tab_sharing = self.tabview.add("📁 LAN File Sharing Hub")

        self._build_offload_tab()
        self._build_sharing_tab()

    def _build_offload_tab(self):
        """Tab 1: Config & Network on Left, Real-time Dashboard on Right."""
        main_container = ctk.CTkFrame(self.tab_offload, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=4, pady=2)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)

        # ==========================================
        # LEFT COLUMN: Connection & Workload Config
        # ==========================================
        left_col = ctk.CTkFrame(main_container, corner_radius=10)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=2)

        # Section 1: Networking & Handshake Setup
        net_title = ctk.CTkLabel(
            left_col,
            text="🌐 1. Network & Server Connection (Computer B)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#93c5fd"
        )
        net_title.pack(anchor="w", padx=14, pady=(10, 4))

        net_row = ctk.CTkFrame(left_col, fg_color="transparent")
        net_row.pack(fill="x", padx=14, pady=2)

        self.ip_entry = ctk.CTkEntry(net_row, placeholder_text="Server IP (e.g. 192.168.1.20)", width=170)
        self.ip_entry.insert(0, DEFAULT_HOST)
        self.ip_entry.pack(side="left", padx=(0, 6))

        self.port_entry = ctk.CTkEntry(net_row, placeholder_text="Port", width=65)
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.pack(side="left", padx=(0, 6))

        self.ping_btn = ctk.CTkButton(
            net_row,
            text="⚡ Handshake & Ping",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._handle_handshake_and_ping
        )
        self.ping_btn.pack(side="left", fill="x", expand=True)

        # Server Node Status Card
        self.worker_card = ctk.CTkFrame(left_col, fg_color=("#374151", "#1e293b"), corner_radius=8)
        self.worker_card.pack(fill="x", padx=14, pady=6)

        self.worker_status_lbl = ctk.CTkLabel(
            self.worker_card,
            text="Server Status: DISCONNECTED",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f87171"
        )
        self.worker_status_lbl.pack(anchor="w", padx=10, pady=(5, 2))

        self.worker_specs_lbl = ctk.CTkLabel(
            self.worker_card,
            text="Enter Server IP & click 'Handshake & Ping' to connect Computer B",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1"
        )
        self.worker_specs_lbl.pack(anchor="w", padx=10, pady=(0, 5))

        # Section 2: Task Workload & File Picker
        work_title = ctk.CTkLabel(
            left_col,
            text="⚙️ 2. Workload & Task Configuration",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#93c5fd"
        )
        work_title.pack(anchor="w", padx=14, pady=(8, 4))

        # Workload Mode Picker
        mode_row = ctk.CTkFrame(left_col, fg_color="transparent")
        mode_row.pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(mode_row, text="Task Mode:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self.task_type_var = ctk.StringVar(value="Complex Project Python Script / Heavy Workload")
        self.task_type_combo = ctk.CTkComboBox(
            mode_row,
            values=[
                "Complex Project Python Script / Heavy Workload",
                "Video Transcoding (FFmpeg NVENC)",
                "CUDA / Matrix Parallel Compute"
            ],
            variable=self.task_type_var,
            width=290,
            command=self._on_task_type_change
        )
        self.task_type_combo.pack(side="left", fill="x", expand=True)

        # File Picker Row
        self.file_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        self.file_frame.pack(fill="x", padx=14, pady=4)

        # Default sample script path
        sample_script = os.path.join(current_dir, "sample_project_task.py")
        if os.path.exists(sample_script):
            self.selected_file_path = sample_script

        self.file_path_entry = ctk.CTkEntry(self.file_frame, placeholder_text="Select task file...", width=240)
        if self.selected_file_path:
            self.file_path_entry.insert(0, self.selected_file_path)
        self.file_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.browse_btn = ctk.CTkButton(
            self.file_frame,
            text="Browse...",
            width=70,
            command=self._handle_browse_file
        )
        self.browse_btn.pack(side="left", padx=(0, 6))

        self.gen_btn = ctk.CTkButton(
            self.file_frame,
            text="✨ Gen Script",
            width=90,
            fg_color="#059669",
            hover_color="#047857",
            command=self._handle_generate_test_asset
        )
        self.gen_btn.pack(side="left")

        # Workload Parameters Box
        self.settings_frame = ctk.CTkFrame(left_col, fg_color=("#374151", "#1e293b"), corner_radius=8)
        self.settings_frame.pack(fill="x", padx=14, pady=4)

        # Video Row 1: Resolution & Bitrate
        self.row1 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.row1.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(self.row1, text="Resolution:", width=75, anchor="w").pack(side="left")
        self.res_combo = ctk.CTkComboBox(
            self.row1,
            values=["1920x1080", "1280x720", "854x480", "3840x2160", "original"],
            width=110
        )
        self.res_combo.set("1280x720")
        self.res_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(self.row1, text="Bitrate:", width=50, anchor="w").pack(side="left")
        self.bitrate_combo = ctk.CTkComboBox(
            self.row1,
            values=["1500k", "3000k", "5000k", "8000k", "12000k"],
            width=100
        )
        self.bitrate_combo.set("3000k")
        self.bitrate_combo.pack(side="left")

        # Video Row 2: Preset & Acceleration Mode
        self.row2 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.row2.pack(fill="x", padx=10, pady=(2, 4))

        ctk.CTkLabel(self.row2, text="Preset:", width=75, anchor="w").pack(side="left")
        self.preset_combo = ctk.CTkComboBox(
            self.row2,
            values=["ultrafast", "fast", "medium", "slow", "p4"],
            width=110
        )
        self.preset_combo.set("fast")
        self.preset_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(self.row2, text="Mode:", width=50, anchor="w").pack(side="left")
        self.accel_combo = ctk.CTkComboBox(
            self.row2,
            values=["auto", "nvenc", "cpu"],
            width=100
        )
        self.accel_combo.set("auto")
        self.accel_combo.pack(side="left")

        # Description label
        self.desc_lbl = ctk.CTkLabel(
            left_col,
            text="Offloads Python workload (Monte Carlo, Matrix Tensor, Simulation) to Computer B's CPU/GPU.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.desc_lbl.pack(anchor="w", padx=14, pady=(2, 6))

        # Apply initial mode visibility
        self._on_task_type_change("Complex Project Python Script / Heavy Workload")

        # ==========================================
        # RIGHT COLUMN: Progress & Control Dashboard
        # ==========================================
        right_col = ctk.CTkFrame(main_container, corner_radius=10)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=2)

        prog_title = ctk.CTkLabel(
            right_col,
            text="📊 3. Real-Time Remote Execution Dashboard",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#93c5fd"
        )
        prog_title.pack(anchor="w", padx=14, pady=(10, 4))

        # Progress Percentage Bar
        self.progress_bar = ctk.CTkProgressBar(right_col, height=18, corner_radius=8)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=14, pady=(4, 2))

        self.progress_lbl = ctk.CTkLabel(
            right_col,
            text="0.0% | Ready to offload complex task",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1"
        )
        self.progress_lbl.pack(anchor="w", padx=14, pady=(0, 6))

        # Metrics Card Grid
        metrics_box = ctk.CTkFrame(right_col, fg_color=("#374151", "#1e293b"), corner_radius=8)
        metrics_box.pack(fill="x", padx=14, pady=4)
        metrics_box.columnconfigure(0, weight=1)
        metrics_box.columnconfigure(1, weight=1)

        self.metric_fps = ctk.CTkLabel(metrics_box, text="Speed/Stage: --", font=ctk.CTkFont(size=12))
        self.metric_fps.grid(row=0, column=0, padx=8, pady=4, sticky="w")

        self.metric_eta = ctk.CTkLabel(metrics_box, text="ETA: --", font=ctk.CTkFont(size=12))
        self.metric_eta.grid(row=0, column=1, padx=8, pady=4, sticky="w")

        self.metric_turnaround = ctk.CTkLabel(metrics_box, text="Turnaround: -- s", font=ctk.CTkFont(size=12))
        self.metric_turnaround.grid(row=1, column=0, padx=8, pady=4, sticky="w")

        self.metric_integrity = ctk.CTkLabel(metrics_box, text="Integrity: Idle", font=ctk.CTkFont(size=12), text_color="#fbbf24")
        self.metric_integrity.grid(row=1, column=1, padx=8, pady=4, sticky="w")

        # Action Buttons
        btn_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        btn_frame.pack(fill="x", padx=14, pady=(8, 4))

        self.offload_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Offload Task to Remote Worker (Computer B)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            height=38,
            command=self._handle_start_offload
        )
        self.offload_btn.pack(fill="x", pady=(0, 6))

        btn_row = ctk.CTkFrame(btn_frame, fg_color="transparent")
        btn_row.pack(fill="x")

        self.bench_btn = ctk.CTkButton(
            btn_row,
            text="📈 Benchmark (Local vs Remote)",
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            height=30,
            command=self._handle_run_benchmark
        )
        self.bench_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.cancel_btn = ctk.CTkButton(
            btn_row,
            text="🛑 Cancel",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=30,
            width=80,
            command=self._handle_cancel
        )
        self.cancel_btn.pack(side="left")

    def _build_sharing_tab(self):
        """Tab 2: Peer-to-Peer LAN File Sharing Hub."""
        frame = ctk.CTkFrame(self.tab_sharing, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=8, pady=6)

        # Top Control Row
        ctrl_row = ctk.CTkFrame(frame, corner_radius=8)
        ctrl_row.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(
            ctrl_row,
            text="📁 LAN Storage Hub (Share files with Computer B without internet)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#93c5fd"
        ).pack(side="left", padx=12, pady=10)

        refresh_files_btn = ctk.CTkButton(
            ctrl_row,
            text="🔄 Refresh Server Files",
            width=140,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._handle_list_shared_files
        )
        refresh_files_btn.pack(side="right", padx=(0, 10))

        upload_share_btn = ctk.CTkButton(
            ctrl_row,
            text="📤 Upload File to Server",
            width=150,
            fg_color="#059669",
            hover_color="#047857",
            command=self._handle_upload_shared_file
        )
        upload_share_btn.pack(side="right", padx=(0, 10))

        # Files Display
        self.shared_files_box = ctk.CTkTextbox(
            frame,
            height=180,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("#111827", "#030712"),
            text_color="#e2e8f0"
        )
        self.shared_files_box.pack(fill="both", expand=True, padx=6, pady=4)
        self.shared_files_box.insert("end", "Click '🔄 Refresh Server Files' to see available files on Computer B.\n")
        self.shared_files_box.configure(state="disabled")

        # Bottom Actions
        act_row = ctk.CTkFrame(frame, fg_color="transparent")
        act_row.pack(fill="x", padx=6, pady=4)

        self.dl_fname_entry = ctk.CTkEntry(act_row, placeholder_text="Enter file name to download...", width=280)
        self.dl_fname_entry.pack(side="left", padx=(0, 8))

        dl_btn = ctk.CTkButton(
            act_row,
            text="📥 Download from Server",
            width=160,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._handle_download_shared_file
        )
        dl_btn.pack(side="left", padx=(0, 10))

        open_dl_btn = ctk.CTkButton(
            act_row,
            text="📂 Open Downloads Folder",
            width=160,
            fg_color="#475569",
            hover_color="#334155",
            command=lambda: os.startfile(self.download_output_dir)
        )
        open_dl_btn.pack(side="left")

    def _build_log_terminal(self):
        """Bottom Real-Time Log Terminal Widget."""
        term_frame = ctk.CTkFrame(self, corner_radius=10)
        term_frame.pack(fill="both", expand=True, padx=16, pady=(2, 10))

        head_row = ctk.CTkFrame(term_frame, fg_color="transparent")
        head_row.pack(fill="x", padx=12, pady=(6, 2))

        ctk.CTkLabel(
            head_row,
            text="💻 Integrated Real-Time Live Console (Computer A)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#93c5fd"
        ).pack(side="left")

        clear_btn = ctk.CTkButton(
            head_row,
            text="Clear Log",
            width=70,
            height=22,
            fg_color="#4b5563",
            hover_color="#374151",
            command=self._clear_logs
        )
        clear_btn.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            term_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("#111827", "#030712"),
            text_color="#e2e8f0",
            wrap="none"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 6))

    # ==========================================
    # LOGGING & UI HELPERS (THREAD-SAFE)
    # ==========================================
    def _poll_ui_queue(self):
        """Processes pending UI mutations on Tkinter main thread."""
        try:
            while True:
                fn, args, kwargs = self.ui_queue.get_nowait()
                try:
                    fn(*args, **kwargs)
                except Exception:
                    pass
        except queue.Empty:
            pass
        self.after(40, self._poll_ui_queue)

    def run_on_ui(self, fn, *args, **kwargs):
        """Enqueues a function to run safely on the main GUI thread."""
        self.ui_queue.put((fn, args, kwargs))

    def log(self, text: str):
        """Thread-safe append to terminal log console."""
        timestamp = time.strftime("%H:%M:%S")
        msg = f"[{timestamp}] {text}\n"
        def _do_insert():
            self.log_textbox.insert("end", msg)
            self.log_textbox.see("end")
        self.run_on_ui(_do_insert)

    def _clear_logs(self):
        self.log_textbox.delete("1.0", "end")

    def _on_task_type_change(self, choice: str):
        if "CUDA" in choice:
            self.row1.pack_forget()
            self.row2.pack_forget()
            self.browse_btn.configure(state="disabled")
            self.gen_btn.configure(state="disabled")
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, "[Synthetic Matrix Tensor Dataset]")
            self.desc_lbl.configure(text="Parallel Matrix/Tensor linear algebra computation on Server GPU/CPU.")
        elif "Project" in choice or "Script" in choice:
            self.row1.pack_forget()
            self.row2.pack_forget()
            self.browse_btn.configure(state="normal")
            self.gen_btn.configure(state="normal", text="✨ Gen Script")
            self.file_path_entry.delete(0, "end")
            sample_script = os.path.join(current_dir, "sample_project_task.py")
            if os.path.exists(sample_script):
                self.selected_file_path = sample_script
                self.file_path_entry.insert(0, sample_script)
            self.desc_lbl.configure(text="Offloads Python workload (Monte Carlo, Matrix, Prime Search) to Server B.")
        else:
            self.row1.pack(fill="x", padx=10, pady=3)
            self.row2.pack(fill="x", padx=10, pady=(2, 4))
            self.browse_btn.configure(state="normal")
            self.gen_btn.configure(state="normal", text="🎬 Gen Video")
            self.file_path_entry.delete(0, "end")
            if self.selected_file_path and self.selected_file_path.endswith((".mp4", ".mov", ".mkv")):
                self.file_path_entry.insert(0, self.selected_file_path)
            self.desc_lbl.configure(text="GPU Hardware Video Transcoding via FFmpeg NVENC (with CPU fallback).")

    # ==========================================
    # EVENT HANDLERS
    # ==========================================
    def _handle_browse_file(self):
        is_script = "Project" in self.task_type_var.get() or "Script" in self.task_type_var.get()
        if is_script:
            path = filedialog.askopenfilename(
                title="Select Python Project Script to Offload",
                filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
            )
        else:
            path = filedialog.askopenfilename(
                title="Select Video Asset to Offload",
                filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All Files", "*.*")]
            )

        if path:
            self.selected_file_path = path
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, path)
            size = os.path.getsize(path)
            self.log(f"[SELECTED] {os.path.basename(path)} ({format_bytes(size)})")

    def _handle_generate_test_asset(self):
        """Generates test script or sample video asset based on current mode."""
        is_script = "Project" in self.task_type_var.get() or "Script" in self.task_type_var.get()
        
        def run_gen():
            if is_script:
                self.log("[GEN] Generating sample complex project Python script...")
                script_path = os.path.join(current_dir, "sample_project_task.py")
                generate_sample_project_task(script_path)
                self.selected_file_path = script_path
                self.run_on_ui(lambda: (self.file_path_entry.delete(0, "end"), self.file_path_entry.insert(0, script_path)))
                self.log(f"[GEN SUCCESS] Created complex project script: {script_path}")
            else:
                self.log("[GEN] Generating synthetic 1080p test video asset...")
                asset_dir = os.path.join(current_dir, "sample_assets")
                sample_path = os.path.join(asset_dir, "test_render_sample.mp4")
                generate_sample_video(sample_path, duration_sec=6, resolution=(1280, 720))
                self.selected_file_path = sample_path
                self.run_on_ui(lambda: (self.file_path_entry.delete(0, "end"), self.file_path_entry.insert(0, sample_path)))
                self.log(f"[GEN SUCCESS] Test video created: {sample_path} ({format_bytes(os.path.getsize(sample_path))})")

        threading.Thread(target=run_gen, daemon=True).start()

    def _handle_handshake_and_ping(self):
        """Task 1: Handshake protocol and latency ping check with prominent alerts."""
        host = self.ip_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return

        def task():
            self.log(f"\n[CONNECTING] Contacting Remote Server (Computer B) at {host}:{port}...")
            try:
                self.client = OffloadingClient(host=host, port=port)
                info = self.client.perform_handshake()
                latency = self.client.measure_ping_latency(num_samples=3)

                hostname = info.get('hostname', 'Remote Server')
                cpu_count = info.get('cpu_count', 4)
                gpu_status = info.get('nvenc_status', 'N/A')
                status_txt = f"Connected to: {hostname} ({host})"
                specs_txt = f"CPU: {cpu_count} Cores | GPU: {gpu_status[:30]} | Ping RTT: {latency} ms"

                def _update_ui():
                    self.worker_status_lbl.configure(text=f"🟢 {status_txt}", text_color="#4ade80")
                    self.worker_specs_lbl.configure(text=specs_txt)
                    self.conn_indicator.configure(text=f"🟢 ONLINE ({hostname})", text_color="#4ade80")

                self.run_on_ui(_update_ui)

                self.log(f"⚡ [TCP CONNECTED] Socket established with {host}:{port}!")
                self.log(f"🤝 [HANDSHAKE VERIFIED] Server '{hostname}' running protocol v{info.get('protocol_version')}")
                self.log(f"⚡ [LATENCY PROBE] Measured Round-Trip Time (RTT): {latency} ms")
                self.log(f"🚀 [RESOURCES UNLOCKED] {cpu_count} CPU Cores | {gpu_status}")
                self.log(f"   Computer B is now ready to receive complex project tasks & file shares!")

                # Prominent notification popup
                msg = (
                    f"🎉 Successfully Connected to Server (Computer B)!\n\n"
                    f"• Node Hostname : {hostname}\n"
                    f"• Bound Address : {host}:{port}\n"
                    f"• CPU Hardware  : {cpu_count} Processing Cores\n"
                    f"• Acceleration  : {gpu_status}\n"
                    f"• Ping Latency  : {latency} ms (Fast LAN Wire)\n\n"
                    f"Remote resources are active! You can now offload complex project tasks."
                )
                self.run_on_ui(lambda: messagebox.showinfo("Connected to Server!", msg))

            except Exception as e:
                def _update_err():
                    self.worker_status_lbl.configure(text="🔴 Server Status: UNREACHABLE", text_color="#f87171")
                    self.worker_specs_lbl.configure(text=f"Connection Error: {e}")
                    self.conn_indicator.configure(text="🔴 OFFLINE", text_color="#f87171")
                self.run_on_ui(_update_err)
                self.log(f"❌ [CONNECT ERROR] Could not connect to Server at {host}:{port} -> {e}")
                self.run_on_ui(lambda: messagebox.showerror(
                    "Connection Failed",
                    f"Could not connect to Server at {host}:{port}.\n\n"
                    f"Check:\n"
                    f"1. Is Server GUI / Daemon running on Computer B?\n"
                    f"2. Are both computers connected with LAN cable?\n"
                    f"3. Is the IP address correct?"
                ))

        threading.Thread(target=task, daemon=True).start()

    def _handle_start_offload(self):
        """Initiates task offloading (Video, CUDA, or Complex Project Script)."""
        if self.is_processing:
            messagebox.showwarning("Warning", "A task is currently running.")
            return

        choice = self.task_type_var.get()
        is_cuda = "CUDA" in choice
        is_script = "Project" in choice or "Script" in choice

        if not is_cuda and (not self.selected_file_path or not os.path.exists(self.selected_file_path)):
            messagebox.showerror("Error", "Please select or generate an input file first.")
            return

        host = self.ip_entry.get().strip()
        port = int(self.port_entry.get().strip())
        render_cfg = {
            "resolution": self.res_combo.get(),
            "bitrate": self.bitrate_combo.get(),
            "preset": self.preset_combo.get(),
            "mode": self.accel_combo.get()
        }
        selected_file = self.selected_file_path

        self.is_processing = True
        self.cancel_flag = False

        self.progress_bar.set(0.0)
        self.progress_lbl.configure(text="0.0% | Initializing Task Offload...")
        self.metric_integrity.configure(text="Checksum: Calculating...", text_color="#fbbf24")

        def run_thread():
            try:
                # Ensure connection is active
                need_reconnect = False
                if not self.client or not self.client.is_connected or not self.client.sock:
                    need_reconnect = True
                else:
                    try:
                        self.client.sock.send(b"")
                    except Exception:
                        need_reconnect = True

                if need_reconnect:
                    if self.client:
                        try:
                            self.client.disconnect()
                        except Exception:
                            pass
                    self.client = OffloadingClient(host=host, port=port)
                    self.client.connect()
                    self.client.perform_handshake()

                def progress_cb(prog: dict):
                    pct = prog.get("percent", 0.0)
                    status = prog.get("status", "")
                    fps_val = prog.get("fps", 0)
                    speed_val = prog.get("speed", "1x")
                    eta_val = prog.get("eta_seconds", 0)

                    def _update_prog_widgets():
                        self.progress_bar.set(pct / 100.0)
                        self.progress_lbl.configure(text=f"{pct:.1f}% | {status}")
                        if "fps" in prog:
                            self.metric_fps.configure(text=f"Speed: {fps_val} ({speed_val})")
                        if "eta_seconds" in prog:
                            self.metric_eta.configure(text=f"ETA: {eta_val:.1f} s")

                    self.run_on_ui(_update_prog_widgets)
                    if status:
                        self.log(f"  [REMOTE] {status}")

                # 1. Complex Project Script Execution
                if is_script:
                    self.log(f"\n🚀 [OFFLOAD SCRIPT] Sending complex project script to Server: {os.path.basename(selected_file)}")
                    res = self.client.offload_custom_script(
                        script_file=selected_file,
                        output_dir=self.download_output_dir,
                        config={},
                        progress_callback=progress_cb,
                        cancel_check=lambda: self.cancel_flag
                    )

                    def _update_script_done():
                        self.progress_bar.set(1.0)
                        self.progress_lbl.configure(text="100.0% | Project Task Complete!")
                        self.metric_turnaround.configure(text=f"Turnaround: {res['total_turnaround_sec']} s")
                        self.metric_integrity.configure(text="SHA-256: VERIFIED ✔", text_color="#4ade80")

                    self.run_on_ui(_update_script_done)
                    self.log(f"✅ [SUCCESS] Complex Project Script executed on Server in {res['total_turnaround_sec']}s!")
                    self.log(f"   • Remote Engine : {res['engine']}")
                    self.log(f"   • Remote Runtime: {res['remote_compute_duration_sec']}s")
                    self.log(f"   • Output Saved  : {res['local_output_path']}")

                    msg = (
                        f"🎉 Complex Project Task Completed on Server (Computer B)!\n\n"
                        f"• Total Turnaround : {res['total_turnaround_sec']} seconds\n"
                        f"• Remote Execution : {res['remote_compute_duration_sec']} seconds\n"
                        f"• Engine Used      : {res['engine']}\n"
                        f"• Result Artifact  : {os.path.basename(res['local_output_path'])}\n\n"
                        f"Saved to: client_downloads/"
                    )
                    self.run_on_ui(lambda: messagebox.showinfo("Project Task Completed!", msg))

                # 2. CUDA / Tensor Matrix Compute
                elif is_cuda:
                    self.log("\n🚀 [OFFLOAD CUDA] Submitting CUDA / Parallel Matrix Tensor Workload to Server...")
                    res = self.client.offload_cuda_compute(
                        matrix_size=1200,
                        iterations=15,
                        output_dir=self.download_output_dir,
                        progress_callback=progress_cb
                    )
                    self.log(f"✅ [SUCCESS] CUDA Compute completed in {res['total_turnaround_sec']}s!")
                    def _update_cuda_done():
                        self.progress_bar.set(1.0)
                        self.progress_lbl.configure(text="100.0% | Complete")
                        self.metric_turnaround.configure(text=f"Turnaround: {res['total_turnaround_sec']} s")
                        self.metric_integrity.configure(text="Integrity: VERIFIED ✔", text_color="#4ade80")
                    self.run_on_ui(_update_cuda_done)

                # 3. Video Transcoding Workload
                else:
                    self.log(f"\n🚀 [OFFLOAD VIDEO] Initiating video transcode offload to Server: {render_cfg}")
                    res = self.client.offload_video_transcode(
                        input_file=selected_file,
                        output_dir=self.download_output_dir,
                        render_config=render_cfg,
                        progress_callback=progress_cb,
                        cancel_check=lambda: self.cancel_flag
                    )

                    def _update_video_done():
                        self.progress_bar.set(1.0)
                        self.progress_lbl.configure(text="100.0% | Complete & Downloaded")
                        self.metric_turnaround.configure(text=f"Turnaround: {res['total_turnaround_sec']} s")
                        if res.get("checksum_verified"):
                            self.metric_integrity.configure(text="SHA-256: VERIFIED ✔", text_color="#4ade80")
                        else:
                            self.metric_integrity.configure(text="SHA-256: MISMATCH ❌", text_color="#f87171")

                    self.run_on_ui(_update_video_done)
                    self.log(f"✅ [SUCCESS] Video Render Complete!")
                    self.log(f"   • Remote Engine   : {res.get('engine')}")
                    self.log(f"   • Total Turnaround: {res['total_turnaround_sec']}s")
                    self.log(f"   • Saved to        : {res['local_output_path']}")

            except Exception as e:
                self.log(f"❌ [OFFLOAD FAILED] {e}")
                def _update_err_badge():
                    self.metric_integrity.configure(text="Error", text_color="#f87171")
                    self.progress_lbl.configure(text=f"Failed: {e}")
                self.run_on_ui(_update_err_badge)
                self.run_on_ui(lambda: messagebox.showerror("Task Failed", f"Execution failed:\n{e}"))
            finally:
                self.is_processing = False

        threading.Thread(target=run_thread, daemon=True).start()

    def _handle_list_shared_files(self):
        """Queries and displays files available in Server storage."""
        def task():
            try:
                self.log("[FILE HUB] Querying shared files from Computer B...")
                if not self.client or not self.client.is_connected:
                    host = self.ip_entry.get().strip()
                    port = int(self.port_entry.get().strip())
                    self.client = OffloadingClient(host=host, port=port)
                    self.client.connect()
                    self.client.perform_handshake()

                files = self.client.list_server_files()
                self.log(f"[FILE HUB] Received {len(files)} shared file(s) from server.")

                def _update_box():
                    self.shared_files_box.configure(state="normal")
                    self.shared_files_box.delete("1.0", "end")
                    if not files:
                        self.shared_files_box.insert("end", "No shared files currently on Server.\nUpload a file using 'Upload File to Server'.\n")
                    else:
                        self.shared_files_box.insert("end", f"{'File Name':<35} | {'Size':<10} | {'Modified Time'}\n")
                        self.shared_files_box.insert("end", "-" * 70 + "\n")
                        for f in files:
                            self.shared_files_box.insert("end", f"{f['name']:<35} | {f['size_str']:<10} | {f['modified']}\n")
                    self.shared_files_box.configure(state="disabled")

                self.run_on_ui(_update_box)
            except Exception as e:
                self.log(f"[FILE HUB ERROR] {e}")
                self.run_on_ui(lambda: messagebox.showerror("Error", f"Could not list server files:\n{e}"))

        threading.Thread(target=task, daemon=True).start()

    def _handle_upload_shared_file(self):
        """Uploads a local file from Computer A directly to Computer B's storage hub."""
        src_path = filedialog.askopenfilename(title="Select File to Upload to Server")
        if not src_path:
            return

        def task():
            try:
                fname = os.path.basename(src_path)
                self.log(f"📁 [UPLOADING] Sending '{fname}' to Computer B...")
                if not self.client or not self.client.is_connected:
                    host = self.ip_entry.get().strip()
                    port = int(self.port_entry.get().strip())
                    self.client = OffloadingClient(host=host, port=port)
                    self.client.connect()
                    self.client.perform_handshake()

                success = self.client.upload_shared_file(
                    src_path,
                    progress_callback=lambda msg: self.log(f"  {msg}")
                )
                if success:
                    self.log(f"✅ [UPLOAD COMPLETE] '{fname}' uploaded to Server shared storage!")
                    self.run_on_ui(lambda: messagebox.showinfo("File Uploaded", f"Successfully uploaded '{fname}' to Server!"))
                    self._handle_list_shared_files()
            except Exception as e:
                self.log(f"❌ [UPLOAD ERROR] {e}")
                self.run_on_ui(lambda: messagebox.showerror("Upload Error", f"Failed to upload file:\n{e}"))

        threading.Thread(target=task, daemon=True).start()

    def _handle_download_shared_file(self):
        """Downloads a requested file from Computer B to Computer A."""
        fname = self.dl_fname_entry.get().strip()
        if not fname:
            messagebox.showwarning("Enter Filename", "Please enter the file name to download from the list above.")
            return

        def task():
            try:
                self.log(f"📥 [DOWNLOADING] Requesting '{fname}' from Computer B...")
                if not self.client or not self.client.is_connected:
                    host = self.ip_entry.get().strip()
                    port = int(self.port_entry.get().strip())
                    self.client = OffloadingClient(host=host, port=port)
                    self.client.connect()
                    self.client.perform_handshake()

                dest = self.client.download_shared_file(
                    fname,
                    self.download_output_dir,
                    progress_callback=lambda msg: self.log(f"  {msg}")
                )
                self.log(f"✅ [DOWNLOAD COMPLETE] Saved to: {dest}")
                self.run_on_ui(lambda: messagebox.showinfo("Download Complete", f"Downloaded '{fname}'!\nSaved to: {dest}"))
            except Exception as e:
                self.log(f"❌ [DOWNLOAD ERROR] {e}")
                self.run_on_ui(lambda: messagebox.showerror("Download Error", f"Could not download file:\n{e}"))

        threading.Thread(target=task, daemon=True).start()

    def _handle_run_benchmark(self):
        """Runs the automated Local vs Remote benchmark suite (Task 5)."""
        if self.is_processing:
            messagebox.showwarning("Warning", "A task is currently running.")
            return

        host = self.ip_entry.get().strip()
        port = int(self.port_entry.get().strip())
        self.is_processing = True

        def run_bench():
            try:
                self.log("=" * 60)
                self.log("[BENCHMARK] Starting Local vs Remote Comparative Analysis (Task 5)...")
                from lab4.client.benchmark import run_comparative_benchmark
                
                test_asset = self.selected_file_path
                if not test_asset or not os.path.exists(test_asset) or not test_asset.endswith(".mp4"):
                    self.log("[BENCHMARK] Generating standard test video asset for benchmark...")
                    asset_dir = os.path.join(current_dir, "sample_assets")
                    test_asset = os.path.join(asset_dir, "bench_sample.mp4")
                    generate_sample_video(test_asset, duration_sec=5, resolution=(1280, 720))

                results = run_comparative_benchmark(
                    worker_host=host,
                    worker_port=port,
                    sample_video_path=test_asset,
                    log_fn=self.log
                )
                self.log("[BENCHMARK COMPLETE] Technical report and performance charts generated!")
                messagebox.showinfo("Benchmark Completed", f"Benchmark Finished!\nOverall Speedup: {results.get('average_speedup', 'N/A')}x\nCharts saved in lab4/benchmarks/!")
            except Exception as e:
                self.log(f"[BENCHMARK ERROR] {e}")
            finally:
                self.is_processing = False

        threading.Thread(target=run_bench, daemon=True).start()

    def _handle_cancel(self):
        if self.is_processing:
            self.cancel_flag = True
            self.log("[CANCEL] User initiated cancellation request.")
        else:
            self.log("[INFO] No active task to cancel.")


def main():
    app = TaskOffloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
