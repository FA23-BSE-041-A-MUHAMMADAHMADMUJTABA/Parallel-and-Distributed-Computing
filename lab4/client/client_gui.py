"""
================================================================================
CSC-334: Parallel and Distributed Computing
Lab 4: Custom Distributed Task Offloading & Remote GPU Rendering System
Module: client/client_gui.py
Description: Modern CustomTkinter Desktop GUI for Task Offloading & Remote GPU Rendering.
================================================================================
"""

import os
import sys
import time
import queue
import threading
from typing import Optional
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Add repository root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from lab4.client.network_client import OffloadingClient
from lab4.common.utils import generate_sample_video, format_bytes, format_time, compute_sha256
from lab4.common.protocol import DEFAULT_HOST, DEFAULT_PORT


class TaskOffloaderApp(ctk.CTk):
    """
    Modern CustomTkinter GUI for Custom Distributed Task Offloading
    and Remote GPU Rendering System.
    """
    def __init__(self):
        super().__init__()

        # Window Appearance & Geometry
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.title("CSC-334: Distributed Task Offloading & Remote GPU Rendering System")
        self.geometry("1060x750")
        self.minsize(960, 650)

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
        self._build_main_grid()
        self._build_log_terminal()

        # Log Initial System Banner
        self.log("[SYSTEM] Distributed Task Offloading Client initialized.")
        self.log(f"[SYSTEM] Default Target: {DEFAULT_HOST}:{DEFAULT_PORT}. Click 'Handshake & Ping' to connect.")

    def _build_header(self):
        """Top Header Banner with Course & System Details."""
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#1f2937", "#111827"))
        header_frame.pack(fill="x", padx=16, pady=(12, 8))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="⚡ CSC-334: Distributed Task Offloading & Remote GPU Rendering",
            font=ctk.CTkFont(family="Inter", size=19, weight="bold"),
            text_color="#60a5fa"
        )
        title_lbl.pack(anchor="w", padx=16, pady=(10, 2))

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Peer-to-Peer Remote Acceleration | FFmpeg NVENC / CUDA GPU Daemon | FA23-BSE-041",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color="#9ca3af"
        )
        sub_lbl.pack(anchor="w", padx=16, pady=(0, 10))

    def _build_main_grid(self):
        """Builds two columns: Left (Config & Network) and Right (Progress & Actions)."""
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=16, pady=4)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)

        # ==========================================
        # LEFT COLUMN: Connection & Workload Config
        # ==========================================
        left_col = ctk.CTkFrame(main_container, corner_radius=10)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=4)

        # Section 1: Networking & Handshake Setup (Task 1)
        net_title = ctk.CTkLabel(
            left_col,
            text="🌐 1. Network & Remote Worker Setup",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#93c5fd"
        )
        net_title.pack(anchor="w", padx=14, pady=(12, 6))

        net_row = ctk.CTkFrame(left_col, fg_color="transparent")
        net_row.pack(fill="x", padx=14, pady=4)

        self.ip_entry = ctk.CTkEntry(net_row, placeholder_text="Worker IP", width=140)
        self.ip_entry.insert(0, DEFAULT_HOST)
        self.ip_entry.pack(side="left", padx=(0, 6))

        self.port_entry = ctk.CTkEntry(net_row, placeholder_text="Port", width=70)
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

        # Worker Node Status Card
        self.worker_card = ctk.CTkFrame(left_col, fg_color=("#374151", "#1e293b"), corner_radius=8)
        self.worker_card.pack(fill="x", padx=14, pady=8)

        self.worker_status_lbl = ctk.CTkLabel(
            self.worker_card,
            text="Worker Status: DISCONNECTED",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f87171"
        )
        self.worker_status_lbl.pack(anchor="w", padx=10, pady=(6, 2))

        self.worker_specs_lbl = ctk.CTkLabel(
            self.worker_card,
            text="Capabilities: Unknown | Latency: -- ms",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1"
        )
        self.worker_specs_lbl.pack(anchor="w", padx=10, pady=(0, 6))

        # Section 2: Task Workload & File Picker (Task 2 & 3)
        work_title = ctk.CTkLabel(
            left_col,
            text="⚙️ 2. Workload & Render Configuration",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#93c5fd"
        )
        work_title.pack(anchor="w", padx=14, pady=(12, 6))

        # Workload Mode Picker
        mode_row = ctk.CTkFrame(left_col, fg_color="transparent")
        mode_row.pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(mode_row, text="Task Mode:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self.task_type_var = ctk.StringVar(value="Video Transcoding (FFmpeg NVENC)")
        self.task_type_combo = ctk.CTkComboBox(
            mode_row,
            values=["Video Transcoding (FFmpeg NVENC)", "CUDA / Matrix Parallel Compute"],
            variable=self.task_type_var,
            width=260,
            command=self._on_task_type_change
        )
        self.task_type_combo.pack(side="left", fill="x", expand=True)

        # File Picker Row
        self.file_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        self.file_frame.pack(fill="x", padx=14, pady=6)

        self.file_path_entry = ctk.CTkEntry(self.file_frame, placeholder_text="No file selected...", width=260)
        self.file_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.browse_btn = ctk.CTkButton(
            self.file_frame,
            text="Browse...",
            width=80,
            command=self._handle_browse_file
        )
        self.browse_btn.pack(side="left", padx=(0, 6))

        self.gen_btn = ctk.CTkButton(
            self.file_frame,
            text="🎬 Gen Asset",
            width=86,
            fg_color="#059669",
            hover_color="#047857",
            command=self._handle_generate_test_asset
        )
        self.gen_btn.pack(side="left")

        # Render Parameters Grid
        self.settings_frame = ctk.CTkFrame(left_col, fg_color=("#374151", "#1e293b"), corner_radius=8)
        self.settings_frame.pack(fill="x", padx=14, pady=6)

        # Resolution & Bitrate
        row1 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(row1, text="Resolution:", width=75, anchor="w").pack(side="left")
        self.res_combo = ctk.CTkComboBox(
            row1,
            values=["1920x1080", "1280x720", "854x480", "3840x2160", "original"],
            width=120
        )
        self.res_combo.set("1280x720")
        self.res_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row1, text="Bitrate:", width=50, anchor="w").pack(side="left")
        self.bitrate_combo = ctk.CTkComboBox(
            row1,
            values=["1500k", "3000k", "5000k", "8000k", "12000k"],
            width=100
        )
        self.bitrate_combo.set("3000k")
        self.bitrate_combo.pack(side="left")

        # Preset & Acceleration Mode
        row2 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(2, 6))

        ctk.CTkLabel(row2, text="Preset:", width=75, anchor="w").pack(side="left")
        self.preset_combo = ctk.CTkComboBox(
            row2,
            values=["ultrafast", "fast", "medium", "slow", "p4"],
            width=120
        )
        self.preset_combo.set("fast")
        self.preset_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row2, text="Mode:", width=50, anchor="w").pack(side="left")
        self.accel_combo = ctk.CTkComboBox(
            row2,
            values=["auto", "nvenc", "cpu"],
            width=100
        )
        self.accel_combo.set("auto")
        self.accel_combo.pack(side="left")

        # ==========================================
        # RIGHT COLUMN: Progress & Control Dashboard
        # ==========================================
        right_col = ctk.CTkFrame(main_container, corner_radius=10)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=4)

        prog_title = ctk.CTkLabel(
            right_col,
            text="📊 3. Real-Time Execution Dashboard",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#93c5fd"
        )
        prog_title.pack(anchor="w", padx=14, pady=(12, 6))

        # Progress Percentage Bar
        self.progress_bar = ctk.CTkProgressBar(right_col, height=18, corner_radius=8)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=14, pady=(6, 2))

        self.progress_lbl = ctk.CTkLabel(
            right_col,
            text="0.0% | Ready for offloading",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1"
        )
        self.progress_lbl.pack(anchor="w", padx=14, pady=(0, 8))

        # Metrics Card Grid
        metrics_box = ctk.CTkFrame(right_col, fg_color=("#374151", "#1e293b"), corner_radius=8)
        metrics_box.pack(fill="x", padx=14, pady=6)
        metrics_box.columnconfigure(0, weight=1)
        metrics_box.columnconfigure(1, weight=1)

        self.metric_fps = ctk.CTkLabel(metrics_box, text="Speed: -- fps (1.0x)", font=ctk.CTkFont(size=12))
        self.metric_fps.grid(row=0, column=0, padx=8, pady=6, sticky="w")

        self.metric_eta = ctk.CTkLabel(metrics_box, text="ETA: -- s", font=ctk.CTkFont(size=12))
        self.metric_eta.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        self.metric_turnaround = ctk.CTkLabel(metrics_box, text="Turnaround: -- s", font=ctk.CTkFont(size=12))
        self.metric_turnaround.grid(row=1, column=0, padx=8, pady=6, sticky="w")

        self.metric_integrity = ctk.CTkLabel(metrics_box, text="Integrity: Pending", font=ctk.CTkFont(size=12), text_color="#fbbf24")
        self.metric_integrity.grid(row=1, column=1, padx=8, pady=6, sticky="w")

        # Action Buttons
        btn_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        btn_frame.pack(fill="x", padx=14, pady=(12, 6))

        self.offload_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Offload Task to Remote Worker",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            height=40,
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
            height=32,
            command=self._handle_run_benchmark
        )
        self.bench_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.cancel_btn = ctk.CTkButton(
            btn_row,
            text="🛑 Cancel",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=32,
            width=80,
            command=self._handle_cancel
        )
        self.cancel_btn.pack(side="left")

    def _build_log_terminal(self):
        """Bottom Real-Time Log Terminal Widget (Task 3)."""
        term_frame = ctk.CTkFrame(self, corner_radius=10)
        term_frame.pack(fill="both", expand=True, padx=16, pady=(4, 14))

        head_row = ctk.CTkFrame(term_frame, fg_color="transparent")
        head_row.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            head_row,
            text="💻 Integrated Real-Time Log Console",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#93c5fd"
        ).pack(side="left")

        clear_btn = ctk.CTkButton(
            head_row,
            text="Clear Log",
            width=70,
            height=24,
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
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    # ==========================================
    # LOGGING & UI HELPERS (THREAD-SAFE)
    # ==========================================
    def _poll_ui_queue(self):
        """Processes pending UI mutations on Tkinter main event thread."""
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
            self.res_combo.configure(state="disabled")
            self.bitrate_combo.configure(state="disabled")
            self.preset_combo.configure(state="disabled")
            self.browse_btn.configure(state="disabled")
            self.gen_btn.configure(state="disabled")
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, "[Synthetic Matrix Tensor Dataset]")
        else:
            self.res_combo.configure(state="normal")
            self.bitrate_combo.configure(state="normal")
            self.preset_combo.configure(state="normal")
            self.browse_btn.configure(state="normal")
            self.gen_btn.configure(state="normal")
            self.file_path_entry.delete(0, "end")
            if self.selected_file_path:
                self.file_path_entry.insert(0, self.selected_file_path)

    # ==========================================
    # EVENT HANDLERS
    # ==========================================
    def _handle_browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Video Asset to Offload",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All Files", "*.*")]
        )
        if path:
            self.selected_file_path = path
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, path)
            size = os.path.getsize(path)
            self.log(f"[ASSET] Selected: {os.path.basename(path)} ({format_bytes(size)})")

    def _handle_generate_test_asset(self):
        """Generates a synthetic 1080p sample video for instant testing."""
        def run_gen():
            self.log("[GEN] Generating synthetic 1080p test video asset...")
            asset_dir = os.path.join(current_dir, "sample_assets")
            sample_path = os.path.join(asset_dir, "test_render_sample.mp4")
            generate_sample_video(sample_path, duration_sec=6, resolution=(1280, 720))
            self.selected_file_path = sample_path
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, sample_path)
            self.log(f"[GEN SUCCESS] Test video created: {sample_path} ({format_bytes(os.path.getsize(sample_path))})")

        threading.Thread(target=run_gen, daemon=True).start()

    def _handle_handshake_and_ping(self):
        """Task 1: Handshake protocol and latency ping check."""
        host = self.ip_entry.get().strip()
        port = int(self.port_entry.get().strip())

        def task():
            self.log(f"[HANDSHAKE] Contacting Remote Worker at {host}:{port}...")
            try:
                self.client = OffloadingClient(host=host, port=port)
                info = self.client.perform_handshake()
                latency = self.client.measure_ping_latency(num_samples=3)

                status_txt = f"Worker: ONLINE ({info.get('hostname')})"
                specs_txt = f"OS: {info.get('os')} | CPU: {info.get('cpu_count')} Cores | GPU: {info.get('nvenc_status')[:32]} | RTT: {latency} ms"

                def _update_ui():
                    self.worker_status_lbl.configure(text=status_txt, text_color="#4ade80")
                    self.worker_specs_lbl.configure(text=specs_txt)

                self.run_on_ui(_update_ui)

                self.log(f"[HANDSHAKE SUCCESS] Protocol v{info.get('protocol_version')} confirmed.")
                self.log(f"[NET LATENCY] Measured Round-Trip Time (RTT): {latency} ms")
                self.log(f"[WORKER SPECS] Host: {info.get('hostname')} | Acceleration: {info.get('nvenc_status')}")
            except Exception as e:
                def _update_err():
                    self.worker_status_lbl.configure(text="Worker: OFFLINE / UNREACHABLE", text_color="#f87171")
                    self.worker_specs_lbl.configure(text=f"Error: {e}")
                self.run_on_ui(_update_err)
                self.log(f"[ERROR] Handshake failed: {e}")

        threading.Thread(target=task, daemon=True).start()

    def _handle_start_offload(self):
        """Initiates task offloading in a background worker thread."""
        if self.is_processing:
            messagebox.showwarning("Warning", "A task is currently running.")
            return

        is_cuda = "CUDA" in self.task_type_var.get()
        if not is_cuda and (not self.selected_file_path or not os.path.exists(self.selected_file_path)):
            messagebox.showerror("Error", "Please select or generate an input video asset first.")
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
        self.metric_integrity.configure(text="Integrity: Computing Checksum...", text_color="#fbbf24")

        def run_thread():
            try:
                # Ensure connection is alive and healthy
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
                            self.metric_fps.configure(text=f"Speed: {fps_val} fps ({speed_val})")
                        if "eta_seconds" in prog:
                            self.metric_eta.configure(text=f"ETA: {eta_val:.1f} s")

                    self.run_on_ui(_update_prog_widgets)

                    if status and ("Rendering" in status or "Computing" in status):
                        self.log(f"  [STREAM] {status} (FPS: {fps_val}, Speed: {speed_val})")

                if is_cuda:
                    self.log("[OFFLOAD] Submitting CUDA / Parallel Matrix Compute Job...")
                    res = self.client.offload_cuda_compute(
                        matrix_size=1200,
                        iterations=15,
                        output_dir=self.download_output_dir,
                        progress_callback=progress_cb
                    )
                    self.log(f"[SUCCESS] CUDA Compute completed in {res['total_turnaround_sec']}s!")
                    def _update_cuda_done():
                        self.metric_turnaround.configure(text=f"Turnaround: {res['total_turnaround_sec']} s")
                        self.metric_integrity.configure(text="Compute Integrity: VERIFIED", text_color="#4ade80")
                    self.run_on_ui(_update_cuda_done)
                else:
                    self.log(f"[OFFLOAD] Initiating video transcode offload: {render_cfg}")
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

                    if res.get("checksum_verified"):
                        self.log(f"[VERIFIED] SHA-256 Checksum: {res['output_sha256'][:16]}... matched perfectly!")
                    else:
                        self.log("[ALERT] SHA-256 Checksum mismatch on downloaded asset!")

                    self.log(f"[OFFLOAD METRICS]")
                    self.log(f"  • Remote Engine    : {res.get('engine')}")
                    self.log(f"  • Upload Duration  : {res['upload_duration_sec']}s")
                    self.log(f"  • Remote Compute   : {res['remote_compute_duration_sec']}s")
                    self.log(f"  • Download Duration: {res['download_duration_sec']}s")
                    self.log(f"  • Network Overhead : {res['network_overhead_sec']}s")
                    self.log(f"  • Total Turnaround : {res['total_turnaround_sec']}s")
                    self.log(f"  • Saved Result To  : {res['local_output_path']}")

            except Exception as e:
                self.log(f"[OFFLOAD FAILED] {e}")
                def _update_err_badge():
                    self.metric_integrity.configure(text="Error", text_color="#f87171")
                self.run_on_ui(_update_err_badge)
            finally:
                self.is_processing = False

        threading.Thread(target=run_thread, daemon=True).start()

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
                
                # Use current file or generate one
                test_asset = self.selected_file_path
                if not test_asset or not os.path.exists(test_asset):
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
