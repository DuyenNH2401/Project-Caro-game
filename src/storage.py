# src/storage.py
from __future__ import annotations
import os, json, csv
from typing import Any, Dict, List, Optional
from datetime import datetime
from models import Move

DATA_DIR = os.path.join("data")
LOG_DIR = os.path.join(DATA_DIR, "logs")
REPLAY_DIR = os.path.join(DATA_DIR, "replays")
MATCH_HISTORY_DIR = os.path.join(DATA_DIR, "match_history")
RULES_PATH = os.path.join(DATA_DIR, "rules.json")
THEMES_PATH = os.path.join(DATA_DIR, "themes.json")
PREFERENCES_PATH = os.path.join(DATA_DIR, "preferences.json")

DEFAULT_RULES = {
    "allowed_board_sizes": [3, 5, 7, 9, 13, 15, 19],
    "per_move_seconds": 20,
    "win_length": "min(5, board_size)"
}

DEFAULT_THEMES = {
    "pieces": "letters",  # "letters" | "stones" | "custom"
    "avatars": {
        "p1": None,
        "p2": None
    }
}

DEFAULT_PREFERENCES = {
    "theme": "default",
    "board_size": 13,
    "difficulty": "medium",
    "per_move_seconds": 20,
    "sound_enabled": True,
    "music_enabled": True,
}


def _safe_read_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default.copy()


def _safe_write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_rules() -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(RULES_PATH):
        _safe_write_json(RULES_PATH, DEFAULT_RULES)
    return _safe_read_json(RULES_PATH, DEFAULT_RULES)


def load_themes() -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(THEMES_PATH):
        _safe_write_json(THEMES_PATH, DEFAULT_THEMES)
    return _safe_read_json(THEMES_PATH, DEFAULT_THEMES)


def load_preferences() -> Dict[str, Any]:
    """Load user preferences (theme, last settings, etc.)"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PREFERENCES_PATH):
        _safe_write_json(PREFERENCES_PATH, DEFAULT_PREFERENCES)
    return _safe_read_json(PREFERENCES_PATH, DEFAULT_PREFERENCES)


def save_preferences(preferences: Dict[str, Any]) -> None:
    """Save user preferences"""
    _safe_write_json(PREFERENCES_PATH, preferences)


def write_history_csv(match_id: str, moves: List[Move]) -> None:
    """OLD FORMAT - Keep for backward compatibility"""
    os.makedirs(LOG_DIR, exist_ok=True)
    path = os.path.join(LOG_DIR, f"{match_id}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["turn", "player_name", "piece", "row", "col", "timestamp"])
        for m in moves:
            w.writerow(m.csv_row())


def append_replay_jsonl(match_id: str, moves: List[Move]) -> None:
    """OLD FORMAT - Keep for backward compatibility"""
    os.makedirs(REPLAY_DIR, exist_ok=True)
    path = os.path.join(REPLAY_DIR, f"{match_id}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        for m in moves:
            f.write(json.dumps({
                "turn": m.turn_no, "player_name": m.player_name, "piece": m.piece,
                "row": m.row, "col": m.col, "ts": m.ts
            }) + "\n")


def write_match_history_csv(
        match_id: str,
        match_date: str,
        player1_name: str,
        player2_name: str,
        moves: List[Move],
        winner: Optional[str] = None,
        board_size: int = 13,
        time_per_move: int = 20
) -> None:
    """
    NEW FORMAT: Write match history in the requested CSV format

    Format:
    - Column 1: Timestamp/Date
    - Column 2: Player 1 moves [move_number, row, col]
    - Column 3: Player 2 moves [move_number, row, col]

    Args:
        match_id: Unique match identifier
        match_date: Date/time of the match (ISO format)
        player1_name: Name of player 1
        player2_name: Name of player 2
        moves: List of all moves in the match
        winner: Name of the winner (optional)
        board_size: Size of the board
        time_per_move: Time limit per move
    """
    os.makedirs(MATCH_HISTORY_DIR, exist_ok=True)
    path = os.path.join(MATCH_HISTORY_DIR, f"{match_id}.csv")

    # Separate moves by player
    player1_moves = {}  # move_number -> (row, col)
    player2_moves = {}  # move_number -> (row, col)

    for move in moves:
        if move.player_name == player1_name or move.player_id == "p1":
            player1_moves[move.turn_no] = (move.row, move.col)
        else:
            player2_moves[move.turn_no] = (move.row, move.col)

    # Find max turn number
    max_turn = max(
        max(player1_moves.keys(), default=0),
        max(player2_moves.keys(), default=0)
    )

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header with metadata
        writer.writerow(["Match History"])
        writer.writerow(["Match ID", match_id])
        writer.writerow(["Date", match_date])
        writer.writerow(["Player 1", player1_name])
        writer.writerow(["Player 2", player2_name])
        writer.writerow(["Board Size", f"{board_size}x{board_size}"])
        writer.writerow(["Time per Move", f"{time_per_move}s"])
        if winner:
            writer.writerow(["Winner", winner])
        writer.writerow([])  # Empty row

        # Write column headers
        writer.writerow(["Timestamp", f"{player1_name} Moves", f"{player2_name} Moves"])

        # Write moves row by row
        move_count = 0
        for turn in range(1, max_turn + 1):
            timestamp = ""
            p1_move = ""
            p2_move = ""

            # Get timestamp from first move in this turn pair
            if turn in player1_moves:
                move = next(
                    (m for m in moves if m.turn_no == turn and (m.player_id == "p1" or m.player_name == player1_name)),
                    None)
                if move:
                    timestamp = move.ts
                row, col = player1_moves[turn]
                move_count += 1
                p1_move = f"[{move_count}, {row}, {col}]"

            if turn in player2_moves:
                if not timestamp:
                    move = next((m for m in moves if m.turn_no == turn), None)
                    if move:
                        timestamp = move.ts
                row, col = player2_moves[turn]
                move_count += 1
                p2_move = f"[{move_count}, {row}, {col}]"

            # Only write row if at least one player made a move
            if p1_move or p2_move:
                writer.writerow([timestamp, p1_move, p2_move])


def read_match_history_csv(match_id: str) -> Optional[Dict[str, Any]]:
    """
    Read match history from CSV file

    Returns:
        Dictionary containing match metadata and moves, or None if file doesn't exist
    """
    path = os.path.join(MATCH_HISTORY_DIR, f"{match_id}.csv")

    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

            # Parse metadata
            metadata = {}
            move_data = []
            in_moves_section = False

            for i, row in enumerate(rows):
                if not row:
                    continue

                if row[0] == "Timestamp":
                    in_moves_section = True
                    continue

                if not in_moves_section:
                    if len(row) >= 2:
                        metadata[row[0]] = row[1]
                else:
                    # Parse move data
                    move_data.append({
                        "timestamp": row[0] if len(row) > 0 else "",
                        "player1_move": row[1] if len(row) > 1 else "",
                        "player2_move": row[2] if len(row) > 2 else ""
                    })

            return {
                "metadata": metadata,
                "moves": move_data
            }

    except Exception as e:
        print(f"Error reading match history: {e}")
        return None


def list_match_histories() -> List[Dict[str, str]]:
    """
    List all available match histories

    Returns:
        List of dictionaries with match_id, date, and file path
    """
    os.makedirs(MATCH_HISTORY_DIR, exist_ok=True)

    matches = []
    for filename in os.listdir(MATCH_HISTORY_DIR):
        if filename.endswith('.csv'):
            match_id = filename[:-4]  # Remove .csv extension
            path = os.path.join(MATCH_HISTORY_DIR, filename)

            # Try to get date from file
            try:
                data = read_match_history_csv(match_id)
                if data:
                    matches.append({
                        "match_id": match_id,
                        "date": data["metadata"].get("Date", "Unknown"),
                        "player1": data["metadata"].get("Player 1", "Unknown"),
                        "player2": data["metadata"].get("Player 2", "Unknown"),
                        "winner": data["metadata"].get("Winner", "N/A"),
                        "path": path
                    })
            except Exception:
                # If parsing fails, just add basic info
                matches.append({
                    "match_id": match_id,
                    "date": "Unknown",
                    "path": path
                })

    # Sort by date (newest first)
    matches.sort(key=lambda x: x.get("date", ""), reverse=True)
    return matches

def save_themes(data: Dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(THEMES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)