# src/ai.py
from __future__ import annotations
import random, math
from typing import Tuple, List, Optional, Iterable
from models import GameState

# We treat blocked cells like "walls" when scanning (breaks lines).
SENT_WALL = "|"

WEIGHTS = {
    # pattern scores (bigger = stronger for CPU)
    "FIVE":        1_000_000,
    "OPEN_FOUR":     100_000,
    "CLOSED_FOUR":    40_000,
    "OPEN_THREE":      5_000,
    "CLOSED_THREE":       800,
    "OPEN_TWO":           200,
    "CLOSED_TWO":          60,
    "ONE":                 10,
}

class CPU:
    """
    Smarter CPU with 3 levels:
      - easy:   random legal move
      - medium: immediate win/block + greedy eval on candidate set
      - hard:   immediate win/block + depth-2 alpha-beta on pruned candidates
    Note: assumes CPU piece is 'O' by default. Pass piece='X' if you swap.
    """
    def __init__(self, difficulty: str = "easy", piece: str = "O"):
        assert difficulty in {"easy", "medium", "hard"}
        assert piece in {"X", "O"}
        self.difficulty = difficulty
        self.cpu_piece = piece
        self.opp_piece = "X" if piece == "O" else "O"

    # ---- public ------------------------------------------------------------
    def choose_move(self, state: GameState) -> Tuple[int, int]:
        # gather legal empties (exclude blocked)
        empties = legal_empties(state)
        if not empties:
            return (-1, -1)

        # if opening, prefer center-ish
        if board_is_empty(state):
            n = state.board_size
            return (n // 2, n // 2)

        # Tactics first: win in 1, block in 1
        win_now = self._find_tactical_win(state, self.cpu_piece, empties)
        if win_now:
            return win_now
        block_now = self._find_tactical_win(state, self.opp_piece, empties)
        if block_now:
            return block_now

        # Candidates: near existing stones to cut branching
        cands = candidate_moves(state, empties, radius=2)
        if not cands:
            cands = empties

        if self.difficulty == "easy":
            return random.choice(cands)

        if self.difficulty == "medium":
            # Greedy: pick max eval after hypothetical placement
            best, best_val = None, -math.inf
            grid = clone_grid(state)
            blockset = set(state.blocked_expiry.keys())
            for r, c in cands:
                grid[r][c] = self.cpu_piece
                val = evaluate_grid(grid, blockset, self.cpu_piece, state.win_length)
                grid[r][c] = None
                if val > best_val:
                    best, best_val = (r, c), val
            return best or random.choice(cands)

        # hard: tiny search with alpha-beta (depth 2)
        best, _ = self._search_best(state, cands, depth=2, breadth=12)
        return best or random.choice(cands)

    # ---- tactics -----------------------------------------------------------
    def _find_tactical_win(self, state: GameState, piece: str, empties: List[Tuple[int,int]]) -> Optional[Tuple[int,int]]:
        # One-ply: if placing 'piece' here makes 5 (or win_length), take it.
        n = state.board_size
        grid = state.grid
        for r, c in empties:
            if winning_if_place(grid, state.blocked_expiry, n, r, c, piece, state.win_length):
                return (r, c)
        return None

    # ---- search ------------------------------------------------------------
    def _search_best(self, state: GameState, cands: List[Tuple[int,int]], depth: int, breadth: int):
        """
        Negamax with alpha-beta, depth-2 default.
        Breadth limit: order by shallow eval and keep top-K.
        """
        grid = clone_grid(state)
        blocks = set(state.blocked_expiry.keys())
        # move ordering
        ordered = order_moves(grid, blocks, cands, self.cpu_piece, state.win_length)[:breadth]
        alpha, beta = -math.inf, math.inf
        best_move, best_val = None, -math.inf
        for (r, c) in ordered:
            grid[r][c] = self.cpu_piece
            val = -negamax(grid, blocks, depth-1, alpha=-beta, beta=-alpha,
                           me=self.opp_piece, opp=self.cpu_piece, win_len=state.win_length)
            grid[r][c] = None
            if val > best_val:
                best_val, best_move = val, (r, c)
            alpha = max(alpha, val)
            if alpha >= beta:
                break
        return best_move, best_val

# -----------------------------------------------------------------------------
# Helpers: legality, candidates, evaluation, search
# -----------------------------------------------------------------------------

def legal_empties(state: GameState) -> List[Tuple[int,int]]:
    blocked = set(state.blocked_expiry.keys())
    n = state.board_size
    out = []
    for r in range(n):
        for c in range(n):
            if state.grid[r][c] is None and (r, c) not in blocked:
                out.append((r, c))
    return out

def board_is_empty(state: GameState) -> bool:
    for row in state.grid:
        for v in row:
            if v in ("X","O"):
                return False
    return True

def candidate_moves(state: GameState, empties: List[Tuple[int,int]], radius: int = 2) -> List[Tuple[int,int]]:
    n = state.board_size
    stones = {(r, c) for r in range(n) for c in range(n) if state.grid[r][c] in ("X","O")}
    if not stones:
        return []
    cands = set()
    for (sr, sc) in stones:
        for r in range(sr - radius, sr + radius + 1):
            for c in range(sc - radius, sc + radius + 1):
                if 0 <= r < n and 0 <= c < n and state.grid[r][c] is None and (r, c) not in state.blocked_expiry:
                    cands.add((r, c))
    # small heuristic: bias towards center
    ctr = (n - 1) / 2.0
    return sorted(cands, key=lambda rc: abs(rc[0]-ctr)+abs(rc[1]-ctr))

def clone_grid(state: GameState):
    return [row[:] for row in state.grid]

def winning_if_place(grid, blocked_expiry, n, r, c, piece, win_len) -> bool:
    if (r, c) in blocked_expiry or grid[r][c] is not None:
        return False
    grid[r][c] = piece
    won = is_win_from_grid(grid, n, r, c, piece, win_len)
    grid[r][c] = None
    return won

DIRS = [(1,0),(0,1),(1,1),(1,-1)]

def is_win_from_grid(grid, n, r, c, piece, win_len) -> bool:
    for dr, dc in DIRS:
        cnt = 1
        rr, cc = r+dr, c+dc
        while 0 <= rr < n and 0 <= cc < n and grid[rr][cc] == piece:
            cnt += 1; rr += dr; cc += dc
        rr, cc = r-dr, c-dc
        while 0 <= rr < n and 0 <= cc < n and grid[rr][cc] == piece:
            cnt += 1; rr -= dr; cc -= dc
        if cnt >= win_len:
            return True
    return False

def order_moves(grid, blocks, moves, me, win_len) -> List[Tuple[int,int]]:
    """Simple ordering: immediate wins > blocks > eval score."""
    n = len(grid)
    wins = []
    blocks_list = []
    rest = []
    # classify
    for r, c in moves:
        if winning_if_place(grid, blocks, n, r, c, me, win_len):
            wins.append((r, c)); continue
        opp = "X" if me == "O" else "O"
        if winning_if_place(grid, blocks, n, r, c, opp, win_len):
            blocks_list.append((r, c)); continue
        rest.append((r, c))
    # order rest with shallow eval
    rest_sorted = sorted(rest, key=lambda rc: shallow_move_score(grid, blocks, rc[0], rc[1], me, win_len), reverse=True)
    return wins + blocks_list + rest_sorted

def shallow_move_score(grid, blocks, r, c, me, win_len):
    grid[r][c] = me
    val = evaluate_grid(grid, blocks, me, win_len)
    grid[r][c] = None
    return val

# ---- evaluation -------------------------------------------------------------

def evaluate_grid(grid, blocks, me, win_len) -> float:
    """Pattern-based static eval. Positive is good for 'me'."""
    opp = "X" if me == "O" else "O"
    n = len(grid)

    lines: List[List[str]] = []

    def push_line(seq: List[str]):
        if seq:
            lines.append(seq[:])

    # rows
    for r in range(n):
        cur = []
        for c in range(n):
            cur.append(enc_cell(grid, blocks, r, c))
        push_line(cur)
    # cols
    for c in range(n):
        cur = []
        for r in range(n):
            cur.append(enc_cell(grid, blocks, r, c))
        push_line(cur)
    # diag /
    for start in range(n):
        cur = []
        r, c = start, 0
        while r >= 0 and c < n:
            cur.append(enc_cell(grid, blocks, r, c))
            r -= 1; c += 1
        push_line(cur)
    for start in range(1, n):
        cur = []
        r, c = n-1, start
        while r >= 0 and c < n:
            cur.append(enc_cell(grid, blocks, r, c))
            r -= 1; c += 1
        push_line(cur)
    # diag \
    for start in range(n):
        cur = []
        r, c = start, 0
        while r < n and c < n:
            cur.append(enc_cell(grid, blocks, r, c))
            r += 1; c += 1
        push_line(cur)
    for start in range(1, n):
        cur = []
        r, c = 0, start
        while r < n and c < n:
            cur.append(enc_cell(grid, blocks, r, c))
            r += 1; c += 1
        push_line(cur)

    my_score = 0
    opp_score = 0

    # score patterns in all lines
    for seq in lines:
        my_score  += score_line(seq, me,  win_len)
        opp_score += score_line(seq, opp, win_len)

    # centrality bias
    ctr = (n - 1) / 2.0
    cen_bonus = 0.0
    for r in range(n):
        for c in range(n):
            if grid[r][c] == me:
                cen_bonus += 0.3 / (1 + abs(r-ctr) + abs(c-ctr))
            elif grid[r][c] == opp:
                cen_bonus -= 0.3 / (1 + abs(r-ctr) + abs(c-ctr))

    # weigh opponent threats slightly higher to encourage blocking
    return (my_score - 1.15 * opp_score) + cen_bonus

def enc_cell(grid, blocks, r, c):
    if (r, c) in blocks:
        return SENT_WALL  # wall breaks patterns
    v = grid[r][c]
    if v is None:
        return "."
    return v

def score_line(seq: List[str], piece: str, win_len: int) -> int:
    s = 0
    n = len(seq)
    i = 0
    while i < n:
        if seq[i] != piece:
            i += 1
            continue
        j = i
        while j < n and seq[j] == piece:
            j += 1
        L = j - i
        left  = seq[i-1] if i-1 >= 0 else SENT_WALL
        right = seq[j]   if j   < n else SENT_WALL
        open_ends = (1 if left == "." else 0) + (1 if right == "." else 0)

        if L >= win_len:
            s += WEIGHTS["FIVE"]; i = j; continue
        if L == 4:
            s += WEIGHTS["OPEN_FOUR"] if open_ends == 2 else WEIGHTS["CLOSED_FOUR"]
        elif L == 3:
            s += WEIGHTS["OPEN_THREE"] if open_ends == 2 else WEIGHTS["CLOSED_THREE"]
        elif L == 2:
            s += WEIGHTS["OPEN_TWO"] if open_ends == 2 else WEIGHTS["CLOSED_TWO"]
        else:
            s += WEIGHTS["ONE"]
        i = j
    return s

# ---- negamax ---------------------------------------------------------------

def negamax(grid, blocks, depth, alpha, beta, me, opp, win_len) -> float:
    # terminal: direct five on board?
    if has_win_anywhere(grid, me, win_len):
        return  WEIGHTS["FIVE"]
    if has_win_anywhere(grid, opp, win_len):
        return -WEIGHTS["FIVE"]
    if depth == 0:
        return evaluate_grid(grid, blocks, me, win_len)

    moves = pruned_moves_for_search(grid, blocks, radius=2)
    if not moves:
        return 0.0

    # order by shallow score
    moves = sorted(moves, key=lambda rc: shallow_move_score(grid, blocks, rc[0], rc[1], me, win_len), reverse=True)

    best = -math.inf
    for (r, c) in moves[:12]:  # hard cap at 12 per node
        grid[r][c] = me
        val = -negamax(grid, blocks, depth-1, -beta, -alpha, opp, me, win_len)
        grid[r][c] = None
        if val > best:
            best = val
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best

def has_win_anywhere(grid, piece, win_len) -> bool:
    n = len(grid)
    for r in range(n):
        for c in range(n):
            if grid[r][c] == piece and is_win_from_grid(grid, n, r, c, piece, win_len):
                return True
    return False

def pruned_moves_for_search(grid, blocks, radius=2):
    n = len(grid)
    stones = {(r,c) for r in range(n) for c in range(n) if grid[r][c] in ("X","O")}
    if not stones:
        ctr = n//2
        return [(ctr, ctr)]
    cands = set()
    for (sr, sc) in stones:
        for r in range(sr - radius, sr + radius + 1):
            for c in range(sc - radius, sc + radius + 1):
                if 0 <= r < n and 0 <= c < n and grid[r][c] is None and (r, c) not in blocks:
                    cands.add((r, c))
    return list(cands)
