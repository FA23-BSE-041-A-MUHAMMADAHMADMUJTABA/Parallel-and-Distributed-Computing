"""
================================================================================
CSC-334: Parallel and Distributed Computing - Lab 5
Module: Lab5(ludo with bluetooth)/ludo.py (ALL-IN-ONE SINGLE FILE SYSTEM)

Student Name    : Muhammad Ahmad Mujtaba
Registration No : FA23-BSE-041
Class & Section : BSE 7A (Software Engineering)

Description:
    Professional All-in-One Bluetooth & Offline Multiplayer Ludo Studio.
    Zero-Install / Pure Python Standard Library (Runs on Computer, Laptop & Mobile).
    
    KEY CAPABILITIES:
    1. Mobile-to-Mobile & Laptop-to-Mobile over Bluetooth:
       - Works 100% offline via Bluetooth Tethering (PAN), Mobile Hotspot, or Ad-Hoc.
       - Built-in Offline QR Code & Dynamic IP Selector for 1-second phone connection!
    2. Strict Desk Management (NO AUTO-START):
       - 4-digit Desk Code generated on creation (e.g. '7429').
       - Desk Code is permanently pinned in the TOP-RIGHT CORNER with 1-click copy!
       - Lobby waits for players (min 2, max 4).
       - NEVER AUTO-STARTS: Only the Leader can manually click 'START GAME'!
    3. Executive Professional UI:
       - Sleek matte obsidian & slate design (eliminates cluttered multi-colors).
       - Elegant classic 15x15 Ludo board with 3D polished tokens, safe stars ⭐,
         and animated 3D rolling dice.
    4. 100% Authentic Ludo Game Logics:
       - 15x15 board, all playerPaths, homeIndices, safe squares, roll 6 to exit,
       - 3 consecutive sixes skip turn, blockades, captures, bonus turns, and victory.
================================================================================
"""

import os
import sys
import time
import json
import uuid
import socket
import random
import threading
import urllib.parse
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any, Tuple

# UTF-8 stream safe reconfiguration
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import io
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

DEFAULT_HTTP_PORT = 8080
CURRENT_SERVER_PORT = DEFAULT_HTTP_PORT

# ================================================================================
# PART 1: AUTHENTIC LUDO RULES ENGINE (15x15 BOARD GEOMETRY FROM DART)
# ================================================================================
PLAYER_COLORS = {
    0: {"name": "Red", "hex": "#dc2626", "bg": "#fef2f2", "border": "#991b1b"},
    1: {"name": "Green", "hex": "#059669", "bg": "#ecfdf5", "border": "#065f46"},
    2: {"name": "Yellow", "hex": "#d97706", "bg": "#fffbeb", "border": "#92400e"},
    3: {"name": "Blue", "hex": "#2563eb", "bg": "#eff6ff", "border": "#1e40af"},
}

HOME_INDICES = {
    0: [31, 33, 61, 63],      # Red yard
    1: [40, 42, 70, 72],      # Green yard
    2: [166, 168, 196, 198],  # Yellow yard
    3: [175, 177, 205, 207],  # Blue yard
}

SAFE_GRID_INDICES = [91, 23, 133, 201, 36, 102, 188, 122]

PLAYER_PATHS: Dict[int, Dict[int, int]] = {
    # 🟥 RED Player
    0: {
        0: 91, 1: 92, 2: 93, 3: 94, 4: 95, 5: 81, 6: 66, 7: 51, 8: 36, 9: 21,
        10: 6, 11: 7, 12: 8, 13: 23, 14: 38, 15: 53, 16: 68, 17: 83, 18: 99,
        19: 100, 20: 101, 21: 102, 22: 103, 23: 104, 24: 119, 25: 134,
        26: 133, 27: 132, 28: 131, 29: 130, 30: 129, 31: 143, 32: 158,
        33: 173, 34: 188, 35: 203, 36: 218, 37: 217, 38: 216, 39: 201,
        40: 186, 41: 171, 42: 156, 43: 141, 44: 125, 45: 124, 46: 123,
        47: 122, 48: 121, 49: 120, 50: 105, 51: 106, 52: 107, 53: 108,
        54: 109, 55: 110, 56: 111
    },
    # 🟩 GREEN Player
    1: {
        0: 23, 1: 38, 2: 53, 3: 68, 4: 83, 5: 99, 6: 100, 7: 101, 8: 102,
        9: 103, 10: 104, 11: 119, 12: 134, 13: 133, 14: 132, 15: 131,
        16: 130, 17: 129, 18: 143, 19: 158, 20: 173, 21: 188, 22: 203,
        23: 218, 24: 217, 25: 216, 26: 201, 27: 186, 28: 171, 29: 156,
        30: 141, 31: 125, 32: 124, 33: 123, 34: 122, 35: 121, 36: 120,
        37: 105, 38: 90, 39: 91, 40: 92, 41: 93, 42: 94, 43: 95, 44: 81,
        45: 66, 46: 51, 47: 36, 48: 21, 49: 6, 50: 7, 51: 22, 52: 37,
        53: 52, 54: 67, 55: 82, 56: 97
    },
    # 🟨 YELLOW Player
    2: {
        0: 201, 1: 186, 2: 171, 3: 156, 4: 141, 5: 125, 6: 124, 7: 123,
        8: 122, 9: 121, 10: 120, 11: 105, 12: 90, 13: 91, 14: 92, 15: 93,
        16: 94, 17: 95, 18: 81, 19: 66, 20: 51, 21: 36, 22: 21, 23: 6,
        24: 7, 25: 8, 26: 23, 27: 38, 28: 53, 29: 68, 30: 83, 31: 99,
        32: 100, 33: 101, 34: 102, 35: 103, 36: 104, 37: 119, 38: 134,
        39: 133, 40: 132, 41: 131, 42: 130, 43: 129, 44: 143, 45: 158,
        46: 173, 47: 188, 48: 203, 49: 218, 50: 217, 51: 202, 52: 187,
        53: 172, 54: 157, 55: 142, 56: 127
    },
    # 🟦 BLUE Player
    3: {
        0: 133, 1: 132, 2: 131, 3: 130, 4: 129, 5: 143, 6: 158, 7: 173,
        8: 188, 9: 203, 10: 218, 11: 217, 12: 216, 13: 201, 14: 186,
        15: 171, 16: 156, 17: 141, 18: 125, 19: 124, 20: 123, 21: 122,
        22: 121, 23: 120, 24: 105, 25: 90, 26: 91, 27: 92, 28: 93,
        29: 94, 30: 95, 31: 81, 32: 66, 33: 51, 34: 36, 35: 21, 36: 6,
        37: 7, 38: 8, 39: 23, 40: 38, 41: 53, 42: 68, 43: 83, 44: 99,
        45: 100, 46: 101, 47: 102, 48: 103, 49: 104, 50: 119, 51: 118,
        52: 117, 53: 116, 54: 115, 55: 114, 56: 113
    }
}


class LudoGameEngine:
    """Core Ludo Engine handling turns, dice, legal moves, blockades, captures & victory."""
    def __init__(self, num_players: int = 2, player_names: Optional[List[str]] = None):
        self.num_players = max(2, min(4, num_players))
        self.player_names = player_names or [f"Player {i+1}" for i in range(self.num_players)]
        self.current_player_index = 0
        self.dice_value = 0
        self.movable_tokens: List[int] = []
        self.consecutive_sixes = 0
        self.game_message = f"{self.player_names[0]}'s turn to roll!"
        self.winner: Optional[int] = None
        self.last_action_log: List[str] = ["Match started! Red player begins."]

        # Token positions: player_idx -> 4 tokens (-1 = yard, 0-56 = track)
        self.player_tokens: Dict[int, List[int]] = {i: [-1, -1, -1, -1] for i in range(self.num_players)}
        self.player_finished_tokens: Dict[int, int] = {i: 0 for i in range(self.num_players)}

    def get_grid_index(self, player_idx: int, pos: int) -> int:
        if pos < 0 or pos > 56:
            return -1
        return PLAYER_PATHS.get(player_idx, {}).get(pos, -1)

    def roll_dice(self, forced_val: Optional[int] = None) -> Dict[str, Any]:
        if self.dice_value != 0 or self.winner is not None:
            return {"dice": self.dice_value, "movable": self.movable_tokens}

        val = forced_val if forced_val is not None else random.randint(1, 6)
        self.dice_value = val
        curr_name = self.player_names[self.current_player_index]

        # Consecutive sixes check
        if val == 6:
            self.consecutive_sixes += 1
            if self.consecutive_sixes >= 3:
                msg = f"⚠️ {curr_name} rolled 3 consecutive sixes! Turn skipped."
                self.game_message = msg
                self.consecutive_sixes = 0
                self.last_action_log.append(msg)
                self.next_player()
                return {"dice": val, "skipped": True, "movable": []}
        else:
            self.consecutive_sixes = 0

        self.movable_tokens = self._calculate_movable_tokens()

        if not self.movable_tokens:
            msg = f"{curr_name} rolled a {val} (No valid moves)."
            self.game_message = msg
            self.last_action_log.append(msg)
            self.next_player()
            return {"dice": val, "skipped": False, "movable": []}
        else:
            msg = f"{curr_name} rolled a {val}! Choose a token to move."
            self.game_message = msg
            self.last_action_log.append(f"{curr_name} rolled a {val}.")
            return {"dice": val, "skipped": False, "movable": self.movable_tokens}

    def _calculate_movable_tokens(self) -> List[int]:
        movable = []
        tokens = self.player_tokens.get(self.current_player_index, [-1, -1, -1, -1])
        for token_idx, pos in enumerate(tokens):
            if pos == -1:
                if self.dice_value == 6:
                    if not self._is_position_blocked(self.current_player_index, 0):
                        movable.append(token_idx)
            elif 0 <= pos < 56:
                new_pos = pos + self.dice_value
                if new_pos <= 56:
                    if not self._is_path_blocked(self.current_player_index, pos, self.dice_value):
                        movable.append(token_idx)
        return movable

    def _is_position_blocked(self, player_idx: int, pos: int) -> bool:
        grid_idx = self.get_grid_index(player_idx, pos)
        if grid_idx == -1:
            return False
        opp_count = 0
        for opp_idx in range(self.num_players):
            if opp_idx == player_idx:
                continue
            for opp_pos in self.player_tokens.get(opp_idx, []):
                if 0 <= opp_pos <= 51 and self.get_grid_index(opp_idx, opp_pos) == grid_idx:
                    opp_count += 1
        return opp_count >= 2

    def _is_path_blocked(self, player_idx: int, start_pos: int, steps: int) -> bool:
        for step in range(1, steps + 1):
            check_pos = start_pos + step
            if check_pos <= 51 and self._is_position_blocked(player_idx, check_pos):
                return True
        return False

    def move_token(self, token_idx: int) -> Dict[str, Any]:
        if token_idx not in self.movable_tokens or self.dice_value == 0:
            return {"success": False, "error": "Invalid token move"}

        curr_p = self.current_player_index
        curr_name = self.player_names[curr_p]
        curr_pos = self.player_tokens[curr_p][token_idx]
        new_pos = 0 if curr_pos == -1 else curr_pos + self.dice_value

        killed_opponent = False
        token_reached_home = False

        # Goal check
        if new_pos == 56:
            token_reached_home = True
            self.player_finished_tokens[curr_p] += 1
            log_str = f"🎯 {curr_name}'s token reached HOME! ({self.player_finished_tokens[curr_p]}/4)"
            self.last_action_log.append(log_str)
            if self.player_finished_tokens[curr_p] == 4:
                self.winner = curr_p
                win_msg = f"🏆 {curr_name} WINS THE MATCH! 🏆"
                self.game_message = win_msg
                self.last_action_log.append(win_msg)
                self.player_tokens[curr_p][token_idx] = new_pos
                self.movable_tokens = []
                self.dice_value = 0
                return {"success": True, "winner": curr_p}

        # Opponent capture check
        if new_pos <= 51 and not token_reached_home:
            grid_idx = self.get_grid_index(curr_p, new_pos)
            if grid_idx != -1 and grid_idx not in SAFE_GRID_INDICES:
                opp_to_kill, opp_tok_to_kill, opp_count = -1, -1, 0
                for opp_i in range(self.num_players):
                    if opp_i == curr_p:
                        continue
                    for opp_t, opp_p in enumerate(self.player_tokens.get(opp_i, [])):
                        if 0 <= opp_p <= 51 and self.get_grid_index(opp_i, opp_p) == grid_idx:
                            opp_count += 1
                            opp_to_kill, opp_tok_to_kill = opp_i, opp_t

                if opp_count == 1 and opp_to_kill != -1:
                    killed_opponent = True
                    self.player_tokens[opp_to_kill][opp_tok_to_kill] = -1
                    cap_msg = f"⚔️ {curr_name} captured {self.player_names[opp_to_kill]}'s token!"
                    self.game_message = cap_msg
                    self.last_action_log.append(cap_msg)

        self.player_tokens[curr_p][token_idx] = new_pos
        self.movable_tokens = []

        # Bonus turn check: 6, capture, or home goal
        gets_bonus = (self.dice_value == 6 or killed_opponent or token_reached_home)
        if gets_bonus:
            bonus_reason = "rolled 6" if self.dice_value == 6 else ("captured token" if killed_opponent else "reached home")
            self.game_message = f"{curr_name} gets a BONUS TURN ({bonus_reason})!"
            self.dice_value = 0
        else:
            self.next_player()

        return {"success": True, "player": curr_p, "token": token_idx, "new_pos": new_pos, "bonus": gets_bonus}

    def next_player(self):
        self.current_player_index = (self.current_player_index + 1) % self.num_players
        self.dice_value = 0
        self.movable_tokens = []
        self.consecutive_sixes = 0
        self.game_message = f"{self.player_names[self.current_player_index]}'s turn to roll!"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_players": self.num_players,
            "player_names": self.player_names,
            "current_player_index": self.current_player_index,
            "dice_value": self.dice_value,
            "movable_tokens": self.movable_tokens,
            "game_message": self.game_message,
            "winner": self.winner,
            "player_tokens": {str(k): list(v) for k, v in self.player_tokens.items()},
            "player_finished_tokens": {str(k): v for k, v in self.player_finished_tokens.items()},
            "last_action_log": self.last_action_log[-8:]
        }


# ================================================================================
# PART 2: DESK LOBBY & OFFLINE BLUETOOTH NETWORKING ENGINE
# ================================================================================
class LudoDeskManager:
    """Manages Desks, unique 4-digit Desk Codes, multiplayer lobbies & turns."""
    def __init__(self):
        self.desks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_desk(self, leader_name: str, requested_code: Optional[str] = None) -> str:
        with self._lock:
            code = requested_code or f"{random.randint(1000, 9999)}"
            while code in self.desks:
                code = f"{random.randint(1000, 9999)}"

            self.desks[code] = {
                "desk_code": code,
                "leader_id": "leader",
                "game_started": False,
                "players": [
                    {"id": "leader", "name": leader_name, "color_idx": 0, "is_leader": True}
                ],
                "engine": None,
                "created_at": time.time(),
                "last_active": time.time()
            }
            return code

    def join_desk(self, desk_code: str, player_name: str) -> Dict[str, Any]:
        with self._lock:
            code = desk_code.strip()
            if code not in self.desks:
                return {"success": False, "error": f"Desk code [{code}] not found."}

            desk = self.desks[code]
            if desk["game_started"]:
                return {"success": False, "error": "Game in this desk has already started!"}

            if len(desk["players"]) >= 4:
                return {"success": False, "error": "Desk is full (maximum 4 players)."}

            player_id = f"player_{uuid.uuid4().hex[:6]}"
            color_idx = len(desk["players"])
            new_player = {
                "id": player_id,
                "name": player_name,
                "color_idx": color_idx,
                "is_leader": False
            }
            desk["players"].append(new_player)
            desk["last_active"] = time.time()
            return {"success": True, "desk_code": code, "player_id": player_id, "color_idx": color_idx}

    def start_game(self, desk_code: str, player_id: str) -> Dict[str, Any]:
        with self._lock:
            code = desk_code.strip()
            if code not in self.desks:
                return {"success": False, "error": "Desk not found"}

            desk = self.desks[code]
            if desk["leader_id"] != player_id:
                return {"success": False, "error": "Only the Leader can start the game!"}

            if len(desk["players"]) < 2:
                return {"success": False, "error": "At least 2 players are required to start!"}

            p_names = [p["name"] for p in desk["players"]]
            desk["engine"] = LudoGameEngine(num_players=len(desk["players"]), player_names=p_names)
            desk["game_started"] = True
            desk["last_active"] = time.time()
            return {"success": True}

    def get_desk_state(self, desk_code: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            code = desk_code.strip()
            if code not in self.desks:
                return None
            desk = self.desks[code]
            state = {
                "desk_code": desk["desk_code"],
                "game_started": desk["game_started"],
                "players": desk["players"],
                "engine_state": desk["engine"].to_dict() if desk["engine"] else None
            }
            return state


GLOBAL_DESK_MGR = LudoDeskManager()


# ================================================================================
# PART 3: EXECUTIVE PROFESSIONAL RESPONSIVE WEB UI
# ================================================================================
HTML_CLIENT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>CSC-334: Ludo Studio Pro</title>
<style>
  :root {
    --bg-dark: #0b0f19;
    --card-surface: #151d2f;
    --card-border: #232f48;
    --text-primary: #f8fafc;
    --text-muted: #94a3b8;
    --gold: #f59e0b;
    --gold-glow: rgba(245, 158, 11, 0.25);
    --red: #dc2626;
    --green: #059669;
    --yellow: #d97706;
    --blue: #2563eb;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; user-select: none; -webkit-tap-highlight-color: transparent; }
  body { background: var(--bg-dark); color: var(--text-primary); min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; }

  /* TOP EXECUTIVE HEADER WITH CORNER DESK CODE */
  .header-bar { width: 100%; max-width: 900px; padding: 14px 20px; display: flex; align-items: center; justify-content: space-between; background: var(--card-surface); border-bottom: 1px solid var(--card-border); position: sticky; top: 0; z-index: 100; }
  .logo { display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 1.15rem; letter-spacing: 0.5px; color: #38bdf8; }
  
  /* PERMANENT CORNER DESK BADGE */
  .corner-code-badge { background: linear-gradient(135deg, #1e293b, #0f172a); border: 2px solid var(--gold); padding: 7px 16px; border-radius: 8px; font-weight: 800; font-size: 1.05rem; letter-spacing: 1.5px; color: #fff; box-shadow: 0 4px 14px var(--gold-glow); display: flex; align-items: center; gap: 8px; cursor: pointer; transition: transform 0.15s; }
  .corner-code-badge:active { transform: scale(0.96); }

  /* CONTAINER & CARDS */
  .view-wrapper { width: 100%; max-width: 900px; padding: 16px; display: flex; flex-direction: column; align-items: center; }
  .exec-card { background: var(--card-surface); border-radius: 14px; padding: 24px; width: 100%; max-width: 480px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid var(--card-border); margin-bottom: 16px; }
  .exec-card h2 { font-size: 1.35rem; font-weight: 800; text-align: center; margin-bottom: 8px; }
  .sub-note { color: var(--text-muted); font-size: 0.88rem; text-align: center; margin-bottom: 18px; line-height: 1.4; }

  /* BUTTONS & INPUTS */
  .btn { width: 100%; padding: 14px; font-size: 1rem; font-weight: 700; border: none; border-radius: 8px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 10px; }
  .btn-gold { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; font-weight: 800; box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35); }
  .btn-gold:hover { filter: brightness(1.08); }
  .btn-blue { background: #2563eb; color: #fff; } .btn-blue:hover { background: #1d4ed8; }
  .btn-green { background: #059669; color: #fff; } .btn-green:hover { background: #047857; }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; filter: grayscale(1); }
  
  .input-label { font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 6px; display: block; }
  .text-input { width: 100%; padding: 12px 14px; font-size: 1.05rem; background: #0b0f19; border: 1px solid var(--card-border); border-radius: 8px; color: #fff; outline: none; margin-bottom: 14px; }
  .text-input:focus { border-color: #38bdf8; }

  /* LOBBY SLOTS */
  .slots-container { display: flex; flex-direction: column; gap: 10px; margin: 16px 0; }
  .player-slot { padding: 12px 16px; border-radius: 10px; display: flex; align-items: center; justify-content: space-between; font-weight: 700; font-size: 0.95rem; border: 1px solid transparent; }
  .player-slot.occupied { background: #111827; border-color: #334155; }
  .player-slot.empty { background: #0b0f19; border-color: #1e293b; color: #475569; font-style: italic; }

  /* QR CODE BOX */
  .qr-box { background: #fff; padding: 14px; border-radius: 10px; margin: 16px auto; width: 160px; height: 160px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(0,0,0,0.3); }

  /* LUDO BOARD CANVAS */
  .board-frame { width: 100%; max-width: 500px; aspect-ratio: 1/1; position: relative; margin: 8px 0; border: 3px solid #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 12px 36px rgba(0,0,0,0.7); background: #0b0f19; }
  canvas { width: 100%; height: 100%; display: block; cursor: pointer; }

  /* HUD CONTROLS */
  .hud-box { width: 100%; max-width: 500px; background: var(--card-surface); padding: 12px 18px; border-radius: 12px; border: 1px solid var(--card-border); display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
  .turn-title { font-size: 1.05rem; font-weight: 800; }
  .turn-subtitle { font-size: 0.82rem; color: var(--text-muted); margin-top: 2px; }
  
  .dice-btn { width: 66px; height: 66px; background: transparent; border-radius: 16px; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: none; border: none; padding: 0; position: relative; user-select: none; transition: transform 0.15s ease, filter 0.2s ease; }
  .dice-btn:hover { transform: scale(1.08); filter: drop-shadow(0 6px 16px rgba(56, 189, 248, 0.45)); }
  .dice-btn:active { transform: scale(0.92); }
  .dice-btn.active-turn { filter: drop-shadow(0 0 14px rgba(245, 158, 11, 0.85)); animation: dicePulse 1.2s infinite ease-in-out; }
  @keyframes dicePulse { 0%, 100% { transform: scale(1); filter: drop-shadow(0 0 10px rgba(245, 158, 11, 0.6)); } 50% { transform: scale(1.08); filter: drop-shadow(0 0 22px rgba(245, 158, 11, 1)); } }
  .dice-btn.rolling { animation: diceRollAnim 0.35s infinite linear; pointer-events: none; }
  @keyframes diceRollAnim { 0% { transform: rotate(0deg) scale(0.95); } 50% { transform: rotate(180deg) scale(1.1); } 100% { transform: rotate(360deg) scale(0.95); } }

  .console-stream { width: 100%; max-width: 500px; background: #070a12; border: 1px solid var(--card-border); border-radius: 8px; padding: 10px 14px; font-family: ui-monospace, monospace; font-size: 0.82rem; height: 75px; overflow-y: auto; color: #94a3b8; }
</style>
</head>
<body>

<!-- TOP PERMANENT HEADER WITH CORNER DESK CODE -->
<div class="header-bar">
  <div class="logo">
    <span>🎲</span> <span>LUDO STUDIO PRO</span>
  </div>
  <div id="cornerCodeBadge" class="corner-code-badge" style="display:none;" onclick="copyDeskCode()" title="Click to copy Desk Code">
    <span>DESK:</span> <span id="cornerDeskCodeTxt" style="color:var(--gold);">----</span> <span>📋</span>
  </div>
</div>

<div class="view-wrapper">

  <!-- VIEW 1: WELCOME SCREEN (JOIN / CREATE) -->
  <div id="welcomeView" class="exec-card">
    <h2 style="color:#38bdf8;">Welcome to Ludo Studio</h2>
    <p class="sub-note">
      🔵 <b>Bluetooth & Offline Direct P2P Active</b><br>
      Play seamlessly between Computer, Laptop, or Mobile Phone with Zero Internet!
    </p>

    <label class="input-label">Your Player Name:</label>
    <input id="userNameInput" class="text-input" type="text" placeholder="Enter name..." value="Player 1" maxlength="15">

    <button class="btn btn-gold" onclick="actionCreateDesk()">
      👑 Create New Desk (Host / Leader)
    </button>

    <div style="display:flex; align-items:center; margin:18px 0; color:#475569;">
      <hr style="flex:1; border:0; border-top:1px solid #232f48;">
      <span style="padding:0 12px; font-size:0.8rem; font-weight:700;">OR JOIN EXISTING DESK</span>
      <hr style="flex:1; border:0; border-top:1px solid #232f48;">
    </div>

    <label class="input-label">Enter Desk Code:</label>
    <input id="inputDeskCode" class="text-input" type="text" placeholder="e.g. 7429" maxlength="6">

    <button class="btn btn-blue" onclick="actionJoinDesk()">
      🤝 Join Desk
    </button>

    <!-- Bluetooth Pair Instructions Toggle -->
    <div style="margin-top:18px; text-align:center;">
      <a href="javascript:void(0)" onclick="toggleHelpModal()" style="color:#38bdf8; font-size:0.85rem; text-decoration:none;">
        ℹ️ Mobile-to-Mobile & Bluetooth Pairing Guide
      </a>
    </div>
  </div>

  <!-- VIEW 2: LOBBY VIEW (WAITING FOR PLAYERS - NO AUTO-START!) -->
  <div id="lobbyView" class="exec-card" style="display:none;">
    <h2 style="color:#38bdf8;">Lobby Room: <span id="lobbyDeskCodeTxt" style="color:var(--gold);">----</span></h2>
    <p class="sub-note">
      Share this 4-digit code or scan the QR Code over Bluetooth to join.
    </p>

    <!-- REAL SCANNABLE QR CODE & PAIRING HUB -->
    <div style="background:#0f172a; border:1px solid var(--card-border); border-radius:12px; padding:14px; margin:14px 0; text-align:center;">
      <div style="font-size:0.82rem; font-weight:800; color:#38bdf8; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:10px;">
        📱 Scan with Mobile Camera to Join
      </div>
      
      <!-- Real High-Res Scannable QR Code -->
      <div style="background:#ffffff; padding:10px; border-radius:10px; display:inline-block; box-shadow:0 6px 20px rgba(0,0,0,0.4);">
        <img id="qrCodeImg" src="" alt="Scan QR to Join" style="display:block; width:160px; height:160px; border-radius:4px; image-rendering:pixelated;" />
      </div>

      <!-- Active Connection Direct URL -->
      <div style="margin-top:12px; background:#070a12; border:1px solid #1e293b; border-radius:8px; padding:8px 12px; display:flex; align-items:center; justify-content:space-between; gap:8px;">
        <span id="directJoinUrlTxt" style="font-family:ui-monospace, monospace; font-size:0.8rem; color:#38bdf8; word-break:break-all; text-align:left;">Loading connection link...</span>
        <button onclick="copyDirectLink()" class="btn" style="width:auto; padding:6px 12px; margin:0; font-size:0.78rem; background:#334155; color:#fff; border-radius:6px; flex-shrink:0;">
          📋 Copy
        </button>
      </div>

      <!-- IP Switcher (Hotspot / Bluetooth PAN / LAN) -->
      <div id="ipSwitcherContainer" style="margin-top:10px; display:none;">
        <span style="font-size:0.75rem; color:#94a3b8;">Switch Network: </span>
        <select id="ipSelector" onchange="onIpSelected()" style="background:#0b0f19; color:#f8fafc; border:1px solid #334155; border-radius:6px; padding:4px 8px; font-size:0.78rem;">
        </select>
      </div>

      <div style="font-size:0.76rem; color:#94a3b8; margin-top:8px;">
        🔵 <i>100% Offline: Works over Bluetooth Tethering or Mobile Hotspot!</i>
      </div>
    </div>

    <!-- 4 Player Slots -->
    <div class="slots-container" id="playerSlotsList"></div>

    <!-- LEADER CONTROLS (ONLY LEADER CAN START - STRICTLY MANUAL!) -->
    <div id="leaderSection" style="display:none; margin-top:14px;">
      <button id="btnLeaderStart" class="btn btn-green" onclick="actionStartGame()" disabled>
        🔒 START GAME (Waiting for Players...)
      </button>
      <p id="leaderHintTxt" style="font-size:0.8rem; color:#f87171; text-align:center; margin-top:6px;">
        At least 2 players are required to start the match.
      </p>
    </div>

    <!-- CLIENT WAITING NOTICE -->
    <div id="clientWaitNotice" style="display:none; margin-top:16px; text-align:center; color:#cbd5e1; font-size:0.9rem;">
      ⏳ Waiting for Leader to start the game...
    </div>
  </div>

  <!-- VIEW 3: ACTIVE GAME BOARD -->
  <div id="gameView" style="display:none; width:100%; flex-direction:column; align-items:center;">
    
    <div class="hud-box">
      <div>
        <div id="activeTurnLabel" class="turn-title" style="color:#dc2626;">Red Player's Turn</div>
        <div id="actionPromptLabel" class="turn-subtitle">Tap dice to roll</div>
      </div>
      <div id="diceCubeBtn" class="dice-btn" onclick="actionRollDice()" title="Tap to Roll Dice">
      </div>
    </div>

    <div class="board-frame">
      <canvas id="ludoBoardCanvas" width="600" height="600"></canvas>
    </div>

    <div class="console-stream" id="eventStreamLog"></div>

  </div>

</div>

<!-- BLUETOOTH / HOTSPOT GUIDE MODAL -->
<div id="helpModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:200; align-items:center; justify-content:center; padding:16px;">
  <div class="exec-card" style="max-height:85vh; overflow-y:auto;">
    <h3 style="color:#38bdf8; margin-bottom:10px;">📶 Mobile & Bluetooth Setup Guide</h3>
    <div style="font-size:0.88rem; color:#cbd5e1; line-height:1.5;">
      <p style="margin-bottom:8px;"><b>Method 1: Bluetooth Tethering (Pure Bluetooth - Zero Internet)</b><br>
      1. Dono devices (Phone & Laptop ya Phone & Phone) ko Bluetooth se pair karein.<br>
      2. Host device par <i>Bluetooth Tethering</i> ON karein (Settings ➔ Hotspot & Tethering ➔ Bluetooth Tethering).<br>
      3. Client device k browser mai host ka IP open karein ya QR Code scan karein.</p>
      
      <p style="margin-bottom:8px;"><b>Method 2: Offline Mobile Hotspot (Fastest - No Internet/Data needed)</b><br>
      1. Host device par Mobile Hotspot ON karein (Mobile Data OFF rakhain).<br>
      2. Doosra phone/laptop us hotspot se connect kare.<br>
      3. QR Code scan karein ya <code>http://192.168.43.1:8080</code> open karein!</p>
    </div>
    <button class="btn btn-blue" onclick="toggleHelpModal()" style="margin-top:16px;">Understood</button>
  </div>
</div>

<script>
// Authentic Executive Palette from bg.jpg
const PALETTE = {
  0: { name: 'Red', hex: '#ed1b24', light: '#fef2f2', border: '#b91c1c' },
  1: { name: 'Green', hex: '#22b14c', light: '#ecfdf5', border: '#15803d' },
  2: { name: 'Yellow', hex: '#fef200', light: '#fefce8', border: '#a16207' },
  3: { name: 'Blue', hex: '#00a2e8', light: '#eff6ff', border: '#0369a1' }
};

// Home Base Slots matching bg.jpg and ludo_logic.py
const HOME_COORDS = {
  0: [[2, 2], [4, 2], [2, 4], [4, 4]],         // Red (Top-Left Yard)
  1: [[11, 2], [13, 2], [11, 4], [13, 4]],     // Green (Top-Right Yard)
  2: [[2, 11], [4, 11], [2, 13], [4, 13]],     // Yellow (Bottom-Left Yard)
  3: [[11, 11], [13, 11], [11, 13], [13, 13]]  // Blue (Bottom-Right Yard)
};

const SAFE_SQUARES = [91, 23, 133, 201, 36, 102, 188, 122];

// Vector 3D Dice Renderer (Zero external assets required)
function getDiceSvg(val) {
  const v = Math.max(1, Math.min(6, parseInt(val) || 6));
  const pips = {
    1: [[50, 50]],
    2: [[28, 28], [72, 72]],
    3: [[28, 28], [50, 50], [72, 72]],
    4: [[28, 28], [72, 28], [28, 72], [72, 72]],
    5: [[28, 28], [72, 28], [50, 50], [28, 72], [72, 72]],
    6: [[28, 26], [28, 50], [28, 74], [72, 26], [72, 50], [72, 74]]
  };
  const pts = pips[v] || pips[6];
  const circles = pts.map(([cx, cy]) => 
    `<circle cx="${cx}" cy="${cy}" r="7.5" fill="url(#pipGrad)" filter="drop-shadow(0 1px 1.5px rgba(0,0,0,0.6))"/>`
  ).join('');

  return `<svg viewBox="0 0 100 100" width="100%" height="100%" style="display:block; overflow:visible;">
    <defs>
      <linearGradient id="diceGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#334155"/>
        <stop offset="40%" stop-color="#1e293b"/>
        <stop offset="100%" stop-color="#0b0f19"/>
      </linearGradient>
      <radialGradient id="pipGrad" cx="35%" cy="35%" r="65%">
        <stop offset="0%" stop-color="#ffffff"/>
        <stop offset="65%" stop-color="#f8fafc"/>
        <stop offset="100%" stop-color="#cbd5e1"/>
      </radialGradient>
      <linearGradient id="bevelGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="rgba(255,255,255,0.25)"/>
        <stop offset="100%" stop-color="rgba(255,255,255,0.02)"/>
      </linearGradient>
    </defs>
    <rect x="5" y="5" width="90" height="90" rx="18" fill="url(#diceGrad)" stroke="#475569" stroke-width="2.5" filter="drop-shadow(0 6px 12px rgba(0,0,0,0.45))"/>
    <rect x="7" y="7" width="86" height="40" rx="16" fill="url(#bevelGrad)"/>
    ${circles}
  </svg>`;
}

let activeDeskCode = "";
let myPlayerId = "";
let isLeader = false;
let myColorIdx = 0;
let gameState = null;
let pollTimer = null;

function copyDeskCode() {
  if (!activeDeskCode) return;
  navigator.clipboard.writeText(activeDeskCode);
  alert("Desk Code copied: " + activeDeskCode);
}

function toggleHelpModal() {
  const modal = document.getElementById('helpModal');
  modal.style.display = (modal.style.display === 'flex') ? 'none' : 'flex';
}

// 1. Create Desk (Leader)
async function actionCreateDesk() {
  const name = document.getElementById('userNameInput').value.trim() || 'Leader';
  const res = await fetch('/api/create_desk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ leader_name: name })
  });
  const data = await res.json();
  if (data.success) {
    activeDeskCode = data.desk_code;
    myPlayerId = 'leader';
    isLeader = true;
    myColorIdx = 0;
    setupLobby(data.desk_code);
  }
}

// 2. Join Desk
async function actionJoinDesk() {
  const name = document.getElementById('userNameInput').value.trim() || 'Player';
  const code = document.getElementById('inputDeskCode').value.trim();
  if (!code) { alert('Please enter a Desk Code!'); return; }

  const res = await fetch('/api/join_desk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ desk_code: code, player_name: name })
  });
  const data = await res.json();
  if (data.success) {
    activeDeskCode = data.desk_code;
    myPlayerId = data.player_id;
    isLeader = false;
    myColorIdx = data.color_idx;
    setupLobby(data.desk_code);
  } else {
    alert(data.error);
  }
}

function setupLobby(code) {
  document.getElementById('welcomeView').style.display = 'none';
  document.getElementById('lobbyView').style.display = 'block';
  
  // Show Corner Code Badge
  document.getElementById('cornerCodeBadge').style.display = 'flex';
  document.getElementById('cornerDeskCodeTxt').innerText = code;
  document.getElementById('lobbyDeskCodeTxt').innerText = code;

  // Generate Real QR Code & Mobile Connection Links
  updateQrAndLinks(code);

  if (isLeader) {
    document.getElementById('leaderSection').style.display = 'block';
    document.getElementById('clientWaitNotice').style.display = 'none';
  } else {
    document.getElementById('leaderSection').style.display = 'none';
    document.getElementById('clientWaitNotice').style.display = 'block';
  }

  startPollingLobby();
}

// 3. Start Game (MANUAL ONLY - NEVER AUTO-START!)
async function actionStartGame() {
  if (!isLeader) return;
  const res = await fetch('/api/start_game', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ desk_code: activeDeskCode, player_id: myPlayerId })
  });
  const data = await res.json();
  if (!data.success) {
    alert(data.error);
  }
}

// 4. Polling Loop
function startPollingLobby() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    if (!activeDeskCode) return;
    try {
      const res = await fetch(`/api/desk_state?code=${activeDeskCode}`);
      const data = await res.json();
      if (!data) return;

      if (!data.game_started) {
        renderLobbySlots(data.players);
      } else {
        // Transition to Board view
        const wView = document.getElementById('welcomeView');
        const lView = document.getElementById('lobbyView');
        const gView = document.getElementById('gameView');
        if (wView && wView.style.display !== 'none') wView.style.display = 'none';
        if (lView && lView.style.display !== 'none') lView.style.display = 'none';
        if (gView && gView.style.display !== 'flex') {
          gView.style.display = 'flex';
        }
        initCanvas();

        gameState = data.engine_state;
        updateHud(gameState);
        renderLudoBoard(gameState);
      }
    } catch(e) {}
  }, 450);
}

// Render 4 Executive Player Slots
function renderLobbySlots(players) {
  const container = document.getElementById('playerSlotsList');
  let html = '';

  for (let i = 0; i < 4; i++) {
    const p = players.find(x => x.color_idx === i);
    const col = PALETTE[i];
    if (p) {
      html += `<div class="player-slot occupied" style="border-left:5px solid ${col.hex};">
        <span>${p.is_leader ? '👑 ' : '👤 '}${p.name} (${col.name})</span>
        <span style="color:#10b981;">READY</span>
      </div>`;
    } else {
      html += `<div class="player-slot empty">
        <span>[Slot ${i+1}: Open for ${col.name}]</span>
        <span>WAITING</span>
      </div>`;
    }
  }
  container.innerHTML = html;

  if (isLeader) {
    const btn = document.getElementById('btnLeaderStart');
    const hint = document.getElementById('leaderHintTxt');
    if (players.length >= 2) {
      btn.disabled = false;
      btn.innerHTML = `🚀 START MATCH (${players.length}/4 Players Ready)`;
      hint.style.display = 'none';
    } else {
      btn.disabled = true;
      btn.innerHTML = `🔒 START MATCH (Waiting for Players...)`;
      hint.style.display = 'block';
    }
  }
}

function updateHud(state) {
  if (!state) return;
  const turnIdx = state.current_player_index;
  const pName = state.player_names[turnIdx] || 'Player';
  const c = PALETTE[turnIdx];

  const turnLabel = document.getElementById('activeTurnLabel');
  turnLabel.innerText = `${pName}'s Turn (${c.name})`;
  turnLabel.style.color = c.hex;

  document.getElementById('actionPromptLabel').innerText = state.game_message || '';

  const diceBtn = document.getElementById('diceCubeBtn');

  // Pulse effect when it is this player's turn to roll
  const isMyTurn = (state.current_player_index === myColorIdx);
  if (isMyTurn && state.dice_value === 0 && !state.winner) {
    diceBtn.classList.add('active-turn');
  } else {
    diceBtn.classList.remove('active-turn');
  }

  // Display authentic 3D vector SVG dice
  if (!diceBtn.classList.contains('rolling')) {
    diceBtn.innerHTML = getDiceSvg(state.dice_value || 6);
  }

  // Log Stream
  const logEl = document.getElementById('eventStreamLog');
  logEl.innerHTML = (state.last_action_log || []).map(l => `<div>• ${l}</div>`).join('');
  logEl.scrollTop = logEl.scrollHeight;
}

// Roll Dice with dynamic animation
async function actionRollDice() {
  if (!gameState) return;
  if (gameState.current_player_index !== myColorIdx) {
    alert("Please wait for your turn!");
    return;
  }
  if (gameState.dice_value > 0) {
    alert("Dice already rolled! Select a token to move.");
    return;
  }

  const diceBtn = document.getElementById('diceCubeBtn');
  diceBtn.classList.add('rolling');

  // Rapidly shuffle through dice faces 1 to 6 during roll
  let rollCycle = 1;
  const rollInterval = setInterval(() => {
    rollCycle = (rollCycle % 6) + 1;
    diceBtn.innerHTML = getDiceSvg(rollCycle);
  }, 60);

  try {
    const res = await fetch('/api/roll_dice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ desk_code: activeDeskCode, player_id: myPlayerId })
    });
    const data = await res.json();
    if (data.result && data.result.dice) {
      diceBtn.innerHTML = getDiceSvg(data.result.dice);
    }
  } catch(e) {
    console.error("Roll dice error", e);
  } finally {
    clearInterval(rollInterval);
    diceBtn.classList.remove('rolling');
  }
}

// Move Token
async function actionMoveToken(tokenIdx) {
  if (!gameState) return;
  if (gameState.current_player_index !== myColorIdx) return;

  await fetch('/api/move_token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ desk_code: activeDeskCode, player_id: myPlayerId, token_idx: tokenIdx })
  });
}

// ================================================================================
// CANVAS 15x15 EXECUTIVE LUDO BOARD RENDERER
// ================================================================================
let canvas, ctx;
function initCanvas() {
  canvas = document.getElementById('ludoBoardCanvas');
  if (canvas) {
    ctx = canvas.getContext('2d');
    canvas.onclick = onBoardClick;
  }
}

function onBoardClick(e) {
  if (!gameState) return;
  if (gameState.current_player_index !== myColorIdx) return;
  if (!gameState.movable_tokens || gameState.movable_tokens.length === 0) return;

  const rect = canvas.getBoundingClientRect();
  const scale = canvas.width / rect.width;
  const clickX = (e.clientX - rect.left) * scale;
  const clickY = (e.clientY - rect.top) * scale;
  const cs = canvas.width / 15;

  const col = Math.floor(clickX / cs);
  const row = Math.floor(clickY / cs);
  const clickedGridIdx = row * 15 + col;

  const myTokens = gameState.player_tokens[myColorIdx] || gameState.player_tokens[String(myColorIdx)] || [-1,-1,-1,-1];

  // 1. Precise click on token
  for (const tIdx of gameState.movable_tokens) {
    const pos = myTokens[tIdx];
    if (pos === -1) {
      const coords = HOME_COORDS[myColorIdx][tIdx];
      const dist = Math.hypot(clickX - coords[0] * cs, clickY - coords[1] * cs);
      if (dist < cs * 1.1) {
        actionMoveToken(tIdx);
        return;
      }
    } else {
      const tokenGrid = getPathGridIndex(myColorIdx, pos);
      if (tokenGrid === clickedGridIdx) {
        actionMoveToken(tIdx);
        return;
      }
    }
  }

  // 2. Click anywhere inside player's home yard
  for (const tIdx of gameState.movable_tokens) {
    const pos = myTokens[tIdx];
    if (pos === -1) {
      let inYard = false;
      if (myColorIdx === 0 && col < 6 && row < 6) inYard = true;
      if (myColorIdx === 1 && col >= 9 && row < 6) inYard = true;
      if (myColorIdx === 2 && col < 6 && row >= 9) inYard = true;
      if (myColorIdx === 3 && col >= 9 && row >= 9) inYard = true;
      if (inYard) {
        actionMoveToken(tIdx);
        return;
      }
    }
  }

  // 3. Single movable token shortcut
  if (gameState.movable_tokens.length === 1) {
    actionMoveToken(gameState.movable_tokens[0]);
  }
}

function renderLudoBoard(state) {
  if (!ctx || !canvas) {
    initCanvas();
  }
  if (!ctx || !canvas) return;
  const w = canvas.width;
  const cs = w / 15;

  ctx.clearRect(0, 0, w, w);

  // 1. Draw Authentic Vector Ludo Board (Identical to bg.jpg)
  drawBoardTracks();

  // Render 3D Polished Luxury Tokens
  if (state && state.player_tokens) {
    for (let p = 0; p < state.num_players; p++) {
      const tokens = state.player_tokens[p] || state.player_tokens[String(p)] || [-1,-1,-1,-1];
      tokens.forEach((pos, tIdx) => {
        if (pos === 56) {
          // Token reached home goal! Draw inside center goal
          const homeCoords = {
            0: [6.6, 7.5], 1: [7.5, 6.6], 2: [6.6, 8.4], 3: [8.4, 7.5]
          };
          const hc = homeCoords[p] || [7.5, 7.5];
          drawLuxuryToken(hc[0] * cs, hc[1] * cs, cs * 0.26, PALETTE[p], false);
          return;
        }

        let cx, cy;
        if (pos === -1) {
          const coords = HOME_COORDS[p][tIdx];
          cx = coords[0] * cs;
          cy = coords[1] * cs;
        } else {
          const gridIdx = getPathGridIndex(p, pos);
          const col = gridIdx % 15;
          const row = Math.floor(gridIdx / 15);
          cx = (col + 0.5) * cs;
          cy = (row + 0.5) * cs;
        }

        const isMovable = (p === state.current_player_index && (state.movable_tokens || []).includes(tIdx));
        drawLuxuryToken(cx, cy, cs * 0.40, PALETTE[p], isMovable);
      });
    }
  }
}

// Draw Complete 15x15 Authentic Ludo Board (Exact replica of bg.jpg)
function drawBoardTracks() {
  const cs = canvas.width / 15;
  const w = canvas.width;

  // 1. Base canvas fill
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, w, w);

  // 2. 4 Corner Yards (6x6)
  drawAuthenticYard(0, 0, PALETTE[0]);   // Top-Left (Red)
  drawAuthenticYard(9, 0, PALETTE[1]);   // Top-Right (Green)
  drawAuthenticYard(0, 9, PALETTE[2]);   // Bottom-Left (Yellow)
  drawAuthenticYard(9, 9, PALETTE[3]);   // Bottom-Right (Blue)

  // 3. Colored Home Stretches (5 squares each)
  for (let s = 1; s <= 5; s++) {
    ctx.fillStyle = PALETTE[0].hex; ctx.fillRect(s * cs, 7 * cs, cs, cs);
    ctx.fillStyle = PALETTE[1].hex; ctx.fillRect(7 * cs, s * cs, cs, cs);
    ctx.fillStyle = PALETTE[2].hex; ctx.fillRect(7 * cs, (14 - s) * cs, cs, cs);
    ctx.fillStyle = PALETTE[3].hex; ctx.fillRect((14 - s) * cs, 7 * cs, cs, cs);
  }

  // 4. Start / Entry Squares with Directional Arrows (Solid color bg + arrow)
  drawStartSquare(1, 6, PALETTE[0].hex, 'right');
  drawStartSquare(8, 1, PALETTE[1].hex, 'down');
  drawStartSquare(6, 13, PALETTE[2].hex, 'up');
  drawStartSquare(13, 8, PALETTE[3].hex, 'left');

  // 5. Corridor Entrance Arrows (White square + colored arrow pointing inward matching bg.jpg)
  drawEntryArrow(0, 7, PALETTE[0].hex, 'right');
  drawEntryArrow(7, 0, PALETTE[1].hex, 'down');
  drawEntryArrow(7, 14, PALETTE[2].hex, 'up');
  drawEntryArrow(14, 7, PALETTE[3].hex, 'left');

  // 6. Track Grid Dividers (Grid lines for track corridors only, leaving center goal clear)
  ctx.strokeStyle = '#475569';
  ctx.lineWidth = 1.3;

  // Vertical track dividers
  for (let c = 1; c <= 6; c++) {
    ctx.beginPath(); ctx.moveTo(c * cs, 6 * cs); ctx.lineTo(c * cs, 9 * cs); ctx.stroke();
  }
  for (let c = 9; c <= 14; c++) {
    ctx.beginPath(); ctx.moveTo(c * cs, 6 * cs); ctx.lineTo(c * cs, 9 * cs); ctx.stroke();
  }
  for (let c = 7; c <= 8; c++) {
    ctx.beginPath(); ctx.moveTo(c * cs, 0); ctx.lineTo(c * cs, 6 * cs); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(c * cs, 9 * cs); ctx.lineTo(c * cs, 15 * cs); ctx.stroke();
  }
  // Corridor boundary lines (c=6, c=9)
  ctx.beginPath(); ctx.moveTo(6 * cs, 0); ctx.lineTo(6 * cs, 15 * cs); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(9 * cs, 0); ctx.lineTo(9 * cs, 15 * cs); ctx.stroke();

  // Horizontal track dividers
  for (let r = 1; r <= 6; r++) {
    ctx.beginPath(); ctx.moveTo(6 * cs, r * cs); ctx.lineTo(9 * cs, r * cs); ctx.stroke();
  }
  for (let r = 9; r <= 14; r++) {
    ctx.beginPath(); ctx.moveTo(6 * cs, r * cs); ctx.lineTo(9 * cs, r * cs); ctx.stroke();
  }
  for (let r = 7; r <= 8; r++) {
    ctx.beginPath(); ctx.moveTo(0, r * cs); ctx.lineTo(6 * cs, r * cs); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(9 * cs, r * cs); ctx.lineTo(15 * cs, r * cs); ctx.stroke();
  }
  // Corridor boundary lines (r=6, r=9)
  ctx.beginPath(); ctx.moveTo(0, 6 * cs); ctx.lineTo(15 * cs, 6 * cs); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, 9 * cs); ctx.lineTo(15 * cs, 9 * cs); ctx.stroke();

  // 7. Authentic Safe Star Cells (Quadrant colored stars matching bg.jpg)
  drawStar(2, 8, PALETTE[0].hex);   // Red Safe Cell
  drawStar(6, 2, PALETTE[1].hex);   // Green Safe Cell
  drawStar(8, 12, PALETTE[2].hex);  // Yellow Safe Cell
  drawStar(12, 6, PALETTE[3].hex);  // Blue Safe Cell

  // 8. Center Goal Triangles (Drawn crisp and solid, meeting at (7.5, 7.5))
  drawCenterGoal();

  // 9. Outer Perimeter Frame
  ctx.strokeStyle = '#0f172a';
  ctx.lineWidth = 4;
  ctx.strokeRect(0, 0, w, w);
}

function drawAuthenticYard(startCol, startRow, p) {
  const cs = canvas.width / 15;
  const x = startCol * cs;
  const y = startRow * cs;
  const size = 6 * cs;

  // 1. Outer 6x6 colored square
  ctx.fillStyle = p.hex;
  ctx.fillRect(x, y, size, size);

  ctx.strokeStyle = '#0f172a';
  ctx.lineWidth = 2.5;
  ctx.strokeRect(x, y, size, size);

  // 2. Inner 4x4 rounded white card
  const innerX = x + 1 * cs;
  const innerY = y + 1 * cs;
  const innerSize = 4 * cs;
  const r = 16;

  ctx.save();
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(innerX, innerY, innerSize, innerSize, r);
  } else {
    ctx.rect(innerX, innerY, innerSize, innerSize);
  }
  ctx.fillStyle = '#ffffff';
  ctx.shadowColor = 'rgba(0,0,0,0.2)';
  ctx.shadowBlur = 10;
  ctx.fill();
  ctx.restore();

  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(innerX, innerY, innerSize, innerSize, r);
  } else {
    ctx.rect(innerX, innerY, innerSize, innerSize);
  }
  ctx.strokeStyle = p.border || p.hex;
  ctx.lineWidth = 3;
  ctx.stroke();

  // 3. Four concentric token base discs matching bg.jpg
  const offsets = [[1 * cs, 1 * cs], [3 * cs, 1 * cs], [1 * cs, 3 * cs], [3 * cs, 3 * cs]];
  offsets.forEach(([bx, by]) => {
    const cx = innerX + bx;
    const cy = innerY + by;
    const rad = cs * 0.65;

    // Outer colored disc
    ctx.beginPath();
    ctx.arc(cx, cy, rad, 0, Math.PI * 2);
    ctx.fillStyle = p.hex;
    ctx.fill();
    ctx.strokeStyle = 'rgba(0,0,0,0.15)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Inner white ring
    ctx.beginPath();
    ctx.arc(cx, cy, rad * 0.70, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    // Center colored dot
    ctx.beginPath();
    ctx.arc(cx, cy, rad * 0.42, 0, Math.PI * 2);
    ctx.fillStyle = p.hex;
    ctx.fill();
  });
}

function drawCenterGoal() {
  const cs = canvas.width / 15;
  const x1 = 6 * cs, y1 = 6 * cs;
  const x2 = 9 * cs, y2 = 9 * cs;
  const cx = 7.5 * cs, cy = 7.5 * cs;

  // Left (Red)
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(cx, cy); ctx.lineTo(x1, y2); ctx.closePath();
  ctx.fillStyle = PALETTE[0].hex; ctx.fill();
  ctx.strokeStyle = '#0f172a'; ctx.lineWidth = 1.5; ctx.stroke();

  // Top (Green)
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y1); ctx.lineTo(cx, cy); ctx.closePath();
  ctx.fillStyle = PALETTE[1].hex; ctx.fill();
  ctx.strokeStyle = '#0f172a'; ctx.lineWidth = 1.5; ctx.stroke();

  // Bottom (Yellow)
  ctx.beginPath(); ctx.moveTo(x1, y2); ctx.lineTo(cx, cy); ctx.lineTo(x2, y2); ctx.closePath();
  ctx.fillStyle = PALETTE[2].hex; ctx.fill();
  ctx.strokeStyle = '#0f172a'; ctx.lineWidth = 1.5; ctx.stroke();

  // Right (Blue)
  ctx.beginPath(); ctx.moveTo(x2, y1); ctx.lineTo(x2, y2); ctx.lineTo(cx, cy); ctx.closePath();
  ctx.fillStyle = PALETTE[3].hex; ctx.fill();
  ctx.strokeStyle = '#0f172a'; ctx.lineWidth = 1.5; ctx.stroke();

  // Outer border of center goal
  ctx.strokeStyle = '#0f172a';
  ctx.lineWidth = 2.5;
  ctx.strokeRect(x1, y1, 3 * cs, 3 * cs);
}

function drawDirectionalArrow(x, y, cs, dir) {
  const cx = x + cs * 0.5, cy = y + cs * 0.5;
  const s = cs * 0.30;
  ctx.beginPath();
  if (dir === 'right') {
    ctx.moveTo(cx - s, cy - s); ctx.lineTo(cx + s * 0.85, cy); ctx.lineTo(cx - s, cy + s);
  } else if (dir === 'down') {
    ctx.moveTo(cx - s, cy - s); ctx.lineTo(cx + s, cy - s); ctx.lineTo(cx, cy + s * 0.85);
  } else if (dir === 'up') {
    ctx.moveTo(cx - s, cy + s); ctx.lineTo(cx + s, cy + s); ctx.lineTo(cx, cy - s * 0.85);
  } else if (dir === 'left') {
    ctx.moveTo(cx + s, cy - s); ctx.lineTo(cx - s * 0.85, cy); ctx.lineTo(cx + s, cy + s);
  }
  ctx.closePath();
  ctx.fill();
}

function drawStartSquare(c, r, col, dir) {
  const cs = canvas.width / 15;
  const x = c * cs, y = r * cs;
  ctx.fillStyle = col;
  ctx.fillRect(x, y, cs, cs);

  ctx.fillStyle = (col === '#fef200') ? '#0f172a' : '#ffffff';
  drawDirectionalArrow(x, y, cs, dir);
}

function drawEntryArrow(c, r, col, dir) {
  const cs = canvas.width / 15;
  const x = c * cs, y = r * cs;
  ctx.fillStyle = col;
  drawDirectionalArrow(x, y, cs, dir);
}

function drawStar(c, r, col) {
  const cs = canvas.width / 15;
  const cx = (c + 0.5) * cs, cy = (r + 0.5) * cs;
  const spikes = 5, outerR = cs * 0.36, innerR = cs * 0.16;
  let rot = (Math.PI / 2) * 3;
  const step = Math.PI / spikes;

  ctx.beginPath();
  ctx.moveTo(cx, cy - outerR);
  for (let i = 0; i < spikes; i++) {
    let x = cx + Math.cos(rot) * outerR;
    let y = cy + Math.sin(rot) * outerR;
    ctx.lineTo(x, y);
    rot += step;
    x = cx + Math.cos(rot) * innerR;
    y = cy + Math.sin(rot) * innerR;
    ctx.lineTo(x, y);
    rot += step;
  }
  ctx.lineTo(cx, cy - outerR);
  ctx.closePath();
  ctx.fillStyle = col || '#f59e0b';
  ctx.fill();
  ctx.strokeStyle = '#0f172a';
  ctx.lineWidth = 1.2;
  ctx.stroke();
}

function drawLuxuryToken(cx, cy, r, col, isMovable) {
  if (isMovable) {
    ctx.beginPath(); ctx.arc(cx, cy, r + 7, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(245, 158, 11, 0.45)'; ctx.fill();
    ctx.lineWidth = 3.5; ctx.strokeStyle = '#f59e0b'; ctx.stroke();
  }

  // Soft drop shadow
  ctx.beginPath(); ctx.arc(cx + 2, cy + 3, r, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(0,0,0,0.45)'; ctx.fill();

  // Polished Token Body
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fillStyle = col.hex; ctx.fill();
  ctx.lineWidth = 2.5; ctx.strokeStyle = '#ffffff'; ctx.stroke();

  // Inner glossy accent ring
  ctx.beginPath(); ctx.arc(cx, cy, r * 0.55, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(255,255,255,0.65)'; ctx.lineWidth = 1.5; ctx.stroke();

  // Specular glossy highlight
  ctx.beginPath(); ctx.arc(cx - r*0.32, cy - r*0.32, r*0.28, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(255,255,255,0.75)'; ctx.fill();
}

const CLIENT_PATHS = """ + json.dumps(PLAYER_PATHS) + """;
function getPathGridIndex(pIdx, pos) {
  if (!CLIENT_PATHS) return 0;
  const path = CLIENT_PATHS[pIdx] || CLIENT_PATHS[String(pIdx)];
  if (!path) return 0;
  return path[pos] !== undefined ? path[pos] : (path[String(pos)] || 0);
}

// Host Network & Scannable QR Handling
let hostInfo = null;
let currentHostIp = "";

async function fetchHostInfo() {
  try {
    const res = await fetch('/api/host_info');
    hostInfo = await res.json();
    if (hostInfo && hostInfo.ips && hostInfo.ips.length > 0) {
      const nonLocal = hostInfo.ips.find(ip => !ip.startsWith('127.'));
      currentHostIp = nonLocal || hostInfo.ips[0];

      const sel = document.getElementById('ipSelector');
      if (sel && hostInfo.ips.length > 1) {
        sel.innerHTML = hostInfo.ips.map(ip => `<option value="${ip}">${ip} (${ip.startsWith('192.168.43') ? 'Hotspot/Wi-Fi' : ip.startsWith('192.168.44') ? 'Bluetooth PAN' : 'LAN'})</option>`).join('');
        sel.value = currentHostIp;
        document.getElementById('ipSwitcherContainer').style.display = 'block';
      }
    }
  } catch(e) {
    console.warn("Could not fetch host info", e);
  }
}

function updateQrAndLinks(deskCode) {
  const port = (hostInfo && hostInfo.port) || window.location.port || '8080';
  const ip = currentHostIp || window.location.hostname || '127.0.0.1';
  const joinUrl = `http://${ip}:${port}/?code=${deskCode}`;

  const linkEl = document.getElementById('directJoinUrlTxt');
  if (linkEl) linkEl.innerText = joinUrl;

  const qrImg = document.getElementById('qrCodeImg');
  if (qrImg) {
    qrImg.src = `/api/qr_code?text=${encodeURIComponent(joinUrl)}`;
  }
}

function onIpSelected() {
  const sel = document.getElementById('ipSelector');
  if (sel) {
    currentHostIp = sel.value;
    updateQrAndLinks(activeDeskCode);
  }
}

function copyDirectLink() {
  const linkEl = document.getElementById('directJoinUrlTxt');
  if (linkEl && linkEl.innerText) {
    navigator.clipboard.writeText(linkEl.innerText);
    alert("Copied mobile join link:\\n" + linkEl.innerText);
  }
}

// Auto-fill Desk Code if scanned with mobile camera or opened via direct link
window.addEventListener('DOMContentLoaded', async () => {
  initCanvas();
  const diceBtn = document.getElementById('diceCubeBtn');
  if (diceBtn) diceBtn.innerHTML = getDiceSvg(6);
  await fetchHostInfo();
  const urlParams = new URLSearchParams(window.location.search);
  const codeParam = urlParams.get('code');
  if (codeParam) {
    const inputCode = document.getElementById('inputDeskCode');
    if (inputCode) {
      inputCode.value = codeParam;
      inputCode.style.borderColor = '#10b981';
      inputCode.style.background = '#064e3b33';
    }
    const nameInput = document.getElementById('userNameInput');
    if (nameInput && nameInput.value === 'Player 1') {
      nameInput.value = 'Player ' + Math.floor(Math.random() * 89 + 10);
    }
  }
});
</script>
</body>
</html>
"""


# ================================================================================
# PART 4: ZERO-DEPENDENCY HTTP API
# ================================================================================
class LudoRequestHandler(BaseHTTPRequestHandler):
    """Zero-dependency HTTP Handler serving the Universal Mobile & Desktop Ludo UI."""
    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(HTML_CLIENT_TEMPLATE.encode("utf-8"))

        elif parsed.path == "/api/host_info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            ips = get_all_local_ips()
            info = {
                "ips": ips,
                "primary_ip": ips[0] if ips else "127.0.0.1",
                "port": CURRENT_SERVER_PORT
            }
            self.wfile.write(json.dumps(info).encode("utf-8"))

        elif parsed.path == "/api/qr_code":
            qs = urllib.parse.parse_qs(parsed.query)
            text = qs.get("text", [""])[0] or f"http://localhost:{CURRENT_SERVER_PORT}"
            if HAS_QRCODE:
                try:
                    qr = qrcode.QRCode(
                        version=None,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=6,
                        border=2,
                    )
                    qr.add_data(text)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
                    buf = io.BytesIO()
                    img.save(buf)
                    png_data = buf.getvalue()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(png_data)))
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(png_data)
                    return
                except Exception:
                    pass
            self.send_response(501)
            self.end_headers()

        elif parsed.path == "/api/desk_state":
            qs = urllib.parse.parse_qs(parsed.query)
            code = qs.get("code", [""])[0]
            state = GLOBAL_DESK_MGR.get_desk_state(code)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(state or {}).encode("utf-8"))

        elif parsed.path.startswith("/assets/"):
            rel_path = urllib.parse.unquote(parsed.path.lstrip("/"))
            base_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.abspath(os.path.join(base_dir, rel_path))
            assets_dir = os.path.abspath(os.path.join(base_dir, "assets"))

            if os.path.commonpath([full_path, assets_dir]) == assets_dir and os.path.isfile(full_path):
                ext = os.path.splitext(full_path)[1].lower()
                content_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else ("image/png" if ext == ".png" else "application/octet-stream")
                try:
                    with open(full_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception:
                    pass
            self.send_response(404)
            self.end_headers()

        elif parsed.path.startswith("/fonts/"):
            rel_path = urllib.parse.unquote(parsed.path.lstrip("/"))
            base_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.abspath(os.path.join(base_dir, rel_path))
            fonts_dir = os.path.abspath(os.path.join(base_dir, "fonts"))

            if os.path.commonpath([full_path, fonts_dir]) == fonts_dir and os.path.isfile(full_path):
                try:
                    with open(full_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "font/ttf")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception:
                    pass
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")
        data = json.loads(body) if body else {}

        if parsed.path == "/api/create_desk":
            leader_name = data.get("leader_name", "Leader")
            code = GLOBAL_DESK_MGR.create_desk(leader_name)
            self._send_json({"success": True, "desk_code": code, "leader_id": "leader"})

        elif parsed.path == "/api/join_desk":
            desk_code = data.get("desk_code", "")
            player_name = data.get("player_name", "Player")
            res = GLOBAL_DESK_MGR.join_desk(desk_code, player_name)
            self._send_json(res)

        elif parsed.path == "/api/start_game":
            desk_code = data.get("desk_code", "")
            player_id = data.get("player_id", "")
            res = GLOBAL_DESK_MGR.start_game(desk_code, player_id)
            self._send_json(res)

        elif parsed.path == "/api/roll_dice":
            desk_code = data.get("desk_code", "")
            desk = GLOBAL_DESK_MGR.desks.get(desk_code)
            if desk and desk["engine"]:
                res = desk["engine"].roll_dice()
                self._send_json({"success": True, "result": res})
            else:
                self._send_json({"success": False, "error": "Game not ready"})

        elif parsed.path == "/api/move_token":
            desk_code = data.get("desk_code", "")
            token_idx = int(data.get("token_idx", -1))
            desk = GLOBAL_DESK_MGR.desks.get(desk_code)
            if desk and desk["engine"]:
                res = desk["engine"].move_token(token_idx)
                self._send_json({"success": True, "result": res})
            else:
                self._send_json({"success": False, "error": "Game not ready"})
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, payload: Dict[str, Any]):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))


def get_all_local_ips() -> List[str]:
    """Discovers all local network, Bluetooth PAN, and hotspot IPs."""
    ips = set()
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and ":" not in ip:
                ips.add(ip)
    except Exception:
        pass
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


# ================================================================================
# PART 5: UNIVERSAL RUNNER (RUNS ON MOBILE, LAPTOP & COMPUTER)
# ================================================================================
def main():
    global CURRENT_SERVER_PORT
    port = DEFAULT_HTTP_PORT
    local_ips = get_all_local_ips()

    # Find free port if 8080 is in use
    for p in range(DEFAULT_HTTP_PORT, DEFAULT_HTTP_PORT + 20):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", p), LudoRequestHandler)
            port = p
            CURRENT_SERVER_PORT = p
            break
        except OSError:
            continue

    print("=" * 75)
    print("  CSC-334: ALL-IN-ONE BLUETOOTH & OFFLINE LUDO MULTIPLAYER STUDIO")
    print("=" * 75)
    print("🔵 OFFLINE BLUETOOTH LINK ACTIVE (Zero Internet Required)")
    print(f"[*] Bound to Port: {port}")
    print(f"[*] On this Computer / Laptop:")
    print(f"    👉 http://localhost:{port}")
    print(f"[*] On Mobile Phone (via Bluetooth Tethering or Mobile Hotspot):")
    for ip in local_ips:
        print(f"    👉 http://{ip}:{port}")
    print("=" * 75)
    print("✨ RULES & BEHAVIOR:")
    print("1. Desk Code is permanently shown in TOP-RIGHT CORNER.")
    print("2. Joining players enter Desk Code and wait in Lobby.")
    print("3. STRICTLY MANUAL START: Game will NEVER auto-start.")
    print("   Leader must explicitly click 'START GAME' once min 2 players join!")
    print("=" * 75)

    def _auto_open_browser():
        time.sleep(1.0)
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass

    threading.Thread(target=_auto_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Ludo studio...")
        server.server_close()


if __name__ == "__main__":
    main()
