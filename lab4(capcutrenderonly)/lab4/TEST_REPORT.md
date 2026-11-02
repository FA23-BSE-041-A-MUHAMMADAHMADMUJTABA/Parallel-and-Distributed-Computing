# Validation Report

Validation date: 2026-11-02

## Automated checks performed

| Check | Result | Evidence |
|---|---|---|
| Python syntax compilation | PASS | `py_compile` completed for all project Python modules, including the one-click startup helper and Windows build script. |
| One-click startup wiring | PASS (static validation) | Server GUI schedules firewall setup + automatic server start; client GUI retries LAN discovery and silently handshakes without manual IP/button actions. |
| Zero-config LAN discovery + handshake | PASS | Started the actual local server on TCP 5000, discovered it over UDP 5005, connected the client and completed protocol handshake. |
| Firewall helper non-Windows behavior | PASS | Helper safely returns `not-windows` in the Linux test environment; Windows UAC/rule creation remains unverified here. |
| Server bind error reporting | PASS | Occupied TCP port test triggered the callback with a clear bind/listen error instead of leaving a false “listening” status. |
| Obsolete launch scripts | PASS (package check) | Static-IP setup BAT files and old run-client/run-server BAT launchers are removed from the end-user package. |
| Client ↔ server handshake | PASS | Client connected to a local test server and received `READY` capability metadata. |
| Single-video remote encode | PASS | Test MP4 uploaded, CPU FFmpeg render completed, output downloaded and SHA-256 verified. `ffprobe` reported 1.509002 seconds. |
| Two-part concat + render | PASS | Two 1-second clips were concatenated remotely; output duration 2.044898 seconds; SHA-256 verified. |
| LAN file sharing protocol | PASS | Shared text file uploaded, appeared in server file listing, downloaded and byte-compared successfully. |
| CapCut bundle package + path relocation | PASS | Synthetic full draft folder with an internal cover image and an external MP4 reference was packaged; restored media paths resolved to restored files. |
| CapCut draft registration | PASS | Synthetic `draft_meta_info.json` and `root_meta_info.json` were updated, with index backup behavior. |
| CapCut handoff over TCP | PASS | Client uploaded the CapCut ZIP via the existing file-share protocol, sent the new import request, server restored and registered the project, and returned the project path. |
| Output integrity | PASS | Render download validation checked declared size and SHA-256 values. |

## What this environment could not verify

- This run environment is Linux, not Windows. Native Windows `.exe` files were **not built** here. Use `BUILD_WINDOWS.bat` once on a Windows 10/11 x64 build machine with Python 3.11 x64; it creates exactly one client EXE and one server EXE in `release/`. After that, the target PCs only need their respective EXE; no BAT/IP setup is required.
- Automatic Windows Firewall rule creation and UAC approval were not executable in this Linux environment. The server will request a one-time elevated firewall-rule creation for TCP 5000 and UDP 5005, scoped to Private/Domain profiles and the local subnet.
- The UDP discovery + TCP handshake path passed on loopback. The complete GUI auto-start/auto-retry workflow was syntax/static-reviewed but not physically exercised on two Windows PCs in this environment.
- No NVIDIA GPU/NVENC runtime was available for a real hardware render test. The tested render path was CPU `libx264`; NVENC is gated on a successful FFmpeg/device probe and has CPU fallback.
- The GUI was syntax-checked but not interactively exercised on Windows with a real CapCut installation and two physical PCs.
- The new full-draft handoff was tested with synthetic CapCut-like JSON fixtures and over TCP, but **not** with a real CapCut draft or a real Windows CapCut installation in this environment. CapCut's project format is undocumented and version-dependent; cloud/account-gated effects and OS-installed fonts may need manual re-download/install on B.
- The handoff launches CapCut on B if the executable is found. A user must select the transferred project and click Export inside CapCut on B. It does not intercept A's native Export button or automate the export dialog.

## Integration boundary

There are now two distinct workflows. The new full-draft handoff transfers the editable project folder and referenced local assets, registers it on B and opens CapCut there; native CapCut rendering is then performed by the visible CapCut app on B. The older export watcher still performs the alternative A-side CapCut MP4 export followed by an FFmpeg second-pass re-encode on B.
