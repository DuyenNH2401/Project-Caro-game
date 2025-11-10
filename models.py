# src/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from datetime import datetime

Cell = Optional[str]  # None, 'X', 'O', or '#'
Coord = Tuple[int, int]

BOARD_SIZES = [3, 5, 7, 9, 13, 15, 19]

@dataclass
class Player:
    pid: str
    full_name: str
    nickname: str
    gender: str  # 'M' | 'F' | 'N'
    piece: str   # 'X' or 'O'
    avatar_path: Optional[str] = None
    stones_placed: int = 0
    skill_points: int = 0

@dataclass
class Move:
    turn_no: int
    player_id: str
    player_name: str
    piece: str               # 'X' or 'O'
    row: int
    col: int
    action_type: str = "stone"  # "stone", "block", "undo"
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def csv_row(self) -> List[str]:
        return [str(self.turn_no), self.player_name, self.piece, str(self.row), str(self.col), self.ts]

@dataclass
class GameState:
    board_size: int
    grid: List[List[Cell]]
    blocked_expiry: Dict[Coord, int] = field(default_factory=dict)  # (r,c) -> expires_at_global_turn
    history: List[Move] = field(default_factory=list)
    current_idx: int = 0
    global_turn: int = 0  # counts only stones placed (not blocks)
    per_move_seconds: float = 20.0
    remaining_seconds: float = 20.0
    winner_piece: Optional[str] = None

    @property
    def win_length(self) -> int:
        # Keep gomoku spirit but allow tiny boards to finish
        return min(5, self.board_size)

@dataclass
class Match:
    best_of: int = 3
    wins: Dict[str, int] = field(default_factory=dict)  # pid -> wins

    def record_win(self, pid: str) -> None:
        self.wins[pid] = self.wins.get(pid, 0) + 1

    def majority(self) -> int:
        return self.best_of // 2 + 1

    def is_over(self) -> bool:
        return any(w >= self.majority() for w in self.wins.values())
