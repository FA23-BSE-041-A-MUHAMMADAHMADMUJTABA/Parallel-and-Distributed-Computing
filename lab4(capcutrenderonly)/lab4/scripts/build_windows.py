"""Build two independent Windows one-file GUI executables with PyInstaller.

Run from the repository root on Windows:
    py -3.11 -m pip install -r requirements-build.txt
    py -3.11 scripts/build_windows.py

The resulting EXEs are written to release/.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
BUILD = ROOT / "build"


def run_build(name: str, entry_script: Path, extra_collect: list[str]) -> None:
    workpath = BUILD / name.lower()
    specpath = BUILD / "spec"
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", name,
        "--distpath", str(RELEASE),
        "--workpath", str(workpath),
        "--specpath", str(specpath),
        "--paths", str(ROOT),
        "--paths", str(entry_script.parent),
        "--collect-all", "customtkinter",
        "--collect-all", "darkdetect",
        "--collect-all", "imageio_ffmpeg",
        "--collect-all", "numpy",
        *extra_collect,
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "capcut_project",
        str(entry_script),
    ]
    print(f"\n[BUILD] {name}")
    subprocess.run(args, cwd=str(ROOT), check=True)


def main() -> int:
    if os.name != "nt":
        print("ERROR: Windows EXE builds must run on Windows. This script is intentionally Windows-only.")
        return 2

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("ERROR: PyInstaller is missing. Run: python -m pip install -r requirements-build.txt")
        return 2

    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir(parents=True, exist_ok=True)

    # OpenCV is used by the client's sample-video generator, and is dynamically
    # imported inside a function, so collect it explicitly.
    run_build(
        "ComputerA_Client",
        ROOT / "client" / "client_gui.py",
        ["--collect-all", "cv2"],
    )

    run_build(
        "ComputerB_Server",
        ROOT / "server" / "server_gui.py",
        [],
    )

    readme = RELEASE / "READ_FIRST.txt"
    readme.write_text(
        "CSC-334 Distributed Render System\n\n"
        "ONE-CLICK USE (no BAT files, no Python, no IP entry):\n"
        "1) Copy ComputerB_Server.exe to Computer B and double-click it once.\n"
        "2) Copy ComputerA_Client.exe to Computer A and double-click it once.\n"
        "3) Keep both PCs on the same private Wi-Fi/Ethernet LAN. They discover and connect automatically.\n"
        "4) On first server launch, approve the one-time Windows firewall permission if shown.\n\n"
        "No setup_lan_ip scripts, run_client/run_server BAT files, or manual IPs are used.\n"
        "TCP 5000 carries jobs/files; UDP 5005 is used for automatic LAN discovery.\n"
        "The server app stores data in %LOCALAPPDATA%\\CSC334\\Server.\n"
        "The client app stores output in %LOCALAPPDATA%\\CSC334\\Client\\client_downloads.\n\n"
        "The build script is only for generating the EXEs once; do not run it on the target PCs.\n"
        "GPU: Computer B needs a supported NVIDIA GPU/driver and an NVENC-enabled\n"
        "FFmpeg available on PATH (or set FFMPEG_PATH). Otherwise rendering uses CPU.\n",
        encoding="utf-8",
    )

    print("\n[SUCCESS] Built one executable per computer:")
    print(RELEASE / "ComputerA_Client.exe")
    print(RELEASE / "ComputerB_Server.exe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
