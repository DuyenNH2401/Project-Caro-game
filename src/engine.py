# src/engine.py
from __future__ import annotations
from typing import Optional, Tuple, List
from models import GameState, Player, Move, Cell, Coord
from datetime import datetime

DIRS = [(1,0),(0,1),(1,1),(1,-1)]  # vertical, horizontal, diag, anti-diag

class Engine:
    def __init__(self, p1: Player, p2: Player, board_size: int = 9, per_move_seconds: float = 20.0):
        self.players = [p1, p2]
        self.state = self._new_state(board_size, per_move_seconds)
        self.match_start_time = datetime.utcnow().isoformat() + "Z"
        self.match_id = f"match_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # ---- lifecycle ----
    def _new_state(self, size: int, per_move_seconds: float) -> GameState:
        grid = [[None for _ in range(size)] for _ in range(size)]
        return GameState(
            board_size=size,
            grid=grid,
            per_move_seconds=per_move_seconds,
            remaining_seconds=per_move_seconds,
        )

    def reset(self, board_size: Optional[int] = None) -> None:
        size = board_size or self.state.board_size
        self.state = self._new_state(size, self.state.per_move_seconds)
        for pl in self.players:
            pl.stones_placed = 0
            pl.skill_points = 0
        # Reset match tracking
        self.match_start_time = datetime.utcnow().isoformat() + "Z"
        self.match_id = f"match_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # ---- helpers ----
    def current_player(self) -> Player:
        return self.players[self.state.current_idx]

    def opponent_player(self) -> Player:
        return self.players[1 - self.state.current_idx]

    def in_bounds(self, r: int, c: int) -> bool:
        n = self.state.board_size
        return 0 <= r < n and 0 <= c < n

    def cell_empty_and_unblocked(self, r: int, c: int) -> bool:
        return self.state.grid[r][c] is None and (r, c) not in self.state.blocked_expiry

    # ---- rules & checks ----
    def _check_line(self, r: int, c: int, dr: int, dc: int, piece: str) -> int:
        count = 0
        n = self.state.board_size
        rr, cc = r, c
        while 0 <= rr < n and 0 <= cc < n and self.state.grid[rr][cc] == piece:
            count += 1
            rr += dr; cc += dc
        return count

    def is_win_from(self, r: int, c: int, piece: str) -> bool:
        for dr, dc in DIRS:
            back = self._check_line(r - dr, c - dc, -dr, -dc, piece)  # count behind
            fwd  = self._check_line(r, c, dr, dc, piece)              # count forward incl (r,c)
            if back + fwd >= self.state.win_length:
                return True
        return False

    def purge_expired_blocks(self) -> None:
        # remove blocks with expiry <= global_turn
        expired = [coord for coord, t in self.state.blocked_expiry.items() if t <= self.state.global_turn]
        for coord in expired:
            self.state.blocked_expiry.pop(coord, None)

    def get_winner_name(self) -> Optional[str]:
        """Get the name of the winner if game is over"""
        if self.state.winner_piece:
            for player in self.players:
                if player.piece == self.state.winner_piece:
                    return player.nickname or player.full_name
        return None

    def save_match_history(self):
        """Save match history to CSV file"""
        try:
            import storage
            winner = self.get_winner_name()
            storage.write_match_history_csv(
                match_id=self.match_id,
                match_date=self.match_start_time,
                player1_name=self.players[0].nickname or self.players[0].full_name,
                player2_name=self.players[1].nickname or self.players[1].full_name,
                moves=self.state.history,
                winner=winner,
                board_size=self.state.board_size,
                time_per_move=int(self.state.per_move_seconds)
            )
            print(f"Match history saved: {self.match_id}")
        except Exception as e:
            print(f"Error saving match history: {e}")

    # ---- moves ----
    def place_stone(self, r: int, c: int) -> bool:
        if self.state.winner_piece:
            return False
        if not self.in_bounds(r, c) or not self.cell_empty_and_unblocked(r, c):
            return False

        pl = self.current_player()
        self.state.grid[r][c] = pl.piece
        self.state.global_turn += 1

        mv = Move(
            turn_no=self.state.global_turn,
            player_id=pl.pid,
            player_name=pl.nickname or pl.full_name,
            piece=pl.piece,
            row=r, col=c
        )
        self.state.history.append(mv)

        # rotation: +1 skill per 5 stones placed by that player
        pl.stones_placed += 1
        if pl.stones_placed % 5 == 0:
            pl.skill_points += 1

        # win?
        if self.is_win_from(r, c, pl.piece):
            self.state.winner_piece = pl.piece
            # Save match history when game ends
            self.save_match_history()

        # after each stone, blocks may expire
        self.purge_expired_blocks()

        # switch turn & reset timer (even if win; UI can freeze if winner)
        self.state.current_idx = 1 - self.state.current_idx
        self.state.remaining_seconds = self.state.per_move_seconds
        return True

    def place_block(self, r: int, c: int) -> bool:
        if self.state.winner_piece:
            return False
        pl = self.current_player()
        if pl.skill_points <= 0:
            return False
        if not self.in_bounds(r, c):
            return False
        # can only block empty cell without stone
        if self.state.grid[r][c] is not None:
            return False
        if (r, c) in self.state.blocked_expiry:
            return False

        # "#" persists for 5 stones (global)
        self.state.blocked_expiry[(r, c)] = self.state.global_turn + 5
        pl.skill_points -= 1
        return True

    def undo_opponent_last_move(self) -> bool:
        """Current player spends 1 skill point to remove opponent's last stone.
        Does not rewind opponent's rotation history/skill grants; simple & fair enough."""
        if self.state.winner_piece:
            return False
        me = self.current_player()
        if me.skill_points <= 0:
            return False

        # find last move belonging to opponent
        idx = len(self.state.history) - 1
        opp = self.opponent_player()
        while idx >= 0 and self.state.history[idx].player_id != opp.pid:
            idx -= 1
        if idx < 0:
            return False

        mv = self.state.history.pop(idx)
        if self.state.grid[mv.row][mv.col] == mv.piece:
            self.state.grid[mv.row][mv.col] = None
            # global turn was counting stones placed; we reduce it only if that was the last move
            # To keep global expiry consistent, we won't decrement global_turn (keeps block expiries deterministic).
            # Winner must be cleared because board changed.
            self.state.winner_piece = None

        me.skill_points -= 1
        return True

    # ---- clock ----
    def tick(self, dt: float) -> None:
        if self.state.winner_piece:
            return
        self.state.remaining_seconds -= dt
        if self.state.remaining_seconds <= 0:
            # time out: skip turn (no stone placed)
            self.state.remaining_seconds = self.state.per_move_seconds
            self.state.current_idx = 1 - self.state.current_idx