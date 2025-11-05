# src/theme_manager.py
"""
Theme Manager - Quản lý themes đồng bộ cho cả menu và in-game
Tự động load backgrounds từ assets/backgrounds/ theo tên theme
"""
from __future__ import annotations
import os
import json
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import pygame

THEMES_CONFIG_PATH = "data/themes_config.json"
BACKGROUNDS_DIR = "assets/backgrounds"
MUSIC_DIR = "assets/music"



@dataclass
class ThemeConfig:
    name: str
    background_color: Tuple[int, int, int]
    background_image: Optional[str] = None
    accent_color: Tuple[int, int, int] = (220, 170, 60)
    text_color: Tuple[int, int, int] = (30, 30, 30)
    board_color: Tuple[int, int, int] = (240, 200, 140)
    grid_color: Tuple[int, int, int] = (90, 90, 90)
    piece_x_color: Tuple[int, int, int] = (30, 30, 30)
    piece_o_color: Tuple[int, int, int] = (220, 170, 60)
    music: Optional[str] = None
    selectable: bool = True


# Built-in themes with game-compatible colors
DEFAULT_THEMES = {
    "default": ThemeConfig(
        name="Default",
        background_color=(240, 240, 240),
        background_image=None,
        accent_color=(220, 170, 60),
        text_color=(30, 30, 30),
        board_color=(240, 200, 140),
        grid_color=(90, 90, 90),
        piece_x_color=(30, 30, 30),
        piece_o_color=(220, 170, 60)
    ),
    "dark": ThemeConfig(
        name="Dark Mode",
        background_color=(30, 30, 35),
        background_image=None,
        accent_color=(255, 200, 100),
        text_color=(240, 240, 245),
        board_color=(50, 50, 60),
        grid_color=(120, 120, 130),
        piece_x_color=(240, 240, 245),
        piece_o_color=(255, 200, 100)
    ),
    "light": ThemeConfig(
        name="Light Mode",
        background_color=(250, 250, 255),
        background_image=None,
        accent_color=(100, 150, 255),
        text_color=(20, 20, 30),
        board_color=(245, 245, 250),
        grid_color=(180, 180, 200),
        piece_x_color=(50, 50, 70),
        piece_o_color=(100, 150, 255)
    ),
    "ocean": ThemeConfig(
        name="Ocean",
        background_color=(230, 240, 250),
        background_image=None,
        accent_color=(70, 130, 220),
        text_color=(20, 50, 80),
        board_color=(200, 230, 250),
        grid_color=(100, 150, 200),
        piece_x_color=(20, 60, 100),
        piece_o_color=(70, 130, 220)
    ),
    "forest": ThemeConfig(
        name="Forest",
        background_color=(240, 250, 240),
        background_image=None,
        accent_color=(80, 160, 80),
        text_color=(30, 60, 30),
        board_color=(220, 240, 220),
        grid_color=(100, 150, 100),
        piece_x_color=(40, 80, 40),
        piece_o_color=(80, 160, 80)
    ),
    "sunset": ThemeConfig(
        name="Sunset",
        background_color=(255, 240, 230),
        background_image=None,
        accent_color=(255, 150, 80),
        text_color=(80, 40, 20),
        board_color=(255, 230, 200),
        grid_color=(200, 150, 100),
        piece_x_color=(120, 60, 30),
        piece_o_color=(255, 150, 80)
    ),
    "midnight": ThemeConfig(
        name="Midnight",
        background_color=(25, 25, 40),
        background_image=None,
        accent_color=(150, 150, 255),
        text_color=(220, 220, 255),
        board_color=(40, 40, 60),
        grid_color=(100, 100, 150),
        piece_x_color=(200, 200, 255),
        piece_o_color=(150, 150, 255)
    ),
}


class ThemeManager:
    def __init__(self):
        self.themes: Dict[str, ThemeConfig] = {}
        # Copy default themes first
        for key, theme in DEFAULT_THEMES.items():
            self.themes[key] = ThemeConfig(
                name=theme.name,
                background_color=theme.background_color,
                background_image=theme.background_image,
                accent_color=theme.accent_color,
                text_color=theme.text_color,
                board_color=theme.board_color,
                grid_color=theme.grid_color,
                piece_x_color=theme.piece_x_color,
                piece_o_color=theme.piece_o_color
            )

        self._scan_backgrounds()
        self._scan_music()
        self._load_custom_themes()
        self.current_theme_name = "default"
        self._background_cache: Dict[str, pygame.Surface] = {}

        print(f"[ThemeManager] Initialized with {len(self.themes)} themes")
        for theme_name, theme in self.themes.items():
            bg_status = f"with background: {theme.background_image}" if theme.background_image else "no background"
            print(f"  - {theme_name}: {theme.name} ({bg_status})")

    def _scan_backgrounds(self):
        """
        Scan backgrounds directory and auto-assign to themes with matching names
        """
        print(f"[ThemeManager] Scanning backgrounds directory: {BACKGROUNDS_DIR}")

        if not os.path.exists(BACKGROUNDS_DIR):
            print(f"[ThemeManager] Creating backgrounds directory: {BACKGROUNDS_DIR}")
            os.makedirs(BACKGROUNDS_DIR, exist_ok=True)
            return

        # Get absolute path for debugging
        abs_path = os.path.abspath(BACKGROUNDS_DIR)
        print(f"[ThemeManager] Absolute path: {abs_path}")

        files = os.listdir(BACKGROUNDS_DIR)
        print(f"[ThemeManager] Found {len(files)} files in directory")

        for filename in files:
            print(f"[ThemeManager] Checking file: {filename}")

            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                # Extract theme name from filename (without extension)
                theme_name = os.path.splitext(filename)[0].lower()
                bg_path = os.path.join(BACKGROUNDS_DIR, filename)
                abs_bg_path = os.path.abspath(bg_path)

                print(f"[ThemeManager] Found background image: {filename}")
                print(f"[ThemeManager]   -> Theme name: {theme_name}")
                print(f"[ThemeManager]   -> Path: {abs_bg_path}")
                print(f"[ThemeManager]   -> File exists: {os.path.exists(abs_bg_path)}")

                if theme_name in self.themes:
                    # Update existing theme with background
                    print(f"[ThemeManager]   -> Updating existing theme '{theme_name}'")
                    self.themes[theme_name].background_image = bg_path
                else:
                    # Create new theme for this background
                    print(f"[ThemeManager]   -> Creating new theme '{theme_name}'")
                    display_name = theme_name.replace('_', ' ').title()
                    self.themes[theme_name] = ThemeConfig(
                        name=display_name,
                        background_color=(240, 240, 240),
                        background_image=bg_path,
                        accent_color=(220, 170, 60),
                        text_color=(30, 30, 30),
                        board_color=(240, 200, 140),
                        grid_color=(90, 90, 90),
                        piece_x_color=(30, 30, 30),
                        piece_o_color=(220, 170, 60)
                    )
            else:
                print(f"[ThemeManager]   -> Skipping (not an image): {filename}")

    def _scan_music(self):
        print(f"[ThemeManager] Scanning music directory: {MUSIC_DIR}")
        if not os.path.exists(MUSIC_DIR):
            os.makedirs(MUSIC_DIR, exist_ok=True)
            return

        for filename in os.listdir(MUSIC_DIR):
            if not filename.lower().endswith(('.ogg', '.mp3', '.flac', '.wav')):
                continue
            theme_id = os.path.splitext(filename)[0].lower()
            path = os.path.join(MUSIC_DIR, filename)
            if theme_id in self.themes:
                self.themes[theme_id].music = path
            else:
                # create a minimal theme if a song exists for a not-yet-defined theme
                display = theme_id.replace('_',' ').title()
                self.themes[theme_id] = ThemeConfig(
                    name=display,
                    background_color=(240,240,240),
                    music=path
                )
        
        if theme_id in self.themes:
            self.themes[theme_id].music = path
        else:
            display = theme_id.replace('_',' ').title()
            self.themes[theme_id] = ThemeConfig(
                name=display,
                background_color=(240,240,240),
                music=path,
                selectable=False   # <— this blocks it from the Theme menu
            )

    def _load_custom_themes(self):
        """Load custom theme configurations from JSON"""
        if os.path.exists(THEMES_CONFIG_PATH):
            try:
                print(f"[ThemeManager] Loading custom themes from: {THEMES_CONFIG_PATH}")
                with open(THEMES_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for theme_id, theme_data in data.items():
                        existing = self.themes.get(theme_id)

                        # prefer an already-discovered background (e.g., from _scan_backgrounds)
                        bg_path = theme_data.get("background_image",
                                                existing.background_image if existing else None)

                        # preserve music + selectable unless JSON explicitly sets them
                        music = theme_data.get("music", existing.music if existing else None)
                        selectable = theme_data.get("selectable",
                                                    existing.selectable if existing else True)

                        self.themes[theme_id] = ThemeConfig(
                            name=theme_data.get("name", existing.name if existing else theme_id),
                            background_color=tuple(theme_data.get("background_color",
                                                                existing.background_color if existing else (240,240,240))),
                            background_image=bg_path,
                            accent_color=tuple(theme_data.get("accent_color",
                                                            existing.accent_color if existing else (220,170,60))),
                            text_color=tuple(theme_data.get("text_color",
                                                            existing.text_color if existing else (30,30,30))),
                            board_color=tuple(theme_data.get("board_color",
                                                            existing.board_color if existing else (240,200,140))),
                            grid_color=tuple(theme_data.get("grid_color",
                                                            existing.grid_color if existing else (90,90,90))),
                            piece_x_color=tuple(theme_data.get("piece_x_color",
                                                            existing.piece_x_color if existing else (30,30,30))),
                            piece_o_color=tuple(theme_data.get("piece_o_color",
                                                            existing.piece_o_color if existing else (220,170,60))),
                            music=music,
                            selectable=selectable
                        )
                print(f"[ThemeManager] Loaded {len(data)} custom themes")
            except Exception as e:
                print(f"[ThemeManager] Error loading custom themes: {e}")


    def save_custom_theme(self, theme_id: str, theme: ThemeConfig):
        """Save a custom theme to config"""
        self.themes[theme_id] = theme

        # Save to file
        os.makedirs(os.path.dirname(THEMES_CONFIG_PATH), exist_ok=True)

        custom_themes = {}
        for tid, t in self.themes.items():
            if tid not in DEFAULT_THEMES or t.background_image:
                custom_themes[tid] = {
                    "name": t.name,
                    "background_color": list(t.background_color),
                    "background_image": t.background_image,
                    "accent_color": list(t.accent_color),
                    "text_color": list(t.text_color),
                    "board_color": list(t.board_color),
                    "grid_color": list(t.grid_color),
                    "piece_x_color": list(t.piece_x_color),
                    "piece_o_color": list(t.piece_o_color)
                }

        with open(THEMES_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(custom_themes, f, indent=2)

    def get_theme(self, theme_id: str) -> Optional[ThemeConfig]:
        """Get theme by ID"""
        return self.themes.get(theme_id)

    def get_all_themes(self) -> Dict[str, ThemeConfig]:
        """Get all available themes"""
        return self.themes.copy()

    def set_current_theme(self, theme_id: str):
        """Set current active theme"""
        if theme_id in self.themes:
            self.current_theme_name = theme_id
            print(f"[ThemeManager] Set current theme to: {theme_id}")
            theme = self.themes[theme_id]
            print(f"[ThemeManager]   -> Background: {theme.background_image}")
        else:
            print(f"[ThemeManager] Warning: Theme '{theme_id}' not found!")

    def get_current_theme(self) -> ThemeConfig:
        """Get currently active theme"""
        return self.themes.get(self.current_theme_name, DEFAULT_THEMES["default"])

    def load_background(self, theme_id: str, width: int, height: int) -> Optional[pygame.Surface]:
        """Load and cache background image for a theme"""
        theme = self.themes.get(theme_id)
        if not theme:
            print(f"[ThemeManager] load_background: Theme '{theme_id}' not found")
            return None

        if not theme.background_image:
            print(f"[ThemeManager] load_background: Theme '{theme_id}' has no background image")
            return None

        # Check cache
        cache_key = f"{theme_id}_{width}_{height}"
        if cache_key in self._background_cache:
            print(f"[ThemeManager] load_background: Using cached background for '{theme_id}'")
            return self._background_cache[cache_key]

        # Load and scale
        print(f"[ThemeManager] load_background: Loading background for '{theme_id}'")
        print(f"[ThemeManager]   -> Path: {theme.background_image}")
        print(f"[ThemeManager]   -> Target size: {width}x{height}")

        try:
            if os.path.exists(theme.background_image):
                print(f"[ThemeManager]   -> File exists, loading...")
                bg = pygame.image.load(theme.background_image).convert()
                print(f"[ThemeManager]   -> Original size: {bg.get_width()}x{bg.get_height()}")
                bg = pygame.transform.scale(bg, (width, height))
                print(f"[ThemeManager]   -> Scaled to: {bg.get_width()}x{bg.get_height()}")
                self._background_cache[cache_key] = bg
                print(f"[ThemeManager]   -> Cached successfully")
                return bg
            else:
                print(f"[ThemeManager]   -> ERROR: File does not exist!")
                print(f"[ThemeManager]   -> Absolute path: {os.path.abspath(theme.background_image)}")
        except Exception as e:
            print(f"[ThemeManager]   -> ERROR loading background: {e}")
            import traceback
            traceback.print_exc()

        return None

    def clear_cache(self):
        """Clear background image cache"""
        print(f"[ThemeManager] Clearing {len(self._background_cache)} cached backgrounds")
        self._background_cache.clear()


# Singleton instance
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager