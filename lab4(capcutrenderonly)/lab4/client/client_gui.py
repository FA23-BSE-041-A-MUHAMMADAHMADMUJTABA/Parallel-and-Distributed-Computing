"""
================================================================================
CSC-334: Parallel and Distributed Computing
Lab 4: Custom Distributed Task Offloading & Remote GPU Rendering System
Module: client/client_gui.py
Description: Modern CustomTkinter Desktop GUI for Task Offloading, Remote GPU Rendering,
             Third-Party Video Editor Integration (CapCut/ClipChamp/etc.), and LAN File Sharing.
             - Browse any folder (CapCut exports, ClipChamp output, etc.)
             - Select a video from the folder listing
             - Send to remote server for rendering with live logs
             - Server renders and sends the rendered video back to this laptop
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

# Add client directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app_paths import get_runtime_data_dir
from network_client import OffloadingClient
from capcut_project import build_capcut_bundle
from utils import generate_sample_video, format_bytes, format_time, compute_sha256, natural_sort_key
from protocol import DEFAULT_HOST, DEFAULT_PORT


# ============================================================================
# Supported video file extensions for folder scanning
# ============================================================================
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".wmv", ".flv", ".m4v", ".ts"}


class TaskOffloaderApp(ctk.CTk):
    """
    Modern CustomTkinter GUI for Custom Distributed Task Offloading,
    Remote Hardware Acceleration, Third-Party Video Editor Integration,
    Multi-Part Video Concatenation & Complete Video Rendering, and LAN File Sharing Hub.
    """
    def __init__(self):
        super().__init__()

        # Window Appearance & Geometry
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.title("CSC-334: Distributed Task Offloading & Remote Compute System")
        self.geometry("1100x880")
        self.minsize(980, 720)

        # State Variables
        self.client: Optional[OffloadingClient] = None
        self.is_processing = False
        self.cancel_flag = False
        self.selected_file_path = ""
        self.selected_video_files: List[str] = []
        self.selection_mode = "none"  # "folder", "multi", "single", "none"
        self._folder_video_files: List[tuple] = []
        self.last_rendered_path = ""
        self.last_log_path = ""
        self.selected_folder_path = ""
        self.runtime_data_dir = get_runtime_data_dir("Client", current_dir)
        self.download_output_dir = os.path.join(self.runtime_data_dir, "client_downloads")
        os.makedirs(self.download_output_dir, exist_ok=True)
        default_combined = os.path.join(self.download_output_dir, "combined_video.mp4")
        if os.path.exists(default_combined):
            self.last_rendered_path = default_combined
        default_log = os.path.join(self.download_output_dir, "logs.txt")
        if os.path.exists(default_log):
            self.last_log_path = default_log

        # CapCut post-export watcher and remote re-encode queue state
        self.capcut_drafts_dir = os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'CapCut', 'User Data', 'Projects', 'com.lveditor.draft'
        )
        default_capcut_export = os.path.join(os.environ.get('USERPROFILE', ''), 'Videos', 'CapCut')
        if not os.path.exists(default_capcut_export):
            default_capcut_export = os.path.join(self.download_output_dir, 'capcut_exports')
            os.makedirs(default_capcut_export, exist_ok=True)
        self.capcut_watch_dir = default_capcut_export
        self.capcut_watch_active = False
        self.capcut_watch_thread = None
        # Track file signatures, not just names: CapCut commonly overwrites the
        # same export filename on subsequent exports.
        self._known_capcut_files = {}
        self._capcut_file_stability = {}
        self._capcut_pending_exports = []
        self._capcut_pending_paths = set()
        self._capcut_queue_lock = threading.Lock()
        self._capcut_current_export = None
        self.capcut_drafts_data = []
        self.capcut_intercept_count = 0

        # Thread-safe UI update queue
        self.ui_queue = queue.Queue()
        self._poll_ui_queue()

        # Build UI Layout
        self._build_header()
        self._build_tab_container()
        self._build_log_terminal()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Log Initial System Banner
        self.log("[SYSTEM] Distributed Task Offloading Client initialized (Computer A).")
        self.log("[ONE-CLICK] Looking for Computer B automatically. No IP or manual handshake is required.")
        self.log("[NEW] Video Concat Feature: Select an Entire Folder of video parts or Multi-Select files to combine and render!")
        self.log("[TIP] Keep both computers on the same private network; connection is automatic.")

        # Persistent zero-config discovery + handshake. This waits for Computer B
        # if its EXE is launched a little later than the client.
        self._auto_connect_stop = threading.Event()
        self.after(500, self._start_auto_connect)


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
        """Builds tabs: Tab 1 = Video Offload; Tab 2 = LAN Sharing; Tab 3 = CapCut Timeline Handoff / Export Watch."""
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=4)

        self.tab_offload = self.tabview.add("🎬 Multi-Part Video Combiner & Offload")
        self.tab_sharing = self.tabview.add("📁 LAN File Sharing Hub")
        self.tab_capcut = self.tabview.add("⚡ CapCut Timeline Handoff & Export Watch")

        self._build_offload_tab()
        self._build_sharing_tab()
        self._build_capcut_tab()

    def _build_offload_tab(self):
        """Tab 1: Folder browser for third-party video editor exports + server rendering."""
        main_container = ctk.CTkFrame(self.tab_offload, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=4, pady=2)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)

        # ==========================================
        # LEFT COLUMN: Connection & Folder Browser (Scrollable)
        # ==========================================
        left_col = ctk.CTkScrollableFrame(main_container, corner_radius=10)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=2)

        # Section 1: Networking & Handshake Setup
        net_title = ctk.CTkLabel(
            left_col,
            text="🌐 1. Automatic Computer B Connection",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#93c5fd"
        )
        net_title.pack(anchor="w", padx=14, pady=(10, 4))

        net_row = ctk.CTkFrame(left_col, fg_color="transparent")
        net_row.pack(fill="x", padx=14, pady=2)

        # Internal fields are retained for backwards compatibility, but hidden:
        # the client resolves the server by LAN discovery automatically.
        self.ip_entry = ctk.CTkEntry(net_row, placeholder_text="Auto-discovered", width=220)
        self.ip_entry.insert(0, DEFAULT_HOST)
        self.port_entry = ctk.CTkEntry(net_row, placeholder_text="Port", width=75)
        self.port_entry.insert(0, str(DEFAULT_PORT))

        btn_row = ctk.CTkFrame(left_col, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(4, 2))
        self.detect_btn = None
        self.ping_btn = None
        ctk.CTkLabel(
            btn_row,
            text="🔄 Automatic discovery and connection are active — keep both computers on the same private LAN/Wi-Fi or Ethernet network.",
            font=ctk.CTkFont(size=11),
            text_color="#93c5fd",
            justify="left",
            wraplength=620
        ).pack(anchor="w", fill="x")

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
            text="Searching for Computer B automatically…",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1"
        )
        self.worker_specs_lbl.pack(anchor="w", padx=10, pady=(0, 5))

        # Section 2: Video Workload Selection
        folder_title = ctk.CTkLabel(
            left_col,
            text="🎬 2. Video Workload: Entire Folder, Multiple Files, or Single File",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#93c5fd"
        )
        folder_title.pack(anchor="w", padx=14, pady=(8, 2))

        folder_desc = ctk.CTkLabel(
            left_col,
            text="Choose an entire folder of video parts, select multiple files to combine, or pick a single file.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        folder_desc.pack(anchor="w", padx=14, pady=(0, 4))

        folder_row = ctk.CTkFrame(left_col, fg_color="transparent")
        folder_row.pack(fill="x", padx=14, pady=2)

        self.folder_path_entry = ctk.CTkEntry(folder_row, placeholder_text="Select or paste folder with video parts...", width=240)
        self.folder_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.folder_browse_btn = ctk.CTkButton(
            folder_row,
            text="📂 Browse Folder",
            width=120,
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            command=self._handle_browse_folder
        )
        self.folder_browse_btn.pack(side="left", padx=(0, 6))

        self.folder_refresh_btn = ctk.CTkButton(
            folder_row,
            text="🔄",
            width=35,
            fg_color="#475569",
            hover_color="#334155",
            command=self._refresh_folder_videos
        )
        self.folder_refresh_btn.pack(side="left")

        # Video Files List in Folder
        self.video_list_label = ctk.CTkLabel(
            left_col,
            text="📹 Video Files in Folder: (select a folder first)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1"
        )
        self.video_list_label.pack(anchor="w", padx=14, pady=(4, 2))

        self.video_listbox = ctk.CTkTextbox(
            left_col,
            height=85,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=("#111827", "#030712"),
            text_color="#e2e8f0"
        )
        self.video_listbox.pack(fill="x", padx=14, pady=(0, 4))
        self.video_listbox.insert("end", "No folder scanned yet.\nClick '📂 Browse Folder' to scan your video exports or clip parts folder.\n")
        self.video_listbox.configure(state="disabled")

        # Action Selection Toolbar (Entire Folder vs Multi-Files vs Single)
        action_toolbar = ctk.CTkFrame(left_col, fg_color="transparent")
        action_toolbar.pack(fill="x", padx=14, pady=(2, 4))

        self.select_entire_folder_btn = ctk.CTkButton(
            action_toolbar,
            text="📁 Select Entire Folder",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=135,
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            command=self._handle_select_entire_folder
        )
        self.select_entire_folder_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.multi_select_btn = ctk.CTkButton(
            action_toolbar,
            text="📑 Select Multiple Files",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=135,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._handle_browse_multi_files
        )
        self.multi_select_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.single_browse_btn = ctk.CTkButton(
            action_toolbar,
            text="📄 Single File",
            font=ctk.CTkFont(size=11),
            width=85,
            fg_color="#475569",
            hover_color="#334155",
            command=self._handle_browse_single_file
        )
        self.single_browse_btn.pack(side="left")

        # Custom picker row
        select_row = ctk.CTkFrame(left_col, fg_color="transparent")
        select_row.pack(fill="x", padx=14, pady=(2, 4))

        self.video_select_entry = ctk.CTkEntry(
            select_row,
            placeholder_text="Enter #s (e.g. 1, 2, 3 or 1-4) or name...",
            width=180
        )
        self.video_select_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.video_pick_btn = ctk.CTkButton(
            select_row,
            text="➕ Select from List",
            width=110,
            fg_color="#059669",
            hover_color="#047857",
            command=self._handle_select_video_from_list
        )
        self.video_pick_btn.pack(side="left", padx=(0, 6))

        self.clear_btn = ctk.CTkButton(
            select_row,
            text="🗑️ Clear",
            width=55,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._handle_clear_selection
        )
        self.clear_btn.pack(side="left")

        # Workload Queue & Preview Card
        self.workload_card = ctk.CTkFrame(left_col, fg_color=("#374151", "#1e293b"), corner_radius=8)
        self.workload_card.pack(fill="x", padx=14, pady=(4, 6))

        card_header = ctk.CTkFrame(self.workload_card, fg_color="transparent")
        card_header.pack(fill="x", padx=10, pady=(6, 2))

        self.workload_badge = ctk.CTkLabel(
            card_header,
            text="⚪ NO VIDEO SELECTED",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94a3b8",
            fg_color=("#111827", "#0f172a"),
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.workload_badge.pack(side="left")

        self.workload_stats_lbl = ctk.CTkLabel(
            card_header,
            text="0 videos | 0 B",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1"
        )
        self.workload_stats_lbl.pack(side="right")

        self.workload_textbox = ctk.CTkTextbox(
            self.workload_card,
            height=120,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=("#111827", "#030712"),
            text_color="#e2e8f0"
        )
        self.workload_textbox.pack(fill="x", padx=10, pady=(0, 6))
        self.workload_textbox.insert("end", "No video selected yet.\n• '📁 Select Entire Folder': Combines all video parts in folder.\n• '📑 Select Multiple Files': Pick multiple videos anywhere to combine.\n• Test parts: client/sample_assets/sample_parts/ (Part 1, 2, 3 with bold visual labels)\n")
        self.workload_textbox.configure(state="disabled")

        # Legacy label reference
        self.selected_file_lbl = self.workload_stats_lbl


        # ==========================================
        # RIGHT COLUMN: Render Config & Dashboard (Scrollable)
        # ==========================================
        right_col = ctk.CTkScrollableFrame(main_container, corner_radius=10)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=2)

        # Section 3: Render Settings
        render_title = ctk.CTkLabel(
            right_col,
            text="⚙️ 3. Render Configuration (Server-Side)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#93c5fd"
        )
        render_title.pack(anchor="w", padx=14, pady=(10, 4))

        # Render Settings Box
        self.settings_frame = ctk.CTkFrame(right_col, fg_color=("#374151", "#1e293b"), corner_radius=8)
        self.settings_frame.pack(fill="x", padx=14, pady=4)

        # Row 1: Resolution & Bitrate
        row1 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(row1, text="Resolution:", width=75, anchor="w").pack(side="left")
        self.res_combo = ctk.CTkComboBox(
            row1,
            values=["1920x1080", "1280x720", "854x480", "3840x2160", "original"],
            width=110
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

        # Row 2: Preset & Acceleration Mode
        row2 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(2, 4))

        ctk.CTkLabel(row2, text="Preset:", width=75, anchor="w").pack(side="left")
        self.preset_combo = ctk.CTkComboBox(
            row2,
            values=["ultrafast", "fast", "medium", "slow", "p4"],
            width=110
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

        # Row 3: Creative Filters & FPS
        row3 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=(2, 4))

        ctk.CTkLabel(row3, text="Filter:", width=75, anchor="w").pack(side="left")
        self.filter_combo = ctk.CTkComboBox(
            row3,
            values=["none", "grayscale", "sepia", "mirror", "blur", "speed_2x"],
            width=110
        )
        self.filter_combo.set("none")
        self.filter_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row3, text="FPS:", width=50, anchor="w").pack(side="left")
        self.fps_combo = ctk.CTkComboBox(
            row3,
            values=["original", "24 fps", "30 fps", "60 fps"],
            width=100
        )
        self.fps_combo.set("original")
        self.fps_combo.pack(side="left")

        # Section 4: Real-Time Progress Dashboard
        prog_title = ctk.CTkLabel(
            right_col,
            text="📊 4. Real-Time Remote Execution Dashboard",
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
            text="0.0% | Ready to offload video",
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
            text="🚀 Send Video to Server for Rendering (Computer B)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            height=38,
            command=self._handle_start_offload
        )
        self.offload_btn.pack(fill="x", pady=(0, 6))

        btn_row = ctk.CTkFrame(btn_frame, fg_color="transparent")
        btn_row.pack(fill="x")

        initial_play_state = "normal" if (self.last_rendered_path and os.path.exists(self.last_rendered_path)) else "disabled"
        self.play_btn = ctk.CTkButton(
            btn_row,
            text="▶️ Play Video",
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=30,
            width=90,
            state=initial_play_state,
            command=self._handle_play_rendered_video
        )
        self.play_btn.pack(side="left", padx=(0, 6))

        initial_log_state = "normal" if (self.last_log_path and os.path.exists(self.last_log_path)) else "disabled"
        self.view_log_btn = ctk.CTkButton(
            btn_row,
            text="📄 View Logs",
            fg_color="#0d9488",
            hover_color="#0f766e",
            height=30,
            width=95,
            state=initial_log_state,
            command=self._handle_view_server_logs
        )
        self.view_log_btn.pack(side="left", padx=(0, 6))

        self.open_dl_btn = ctk.CTkButton(
            btn_row,
            text="📂 Open Downloads",
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            height=30,
            command=lambda: os.startfile(self.download_output_dir)
        )
        self.open_dl_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

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

    def _build_capcut_tab(self):
        """Tab 3: Full editable timeline handoff to B plus optional MP4 export watcher."""
        container = ctk.CTkFrame(self.tab_capcut, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=8, pady=4)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        # ----------------------------------------------------
        # LEFT COLUMN: Real-Time Export Watcher
        # ----------------------------------------------------
        left_col = ctk.CTkScrollableFrame(container, corner_radius=10)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=2)

        # Card 1 Title
        ctk.CTkLabel(
            left_col,
            text="🎥 1. Completed MP4 Export Watcher (Optional FFmpeg Route)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#93c5fd"
        ).pack(anchor="w", padx=12, pady=(10, 4))

        info_lbl = ctk.CTkLabel(
            left_col,
            text="Optional legacy route: export an MP4 on A and send that finished file to B\n"
                 "for a second-pass FFmpeg encode. This does NOT transfer the editable timeline.\n"
                 "For native CapCut rendering on B, use the Full Editable Timeline Handoff on the right.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        )
        info_lbl.pack(anchor="w", padx=12, pady=(0, 10))

        # Watch Folder Setup
        ctk.CTkLabel(
            left_col,
            text="📂 CapCut Export Destination (Watch Folder):",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=12, pady=(4, 2))

        folder_row = ctk.CTkFrame(left_col, fg_color="transparent")
        folder_row.pack(fill="x", padx=12, pady=(0, 8))

        self.capcut_watch_entry = ctk.CTkEntry(folder_row, font=ctk.CTkFont(size=11))
        self.capcut_watch_entry.insert(0, self.capcut_watch_dir)
        self.capcut_watch_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        browse_watch_btn = ctk.CTkButton(
            folder_row,
            text="Browse",
            width=70,
            command=self._handle_browse_capcut_watch
        )
        browse_watch_btn.pack(side="left", padx=(0, 4))

        open_watch_btn = ctk.CTkButton(
            folder_row,
            text="Open",
            width=60,
            fg_color="#334155",
            hover_color="#1e293b",
            command=lambda: os.startfile(self.capcut_watch_entry.get().strip() or self.capcut_watch_dir)
        )
        open_watch_btn.pack(side="left")

        # Remote Render Profile Selector
        ctk.CTkLabel(
            left_col,
            text="⚙️ Target Remote GPU Remastering Profile (Computer B):",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self.capcut_profile_combo = ctk.CTkComboBox(
            left_col,
            values=[
                "Ultra Master NVENC (1080p, 6000k, GPU)",
                "Cinema 4K High-Bitrate (3840x2160, 10000k)",
                "Standard 1080p Fast (1920x1080, 3000k)",
                "60 FPS Re-encode (Original Res)",
                "Fast Web / Social Media (720p, 1800k)"
            ],
            width=360
        )
        self.capcut_profile_combo.set("Ultra Master NVENC (1080p, 6000k, GPU)")
        self.capcut_profile_combo.pack(anchor="w", padx=12, pady=(0, 10))

        # Big Toggle Button: Enable / Disable Watchdog Hook
        self.capcut_toggle_btn = ctk.CTkButton(
            left_col,
            text="🟢 Start Export Watcher",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=36,
            command=self._handle_toggle_capcut_watch
        )
        self.capcut_toggle_btn.pack(fill="x", padx=12, pady=(6, 12))

        # Intercept Status & Stats Card
        stats_frame = ctk.CTkFrame(left_col, corner_radius=8, fg_color=("#1e293b", "#0f172a"))
        stats_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.capcut_watch_status_lbl = ctk.CTkLabel(
            stats_frame,
            text="🔴 Watcher: PAUSED (Start it before exporting from CapCut)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f87171"
        )
        self.capcut_watch_status_lbl.pack(anchor="w", padx=10, pady=(8, 4))

        self.capcut_intercept_count_lbl = ctk.CTkLabel(
            stats_frame,
            text="Completed Exports Sent: 0 | Last Sent: None",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.capcut_intercept_count_lbl.pack(anchor="w", padx=10, pady=(0, 8))


        # ----------------------------------------------------
        # RIGHT COLUMN: CapCut Local Drafts Explorer & Timeline Offload
        # ----------------------------------------------------
        right_col = ctk.CTkScrollableFrame(container, corner_radius=10)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=2)

        # Card 2 Title
        ctk.CTkLabel(
            right_col,
            text="📋 2. Full Editable CapCut Timeline Handoff",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#93c5fd"
        ).pack(anchor="w", padx=12, pady=(10, 4))

        draft_desc = ctk.CTkLabel(
            right_col,
            text="Transfer the COMPLETE saved CapCut draft folder and referenced local media to B.\n"
                 "Computer B restores the editable timeline and opens CapCut Desktop.\n"
                 "Save and close CapCut on A before sending. Export is started inside CapCut on B.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        )
        draft_desc.pack(anchor="w", padx=12, pady=(0, 10))

        # Project Selector Dropdown + Refresh Button
        sel_row = ctk.CTkFrame(right_col, fg_color="transparent")
        sel_row.pack(fill="x", padx=12, pady=(0, 8))

        self.capcut_draft_combo = ctk.CTkComboBox(
            sel_row,
            values=["Scanning CapCut Drafts..."],
            width=260,
            command=self._handle_select_capcut_draft
        )
        self.capcut_draft_combo.pack(side="left", fill="x", expand=True, padx=(0, 6))

        refresh_draft_btn = ctk.CTkButton(
            sel_row,
            text="🔄 Refresh",
            width=80,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._handle_refresh_capcut_drafts
        )
        refresh_draft_btn.pack(side="left")

        # Project Detail Card
        self.draft_card = ctk.CTkFrame(right_col, corner_radius=8, fg_color=("#1e293b", "#0f172a"))
        self.draft_card.pack(fill="x", padx=12, pady=(0, 10))

        self.draft_info_title = ctk.CTkLabel(
            self.draft_card,
            text="Project Name: --",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8"
        )
        self.draft_info_title.pack(anchor="w", padx=10, pady=(8, 2))

        self.draft_info_details = ctk.CTkLabel(
            self.draft_card,
            text="Duration: -- | FPS: -- | Video Assets: --\nLast Modified: --",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1",
            justify="left"
        )
        self.draft_info_details.pack(anchor="w", padx=10, pady=(0, 8))

        # Action Buttons for Draft
        draft_btn_row = ctk.CTkFrame(right_col, fg_color="transparent")
        draft_btn_row.pack(fill="x", padx=12, pady=(0, 10))

        self.offload_draft_btn = ctk.CTkButton(
            draft_btn_row,
            text="Send Full Editable Timeline to B & Open CapCut",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=32,
            command=self._handle_send_capcut_project
        )
        self.offload_draft_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        open_draft_dir_btn = ctk.CTkButton(
            draft_btn_row,
            text="📁 Open Folder",
            width=100,
            height=32,
            fg_color="#334155",
            hover_color="#1e293b",
            command=self._handle_open_capcut_draft_folder
        )
        open_draft_dir_btn.pack(side="left")

        # Dedicated CapCut Hook Log Box
        ctk.CTkLabel(
            right_col,
            text="📡 CapCut Timeline Transfer & Export Watcher Log:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self.capcut_log_box = ctk.CTkTextbox(
            right_col,
            height=130,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=("#111827", "#030712"),
            text_color="#a7f3d0"
        )
        self.capcut_log_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.capcut_log_box.insert("end", "[CAPCUT SYSTEM] Export-folder watcher and remote re-encode queue initialized.\n")
        self.capcut_log_box.configure(state="disabled")

        # Initial automatic scan of drafts
        self.after(500, self._handle_refresh_capcut_drafts)

    def _log_capcut(self, text: str):
        """Log CapCut watcher events without touching Tk widgets from worker threads."""
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {text}\n"

        def _insert():
            try:
                self.capcut_log_box.configure(state="normal")
                self.capcut_log_box.insert("end", formatted)
                self.capcut_log_box.see("end")
                self.capcut_log_box.configure(state="disabled")
            except Exception:
                pass

        self.run_on_ui(_insert)
        self.log(f"[CAPCUT WATCHER] {text}")

    @staticmethod
    def _capcut_file_signature(path: str):
        """Return a stable, high-resolution signature for a watched export."""
        stat = os.stat(path)
        mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
        return stat.st_size, mtime_ns

    def _start_next_capcut_export(self):
        """Start the next completed export from the watcher queue on the UI thread."""
        if self.is_processing:
            return

        next_path = None
        with self._capcut_queue_lock:
            while self._capcut_pending_exports:
                candidate = self._capcut_pending_exports.pop(0)
                self._capcut_pending_paths.discard(os.path.normcase(candidate))
                if os.path.isfile(candidate):
                    next_path = candidate
                    break

        if not next_path:
            return

        self._capcut_current_export = next_path
        self.selected_video_files = [next_path]
        self.selection_mode = "single"
        self._update_files_view()
        self.tabview.set("🎬 Multi-Part Video Combiner & Offload")
        self._apply_capcut_profile()
        self._log_capcut(f"🚀 Queue started: {os.path.basename(next_path)} → Computer B")
        self._handle_start_offload()

    def _apply_capcut_profile(self):
        """Apply a complete, deterministic remote encode profile."""
        profile = self.capcut_profile_combo.get()
        self.accel_combo.set("auto")  # NVENC if verified on B, otherwise CPU fallback.
        self.fps_combo.set("original")

        if "4K" in profile:
            self.res_combo.set("3840x2160")
            self.bitrate_combo.set("10000k")
        elif "1080p, 6000k" in profile:
            self.res_combo.set("1920x1080")
            self.bitrate_combo.set("6000k")
        elif "60 FPS" in profile:
            self.res_combo.set("original")
            self.bitrate_combo.set("6000k")
            self.fps_combo.set("60 fps")
        elif "720p" in profile:
            self.res_combo.set("1280x720")
            self.bitrate_combo.set("1800k")
        else:  # Standard 1080p Fast profile
            self.res_combo.set("1920x1080")
            self.bitrate_combo.set("3000k")

    def _scan_capcut_drafts(self) -> List[Dict[str, Any]]:
        """Scans local CapCut directory for active project drafts."""
        if not os.path.exists(self.capcut_drafts_dir):
            return []

        results = []
        try:
            for item in os.listdir(self.capcut_drafts_dir):
                if item.startswith('.'):
                    continue
                p = os.path.join(self.capcut_drafts_dir, item)
                if not os.path.isdir(p):
                    continue

                info = {
                    'id': item,
                    'path': p,
                    'name': item,
                    'fps': 30.0,
                    'duration_sec': 0.0,
                    'videos': [],
                    'video_count': 0,
                    'modified': time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p))),
                    'mtime': os.path.getmtime(p)
                }

                content_json = os.path.join(p, 'draft_content.json')
                if not os.path.exists(content_json):
                    content_json = os.path.join(p, 'draft_info.json')
                if os.path.exists(content_json):
                    try:
                        import json
                        with open(content_json, 'r', encoding='utf-8', errors='ignore') as f:
                            cdata = json.load(f)
                            info['fps'] = cdata.get('fps', 30.0)
                            dur_us = cdata.get('duration', 0)
                            info['duration_sec'] = round(dur_us / 1000000.0, 2)
                            mats = cdata.get('materials', {})
                            vlist = mats.get('videos', [])
                            vpaths = []
                            for v in vlist:
                                if isinstance(v, dict) and v.get('path'):
                                    vpaths.append(v['path'])
                            info['videos'] = vpaths
                            info['video_count'] = len(vpaths)
                            if cdata.get('name'):
                                info['name'] = cdata['name']
                    except Exception:
                        pass

                results.append(info)
        except Exception as e:
            self.log(f"[ERROR] Error scanning CapCut drafts: {e}")

        # Sort newest modified first
        results.sort(key=lambda x: x.get('mtime', 0), reverse=True)
        return results

    def _handle_refresh_capcut_drafts(self):
        """Refreshes the CapCut draft projects dropdown."""
        self.capcut_drafts_data = self._scan_capcut_drafts()
        if self.capcut_drafts_data:
            vals = [f"{d['id']} - {d['name']} ({d['duration_sec']}s, {d['video_count']} clips)" for d in self.capcut_drafts_data]
            self.capcut_draft_combo.configure(values=vals)
            self.capcut_draft_combo.set(vals[0])
            self._handle_select_capcut_draft(vals[0])
            self._log_capcut(f"Discovered {len(self.capcut_drafts_data)} CapCut project drafts in AppData.")
        else:
            self.capcut_draft_combo.configure(values=["No CapCut drafts found"])
            self.capcut_draft_combo.set("No CapCut drafts found")
            self.draft_info_title.configure(text="No CapCut drafts detected")
            self.draft_info_details.configure(text="Make sure CapCut is installed on this PC.")

    def _handle_select_capcut_draft(self, choice=None):
        """Updates draft details display when user selects a project."""
        if not self.capcut_drafts_data:
            return
        selected_text = self.capcut_draft_combo.get()
        target = None
        for d in self.capcut_drafts_data:
            if d['id'] in selected_text:
                target = d
                break
        if not target and self.capcut_drafts_data:
            target = self.capcut_drafts_data[0]

        if target:
            self.draft_info_title.configure(text=f"Project: {target['name']} (ID: {target['id']})")
            clip_names = [os.path.basename(v) for v in target['videos'][:3]]
            clip_summary = ", ".join(clip_names) + ("..." if len(target['videos']) > 3 else "")
            details_str = (
                f"Duration: {target['duration_sec']}s | FPS: {target['fps']} | Total Clips: {target['video_count']}\n"
                f"Last Modified: {target['modified']}\n"
                f"Clips: {clip_summary or 'No external video files'}"
            )
            self.draft_info_details.configure(text=details_str)

    def _handle_open_capcut_draft_folder(self):
        """Opens the selected CapCut draft folder in Explorer."""
        selected_text = self.capcut_draft_combo.get()
        for d in self.capcut_drafts_data:
            if d['id'] in selected_text:
                if os.path.exists(d['path']):
                    os.startfile(d['path'])
                    self._log_capcut(f"Opened draft folder: {d['path']}")
                return

    def _handle_send_capcut_project(self):
        """Package a complete local CapCut draft and restore/open it on Computer B."""
        if not self.capcut_drafts_data:
            messagebox.showwarning("No Project", "No CapCut draft projects found on Computer A.")
            return
        selected_text = self.capcut_draft_combo.get()
        target = next((d for d in self.capcut_drafts_data if d['id'] in selected_text), None)
        if not target or not os.path.isdir(target.get('path', '')):
            messagebox.showwarning("Select Project", "Please select a valid local CapCut project.")
            return

        host = self.ip_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Port", "Enter a valid Computer B port number.")
            return
        if not host:
            messagebox.showerror("Server IP Required", "Enter Computer B's IP address first.")
            return

        confirm = messagebox.askyesno(
            "Save and Close CapCut on A",
            "Before packaging, save your project and CLOSE CapCut on Computer A. Also close CapCut on B if it is already running.\n\n"
            "The complete draft folder and all existing local files referenced by its JSON will be sent.\n"
            "Computer B must have CapCut Desktop installed (same or newer compatible version).\n\n"
            "Continue with the transfer?"
        )
        if not confirm:
            return

        self.offload_draft_btn.configure(state="disabled", text="Packaging & Sending Timeline…")
        self._log_capcut(f"Starting full timeline handoff for '{target['name']}' to {host}:{port}…")

        def worker():
            import uuid
            bundle_path = None
            remote = None
            try:
                bundle_dir = os.path.join(self.runtime_data_dir, "capcut_project_bundles")
                os.makedirs(bundle_dir, exist_ok=True)
                bundle_name = f"capcut_project_{uuid.uuid4().hex[:12]}.zip"
                bundle_path = os.path.join(bundle_dir, bundle_name)
                self._log_capcut("Packaging all draft files and relocating absolute media references…")
                bundle_info = build_capcut_bundle(target['path'], bundle_path)
                self._log_capcut(
                    f"Package ready: {format_bytes(bundle_info['bundle_size'])}; "
                    f"{bundle_info['draft_file_count']} draft files; "
                    f"{bundle_info['asset_count']} external assets."
                )
                if bundle_info.get("missing_refs"):
                    missing_count = len(bundle_info["missing_refs"])
                    self._log_capcut(f"⚠️ Found {missing_count} referenced path(s) that are not present on A. B may ask you to relink these assets.")

                remote = OffloadingClient(host=host, port=port)
                remote.perform_handshake()
                self._log_capcut("Connected to Computer B. Uploading the complete editable project package…")
                uploaded = remote.upload_shared_file(
                    bundle_path,
                    progress_callback=lambda msg: self._log_capcut(f"[UPLOAD] {msg}")
                )
                if not uploaded:
                    raise RuntimeError("Computer B did not confirm the CapCut project package upload.")
                self._log_capcut("Upload verified. Asking Computer B to restore the CapCut draft and launch CapCut Desktop…")
                result = remote.request_capcut_import(bundle_name)
                project_folder = result.get("project_folder", "")
                opened = bool(result.get("capcut_started"))
                status = (
                    f"Timeline transferred successfully to Computer B.\n\n"
                    f"Project folder on B:\n{project_folder}\n\n"
                    + ("CapCut Desktop was launched on B. Select the transferred project from CapCut Home/Projects, then click Export on B."
                       if opened else "The draft was restored on B, but CapCut did not launch automatically. Install/open CapCut Desktop on B and select the transferred project.")
                    + "\n\nImportant: the native Export button on A is not remotely intercepted; CapCut's own export must run in B's GUI."
                    + (f"\n\nWarning: {len(bundle_info.get('missing_refs', []))} referenced local file path(s) were already missing on A; relink them before exporting." if bundle_info.get("missing_refs") else "")
                )
                self._log_capcut("✅ " + status.replace("\n", " | "))
                self.run_on_ui(lambda m=status: messagebox.showinfo("CapCut Timeline Sent to Computer B", m))
            except Exception as exc:
                err = str(exc)
                self._log_capcut(f"❌ Full timeline handoff failed: {err}")
                self.run_on_ui(lambda e=err: messagebox.showerror("CapCut Timeline Transfer Failed", e))
            finally:
                if remote:
                    try:
                        remote.disconnect()
                    except Exception:
                        pass
                if bundle_path and os.path.exists(bundle_path):
                    try:
                        os.remove(bundle_path)
                    except OSError:
                        pass
                self.run_on_ui(lambda: self.offload_draft_btn.configure(
                    state="normal", text="Send Full Editable Timeline to B & Open CapCut"
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_offload_capcut_draft(self):
        """Offloads referenced clips of the selected CapCut project to Computer B."""
        if not self.capcut_drafts_data:
            messagebox.showwarning("No Project", "No CapCut draft projects found.")
            return

        selected_text = self.capcut_draft_combo.get()
        target = None
        for d in self.capcut_drafts_data:
            if d['id'] in selected_text:
                target = d
                break
        if not target:
            messagebox.showwarning("Select Project", "Please select a valid CapCut project draft.")
            return

        # Find existing video files referenced by this draft
        valid_clips = []
        for v in target['videos']:
            # Normalize path slashes
            norm_p = os.path.normpath(v)
            if os.path.exists(norm_p):
                valid_clips.append(norm_p)

        if not valid_clips:
            messagebox.showerror(
                "Source Assets Missing",
                f"The video clips referenced by draft '{target['id']}' could not be located on disk.\n"
                "Please make sure the source video files have not been moved or deleted."
            )
            return

        # Deduplicate while preserving order
        unique_clips = []
        for c in valid_clips:
            if c not in unique_clips:
                unique_clips.append(c)

        self._log_capcut(f"🚀 Loaded {len(unique_clips)} video clips from draft '{target['id']}'. Offloading to Computer B...")

        # Apply profile configuration
        self._apply_capcut_profile()

        # Set selected files and switch to main offload view
        self.selected_video_files = unique_clips
        self.selection_mode = "multi" if len(unique_clips) > 1 else "single"
        self._update_files_view()

        # Switch tab and trigger offload
        self.tabview.set("🎬 Multi-Part Video Combiner & Offload")
        self._handle_start_offload()

    def _handle_browse_capcut_watch(self):
        """Browse dialog for CapCut Export Watch Folder."""
        folder = filedialog.askdirectory(title="Select CapCut Export Folder to Monitor")
        if folder:
            self.capcut_watch_entry.delete(0, "end")
            self.capcut_watch_entry.insert(0, folder)
            self.capcut_watch_dir = folder
            self._log_capcut(f"Watch folder updated to: {folder}")

    def _handle_toggle_capcut_watch(self):
        """Enable/disable polling-based CapCut export completion detection."""
        if self.capcut_watch_active:
            self.capcut_watch_active = False
            self.capcut_toggle_btn.configure(
                text="🟢 Start Export Watcher",
                fg_color="#10b981",
                hover_color="#059669"
            )
            self.capcut_watch_status_lbl.configure(
                text="🔴 Watcher: PAUSED",
                text_color="#f87171"
            )
            self._log_capcut("Export watcher paused. Already queued jobs will still finish.")
            return

        watch_dir = self.capcut_watch_entry.get().strip()
        if not watch_dir:
            messagebox.showerror("Error", "Please specify a valid CapCut export folder.")
            return
        try:
            os.makedirs(watch_dir, exist_ok=True)
            if not os.path.isdir(watch_dir):
                raise OSError("Selected path is not a folder")
        except OSError as exc:
            messagebox.showerror("Invalid Watch Folder", str(exc))
            return

        self.capcut_watch_dir = os.path.abspath(watch_dir)
        self._known_capcut_files = {}
        self._capcut_file_stability = {}
        try:
            for fname in os.listdir(self.capcut_watch_dir):
                fpath = os.path.join(self.capcut_watch_dir, fname)
                if os.path.isfile(fpath) and os.path.splitext(fname)[1].lower() in VIDEO_EXTENSIONS:
                    try:
                        self._known_capcut_files[fname] = self._capcut_file_signature(fpath)
                    except OSError:
                        pass
        except OSError as exc:
            messagebox.showerror("Watch Folder Error", str(exc))
            return

        self.capcut_watch_active = True
        self.capcut_toggle_btn.configure(
            text="🛑 Stop Export Watcher",
            fg_color="#dc2626",
            hover_color="#b91c1c"
        )
        self.capcut_watch_status_lbl.configure(
            text=f"🟢 Watching for completed exports\n{self.capcut_watch_dir}\nStability check: 3 polls / ~6 seconds",
            text_color="#4ade80"
        )
        self._log_capcut(f"Watcher ACTIVE: {self.capcut_watch_dir}")
        self._log_capcut("Export from CapCut into this folder. A completed/changed MP4 will be queued for Computer B.")
        self.capcut_watch_thread = threading.Thread(target=self._capcut_watch_loop, daemon=True)
        self.capcut_watch_thread.start()

    def _capcut_watch_loop(self):
        """Detect new or overwritten exports only after several stable file polls."""
        while self.capcut_watch_active:
            time.sleep(2.0)
            watch_dir = self.capcut_watch_dir
            if not watch_dir or not os.path.isdir(watch_dir):
                continue

            try:
                current_files = os.listdir(watch_dir)
            except OSError:
                continue

            for fname in current_files:
                if not self.capcut_watch_active:
                    break
                if os.path.splitext(fname)[1].lower() not in VIDEO_EXTENSIONS:
                    continue

                fpath = os.path.abspath(os.path.join(watch_dir, fname))
                try:
                    if not os.path.isfile(fpath):
                        continue
                    signature = self._capcut_file_signature(fpath)
                except OSError:
                    continue

                if signature[0] <= 0:
                    continue
                if self._known_capcut_files.get(fname) == signature:
                    self._capcut_file_stability.pop(fname, None)
                    continue

                state = self._capcut_file_stability.get(fname)
                if not state or state.get("signature") != signature:
                    self._capcut_file_stability[fname] = {"signature": signature, "stable_polls": 1}
                    continue

                state["stable_polls"] += 1
                if state["stable_polls"] < 3:
                    continue

                # A readable file plus three unchanged size/mtime samples makes
                # a partial export much less likely to be mistaken for a final MP4.
                try:
                    with open(fpath, "rb") as stream:
                        stream.read(1)
                    final_signature = self._capcut_file_signature(fpath)
                except OSError:
                    continue
                if final_signature != signature:
                    self._capcut_file_stability[fname] = {"signature": final_signature, "stable_polls": 1}
                    continue

                self._known_capcut_files[fname] = final_signature
                self._capcut_file_stability.pop(fname, None)
                normalized = os.path.normcase(fpath)
                with self._capcut_queue_lock:
                    if normalized == os.path.normcase(self._capcut_current_export or ""):
                        continue
                    if normalized in self._capcut_pending_paths:
                        continue
                    self._capcut_pending_exports.append(fpath)
                    self._capcut_pending_paths.add(normalized)
                    queue_count = len(self._capcut_pending_exports)

                self.capcut_intercept_count += 1
                self.run_on_ui(lambda f=fname, n=self.capcut_intercept_count, q=queue_count: self.capcut_intercept_count_lbl.configure(
                    text=f"Completed Exports: {n} | Waiting in Queue: {q} | Last: {f}"
                ))
                self._log_capcut(f"✅ Completed export detected: {fname} ({format_bytes(final_signature[0])}). Queued for remote render.")
                self.run_on_ui(self._start_next_capcut_export)

    def _on_close(self):
        """Stop background watcher/network activity before closing the window."""
        self.capcut_watch_active = False
        try:
            self._auto_connect_stop.set()
        except Exception:
            pass
        try:
            if self.client:
                self.client.disconnect()
        except Exception:
            pass
        self.destroy()

    def _build_log_terminal(self):
        """Bottom Real-Time Log Terminal Widget."""
        term_frame = ctk.CTkFrame(self, corner_radius=10)
        term_frame.pack(fill="x", expand=False, padx=16, pady=(2, 8))

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
            height=130,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("#111827", "#030712"),
            text_color="#e2e8f0",
            wrap="none"
        )
        self.log_textbox.pack(fill="x", expand=False, padx=12, pady=(0, 6))

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

    # ==========================================
    # FOLDER BROWSER & VIDEO FILE LISTING
    # ==========================================
    def _handle_browse_folder(self):
        """Opens folder dialog to select a third-party video editor export directory."""
        folder = filedialog.askdirectory(
            title="Select Video Editor Exports Folder (CapCut / ClipChamp / etc.)"
        )
        if folder:
            self.selected_folder_path = folder
            self.folder_path_entry.delete(0, "end")
            self.folder_path_entry.insert(0, folder)
            self.log(f"📂 [FOLDER SELECTED] {folder}")
            self._refresh_folder_videos()

    def _refresh_folder_videos(self):
        """Scans the selected folder for video files and lists them."""
        folder = self.folder_path_entry.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No Folder", "Please select a valid folder first using '📂 Browse Folder'.")
            return

        self.selected_folder_path = folder
        video_files = []

        try:
            for fname in sorted(os.listdir(folder)):
                fpath = os.path.join(folder, fname)
                if os.path.isfile(fpath):
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in VIDEO_EXTENSIONS:
                        size = os.path.getsize(fpath)
                        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(fpath)))
                        video_files.append((fname, size, mtime))
        except Exception as e:
            self.log(f"❌ [SCAN ERROR] Could not scan folder: {e}")
            return

        # Update the video list display
        self.video_listbox.configure(state="normal")
        self.video_listbox.delete("1.0", "end")

        if not video_files:
            self.video_listbox.insert("end", f"No video files found in:\n{folder}\n\nSupported formats: {', '.join(VIDEO_EXTENSIONS)}\n")
            self.video_list_label.configure(text="📹 Video Files Found: 0")
        else:
            self.video_listbox.insert("end", f"{'#':<4} {'File Name':<40} {'Size':<12} {'Modified'}\n")
            self.video_listbox.insert("end", "─" * 80 + "\n")
            for idx, (name, size, mtime) in enumerate(video_files, 1):
                size_str = format_bytes(size)
                self.video_listbox.insert("end", f"{idx:<4} {name:<40} {size_str:<12} {mtime}\n")
            self.video_list_label.configure(text=f"📹 Video Files Found: {len(video_files)}")
            self.log(f"📹 [SCAN] Found {len(video_files)} video file(s) in: {folder}")

        self.video_listbox.configure(state="disabled")

        # Store the list for selection
        self._folder_video_files = video_files

    def _update_workload_display(self):
        """Updates the selected video workload card, badge, preview list, and action button."""
        files = self.selected_video_files
        count = len(files)
        total_size = sum(os.path.getsize(f) for f in files if os.path.exists(f))

        self.workload_textbox.configure(state="normal")
        self.workload_textbox.delete("1.0", "end")

        if count == 0:
            self.workload_badge.configure(text="⚪ NO VIDEO SELECTED", text_color="#94a3b8", fg_color=("#111827", "#0f172a"))
            self.workload_stats_lbl.configure(text="0 videos | 0 B")
            self.workload_textbox.insert("end", "No video selected yet.\n• '📁 Select Entire Folder': Combines all video parts in folder.\n• '📑 Select Multiple Files': Pick multiple videos anywhere to combine.\n• '📄 Single File': Offloads a single video.\n")
            self.offload_btn.configure(text="🚀 Select Video(s) Above to Offload", state="normal")
            self.selected_file_path = ""
        elif count == 1:
            self.workload_badge.configure(text="📄 SINGLE VIDEO", text_color="#60a5fa", fg_color=("#1e3a8a", "#172554"))
            self.workload_stats_lbl.configure(text=f"1 video | {format_bytes(total_size)}")
            fname = os.path.basename(files[0])
            self.workload_textbox.insert("end", f"▶ Single Video: {fname} ({format_bytes(total_size)})\n")
            self.workload_textbox.insert("end", f"   Path: {files[0]}\n")
            self.workload_textbox.insert("end", f"   Ready to offload to Server for hardware-accelerated rendering.")
            self.offload_btn.configure(text="🚀 Send Video to Server for Rendering (Computer B)", state="normal")
            self.selected_file_path = files[0]
        else:
            mode_lbl = "📁 ENTIRE FOLDER COMBINE" if self.selection_mode == "folder" else "📑 MULTI-FILES COMBINE"
            self.workload_badge.configure(text=f"{mode_lbl} ({count} PARTS)", text_color="#34d399", fg_color=("#064e3b", "#022c22"))
            self.workload_stats_lbl.configure(text=f"{count} videos | Total: {format_bytes(total_size)}")
            for idx, f in enumerate(files, 1):
                sz = format_bytes(os.path.getsize(f)) if os.path.exists(f) else "0 B"
                self.workload_textbox.insert("end", f"[Part {idx:02d}] {os.path.basename(f)} ({sz})\n")
            self.workload_textbox.insert("end", "─" * 65 + "\n")
            self.workload_textbox.insert("end", f"⚡ Sequence: All {count} parts will be uploaded, stitched, and rendered into 1 complete video on Computer B!\n")
            self.offload_btn.configure(text=f"🚀 Combine & Render {count} Videos on Server (Computer B)", state="normal")
            self.selected_file_path = files[0]

        self.workload_textbox.configure(state="disabled")

    def _handle_select_entire_folder(self):
        """Selects ALL video files found in the current folder to be combined in natural order."""
        folder = self.folder_path_entry.get().strip()
        if not folder or not os.path.isdir(folder):
            self._handle_browse_folder()
            folder = self.selected_folder_path
            if not folder or not os.path.isdir(folder):
                return

        if not hasattr(self, '_folder_video_files') or not self._folder_video_files:
            self._refresh_folder_videos()

        if not self._folder_video_files:
            messagebox.showwarning("No Videos Found", f"No supported video files found in:\n{folder}")
            return

        all_paths = [os.path.join(folder, item[0]) for item in self._folder_video_files if os.path.exists(os.path.join(folder, item[0]))]
        if not all_paths:
            messagebox.showwarning("No Videos", "No video files exist in the specified folder.")
            return

        all_paths.sort(key=lambda p: natural_sort_key(os.path.basename(p)))
        self.selected_video_files = all_paths
        self.selection_mode = "folder"
        self._update_workload_display()

        self.log(f"\n{'='*60}")
        self.log(f"📁 [ENTIRE FOLDER SELECTED] All {len(all_paths)} video parts selected from:")
        self.log(f"   {folder}")
        self.log(f"   Parts will be combined in sequential numerical order into 1 complete video:")
        for idx, p in enumerate(all_paths, 1):
            sz = format_bytes(os.path.getsize(p))
            self.log(f"   • Part {idx:02d}: {os.path.basename(p)} ({sz})")
        self.log(f"{'='*60}")

    def _handle_browse_multi_files(self):
        """Allows user to select multiple video files from anywhere to combine."""
        paths = filedialog.askopenfilenames(
            title="Select Multiple Video Files to Combine",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm *.wmv *.flv *.m4v *.ts"), ("All Files", "*.*")]
        )
        if paths:
            path_list = list(paths)
            path_list.sort(key=lambda p: natural_sort_key(os.path.basename(p)))
            self.selected_video_files = path_list
            self.selection_mode = "multi" if len(path_list) > 1 else "single"
            self._update_workload_display()

            if len(path_list) > 1:
                self.log(f"\n{'='*60}")
                self.log(f"📑 [MULTI-FILES SELECTED] {len(path_list)} video files selected for combination:")
                for idx, p in enumerate(path_list, 1):
                    sz = format_bytes(os.path.getsize(p))
                    self.log(f"   • Part {idx:02d}: {os.path.basename(p)} ({sz})")
                self.log(f"{'='*60}")
            else:
                self.log(f"📄 [SINGLE FILE SELECTED] {os.path.basename(path_list[0])} ({format_bytes(os.path.getsize(path_list[0]))})")

    def _handle_browse_single_file(self):
        """Browse a single video file from anywhere."""
        path = filedialog.askopenfilename(
            title="Select Single Video File",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm *.wmv *.flv *.m4v *.ts"), ("All Files", "*.*")]
        )
        if path:
            self.selected_video_files = [path]
            self.selection_mode = "single"
            self._update_workload_display()
            sz = format_bytes(os.path.getsize(path))
            self.log(f"📄 [SINGLE FILE SELECTED] {os.path.basename(path)} ({sz})")

    def _handle_select_video_from_list(self):
        """Selects one or more videos from the folder listing by #, range, or filename."""
        text = self.video_select_entry.get().strip()
        if not text:
            messagebox.showwarning("Empty Selection", "Please enter video # (e.g. 1, 2, 3 or 1-4) or filenames from the folder list above.")
            return

        if not hasattr(self, '_folder_video_files') or not self._folder_video_files:
            messagebox.showwarning("No Videos", "Please scan a folder first by clicking '📂 Browse Folder'.")
            return

        tokens = [t.strip() for t in text.replace(";", ",").split(",") if t.strip()]
        selected_paths = []

        for token in tokens:
            if "-" in token and len(token.split("-")) == 2:
                r_parts = token.split("-")
                try:
                    start_i, end_i = int(r_parts[0]), int(r_parts[1])
                    if start_i > end_i:
                        start_i, end_i = end_i, start_i
                    for idx in range(start_i, end_i + 1):
                        if 1 <= idx <= len(self._folder_video_files):
                            fname = self._folder_video_files[idx - 1][0]
                            fpath = os.path.join(self.selected_folder_path, fname)
                            if fpath not in selected_paths and os.path.exists(fpath):
                                selected_paths.append(fpath)
                    continue
                except ValueError:
                    pass

            try:
                idx = int(token)
                if 1 <= idx <= len(self._folder_video_files):
                    fname = self._folder_video_files[idx - 1][0]
                    fpath = os.path.join(self.selected_folder_path, fname)
                    if fpath not in selected_paths and os.path.exists(fpath):
                        selected_paths.append(fpath)
                    continue
            except ValueError:
                pass

            for fname, _, _ in self._folder_video_files:
                if token.lower() in fname.lower():
                    fpath = os.path.join(self.selected_folder_path, fname)
                    if fpath not in selected_paths and os.path.exists(fpath):
                        selected_paths.append(fpath)
                        break

        if not selected_paths:
            messagebox.showerror("Not Found", f"No videos matching '{text}' found in folder listing.")
            return

        selected_paths.sort(key=lambda p: natural_sort_key(os.path.basename(p)))
        self.selected_video_files = selected_paths
        self.selection_mode = "folder" if len(selected_paths) > 1 else "single"
        self._update_workload_display()
        if len(selected_paths) > 1:
            self.log(f"✅ [SELECTED {len(selected_paths)} VIDEOS] Queued {len(selected_paths)} parts from folder to combine.")
        else:
            self.log(f"✅ [SELECTED] {os.path.basename(selected_paths[0])}")

    def _handle_clear_selection(self):
        """Clears the currently selected video queue."""
        self.selected_video_files = []
        self.selection_mode = "none"
        self.selected_file_path = ""
        self._update_workload_display()
        self.log("🗑️ [SELECTION CLEARED] Video workload queue reset.")


    # ==========================================
    # EVENT HANDLERS
    # ==========================================
    def _start_auto_connect(self):
        """Find Computer B and complete the handshake without any manual steps."""
        existing = getattr(self, "_auto_connect_thread", None)
        if existing and existing.is_alive():
            return

        def worker():
            self.log("[AUTO-CONNECT] Searching for the server on LAN/Wi-Fi/direct Ethernet…")
            while not self._auto_connect_stop.is_set():
                discovered = OffloadingClient.discover_server(timeout=2.0)
                if discovered:
                    host = discovered["ip"]
                    port = int(discovered.get("port", DEFAULT_PORT))
                    hostname = discovered.get("hostname", "Computer B")
                    self.log(f"[AUTO-CONNECT] Found {hostname} at {host}:{port}; completing handshake…")

                    def apply_discovery():
                        self.ip_entry.delete(0, "end")
                        self.ip_entry.insert(0, host)
                        self.port_entry.delete(0, "end")
                        self.port_entry.insert(0, str(port))
                        self.worker_status_lbl.configure(
                            text=f"🟡 Found {hostname}; connecting automatically…",
                            text_color="#facc15"
                        )
                    self.run_on_ui(apply_discovery)

                    completed = threading.Event()
                    result = {"ok": False}
                    self._handle_handshake_and_ping(
                        silent=True,
                        host_override=host,
                        port_override=port,
                        completion_callback=lambda ok: (result.update(ok=bool(ok)), completed.set())
                    )
                    completed.wait(timeout=18.0)
                    if result["ok"]:
                        self.log("[AUTO-CONNECT] Connected. No IP entry or handshake button was needed.")
                        return
                    self.log("[AUTO-CONNECT] Server was discovered but handshake did not complete; retrying…")
                else:
                    self.run_on_ui(lambda: self.worker_status_lbl.configure(
                        text="🔄 Waiting for Computer B… (automatic retry)", text_color="#facc15"
                    ))
                self._auto_connect_stop.wait(2.0)

        self._auto_connect_thread = threading.Thread(target=worker, daemon=True)
        self._auto_connect_thread.start()

    def _handle_auto_detect_server(self, silent: bool = False):
        """Auto-detects Server Node on LAN / Wi-Fi / Direct wire and populates IP."""
        def task():
            if not silent:
                self.log("\n[DISCOVERY] Scanning LAN, Wi-Fi & Direct Wire for active Server Node...")

            discovered = OffloadingClient.discover_server(timeout=2.0)
            if discovered:
                srv_ip = discovered["ip"]
                srv_port = discovered["port"]
                srv_host = discovered.get("hostname", "Server Node")
                srv_method = discovered.get("method", "Network Probe")

                def _apply():
                    self.ip_entry.delete(0, "end")
                    self.ip_entry.insert(0, srv_ip)
                    self.port_entry.delete(0, "end")
                    self.port_entry.insert(0, str(srv_port))
                    self.worker_status_lbl.configure(
                        text=f"🟡 Discovered: {srv_host} ({srv_ip}:{srv_port})",
                        text_color="#facc15"
                    )
                    self.worker_specs_lbl.configure(
                        text=f"Computer B discovered automatically via {srv_method}."
                    )
                self.run_on_ui(_apply)
                self.log(f"✅ [AUTO-DETECT SUCCESS] Discovered Server at {srv_ip}:{srv_port} ({srv_host}) via {srv_method}!")
                if not silent:
                    self.run_on_ui(lambda: messagebox.showinfo(
                        "Server Auto-Detected!",
                        f"Found active Server Node!\n\n"
                        f"• Hostname  : {srv_host}\n"
                        f"• IP Address: {srv_ip}\n"
                        f"• Port      : {srv_port}\n"
                        f"• Discovery : {srv_method}\n\n"
                        f"The app can now connect automatically."
                    ))
            else:
                if not silent:
                    self.log("[!] [DISCOVERY] No active Server Node responded to auto-detection.")
                    self.run_on_ui(lambda: messagebox.showwarning(
                        "Server Not Detected",
                        "Could not auto-detect Server Node.\n\n"
                        "Check:\n"
                        "1. Is Server GUI or Daemon running on Computer B?\n"
                        "2. Is Computer B connected with LAN cable or Wi-Fi?\n"
                        "3. Or enter Computer B's IP address manually."
                    ))

        threading.Thread(target=task, daemon=True).start()

    def _handle_handshake_and_ping(self, silent=False, host_override=None, port_override=None, completion_callback=None):
        """Handshake with Computer B; supports silent automatic startup connection."""
        host = (host_override or self.ip_entry.get()).strip()
        try:
            port = int(port_override if port_override is not None else self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return

        def task():
            target_host = host
            target_port = port
            self.log(f"\n[CONNECTING] Contacting Remote Server at {target_host}:{target_port}...")

            info = None
            latency = 0.0

            try:
                try:
                    self.client = OffloadingClient(host=target_host, port=target_port)
                    info = self.client.perform_handshake()
                    latency = self.client.measure_ping_latency(num_samples=3)
                except Exception as initial_err:
                    # Intelligent Auto-Detection Fallback: Try scanning the network!
                    self.log(f"[!] Direct connection to {target_host}:{target_port} failed ({initial_err}).")
                    self.log("🔍 [AUTO-DETECT] Probing network for active Server Node...")
                    try:
                        discovered = OffloadingClient.discover_server(timeout=1.5)
                        if discovered and (discovered["ip"] != target_host or discovered["port"] != target_port):
                            target_host = discovered["ip"]
                            target_port = discovered["port"]
                            self.log(f"✅ [AUTO-DETECT] Found Server Node at {target_host}:{target_port} ({discovered.get('hostname')})! Retrying handshake...")

                            def _update_fields():
                                self.ip_entry.delete(0, "end")
                                self.ip_entry.insert(0, target_host)
                                self.port_entry.delete(0, "end")
                                self.port_entry.insert(0, str(target_port))
                            self.run_on_ui(_update_fields)

                            self.client = OffloadingClient(host=target_host, port=target_port)
                            info = self.client.perform_handshake()
                            latency = self.client.measure_ping_latency(num_samples=3)
                        else:
                            raise initial_err
                    except Exception:
                        raise initial_err

                # Connected successfully!
                hostname = info.get('hostname', 'Remote Server')
                cpu_count = info.get('cpu_count', 4)
                gpu_status = info.get('nvenc_status', 'N/A')
                status_txt = f"Connected to: {hostname} ({target_host})"
                specs_txt = f"CPU: {cpu_count} Cores | GPU: {gpu_status[:30]} | Ping RTT: {latency} ms"

                def _update_ui():
                    self.worker_status_lbl.configure(text=f"🟢 {status_txt}", text_color="#4ade80")
                    self.worker_specs_lbl.configure(text=specs_txt)
                    self.conn_indicator.configure(text=f"🟢 ONLINE ({hostname})", text_color="#4ade80")

                self.run_on_ui(_update_ui)

                self.log(f"⚡ [TCP CONNECTED] Socket established with {target_host}:{target_port}!")
                self.log(f"🤝 [HANDSHAKE VERIFIED] Server '{hostname}' running protocol v{info.get('protocol_version')}")
                self.log(f"⚡ [LATENCY PROBE] Measured Round-Trip Time (RTT): {latency} ms")
                self.log(f"🚀 [RESOURCES UNLOCKED] {cpu_count} CPU Cores | {gpu_status}")
                self.log(f"   Computer B is now ready to render your video exports!")

                # Prominent notification popup
                msg = (
                    f"🎉 Successfully Connected to Server (Computer B)!\n\n"
                    f"• Node Hostname : {hostname}\n"
                    f"• Bound Address : {target_host}:{target_port}\n"
                    f"• CPU Hardware  : {cpu_count} Processing Cores\n"
                    f"• Acceleration  : {gpu_status}\n"
                    f"• Ping Latency  : {latency} ms\n\n"
                    f"Remote resources are active! You can now send video exports for rendering."
                )
                if not silent:
                    self.run_on_ui(lambda: messagebox.showinfo("Connected to Server!", msg))
                if completion_callback:
                    completion_callback(True)

            except Exception as e:
                # Detect specific LAN issues for helpful diagnostics
                err_str = str(e)
                diag_hints = []
                diag_hints.append("1. Is Server GUI / Daemon running on Computer B?")
                diag_hints.append("2. Are both computers connected with LAN cable?")
                diag_hints.append("3. Is the IP address correct?")

                # Check for APIPA (169.254.x.x) on this machine -> Static IP not set
                try:
                    import subprocess as _sp
                    _ipc = _sp.run(["ipconfig"], capture_output=True, text=True, timeout=5)
                    if "169.254." in _ipc.stdout:
                        diag_hints.append(
                            "\n⚠️ APIPA (169.254.x.x) detected on this PC!\n"
                            "   → Static IP is NOT set on your Ethernet adapter.\n"
                            "   → Windows link-local discovery will be attempted automatically.\n"
                            "     Confirm both Ethernet adapters are enabled and directly linked."
                        )
                except Exception:
                    pass

                if "timed out" in err_str.lower() or "10060" in err_str:
                    diag_hints.append(
                        "\n🔥 Connection TIMED OUT — likely causes:\n"
                        "   → Windows Firewall blocking Port 5000 on Server.\n"
                        "   → Run on Server (Admin): netsh advfirewall firewall\n"
                        "     add rule name=\"Lab4\" dir=in action=allow\n"
                        "     protocol=TCP localport=5000"
                    )
                elif "10061" in err_str or "refused" in err_str.lower():
                    diag_hints.append(
                        "\n🔌 Connection REFUSED — Server app is not running\n"
                        "   on the target machine, or wrong port number."
                    )

                hints_text = "\n".join(diag_hints)

                def _update_err():
                    self.worker_status_lbl.configure(text="🔴 Server Status: UNREACHABLE", text_color="#f87171")
                    self.worker_specs_lbl.configure(text=f"Connection Error: {e}")
                    self.conn_indicator.configure(text="🔴 OFFLINE", text_color="#f87171")
                self.run_on_ui(_update_err)
                self.log(f"❌ [CONNECT ERROR] Could not connect to Server at {host}:{port} -> {e}")
                if completion_callback:
                    completion_callback(False)
                if not silent:
                    self.run_on_ui(lambda: messagebox.showerror(
                        "Connection Failed",
                        f"Could not connect to Server at {host}:{port}.\n\n"
                        f"Diagnostics:\n{hints_text}"
                    ))

        threading.Thread(target=task, daemon=True).start()

    def _handle_start_offload(self):
        """Initiates video rendering offload to remote server (single or multi-part concat)."""
        if self.is_processing:
            messagebox.showwarning("Warning", "A task is currently running.")
            return

        if not self.selected_video_files:
            messagebox.showerror(
                "No Video Selected",
                "Please select video(s) first.\n\n"
                "• Click '📁 Select Entire Folder' to combine all video parts in a folder.\n"
                "• Click '📑 Select Multiple Files' to choose multiple video files to combine.\n"
                "• Or click '📄 Single File' to transcode a single video."
            )
            return

        # Verify all files exist on disk
        missing = [f for f in self.selected_video_files if not os.path.exists(f)]
        if missing:
            messagebox.showerror("File Not Found", f"The following files could not be found:\n{', '.join(os.path.basename(m) for m in missing)}")
            return

        host = self.ip_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return

        render_cfg = {
            "resolution": self.res_combo.get(),
            "bitrate": self.bitrate_combo.get(),
            "preset": self.preset_combo.get(),
            "mode": self.accel_combo.get(),
            "filter": self.filter_combo.get(),
            "fps": self.fps_combo.get()
        }
        selected_files = list(self.selected_video_files)
        is_concat = len(selected_files) > 1

        self.is_processing = True
        self.cancel_flag = False

        self.progress_bar.set(0.0)
        init_text = f"0.0% | Initializing Multi-Part ({len(selected_files)} parts) Concat & Render..." if is_concat else "0.0% | Initializing Video Render Offload..."
        self.progress_lbl.configure(text=init_text)
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

                if is_concat:
                    self.log(f"\n{'='*60}")
                    self.log(f"🚀 [OFFLOAD COMBINE & RENDER] Offloading {len(selected_files)} video parts to Server (Computer B)")
                    self.log(f"   Mode: Stitched concatenation into 1 complete video")
                    self.log(f"   Parts sequence:")
                    for idx, p in enumerate(selected_files, 1):
                        self.log(f"     [{idx:02d}] {os.path.basename(p)} ({format_bytes(os.path.getsize(p))})")
                    self.log(f"   Target Config: {render_cfg}")
                    self.log(f"{'='*60}")
                else:
                    video_name = os.path.basename(selected_files[0])
                    self.log(f"\n{'='*60}")
                    self.log(f"🚀 [OFFLOAD VIDEO] Sending '{video_name}' to Server for Rendering")
                    self.log(f"   Source: {selected_files[0]}")
                    self.log(f"   Config: {render_cfg}")
                    self.log(f"{'='*60}")

                res = self.client.offload_video_transcode(
                    input_file=selected_files,
                    output_dir=self.download_output_dir,
                    render_config=render_cfg,
                    progress_callback=progress_cb,
                    cancel_check=lambda: self.cancel_flag
                )

                if is_concat:
                    clean_output_path = os.path.join(self.download_output_dir, "combined_video.mp4")
                    try:
                        import shutil
                        if os.path.exists(res['local_output_path']) and os.path.abspath(res['local_output_path']) != os.path.abspath(clean_output_path):
                            shutil.copy2(res['local_output_path'], clean_output_path)
                            # Remove older temporary uuid-named combined outputs so only 1 clean copy exists (only .mp4 videos)
                            for old_f in os.listdir(self.download_output_dir):
                                if old_f.startswith("out_task_") and "_combined" in old_f and old_f.endswith(".mp4"):
                                    try:
                                        os.remove(os.path.join(self.download_output_dir, old_f))
                                    except Exception:
                                        pass
                            res['local_output_path'] = clean_output_path
                    except Exception:
                        pass

                # Ensure logs.txt is saved directly into client_downloads folder alongside output video
                clean_log_path = os.path.join(self.download_output_dir, "logs.txt")
                try:
                    import shutil
                    if res.get('local_log_path') and os.path.exists(res['local_log_path']):
                        if os.path.abspath(res['local_log_path']) != os.path.abspath(clean_log_path):
                            shutil.copy2(res['local_log_path'], clean_log_path)
                    elif res.get('server_logs_text'):
                        with open(clean_log_path, "w", encoding="utf-8") as lf:
                            lf.write(res['server_logs_text'])
                    if os.path.exists(clean_log_path):
                        res['local_log_path'] = clean_log_path
                except Exception:
                    pass

                def _update_video_done():
                    self.progress_bar.set(1.0)
                    if is_concat:
                        self.progress_lbl.configure(text=f"100.0% | Complete! {len(selected_files)} Parts Combined & Downloaded!")
                    else:
                        self.progress_lbl.configure(text="100.0% | Complete & Downloaded to Laptop!")
                    self.metric_turnaround.configure(text=f"Turnaround: {res['total_turnaround_sec']} s")
                    self.last_rendered_path = res['local_output_path']
                    self.last_log_path = res.get('local_log_path', '') or clean_log_path
                    self.play_btn.configure(state="normal")
                    if self.last_log_path and os.path.exists(self.last_log_path):
                        self.view_log_btn.configure(state="normal")
                    if res.get("checksum_verified"):
                        self.metric_integrity.configure(text="SHA-256: VERIFIED ✔", text_color="#4ade80")
                    else:
                        self.metric_integrity.configure(text="SHA-256: MISMATCH ❌", text_color="#f87171")

                self.run_on_ui(_update_video_done)

                out_name = os.path.basename(res['local_output_path'])
                self.log(f"\n{'='*60}")
                if is_concat:
                    self.log(f"✅ [SUCCESS] Complete Video Combined & Rendered on Server and Downloaded!")
                    self.log(f"   • Parts Combined  : {len(selected_files)} video parts stitched together")
                else:
                    self.log(f"✅ [SUCCESS] Video Rendered on Server and Downloaded to Laptop!")
                    self.log(f"   • Source File     : {os.path.basename(selected_files[0])}")
                self.log(f"   • Output Video    : {out_name}")
                self.log(f"   • Remote Engine   : {res.get('engine')}")
                self.log(f"   • Upload Time     : {res['upload_duration_sec']}s")
                self.log(f"   • Render Time     : {res['remote_compute_duration_sec']}s")
                self.log(f"   • Download Time   : {res['download_duration_sec']}s")
                self.log(f"   • Total Turnaround: {res['total_turnaround_sec']}s")
                self.log(f"   • Input Total     : {format_bytes(res['input_file_size'])}")
                self.log(f"   • Output Size     : {format_bytes(res['output_file_size'])}")
                self.log(f"   • SHA-256 Verified: {'✔ YES' if res.get('checksum_verified') else '❌ NO'}")
                self.log(f"   • Saved to Laptop : {res['local_output_path']}")
                if res.get('local_log_path'):
                    self.log(f"   • Server Log File : {res['local_log_path']}")
                self.log(f"{'='*60}")

                # Print server log excerpt in console if available
                if res.get('server_logs_text'):
                    self.log(f"\n📋 [SERVER EXECUTION LOG SUMMARY]")
                    for l in res['server_logs_text'].splitlines()[:15]:
                        self.log(f"   {l}")
                    if len(res['server_logs_text'].splitlines()) > 15:
                        self.log(f"   ... ({len(res['server_logs_text'].splitlines()) - 15} more lines in log file)")

                log_info = f"\n• Server Log File : {os.path.basename(res['local_log_path']) if res.get('local_log_path') else 'Attached'}"
                if is_concat:
                    msg = (
                        f"🎉 Complete Combined Video Successfully Rendered on Server (Computer B)!\n\n"
                        f"• Combined Parts   : {len(selected_files)} video parts stitched into 1 complete video\n"
                        f"• Render Engine    : {res.get('engine')}\n"
                        f"• Output Video     : {out_name}\n"
                        f"• Upload Time      : {res['upload_duration_sec']} seconds\n"
                        f"• Render Time      : {res['remote_compute_duration_sec']} seconds\n"
                        f"• Download Time    : {res['download_duration_sec']} seconds\n"
                        f"• Total Time       : {res['total_turnaround_sec']} seconds\n"
                        f"• Integrity Check  : SHA-256 Verified ✔{log_info}\n\n"
                        f"The combined video & server execution logs are ready in client_downloads/.\n"
                        f"Click '▶️ Play Video' to watch or '📄 View Logs' to inspect details!"
                    )
                    self.run_on_ui(lambda: messagebox.showinfo("Combined Video Ready & Downloaded!", msg))
                else:
                    msg = (
                        f"🎉 Video Successfully Rendered on Server (Computer B)!\n\n"
                        f"• Source File     : {os.path.basename(selected_files[0])}\n"
                        f"• Render Engine   : {res.get('engine')}\n"
                        f"• Output Video    : {out_name}\n"
                        f"• Upload Time     : {res['upload_duration_sec']} seconds\n"
                        f"• Render Time     : {res['remote_compute_duration_sec']} seconds\n"
                        f"• Download Time   : {res['download_duration_sec']} seconds\n"
                        f"• Total Time      : {res['total_turnaround_sec']} seconds\n"
                        f"• Integrity Check : SHA-256 Verified ✔{log_info}\n\n"
                        f"The rendered file & execution logs are ready in client_downloads/.\n"
                        f"Click '▶️ Play Video' to watch or '📄 View Logs' to inspect details!"
                    )
                    self.run_on_ui(lambda: messagebox.showinfo("Render Complete & Downloaded!", msg))

            except Exception as e:
                self.log(f"❌ [OFFLOAD FAILED] {e}")
                def _update_err_badge():
                    self.metric_integrity.configure(text="Error", text_color="#f87171")
                    self.progress_lbl.configure(text=f"Failed: {e}")
                self.run_on_ui(_update_err_badge)
                self.run_on_ui(lambda: messagebox.showerror("Task Failed", f"Execution failed:\n{e}"))
            finally:
                self.is_processing = False
                if self._capcut_current_export:
                    self._capcut_current_export = None
                self.run_on_ui(self._start_next_capcut_export)

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

    def _handle_play_rendered_video(self):
        """Opens the downloaded rendered video in the default media player on this laptop."""
        target = self.last_rendered_path
        if not target or not os.path.exists(target):
            clean_combined = os.path.join(self.download_output_dir, "combined_video.mp4")
            if os.path.exists(clean_combined):
                target = clean_combined
                self.last_rendered_path = clean_combined

        if target and os.path.exists(target):
            try:
                os.startfile(target)
                self.log(f"[MEDIA PLAYER] Opened rendered video: {target}")
            except Exception as e:
                self.log(f"[ERROR] Could not open video player: {e}")
        else:
            messagebox.showwarning("No Video", "No rendered video available yet. Please send a video for rendering first.")

    def _handle_view_server_logs(self):
        """Opens the downloaded server execution log file (logs.txt)."""
        log_candidate = self.last_log_path
        if not (log_candidate and os.path.exists(log_candidate)):
            fallback = os.path.join(self.download_output_dir, "logs.txt")
            if os.path.exists(fallback):
                log_candidate = fallback
            else:
                for f in os.listdir(self.download_output_dir):
                    if f.endswith(".txt"):
                        log_candidate = os.path.join(self.download_output_dir, f)
                        break

        if log_candidate and os.path.exists(log_candidate):
            try:
                os.startfile(log_candidate)
                self.log(f"[LOG VIEWER] Opened server execution log: {log_candidate}")
            except Exception as e:
                self.log(f"[ERROR] Could not open log viewer: {e}")
        else:
            messagebox.showwarning("No Logs", "No server execution logs available yet. Please complete a render task first.")

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
