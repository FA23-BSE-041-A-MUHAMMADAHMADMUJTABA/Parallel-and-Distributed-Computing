"""Small Windows first-run helpers for the two one-click desktop apps."""
from __future__ import annotations

import os
import subprocess
from typing import Callable, Optional


TCP_RULE = "CSC334-Distributed-Render-TCP5000"
UDP_RULE = "CSC334-Distributed-Render-UDP5005"


def ensure_windows_firewall_access(log: Optional[Callable[[str], None]] = None) -> str:
    """Create private/domain LAN firewall rules, requesting UAC only if missing.

    Does nothing on non-Windows systems. The rules are restricted to the local
    subnet and are persistent, so the UAC prompt is normally a first-run-only
    step per computer.
    """
    emit = log or (lambda _message: None)
    if os.name != "nt":
        return "not-windows"

    rules = [
        (TCP_RULE, "TCP", "5000"),
        (UDP_RULE, "UDP", "5005"),
    ]
    missing = []
    for name, protocol, port in rules:
        try:
            check = subprocess.run(
                ["netsh", "advfirewall", "firewall", "show", "rule", f"name={name}"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if check.returncode != 0:
                missing.append((name, protocol, port))
        except Exception:
            missing.append((name, protocol, port))

    if not missing:
        emit("[FIREWALL] LAN access rules already exist; no setup needed.")
        return "already-configured"

    # One elevated command adds both required rules in one UAC approval.
    commands = []
    for name, protocol, port in missing:
        commands.append(
            f'netsh advfirewall firewall add rule name="{name}" '
            f'dir=in action=allow protocol={protocol} localport={port} '
            'profile=private,domain remoteip=localsubnet'
        )
    command_line = " & ".join(commands)

    try:
        import ctypes
        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        is_admin = False

    if is_admin:
        completed = subprocess.run(
            ["cmd.exe", "/c", command_line],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if completed.returncode == 0:
            emit("[FIREWALL] Private-LAN TCP/UDP access configured.")
            return "configured"
        emit(f"[FIREWALL] Could not configure rules automatically: {completed.stderr or completed.stdout}")
        return "failed"

    try:
        # ShellExecute 'runas' causes a single standard Windows UAC approval.
        params = f'/c {command_line}'
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "cmd.exe", params, None, 0
        )
        if result > 32:
            emit("[FIREWALL] Windows asked for one-time permission to allow this app on your private LAN.")
            return "uac-requested"
        emit("[FIREWALL] Permission was not granted. Allow the app through Windows Firewall to connect the computers.")
        return "permission-denied"
    except Exception as exc:
        emit(f"[FIREWALL] Automatic firewall setup unavailable: {exc}. Allow TCP 5000 and UDP 5005 on Private networks.")
        return "failed"
