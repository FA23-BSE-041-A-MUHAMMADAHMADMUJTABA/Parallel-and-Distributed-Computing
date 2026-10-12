"""
================================================================================
CSC-334: Parallel and Distributed Computing - Lab 5
Module: Lab5(ludo with bluetooth)/ludo_logic.py
Description: Authentic Ludo Game Engine converted from Dart/Flutter to Python.
             Preserves exact 15x15 board geometry, player paths, safe squares,
             blockade mechanics, token captures, and victory rules.
================================================================================
"""

import random
from typing import Dict, List, Optional, Tuple, Any

# 15x15 Board Grid Size
BOARD_GRID_SIZE = 15
TOTAL_GRID_CELLS = 225

# Player Color Mapping
PLAYER_COLORS = {
    0: {"name": "Red", "hex": "#e11d48", "bg": "#ffe4e6"},
    1: {"name": "Green", "hex": "#16a34a", "bg": "#dcfce7"},
    2: {"name": "Yellow", "hex": "#ca8a04", "bg": "#fef9c3"},
    3: {"name": "Blue", "hex": "#2563eb", "bg": "#dbeafe"},
}

# Starting positions for tokens in home yard (grid indices 0-224)
HOME_INDICES = {
    0: [31, 33, 61, 63],      # Red tokens in top-left yard
    1: [40, 42, 70, 72],      # Green tokens in top-right yard
    2: [166, 168, 196, 198],  # Yellow tokens in bottom-right yard
    3: [175, 177, 205, 207],  # Blue tokens in bottom-left yard
}

# Safe squares where tokens CANNOT be captured (Star squares & Entry squares)
SAFE_GRID_INDICES = [91, 23, 133, 201, 36, 102, 188, 122]

# Exact Board Paths from Dart (0-50 main track, 51 entry, 52-56 home stretch)
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
    """
    Pure Ludo Rules Engine managing state, moves, captures, turns, and victory.
    State is fully serializable to/from dict for seamless network replication.
    """
    def __init__(self, num_players: int = 2, player_names: Optional[List[str]] = None):
        self.num_players = max(2, min(4, num_players))
        self.player_names = player_names or [f"Player {i + 1}" for i in range(self.num_players)]
        
        # Game State
        self.game_started = True
        self.current_player_index = 0
        self.dice_value = 0
        self.movable_tokens: List[int] = []
        self.consecutive_sixes = 0
        self.game_message = f"{self.player_names[0]}'s turn to roll!"
        self.winner: Optional[int] = None
        self.is_rolling = False
        self.last_action_log: List[str] = []

        # Token positions: Map player_idx -> list of 4 token positions (-1 = in home yard, 0-56 = on track)
        self.player_tokens: Dict[int, List[int]] = {
            i: [-1, -1, -1, -1] for i in range(self.num_players)
        }
        # Count of finished tokens (reached position 56)
        self.player_finished_tokens: Dict[int, int] = {
            i: 0 for i in range(self.num_players)
        }

    def get_grid_index_for_position(self, player_idx: int, pos: int) -> int:
        """Converts player's relative path index (0-56) to 15x15 board grid index (0-224)."""
        if pos < 0 or pos > 56:
            return -1
        return PLAYER_PATHS.get(player_idx, {}).get(pos, -1)

    def get_home_grid_index(self, player_idx: int, token_idx: int) -> int:
        """Returns the grid cell for a token resting inside its starting home yard."""
        return HOME_INDICES[player_idx][token_idx]

    def roll_dice(self, forced_val: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes a dice roll for current player:
        - Returns dice value (1-6)
        - Tracks consecutive sixes (3 sixes skips turn)
        - Calculates which tokens can legally move
        """
        if self.dice_value != 0 or self.winner is not None:
            return {"dice": self.dice_value, "skipped": False, "movable": self.movable_tokens}

        val = forced_val if forced_val is not None else random.randint(1, 6)
        self.dice_value = val

        curr_name = self.player_names[self.current_player_index]

        # Check consecutive sixes
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

        # Calculate legal moves
        self.movable_tokens = self._calculate_movable_tokens()

        if not self.movable_tokens:
            msg = f"{curr_name} rolled a {val} (No valid moves)."
            self.game_message = msg
            self.last_action_log.append(msg)
            # Advance turn if no moves possible
            self.next_player()
            return {"dice": val, "skipped": False, "movable": []}
        else:
            msg = f"{curr_name} rolled a {val}! Choose a token to move."
            self.game_message = msg
            self.last_action_log.append(f"{curr_name} rolled a {val}.")
            return {"dice": val, "skipped": False, "movable": self.movable_tokens}

    def _calculate_movable_tokens(self) -> List[int]:
        """Identifies which of current player's 4 tokens can legally move."""
        movable = []
        tokens = self.player_tokens.get(self.current_player_index, [-1, -1, -1, -1])

        for token_idx, pos in enumerate(tokens):
            if pos == -1:
                # Token in yard can only exit if rolled a 6
                if self.dice_value == 6:
                    if not self._is_position_blocked(self.current_player_index, 0):
                        movable.append(token_idx)
            elif 0 <= pos < 56:
                new_pos = pos + self.dice_value
                if new_pos <= 56:
                    # Verify no opponent blockade along path
                    if not self._is_path_blocked(self.current_player_index, pos, self.dice_value):
                        movable.append(token_idx)
            # Token at 56 is already finished at home
        return movable

    def _is_position_blocked(self, player_idx: int, pos: int) -> bool:
        """Returns True if position is occupied by a 2+ token blockade of opponents."""
        grid_idx = self.get_grid_index_for_position(player_idx, pos)
        if grid_idx == -1:
            return False

        opponent_count = 0
        for opp_idx in range(self.num_players):
            if opp_idx == player_idx:
                continue
            for opp_pos in self.player_tokens.get(opp_idx, []):
                if 0 <= opp_pos <= 51:
                    if self.get_grid_index_for_position(opp_idx, opp_pos) == grid_idx:
                        opponent_count += 1
        return opponent_count >= 2

    def _is_path_blocked(self, player_idx: int, start_pos: int, steps: int) -> bool:
        """Checks if intermediate squares are blocked by opponent blockades."""
        for step in range(1, steps + 1):
            check_pos = start_pos + step
            if check_pos <= 51 and self._is_position_blocked(player_idx, check_pos):
                return True
        return False

    def move_token(self, token_idx: int) -> Dict[str, Any]:
        """
        Executes a move for token_idx:
        - Updates token position
        - Handles home goal entry (pos 56)
        - Handles capturing opponent tokens on non-safe squares
        - Grants bonus turns for 6, capture, or home goal
        - Checks victory condition
        """
        if token_idx not in self.movable_tokens or self.dice_value == 0:
            return {"success": False, "error": "Invalid token move"}

        curr_p = self.current_player_index
        curr_name = self.player_names[curr_p]
        curr_pos = self.player_tokens[curr_p][token_idx]
        new_pos = 0 if curr_pos == -1 else curr_pos + self.dice_value

        killed_opponent = False
        captured_player_name = ""
        token_reached_home = False

        # 1. Home Goal Check
        if new_pos == 56:
            token_reached_home = True
            self.player_finished_tokens[curr_p] += 1
            log_entry = f"🎯 {curr_name}'s token reached Home! ({self.player_finished_tokens[curr_p]}/4)"
            self.last_action_log.append(log_entry)

            # Victory Check
            if self.player_finished_tokens[curr_p] == 4:
                self.winner = curr_p
                win_msg = f"🏆 {curr_name} WINS THE GAME! 🏆"
                self.game_message = win_msg
                self.last_action_log.append(win_msg)
                self.player_tokens[curr_p][token_idx] = new_pos
                self.movable_tokens = []
                self.dice_value = 0
                return {"success": True, "winner": curr_p, "reached_home": True}

        # 2. Opponent Capture Check (only on main track 0-51, not in safe zones)
        if new_pos <= 51 and not token_reached_home:
            grid_idx = self.get_grid_index_for_position(curr_p, new_pos)
            if grid_idx != -1 and grid_idx not in SAFE_GRID_INDICES:
                opp_to_kill = -1
                opp_token_to_kill = -1
                opp_count = 0

                for opp_i in range(self.num_players):
                    if opp_i == curr_p:
                        continue
                    for opp_t_idx, opp_p_pos in enumerate(self.player_tokens.get(opp_i, [])):
                        if 0 <= opp_p_pos <= 51 and self.get_grid_index_for_position(opp_i, opp_p_pos) == grid_idx:
                            opp_count += 1
                            opp_to_kill = opp_i
                            opp_token_to_kill = opp_t_idx

                # Capture only if exactly 1 token (blockade cannot be killed)
                if opp_count == 1 and opp_to_kill != -1:
                    killed_opponent = True
                    captured_player_name = self.player_names[opp_to_kill]
                    # Send opponent token back to yard (-1)
                    self.player_tokens[opp_to_kill][opp_token_to_kill] = -1
                    cap_msg = f"⚔️ {curr_name} captured {captured_player_name}'s token!"
                    self.game_message = cap_msg
                    self.last_action_log.append(cap_msg)

        # Apply position update
        self.player_tokens[curr_p][token_idx] = new_pos
        self.movable_tokens = []

        # 3. Turn Progression & Bonus Turns
        # Player gets bonus turn if: rolled 6, killed opponent, or reached home!
        gets_bonus = (self.dice_value == 6 or killed_opponent or token_reached_home)

        if gets_bonus:
            bonus_reason = "rolled a 6" if self.dice_value == 6 else ("captured a token" if killed_opponent else "reached home")
            self.game_message = f"{curr_name} gets a BONUS TURN ({bonus_reason})!"
            self.dice_value = 0
        else:
            self.next_player()

        return {
            "success": True,
            "player": curr_p,
            "token": token_idx,
            "new_pos": new_pos,
            "killed_opponent": killed_opponent,
            "token_reached_home": token_reached_home,
            "bonus_turn": gets_bonus,
            "winner": self.winner
        }

    def next_player(self):
        """Passes turn to the next active player."""
        self.current_player_index = (self.current_player_index + 1) % self.num_players
        self.dice_value = 0
        self.movable_tokens = []
        self.consecutive_sixes = 0
        self.game_message = f"{self.player_names[self.current_player_index]}'s turn to roll!"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes entire game state into a JSON-compatible dictionary."""
        return {
            "num_players": self.num_players,
            "player_names": self.player_names,
            "game_started": self.game_started,
            "current_player_index": self.current_player_index,
            "dice_value": self.dice_value,
            "movable_tokens": self.movable_tokens,
            "consecutive_sixes": self.consecutive_sixes,
            "game_message": self.game_message,
            "winner": self.winner,
            "player_tokens": {str(k): list(v) for k, v in self.player_tokens.items()},
            "player_finished_tokens": {str(k): v for k, v in self.player_finished_tokens.items()},
            "last_action_log": self.last_action_log[-10:]
        }

    def from_dict(self, data: Dict[str, Any]):
        """Reconstructs game state from replicated dictionary."""
        self.num_players = data.get("num_players", self.num_players)
        self.player_names = data.get("player_names", self.player_names)
        self.game_started = data.get("game_started", True)
        self.current_player_index = data.get("current_player_index", 0)
        self.dice_value = data.get("dice_value", 0)
        self.movable_tokens = data.get("movable_tokens", [])
        self.consecutive_sixes = data.get("consecutive_sixes", 0)
        self.game_message = data.get("game_message", "")
        self.winner = data.get("winner")
        
        raw_tokens = data.get("player_tokens", {})
        self.player_tokens = {int(k): list(v) for k, v in raw_tokens.items()}
        
        raw_finished = data.get("player_finished_tokens", {})
        self.player_finished_tokens = {int(k): v for k, v in raw_finished.items()}
        
        self.last_action_log = data.get("last_action_log", [])
