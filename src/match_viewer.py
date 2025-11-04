<<<<<<< HEAD
# src/match_viewer.py
"""
Match History Viewer - Tool to view saved match histories
"""
import os
import sys
import storage
from datetime import datetime


def format_move(move_str: str) -> str:
    """Format move string for display"""
    if not move_str:
        return "---"
    return move_str


def view_match(match_id: str):
    """Display a specific match history"""
    data = storage.read_match_history_csv(match_id)

    if not data:
        print(f"Match '{match_id}' not found!")
        return

    metadata = data["metadata"]
    moves = data["moves"]

    # Display metadata
    print("\n" + "=" * 80)
    print("MATCH HISTORY".center(80))
    print("=" * 80)
    print(f"Match ID:      {metadata.get('Match ID', 'N/A')}")
    print(f"Date:          {metadata.get('Date', 'N/A')}")
    print(f"Player 1:      {metadata.get('Player 1', 'N/A')}")
    print(f"Player 2:      {metadata.get('Player 2', 'N/A')}")
    print(f"Board Size:    {metadata.get('Board Size', 'N/A')}")
    print(f"Time/Move:     {metadata.get('Time per Move', 'N/A')}")
    print(f"Winner:        {metadata.get('Winner', 'N/A')}")
    print("=" * 80)

    # Display moves
    print(f"\n{'Turn':<6} {'Timestamp':<28} {metadata.get('Player 1', 'P1'):<20} {metadata.get('Player 2', 'P2'):<20}")
    print("-" * 80)

    for i, move_data in enumerate(moves, 1):
        timestamp = move_data.get("timestamp", "")[:26]  # Truncate timestamp
        p1_move = format_move(move_data.get("player1_move", ""))
        p2_move = format_move(move_data.get("player2_move", ""))
        print(f"{i:<6} {timestamp:<28} {p1_move:<20} {p2_move:<20}")

    print("=" * 80 + "\n")


def list_matches():
    """List all available matches"""
    matches = storage.list_match_histories()

    if not matches:
        print("\nNo match histories found!")
        return

    print("\n" + "=" * 100)
    print("AVAILABLE MATCH HISTORIES".center(100))
    print("=" * 100)
    print(f"{'#':<4} {'Match ID':<30} {'Date':<20} {'Players':<30} {'Winner':<15}")
    print("-" * 100)

    for i, match in enumerate(matches, 1):
        match_id = match.get("match_id", "N/A")
        date = match.get("date", "N/A")[:19]  # Just date and time
        p1 = match.get("player1", "P1")
        p2 = match.get("player2", "P2")
        players = f"{p1} vs {p2}"
        winner = match.get("winner", "N/A")

        print(f"{i:<4} {match_id:<30} {date:<20} {players:<30} {winner:<15}")

    print("=" * 100 + "\n")


def main():
    """Interactive match history viewer"""
    if len(sys.argv) > 1:
        # View specific match
        match_id = sys.argv[1]
        view_match(match_id)
    else:
        # Interactive mode
        while True:
            print("\n╔════════════════════════════════════╗")
            print("║     MATCH HISTORY VIEWER          ║")
            print("╚════════════════════════════════════╝")
            print("\n1. List all matches")
            print("2. View specific match")
            print("3. Exit")

            choice = input("\nEnter your choice (1-3): ").strip()

            if choice == "1":
                list_matches()
            elif choice == "2":
                list_matches()
                match_num = input("\nEnter match number (or match ID): ").strip()

                # Check if it's a number (list index) or match ID
                try:
                    idx = int(match_num) - 1
                    matches = storage.list_match_histories()
                    if 0 <= idx < len(matches):
                        match_id = matches[idx]["match_id"]
                        view_match(match_id)
                    else:
                        print("Invalid match number!")
                except ValueError:
                    # It's a match ID
                    view_match(match_num)
            elif choice == "3":
                print("\nGoodbye!")
                break
            else:
                print("\nInvalid choice!")


if __name__ == "__main__":
=======
# src/match_viewer.py
"""
Match History Viewer - Tool to view saved match histories
"""
import os
import sys
import storage
from datetime import datetime


def format_move(move_str: str) -> str:
    """Format move string for display"""
    if not move_str:
        return "---"
    return move_str


def view_match(match_id: str):
    """Display a specific match history"""
    data = storage.read_match_history_csv(match_id)

    if not data:
        print(f"Match '{match_id}' not found!")
        return

    metadata = data["metadata"]
    moves = data["moves"]

    # Display metadata
    print("\n" + "=" * 80)
    print("MATCH HISTORY".center(80))
    print("=" * 80)
    print(f"Match ID:      {metadata.get('Match ID', 'N/A')}")
    print(f"Date:          {metadata.get('Date', 'N/A')}")
    print(f"Player 1:      {metadata.get('Player 1', 'N/A')}")
    print(f"Player 2:      {metadata.get('Player 2', 'N/A')}")
    print(f"Board Size:    {metadata.get('Board Size', 'N/A')}")
    print(f"Time/Move:     {metadata.get('Time per Move', 'N/A')}")
    print(f"Winner:        {metadata.get('Winner', 'N/A')}")
    print("=" * 80)

    # Display moves
    print(f"\n{'Turn':<6} {'Timestamp':<28} {metadata.get('Player 1', 'P1'):<20} {metadata.get('Player 2', 'P2'):<20}")
    print("-" * 80)

    for i, move_data in enumerate(moves, 1):
        timestamp = move_data.get("timestamp", "")[:26]  # Truncate timestamp
        p1_move = format_move(move_data.get("player1_move", ""))
        p2_move = format_move(move_data.get("player2_move", ""))
        print(f"{i:<6} {timestamp:<28} {p1_move:<20} {p2_move:<20}")

    print("=" * 80 + "\n")


def list_matches():
    """List all available matches"""
    matches = storage.list_match_histories()

    if not matches:
        print("\nNo match histories found!")
        return

    print("\n" + "=" * 100)
    print("AVAILABLE MATCH HISTORIES".center(100))
    print("=" * 100)
    print(f"{'#':<4} {'Match ID':<30} {'Date':<20} {'Players':<30} {'Winner':<15}")
    print("-" * 100)

    for i, match in enumerate(matches, 1):
        match_id = match.get("match_id", "N/A")
        date = match.get("date", "N/A")[:19]  # Just date and time
        p1 = match.get("player1", "P1")
        p2 = match.get("player2", "P2")
        players = f"{p1} vs {p2}"
        winner = match.get("winner", "N/A")

        print(f"{i:<4} {match_id:<30} {date:<20} {players:<30} {winner:<15}")

    print("=" * 100 + "\n")


def main():
    """Interactive match history viewer"""
    if len(sys.argv) > 1:
        # View specific match
        match_id = sys.argv[1]
        view_match(match_id)
    else:
        # Interactive mode
        while True:
            print("\n╔════════════════════════════════════╗")
            print("║     MATCH HISTORY VIEWER          ║")
            print("╚════════════════════════════════════╝")
            print("\n1. List all matches")
            print("2. View specific match")
            print("3. Exit")

            choice = input("\nEnter your choice (1-3): ").strip()

            if choice == "1":
                list_matches()
            elif choice == "2":
                list_matches()
                match_num = input("\nEnter match number (or match ID): ").strip()

                # Check if it's a number (list index) or match ID
                try:
                    idx = int(match_num) - 1
                    matches = storage.list_match_histories()
                    if 0 <= idx < len(matches):
                        match_id = matches[idx]["match_id"]
                        view_match(match_id)
                    else:
                        print("Invalid match number!")
                except ValueError:
                    # It's a match ID
                    view_match(match_num)
            elif choice == "3":
                print("\nGoodbye!")
                break
            else:
                print("\nInvalid choice!")


if __name__ == "__main__":
>>>>>>> 904e807 (them avatar)
    main()