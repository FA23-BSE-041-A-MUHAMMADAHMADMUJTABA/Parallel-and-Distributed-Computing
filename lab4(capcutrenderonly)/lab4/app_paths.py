"""Runtime paths shared by the source and PyInstaller one-file builds."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def get_runtime_data_dir(app_name: str, source_dir: str) -> str:
    """Return a writable persistent data directory.

    Source runs keep data beside their module for backwards compatibility.
    Frozen Windows builds store data under %LOCALAPPDATA%\\CSC334\\<app_name>
    so one-file extraction to a temporary directory never loses user files.
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = os.path.join(base, "CSC334", app_name)
    else:
        path = os.path.abspath(source_dir)
    os.makedirs(path, exist_ok=True)
    return path
