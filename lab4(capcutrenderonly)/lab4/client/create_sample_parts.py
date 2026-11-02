"""
Utility script to generate identifiable sample video parts for testing multi-video concatenation.
Each part has a distinct background color, huge part banner, title, live timestamp counter, and distinct audio tone.
"""

import os
import subprocess
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from server.utils import get_ffmpeg_binary
except ImportError:
    from utils import get_ffmpeg_binary

ffmpeg_exe = get_ffmpeg_binary()
output_dir = os.path.join(current_dir, "sample_assets", "sample_parts")
os.makedirs(output_dir, exist_ok=True)

parts_meta = [
    {
        "filename": "part1.mp4",
        "bg_color": "#1e3a8a",       # Vibrant Deep Blue
        "part_num": "PART 1",
        "title": "PART 1 / 3: OPENING SCENE",
        "description": "Video Offloading Pipeline • Computer A (Client)",
        "freq": 440,                  # Musical Note A4
        "duration": 3,
        "accent": "#60a5fa"
    },
    {
        "filename": "part2.mp4",
        "bg_color": "#065f46",       # Vibrant Emerald Green
        "part_num": "PART 2",
        "title": "PART 2 / 3: MAIN WORKLOAD",
        "description": "GPU/Multi-Core Accelerated Render • Computer B (Server)",
        "freq": 554,                  # Musical Note C#5
        "duration": 3,
        "accent": "#34d399"
    },
    {
        "filename": "part3.mp4",
        "bg_color": "#831843",       # Vibrant Crimson / Berry
        "part_num": "PART 3",
        "title": "PART 3 / 3: FINAL OUTRO",
        "description": "Distributed Stitch Complete • SHA-256 Verified",
        "freq": 659,                  # Musical Note E5
        "duration": 3,
        "accent": "#f472b6"
    }
]

print(f"Using FFmpeg: {ffmpeg_exe}")
print(f"Target Directory: {output_dir}")

for p in parts_meta:
    out_file = os.path.join(output_dir, p["filename"])
    
    # Escape any colons in text strings for FFmpeg filter syntax
    safe_part_num = p['part_num'].replace(':', '\\:')
    safe_title = p['title'].replace(':', '\\:')
    safe_desc = p['description'].replace(':', '\\:')

    # Compose comprehensive visual overlay with FFmpeg drawbox and drawtext
    vf_chain = [
        # 1. Solid background color fill
        f"drawbox=x=0:y=0:w=1280:h=720:color={p['bg_color']}:t=fill",
        # 2. Outer decorative glass-like border
        "drawbox=x=30:y=30:w=1220:h=660:color=white@0.25:t=4",
        # 3. Inner banner box for part badge
        "drawbox=x=340:y=120:w=600:h=180:color=black@0.45:t=fill",
        f"drawbox=x=340:y=120:w=600:h=180:color={p['accent']}:t=4",
        # 4. Giant Part Badge Text
        f"drawtext=text='{safe_part_num}':fontcolor=yellow:fontsize=84:x=(w-text_w)/2:y=165",
        # 5. Large Title
        f"drawtext=text='{safe_title}':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=360",
        # 6. Description Subtitle
        f"drawtext=text='{safe_desc}':fontcolor=white@0.9:fontsize=24:x=(w-text_w)/2:y=435",
        # 7. File identifier label
        f"drawtext=text='[ Source File\\: {p['filename']} | Duration\\: {p['duration']}s ]':fontcolor={p['accent']}:fontsize=26:x=(w-text_w)/2:y=505",
        # 8. Live timestamp counter
        "drawtext=text='Timer\\: %{pts\\:hms}':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=580",
        # 9. Format guarantee
        "format=yuv420p"
    ]

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1280x720:d={p['duration']}:r=30",
        "-f", "lavfi", "-i", f"sine=frequency={p['freq']}:duration={p['duration']}",
        "-vf", ",".join(vf_chain),
        "-c:v", "libx264", "-preset", "fast", "-b:v", "2000k", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out_file
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Failed to generate {p['filename']}:")
        print(res.stderr)
    else:
        sz = os.path.getsize(out_file)
        print(f"[OK] Successfully created {p['filename']} ({sz:,} bytes) in {output_dir}")

print("All sample video parts have been generated with clear visual labels!")
