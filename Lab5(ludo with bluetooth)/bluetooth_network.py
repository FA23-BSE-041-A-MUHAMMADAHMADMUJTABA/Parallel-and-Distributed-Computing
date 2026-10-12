"""
================================================================================
CSC-334: Parallel and Distributed Computing - Lab 5
Module: Lab5(ludo with bluetooth)/bluetooth_network.py
Description: Bluetooth & Offline Peer-to-Peer Networking Engine for Ludo.
             Supports Bluetooth RFCOMM sockets, Bluetooth PAN (Tethering),
             and Offline Direct P2P Broadcast without requiring internet.
             Manages Desk creation, 4-digit Desk Codes, lobby synchronization,
             and leader-only game start authorization.
================================================================================
"""

import os
import sys
import time
import json
import uuid
import struct
import socket
import select
import random
import threading
from typing import Dict, List, Optional, Callable, Any, Tuple

DEFAULT_OFFLINE_PORT = 8888
BROADCAST_BEACON_PORT = 8889
MAGIC_LUDO = b"LU"
HEADER_FORMAT = ">2sH"  # 2 bytes magic, 2 bytes payload length (uint16)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


def generate_desk_code() -> str:
    """Generates an intuitive 4-digit Desk Code (e.g. '7429') for easy sharing."""
    return f"{random.randint(1000, 9999)}"


def get_offline_ips() -> List[str]:
    """Retrieves all local Bluetooth PAN and offline network IP addresses."""
    ips = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ":" not in ip and not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass

    if not ips:
        ips.add("127.0.0.1")
    return sorted(list(ips))


def send_packet(sock: socket.socket, data: Dict[str, Any]) -> None:
    """Sends JSON dictionary payload framed with 4-byte header."""
    payload = json.dumps(data).encode("utf-8")
    if len(payload) > 65535:
        raise ValueError("Payload exceeds maximum packet size")
    header = struct.pack(HEADER_FORMAT, MAGIC_LUDO, len(payload))
    sock.sendall(header + payload)


def recvall(sock: socket.socket, num_bytes: int) -> bytes:
    """Reliably reads exact num_bytes over TCP or Bluetooth stream."""
    buffer = bytearray(num_bytes)
    view = memoryview(buffer)
    received = 0
    while received < num_bytes:
        chunk = sock.recv_into(view[received:], num_bytes - received)
        if chunk == 0:
            raise ConnectionResetError("Remote peer disconnected.")
        received += chunk
    return bytes(buffer)


def read_packet(sock: socket.socket) -> Optional[Dict[str, Any]]:
    """Reads fixed header and deserializes JSON payload."""
    try:
        header_data = recvall(sock, HEADER_SIZE)
        magic, length = struct.unpack(HEADER_FORMAT, header_data)
        if magic != MAGIC_LUDO:
            return None
        payload = recvall(sock, length)
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


class BluetoothDeskHost:
    """
    Leader (Host) Subsystem:
    - Creates a new Desk with a unique 4-digit Desk Code.
    - Listens for connecting players over Bluetooth PAN and RFCOMM.
    - Advertises offline beacon on the Bluetooth/local link so clients can join by Desk Code.
    - Manages player lobby (Leader = Player 0, Red).
    - Enforces rules: Game only starts when Leader initiates and min 2 players are present.
    - Replicates game actions (dice roll, token move, turns) in real time to all peers.
    """
    def __init__(self, leader_name: str = "Leader", desk_code: Optional[str] = None):
        self.leader_name = leader_name
        self.desk_code = desk_code or generate_desk_code()
        self.port = DEFAULT_OFFLINE_PORT

        # Connected Players list: List of dicts [{"id": str, "name": str, "color_idx": int, "is_leader": bool}]
        self.players: List[Dict[str, Any]] = [
            {"id": "leader", "name": self.leader_name, "color_idx": 0, "is_leader": True}
        ]
        self.client_sockets: Dict[str, socket.socket] = {}
        self._lock = threading.Lock()
        self.is_running = False
        self.game_started = False

        # Sockets
        self.server_sock: Optional[socket.socket] = None
        self.beacon_sock: Optional[socket.socket] = None

        # Event Callbacks
        self.on_lobby_updated: Optional[Callable[[List[Dict[str, Any]]], None]] = None
        self.on_game_action: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None

    def log(self, msg: str):
        ts = time.strftime("[%H:%M:%S]")
        formatted = f"{ts} [BLUETOOTH DESK] {msg}"
        print(formatted)
        if self.on_log:
            try:
                self.on_log(formatted)
            except Exception:
                pass

    def start(self):
        """Starts Bluetooth desk listener and offline discovery beacon."""
        self.is_running = True
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("0.0.0.0", self.port))
        self.server_sock.listen(5)
        self.server_sock.settimeout(1.0)

        self.log(f"🟢 Desk Created! Code: [{self.desk_code}] on Port {self.port}")
        self.log(f"   • Leader: {self.leader_name} (Color: RED)")
        self.log(f"   • Bluetooth Offline IPs: {', '.join(get_offline_ips())}")
        self.log(f"   • Waiting for players to join with Desk Code [{self.desk_code}]...")

        # Start Offline Discovery Beacon
        t_beacon = threading.Thread(target=self._run_beacon_broadcaster, daemon=True)
        t_beacon.start()

        # Start Connection Listener
        t_listener = threading.Thread(target=self._run_listener, daemon=True)
        t_listener.start()

    def _run_beacon_broadcaster(self):
        """Broadcasts beacon on Bluetooth PAN/local link for zero-config Desk Code lookup."""
        try:
            self.beacon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.beacon_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            return

        beacon_data = json.dumps({
            "type": "LUDO_BEACON",
            "desk_code": self.desk_code,
            "leader_name": self.leader_name,
            "port": self.port,
            "players_count": len(self.players),
            "game_started": self.game_started
        }).encode("utf-8")

        while self.is_running:
            try:
                self.beacon_sock.sendto(beacon_data, ("<broadcast>", BROADCAST_BEACON_PORT))
            except Exception:
                pass
            time.sleep(1.0)

    def _run_listener(self):
        """Accepts incoming player socket connections."""
        while self.is_running:
            try:
                client_sock, client_addr = self.server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            t = threading.Thread(target=self._handle_client, args=(client_sock, client_addr), daemon=True)
            t.start()

    def _handle_client(self, client_sock: socket.socket, client_addr: Tuple[str, int]):
        """Processes joining handshake, lobby updates, and in-game moves."""
        client_id = f"peer_{uuid.uuid4().hex[:6]}"
        player_name = "Player"
        color_idx = -1

        try:
            # 1. Wait for Join Request
            msg = read_packet(client_sock)
            if not msg or msg.get("type") != "JOIN_REQUEST":
                client_sock.close()
                return

            req_code = msg.get("desk_code", "").strip()
            player_name = msg.get("player_name", f"Player {len(self.players) + 1}").strip()

            if req_code != self.desk_code:
                send_packet(client_sock, {"type": "JOIN_REJECT", "reason": f"Invalid Desk Code: {req_code}"})
                client_sock.close()
                return

            if self.game_started:
                send_packet(client_sock, {"type": "JOIN_REJECT", "reason": "Game has already started!"})
                client_sock.close()
                return

            with self._lock:
                if len(self.players) >= 4:
                    send_packet(client_sock, {"type": "JOIN_REJECT", "reason": "Desk is full (Max 4 players)"})
                    client_sock.close()
                    return

                color_idx = len(self.players)  # 1: Green, 2: Yellow, 3: Blue
                new_player = {
                    "id": client_id,
                    "name": player_name,
                    "color_idx": color_idx,
                    "is_leader": False
                }
                self.players.append(new_player)
                self.client_sockets[client_id] = client_sock

            self.log(f"🤝 [PLAYER JOINED] {player_name} joined desk! (Color: {color_idx}, Total: {len(self.players)}/4)")

            # Send acceptance to joining player
            send_packet(client_sock, {
                "type": "JOIN_ACCEPT",
                "client_id": client_id,
                "desk_code": self.desk_code,
                "color_idx": color_idx,
                "players": self.players
            })

            # Broadcast updated lobby to all players
            self._broadcast_lobby()

            # 2. Main Game Communication Loop
            while self.is_running:
                action = read_packet(client_sock)
                if not action:
                    break

                # Client wants to roll dice or move token
                if self.on_game_action:
                    self.on_game_action(action)

        except Exception as e:
            self.log(f"Client connection error: {e}")
        finally:
            with self._lock:
                if client_id in self.client_sockets:
                    del self.client_sockets[client_id]
                self.players = [p for p in self.players if p["id"] != client_id]

            self.log(f"🔌 [PLAYER LEFT] {player_name} left the desk.")
            self._broadcast_lobby()
            try:
                client_sock.close()
            except Exception:
                pass

    def _broadcast_lobby(self):
        """Synchronizes current lobby player list to all connected players."""
        packet = {"type": "LOBBY_UPDATE", "players": self.players, "desk_code": self.desk_code}
        self.broadcast(packet)
        if self.on_lobby_updated:
            try:
                self.on_lobby_updated(self.players)
            except Exception:
                pass

    def broadcast(self, data: Dict[str, Any]):
        """Transmits packet to all connected player clients."""
        with self._lock:
            dead_clients = []
            for cid, sock in self.client_sockets.items():
                try:
                    send_packet(sock, data)
                except Exception:
                    dead_clients.append(cid)
            for cid in dead_clients:
                if cid in self.client_sockets:
                    del self.client_sockets[cid]

    def start_game(self) -> bool:
        """Leader initiates the game if min 2 players are present."""
        if len(self.players) < 2:
            self.log("⚠️ Cannot start game: Minimum 2 players required!")
            return False

        self.game_started = True
        self.log(f"🚀 [GAME STARTED] Leader launched game with {len(self.players)} players!")
        self.broadcast({"type": "GAME_START", "players": self.players, "desk_code": self.desk_code})
        return True

    def stop(self):
        """Stops desk host listener cleanly."""
        self.is_running = False
        if self.beacon_sock:
            try:
                self.beacon_sock.close()
            except Exception:
                pass
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
        with self._lock:
            for s in self.client_sockets.values():
                try:
                    s.close()
                except Exception:
                    pass
            self.client_sockets.clear()
        self.log("🛑 Desk closed.")


class BluetoothDeskClient:
    """
    Joining Player Subsystem:
    - Auto-discovers or connects to a Desk via 4-digit Desk Code.
    - Works over Bluetooth PAN / Bluetooth RFCOMM / offline link without internet.
    - Synchronizes lobby and game events in real-time.
    """
    def __init__(self, player_name: str = "Player"):
        self.player_name = player_name
        self.sock: Optional[socket.socket] = None
        self.is_connected = False
        self.my_player_info: Dict[str, Any] = {}
        self.desk_code: str = ""
        self.players_in_desk: List[Dict[str, Any]] = []

        # Event Callbacks
        self.on_lobby_updated: Optional[Callable[[List[Dict[str, Any]]], None]] = None
        self.on_game_started: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_game_sync: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None

    def log(self, msg: str):
        ts = time.strftime("[%H:%M:%S]")
        formatted = f"{ts} [BLUETOOTH CLIENT] {msg}"
        print(formatted)
        if self.on_log:
            try:
                self.on_log(formatted)
            except Exception:
                pass

    def discover_and_join(self, desk_code: str, target_host: Optional[str] = None, timeout: float = 6.0) -> bool:
        """
        Discovers the host advertising desk_code on the Bluetooth/offline link,
        connects, and sends join handshake.
        """
        self.desk_code = desk_code.strip()
        host_ip = target_host
        host_port = DEFAULT_OFFLINE_PORT

        # 1. If host IP not provided, search offline discovery beacon
        if not host_ip:
            self.log(f"🔍 Searching for Desk [{self.desk_code}] over Bluetooth/offline link...")
            disc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            disc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                disc_sock.bind(("", BROADCAST_BEACON_PORT))
            except Exception:
                pass
            disc_sock.settimeout(timeout)

            start_t = time.time()
            while time.time() - start_t < timeout:
                try:
                    data, addr = disc_sock.recvfrom(2048)
                    info = json.loads(data.decode("utf-8"))
                    if info.get("type") == "LUDO_BEACON" and info.get("desk_code") == self.desk_code:
                        host_ip = addr[0]
                        host_port = info.get("port", DEFAULT_OFFLINE_PORT)
                        self.log(f"✔ Found Desk [{self.desk_code}] at {host_ip}:{host_port}!")
                        break
                except socket.timeout:
                    break
                except Exception:
                    pass
            try:
                disc_sock.close()
            except Exception:
                pass

        # Fallback to localhost if testing locally
        if not host_ip:
            host_ip = "127.0.0.1"

        # 2. Establish TCP connection
        self.log(f"Connecting to Desk at {host_ip}:{host_port}...")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect((host_ip, host_port))
        self.is_connected = True

        # 3. Send Join Request
        send_packet(self.sock, {
            "type": "JOIN_REQUEST",
            "desk_code": self.desk_code,
            "player_name": self.player_name
        })

        resp = read_packet(self.sock)
        if not resp:
            raise ConnectionError("Host did not respond.")

        if resp.get("type") == "JOIN_REJECT":
            raise ValueError(resp.get("reason", "Rejected by desk."))

        if resp.get("type") == "JOIN_ACCEPT":
            self.my_player_info = {
                "id": resp.get("client_id"),
                "color_idx": resp.get("color_idx"),
                "name": self.player_name,
                "is_leader": False
            }
            self.players_in_desk = resp.get("players", [])
            self.log(f"🎉 Joined Desk [{self.desk_code}] successfully! Assigned Color: {self.my_player_info['color_idx']}")

            # Start background message listener
            t_recv = threading.Thread(target=self._listen_loop, daemon=True)
            t_recv.start()
            return True

        return False

    def _listen_loop(self):
        """Continuously reads server game and lobby broadcast packets."""
        while self.is_connected and self.sock:
            try:
                msg = read_packet(self.sock)
                if not msg:
                    break

                mtype = msg.get("type")
                if mtype == "LOBBY_UPDATE":
                    self.players_in_desk = msg.get("players", [])
                    if self.on_lobby_updated:
                        self.on_lobby_updated(self.players_in_desk)

                elif mtype == "GAME_START":
                    self.players_in_desk = msg.get("players", [])
                    if self.on_game_started:
                        self.on_game_started(msg)

                elif mtype == "GAME_SYNC":
                    if self.on_game_sync:
                        self.on_game_sync(msg.get("state", {}))

            except Exception:
                break

        self.is_connected = False
        self.log("Disconnected from Desk.")
        if self.on_disconnected:
            try:
                self.on_disconnected()
            except Exception:
                pass

    def send_action(self, action_data: Dict[str, Any]):
        """Transmits player move or dice roll to Host."""
        if self.is_connected and self.sock:
            try:
                send_packet(self.sock, action_data)
            except Exception:
                pass

    def disconnect(self):
        """Closes connection."""
        self.is_connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
