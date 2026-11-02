"""
================================================================================
CSC-334: Parallel and Distributed Computing
Lab 4: Custom Distributed Task Offloading & Remote GPU Rendering System
Module: server/server_daemon.py
Description: Server Daemon Entrypoint and CLI Runner.
================================================================================
"""

import os
import sys
import argparse
import signal

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app_paths import get_runtime_data_dir
from network_server import RemoteWorkerServer
from protocol import DEFAULT_PORT


def main():
    parser = argparse.ArgumentParser(description="CSC-334: Remote GPU Task Execution Engine Daemon")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Binding host IP (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Binding TCP port (default: {DEFAULT_PORT})")
    default_storage = os.path.join(get_runtime_data_dir("Server", current_dir), "server_storage")
    parser.add_argument("--storage", type=str, default=default_storage, help="Storage directory")
    args = parser.parse_args()

    server = RemoteWorkerServer(host=args.host, port=args.port, storage_dir=args.storage)

    def signal_handler(sig, frame):
        print("\n[*] Interruption signal received. Stopping worker daemon...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
