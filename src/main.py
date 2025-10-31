# src/main_with_menu.py
from models import Player
from engine import Engine
from ui import UI
from ui_cpu import UICPU
from menu import show_menu
import storage


def main():
    # Load saved preferences
    preferences = storage.load_preferences()

    while True:
        # Show menu and get user choices
        settings = show_menu()

        # User exited menu
        if settings is None:
            break

        # Save preferences for next time
        storage.save_preferences(settings)

        # Load rules from storage
        rules = storage.load_rules()
        per_move_seconds = settings.get("per_move_seconds", 20)
        board_size = settings.get("board_size", 13)
        mode = settings.get("mode")

        # Create players
        p1 = Player(pid="p1", full_name="Player 1", nickname="You", gender="M", piece='X')

        if mode == "pvp":
            p2 = Player(pid="p2", full_name="Player 2", nickname="P2", gender="N", piece='O')
            engine = Engine(p1, p2, board_size=board_size, per_move_seconds=per_move_seconds)
            ui = UI(engine)
            ui.run()

        elif mode == "pvcpu":
            p2 = Player(pid="p2", full_name="CPU", nickname="CPU", gender="N", piece='O')
            difficulty = settings.get("difficulty", "medium")
            engine = Engine(p1, p2, board_size=board_size, per_move_seconds=per_move_seconds)
            ui = UICPU(engine, cpu_difficulty=difficulty)
            ui.run()

if __name__ == "__main__":
    main()