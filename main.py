# src/menu.py
from __future__ import annotations
import pygame
import os
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum
from theme_manager import get_theme_manager, ThemeConfig

# Colors (fallback)
WHITE = (240, 240, 240)
BLACK = (30, 30, 30)
GRAY = (90, 90, 90)
LIGHT_GRAY = (180, 180, 180)
ACCENT = (220, 170, 60)
HOVER = (255, 200, 80)
RED = (200, 70, 70)
GREEN = (80, 200, 80)
BLUE = (70, 130, 220)
PURPLE = (150, 80, 200)


class MenuState(Enum):
    MAIN = "main"
    MODE_SELECT = "mode_select"
    SETTINGS = "settings"
    DIFFICULTY = "difficulty"
    BOARD_SIZE = "board_size"
    TIME_SELECT = "time_select"
    THEME_SELECT = "theme_select"
    RULES = "rules"
    CREDITS = "credits"
    CHAR_SELECT = "char_select"   # New: character + name select screen


class NumericInput:
    def __init__(self, center_x, y, width, height, default="20",
                 color=(230,230,230), text_color=(0,0,0), placeholder="seconds"):
        self.rect = pygame.Rect(center_x - width // 2, y, width, height)
        self.bg = color
        self.text_color = text_color
        self.placeholder = placeholder
        self.font = pygame.font.Font(None, 32)

        self.text = str(default)
        self.active = False
        self.cursor_i = len(self.text)
        self._blink = 0

    def handle_event(self, event):
        """Return True if Enter was pressed (i.e., 'confirm')."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_i > 0:
                    self.text = self.text[:self.cursor_i-1] + self.text[self.cursor_i:]
                    self.cursor_i -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor_i < len(self.text):
                    self.text = self.text[:self.cursor_i] + self.text[self.cursor_i+1:]
            elif event.key == pygame.K_LEFT:
                self.cursor_i = max(0, self.cursor_i - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_i = min(len(self.text), self.cursor_i + 1)
            else:
                if event.unicode.isdigit():
                    self.text = self.text[:self.cursor_i] + event.unicode + self.text[self.cursor_i:]
                    self.cursor_i += 1
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, (80,80,80), self.rect, width=2, border_radius=8)

        display = self.text if self.text else self.placeholder
        color = self.text_color if self.text else (120,120,120)
        surf = self.font.render(display, True, color)
        text_x = self.rect.x + 10
        text_y = self.rect.y + (self.rect.height - surf.get_height()) // 2
        surface.blit(surf, (text_x, text_y))

        # caret blink (aligned to text box baseline)
        if self.active:
            self._blink = (self._blink + 1) % 60
            if self._blink < 30:
                cx = text_x + self.font.size(self.text[:self.cursor_i])[0]
                pygame.draw.line(surface, self.text_color, (cx, text_y), (cx, text_y + surf.get_height()), 1)


    def get_value(self, fallback=20):
        try:
            v = int(self.text)
            return max(1, v)  # clamp to at least 1 second
        except Exception:
            return fallback


class TextInput:
    """Simple text input for player names (letters, numbers, spaces)."""
    def __init__(self, center_x, y, width, height, default="", color=(230,230,230), text_color=(0,0,0), placeholder="Name"):
        self.rect = pygame.Rect(center_x - width // 2, y, width, height)
        self.bg = color
        self.text_color = text_color
        self.placeholder = placeholder
        self.font = pygame.font.Font(None, 28)

        self.text = str(default)
        self.active = False
        self.cursor_i = len(self.text)
        self._blink = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_i > 0:
                    self.text = self.text[:self.cursor_i-1] + self.text[self.cursor_i:]
                    self.cursor_i -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor_i < len(self.text):
                    self.text = self.text[:self.cursor_i] + self.text[self.cursor_i+1:]
            elif event.key == pygame.K_LEFT:
                self.cursor_i = max(0, self.cursor_i - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_i = min(len(self.text), self.cursor_i + 1)
            else:
                # Allow most printable chars except control characters
                if event.unicode and event.unicode.isprintable():
                    self.text = self.text[:self.cursor_i] + event.unicode + self.text[self.cursor_i:]
                    self.cursor_i += 1
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, (80,80,80), self.rect, width=2, border_radius=8)

        display = self.text if self.text else self.placeholder
        color = self.text_color if self.text else (120,120,120)
        surf = self.font.render(display, True, color)
        text_x = self.rect.x + 10
        text_y = self.rect.y + (self.rect.height - surf.get_height()) // 2
        surface.blit(surf, (text_x, text_y))

        if self.active:
            self._blink = (self._blink + 1) % 60
            if self._blink < 30:
                cx = text_x + self.font.size(self.text[:self.cursor_i])[0]
                pygame.draw.line(surface, self.text_color, (cx, text_y), (cx, text_y + surf.get_height()), 1)

    def get_value(self, fallback=""):
        return self.text if self.text else fallback


@dataclass
class Button:
    text: str
    x: int
    y: int
    width: int
    height: int
    action: Optional[Callable] = None
    color: Tuple[int, int, int] = ACCENT
    hover_color: Tuple[int, int, int] = HOVER
    text_color: Tuple[int, int, int] = BLACK
    enabled: bool = True

    def is_hovered(self, mouse_pos: Tuple[int, int]) -> bool:
        mx, my = mouse_pos
        return (self.x <= mx <= self.x + self.width and
                self.y <= my <= self.y + self.height)

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, mouse_pos: Tuple[int, int]):
        color = self.hover_color if self.is_hovered(mouse_pos) and self.enabled else self.color
        if not self.enabled:
            color = GRAY

        # Button background with shadow effect
        shadow_offset = 4
        pygame.draw.rect(screen, (50, 50, 50),
                         (self.x + shadow_offset, self.y + shadow_offset, self.width, self.height),
                         border_radius=8)
        pygame.draw.rect(screen, color, (self.x, self.y, self.width, self.height), border_radius=8)
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 2, border_radius=8)

        # Button text
        text_surf = font.render(self.text, True, self.text_color if self.enabled else LIGHT_GRAY)
        text_rect = text_surf.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
        screen.blit(text_surf, text_rect)


class Menu:
    def __init__(self, width: int = 1200, height: int = 700):
        pygame.init()
        # try to set a window icon if exists (non-fatal)
        try:
            icon_image = pygame.image.load(r'assets\images\pieces\pong.ico')
            pygame.display.set_icon(icon_image)
        except Exception:
            pass

        self.W, self.H = width, height
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Gomoku - Menu")
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_title = pygame.font.SysFont("consolas", 72, bold=True)
        self.font_subtitle = pygame.font.SysFont("consolas", 32, bold=True)
        self.font_normal = pygame.font.SysFont("consolas", 24)
        self.font_small = pygame.font.SysFont("consolas", 18)

        # State
        self.state = MenuState.MAIN
        self.running = True
        self.result = None

        # Theme Manager
        self.theme_manager = get_theme_manager()

        #track what's playing
        self._current_music_theme = None

        # Load saved theme preference
        import storage
        prefs = storage.load_preferences()
        theme_name = prefs.get("theme", "default")
        # safe set theme (catch problems)
        try:
            self.theme_manager.set_current_theme(theme_name)
        except Exception:
            # fallback to default if something weird happens
            try:
                self.theme_manager.set_current_theme("default")
            except Exception:
                pass

        # Settings
        self.settings = {
            "board_size": prefs.get("board_size", 13),
            "difficulty": prefs.get("difficulty", "medium"),
            "per_move_seconds": prefs.get("per_move_seconds", 20),
            "mode": None,
            "theme": theme_name,
        }

        # Background
        self.background_image = None
        # protect background loading in case of corrupted path
        try:
            self._load_background()
        except Exception as e:
            print(f"[Menu] _load_background failed: {e}")
            self.background_image = None

        #start music
        try:
            self._update_menu_music()
        except Exception:
            pass

        # Initialize buttons
        self.buttons = {}
        self._init_buttons()

        # Char selection assets (lazy loaded)
        self.characters_dir = os.path.join("assets", "images", "characters")
        self.thumb_dir = os.path.join(self.characters_dir, "thumbs")
        self.large_dir = os.path.join(self.characters_dir, "large")
        self._thumb_surfaces = []   # list of (id, pygame.Surface)
        self._large_surfaces = {}   # id -> Surface
        self._load_character_assets()

        # Character image sizing: reduce preview size so layout fits
        self.CHAR_PREVIEW_W = 360   # smaller so other UI fits
        self.CHAR_PREVIEW_H = 360
        self.CHAR_GAP_BETWEEN = 48   # gap between P1 and P2 preview panels

        self.THUMB_W = 40
        self.THUMB_H = 40
        self.THUMB_GAP = 12
        self.THUMBS_BOX_H = 80

        # char-select state
        self.char_selected_p1 = None
        self.char_selected_p2 = None
        self.name_input_p1: Optional[TextInput] = None
        self.name_input_p2: Optional[TextInput] = None
        self._char_select_confirm_btn: Optional[Button] = None
        self._char_select_back_btn: Optional[Button] = None
        self._char_select_active_player = 1  # 1 => selecting P1, 2 => P2

        # transient click list for thumbs
        self._thumb_click_list: List[Tuple[pygame.Rect, str]] = []

        # preview/toggle rects to support clicks
        self._p1_preview_rect: Optional[pygame.Rect] = None
        self._p2_preview_rect: Optional[pygame.Rect] = None
        self._p1_toggle_rect: Optional[pygame.Rect] = None
        self._p2_toggle_rect: Optional[pygame.Rect] = None

        #exit confirming
        self._confirming_exit = False
        self._exit_yes_btn: Optional[Button] = None
        self._exit_no_btn: Optional[Button] = None

    # ---- helper: contrast text color for buttons ----
    def _contrast_text_for(self, rgb):
        try:
            r, g, b = rgb
            yiq = (r * 299 + g * 587 + b * 114) / 1000
            return (30, 30, 30) if yiq > 150 else (240, 240, 240)
        except Exception:
            return (240, 240, 240)

    def _load_background(self):
        """Load background image for current theme; guarded against missing files."""
        print(f"[Menu] _load_background called for theme: {self.theme_manager.current_theme_name}")
        theme = self.theme_manager.get_current_theme()
        print(f"[Menu]   -> Theme name: {theme.name}")
        print(f"[Menu]   -> Background image: {theme.background_image}")

        self.background_image = None
        try:
            bg = self.theme_manager.load_background(self.theme_manager.current_theme_name, self.W, self.H)
            if bg:
                self.background_image = bg
            else:
                print("[Menu]   -> No background image loaded, using solid color")
        except Exception as e:
            print(f"[Menu] Error loading background: {e}")
            self.background_image = None

    def _set_theme(self, theme_name: str):
        theme = self.theme_manager.get_theme(theme_name)
        if not theme or not getattr(theme, "selectable", True):
            return  # ignore music-only or invalid themes
        try:
            self.theme_manager.set_current_theme(theme_name)
            self.settings["theme"] = theme_name
            self._load_background()
            self._update_menu_music()
            self._init_buttons()
        except Exception as e:
            print(f"[Menu] _set_theme failed: {e}")

    def _get_current_theme(self) -> ThemeConfig:
        """Get current theme config"""
        return self.theme_manager.get_current_theme()

    def _update_menu_music(self):
        """Play the current theme's music on loop (menu only)."""
        if not pygame.mixer.get_init():
            return
        theme = self._get_current_theme()
        music_path = getattr(theme, "music", None)

        # avoid restarting same track
        if self._current_music_theme == self.theme_manager.current_theme_name:
            return

        # stop previous
        try:
            pygame.mixer.music.fadeout(200)
        except Exception:
            pass

        if music_path and os.path.exists(music_path):
            try:
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.play(loops=-1)
                pygame.mixer.music.set_volume(0.6)
                self._current_music_theme = self.theme_manager.current_theme_name
                print(f"[Menu] Now looping music: {music_path}")
            except Exception as e:
                print(f"[Menu] Failed to play '{music_path}': {e}")
                self._current_music_theme = None
        else:
            self._current_music_theme = None
            print("[Menu] No theme music found; staying quiet.")

    def _stop_menu_music(self, fade_ms: int = 250):
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.fadeout(fade_ms)
            except Exception:
                pass
        self._current_music_theme = None

    def _init_buttons(self):
        """Initialize all button layouts for different menu states"""
        btn_width, btn_height = 300, 60
        center_x = self.W // 2 - btn_width // 2
        start_y = 220
        spacing = 75

        theme = self._get_current_theme()
        accent = theme.accent_color
        text_color = theme.text_color

        # Main Menu Buttons
        self.buttons[MenuState.MAIN] = [
            Button("Player vs Player", center_x, start_y, btn_width, btn_height,
                   lambda: self._enter_char_select("pvp"), color=GREEN, hover_color=(120, 255, 120), text_color=BLACK),
            Button("Player vs CPU", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._change_state(MenuState.DIFFICULTY), color=BLUE, hover_color=(100, 170, 255),
                   text_color=BLACK),
            Button("Settings", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._change_state(MenuState.SETTINGS), color=accent, text_color=text_color),
            Button("Rules", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._change_state(MenuState.RULES), color=accent, text_color=text_color),
            Button("Exit", center_x, start_y + spacing * 4, btn_width, btn_height,
                   self._request_exit, color=RED, hover_color=(255, 100, 100), text_color=BLACK),
        ]

        # Difficulty Selection
        self.buttons[MenuState.DIFFICULTY] = [
            Button("Easy", center_x, start_y, btn_width, btn_height,
                   lambda: self._enter_char_select("pvcpu", "easy"), color=GREEN, hover_color=(120, 255, 120), text_color=BLACK),
            Button("Medium", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._enter_char_select("pvcpu", "medium"), color=accent, text_color=text_color),
            Button("Hard", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._enter_char_select("pvcpu", "hard"), color=RED, hover_color=(255, 100, 100), text_color=BLACK),
            Button("Back", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._change_state(MenuState.MAIN), color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK),
        ]

        # Settings Menu
        self.buttons[MenuState.SETTINGS] = [
            Button("Board Size", center_x, start_y, btn_width, btn_height,
                   lambda: self._change_state(MenuState.BOARD_SIZE), color=accent, text_color=text_color),
            Button("Time per Move", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._change_state(MenuState.TIME_SELECT), color=accent, text_color=text_color),
            Button("Theme", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._change_state(MenuState.THEME_SELECT), color=PURPLE, hover_color=(200, 120, 255),
                   text_color=BLACK),
            Button("Credits", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._change_state(MenuState.CREDITS), color=accent, text_color=text_color),
            Button("Back", center_x, start_y + spacing * 4, btn_width, btn_height,
                   lambda: self._change_state(MenuState.MAIN), color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK),
        ]

        # Board Size Selection
        # Added Back button here so user can return to Settings
        self.buttons[MenuState.BOARD_SIZE] = [
            Button("9 x 9", center_x, start_y, btn_width, btn_height,
                   lambda: self._set_board_size(9), color=accent, text_color=text_color),
            Button("13 x 13", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._set_board_size(13), color=accent, text_color=text_color),
            Button("15 x 15", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._set_board_size(15), color=accent, text_color=text_color),
            Button("Back", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._change_state(MenuState.SETTINGS), color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK),
        ]

        # Time Selection
        field_y = start_y
        self.time_input = NumericInput(center_x + btn_width // 2, field_y, btn_width, btn_height,
                               default="20", color=accent, text_color=text_color, placeholder="seconds")

        self.buttons[MenuState.TIME_SELECT] = [
            Button("Confirm", center_x, field_y + int(spacing * 1.5), btn_width, btn_height,
                lambda: self._set_time(self.time_input.get_value()),
                color=accent, text_color=text_color),

            Button("Back", center_x, field_y + spacing * 3, btn_width, btn_height,
                lambda: self._change_state(MenuState.SETTINGS),
                color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK),
        ]

        # Theme Selection  ── FINAL BLOCK ──────────────────────────────────────
        theme_buttons = []
        small_btn_width = 220
        small_btn_height = 55
        themes_per_row = 3
        start_x = self.W // 2 - (themes_per_row * small_btn_width + (themes_per_row - 1) * 20) // 2
        row_y = start_y

        all_themes = self.theme_manager.get_all_themes()

        def _is_pickable_theme(t):
            # must explicitly be selectable (fallback True)
            if not getattr(t, "selectable", True):
                return False
            # must have a background image that actually exists
            bg = getattr(t, "background_image", None)
            return isinstance(bg, str) and os.path.exists(bg)

        # only show REAL UI themes, not music-only packs
        theme_items = [(tid, t) for tid, t in all_themes.items() if _is_pickable_theme(t)]
        theme_items.sort(key=lambda kv: kv[1].name.lower())

        for idx, (theme_id, theme_obj) in enumerate(theme_items):
            col = idx % themes_per_row
            row = idx // themes_per_row
            x = start_x + col * (small_btn_width + 20)
            y = row_y + row * (small_btn_height + 15)

            display_name = theme_obj.name
            if theme_id == self.theme_manager.current_theme_name:
                display_name = f"✓ {display_name}"

            theme_buttons.append(
                Button(
                    display_name, x, y, small_btn_width, small_btn_height,
                    action=(lambda tn=theme_id: self._set_theme_and_back(tn)),
                    color=theme_obj.accent_color,
                    hover_color=tuple(min(c + 40, 255) for c in theme_obj.accent_color),
                    text_color=theme_obj.text_color,
                )
            )

        rows = (len(theme_items) + themes_per_row - 1) // themes_per_row
        theme_buttons.append(
            Button(
                "Back", center_x,
                row_y + rows * (small_btn_height + 15) + 30,
                btn_width, btn_height,
                lambda: self._change_state(MenuState.SETTINGS),
                color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK
            )
        )

        self.buttons[MenuState.THEME_SELECT] = theme_buttons

        self.buttons[MenuState.THEME_SELECT] = theme_buttons

    def _change_state(self, new_state: MenuState):
        self.state = new_state

    # ---- character assets & UI ----
    def _load_character_assets(self):
        """Load up to 20 thumbnails + larger images. Thumbnails: assets/images/characters/thumbs/*.png
           Large images: assets/images/characters/large/<id>.png
           Bot fallback: assets/images/characters/bot.png
        """
        self._thumb_surfaces = []
        self._large_surfaces = {}
        # Ensure dirs exist; if not, no-op (menu still works)
        if not os.path.exists(self.thumb_dir):
            print(f"[Menu] Character thumbs dir not found: {self.thumb_dir}")
            return
        thumbs = sorted([f for f in os.listdir(self.thumb_dir) if f.lower().endswith(('.png','.jpg','.jpeg'))])
        # limit to 20
        thumbs = thumbs[:20]
        for t in thumbs:
            ident = os.path.splitext(t)[0]  # id from filename
            path = os.path.join(self.thumb_dir, t)
            try:
                surf = pygame.image.load(path).convert_alpha()
                self._thumb_surfaces.append((ident, surf))
            except Exception as e:
                print(f"[Menu] Failed loading thumb {path}: {e}")
        # preload large images for those ids (try png and jpg)
        for ident, _ in self._thumb_surfaces:
            large_path_png = os.path.join(self.large_dir, f"{ident}.png")
            large_path_jpg = os.path.join(self.large_dir, f"{ident}.jpg")
            if os.path.exists(large_path_png):
                try:
                    self._large_surfaces[ident] = pygame.image.load(large_path_png).convert_alpha()
                except Exception:
                    pass
            elif os.path.exists(large_path_jpg):
                try:
                    self._large_surfaces[ident] = pygame.image.load(large_path_jpg).convert_alpha()
                except Exception:
                    pass
        # bot fallback (accept png/jpg)
        bot_path_png = os.path.join(self.characters_dir, "bot.png")
        bot_path_jpg = os.path.join(self.characters_dir, "bot.jpg")
        if os.path.exists(bot_path_png):
            try:
                self._large_surfaces["bot"] = pygame.image.load(bot_path_png).convert_alpha()
            except Exception:
                pass
        elif os.path.exists(bot_path_jpg):
            try:
                self._large_surfaces["bot"] = pygame.image.load(bot_path_jpg).convert_alpha()
            except Exception:
                pass

    def _enter_char_select(self, mode: str, difficulty: Optional[str] = None):
        """Open character/name select screen before starting match."""
        self.settings["mode"] = mode
        if difficulty:
            self.settings["difficulty"] = difficulty

        # Initialize selection defaults
        # Pick first available thumb for p1 and p2 (if available)
        self.char_selected_p1 = self._thumb_surfaces[0][0] if self._thumb_surfaces else None
        self.char_selected_p2 = self._thumb_surfaces[1][0] if len(self._thumb_surfaces) > 1 else None

        # For pvcpu, force p2 to 'bot'
        if mode == "pvcpu":
            self.char_selected_p2 = "bot"

        # name inputs - place them aligned with previews
        preview_w = self.CHAR_PREVIEW_W
        preview_h = self.CHAR_PREVIEW_H
        gap_between = self.CHAR_GAP_BETWEEN
        start_x = (self.W - (preview_w * 2 + gap_between)) // 2
        p1_cx = start_x + preview_w // 2
        p2_cx = start_x + preview_w + gap_between + preview_w // 2

        y1 = 120
        w, h = 360, 44
        default_p1_name = "You"
        default_p2_name = "P2" if mode == "pvp" else "CPU"
        # align name inputs with previews centers
        self.name_input_p1 = TextInput(p1_cx, y1, w, h, default=default_p1_name, color=(255,255,255), text_color=(0,0,0), placeholder="Player 1")
        self.name_input_p2 = TextInput(p2_cx, y1, w, h, default=default_p2_name, color=(255,255,255), text_color=(0,0,0), placeholder="Player 2")
        if mode == "pvcpu":
            # keep p2 name default CPU (bot)
            self.name_input_p2.text = default_p2_name

        # confirm/back buttons
        btn_w, btn_h = 220, 56
        self._char_select_confirm_btn = Button("Start Match", self.W // 2 - btn_w//2, self.H - 90, btn_w, btn_h, action=self._confirm_char_select, color=GREEN, hover_color=(120,255,120))
        self._char_select_back_btn = Button("Back", 40, 40, 120, 44, action=lambda: self._change_state(MenuState.MAIN), color=GRAY, hover_color=LIGHT_GRAY)
        self._char_select_active_player = 1
        self._change_state(MenuState.CHAR_SELECT)

    def _confirm_char_select(self):
        # save chosen characters and names into settings then finish
        self.settings["player1_name"] = self.name_input_p1.get_value("Player 1")
        self.settings["player2_name"] = self.name_input_p2.get_value("Player 2")
        self.settings["p1_char"] = self.char_selected_p1
        self.settings["p2_char"] = self.char_selected_p2
        # finalize and close menu
        self.result = self.settings.copy()
        self.running = False

    def _draw_char_select(self):
        """Render the fighting-game-like character select screen."""
        theme = self._get_current_theme()
        # Title
        title = self.font_title.render("Choose Your Fighters", True, theme.text_color)
        self.screen.blit(title, title.get_rect(center=(self.W//2, 40)))

        # compute preview positions dynamically so they always fit
        preview_w = self.CHAR_PREVIEW_W
        preview_h = self.CHAR_PREVIEW_H
        gap_between = self.CHAR_GAP_BETWEEN
        start_x = (self.W - (preview_w * 2 + gap_between)) // 2
        preview_y = 180
        p1_preview_rect = pygame.Rect(start_x, preview_y, preview_w, preview_h)
        p2_preview_rect = pygame.Rect(start_x + preview_w + gap_between, preview_y, preview_w, preview_h)

        # expose preview rects for click handling
        self._p1_preview_rect = p1_preview_rect
        self._p2_preview_rect = p2_preview_rect

        # Draw name inputs and labels (aligned with previews)
        name_y = 100

        # Player labels
        lbl1 = self.font_subtitle.render("Player 1", True, theme.accent_color)
        self.screen.blit(lbl1, (p1_preview_rect.centerx - lbl1.get_width()//2, name_y - 28))
        lbl2 = self.font_subtitle.render("Player 2", True, theme.accent_color)
        self.screen.blit(lbl2, (p2_preview_rect.centerx - lbl2.get_width()//2, name_y - 28))

        # Draw name input boxes
        if self.name_input_p1:
            self.name_input_p1.draw(self.screen)
        if self.name_input_p2:
            self.name_input_p2.draw(self.screen)

        # Optional clickable toggle buttons under name labels to switch active player
        toggle_w, toggle_h = 70, 30
        toggle_y = name_y + 34
        p1_toggle_rect = pygame.Rect(p1_preview_rect.centerx - toggle_w//2, toggle_y, toggle_w, toggle_h)
        p2_toggle_rect = pygame.Rect(p2_preview_rect.centerx - toggle_w//2, toggle_y, toggle_w, toggle_h)
        self._p1_toggle_rect = p1_toggle_rect
        self._p2_toggle_rect = p2_toggle_rect

        # Draw toggles
        p1_color = theme.accent_color if self._char_select_active_player == 1 else (160,160,160)
        p2_color = theme.accent_color if self._char_select_active_player == 2 else (160,160,160)
        pygame.draw.rect(self.screen, p1_color, p1_toggle_rect, border_radius=8)
        pygame.draw.rect(self.screen, p2_color, p2_toggle_rect, border_radius=8)
        p1_lbl = self.font_small.render("P1", True, self._contrast_text_for(p1_color))
        p2_lbl = self.font_small.render("P2", True, self._contrast_text_for(p2_color))
        self.screen.blit(p1_lbl, p1_lbl.get_rect(center=p1_toggle_rect.center))
        self.screen.blit(p2_lbl, p2_lbl.get_rect(center=p2_toggle_rect.center))

        # Draw large previews (left/right). Scale exactly to preview size (reduced).
        # Border color depends on which player is active (highlight)
        # P1 border
        border_color_p1 = theme.accent_color if self._char_select_active_player == 1 else (40, 40, 40)
        border_color_p2 = theme.accent_color if self._char_select_active_player == 2 else (40, 40, 40)

        pygame.draw.rect(self.screen, (20,20,20,60), p1_preview_rect, border_radius=14)
        pygame.draw.rect(self.screen, border_color_p1, p1_preview_rect, width=4, border_radius=14)
        if self.char_selected_p1 and self.char_selected_p1 in self._large_surfaces:
            img = self._large_surfaces[self.char_selected_p1]
            img_s = pygame.transform.smoothscale(img, (preview_w - 8, preview_h - 8))
            self.screen.blit(img_s, img_s.get_rect(center=p1_preview_rect.center))
        else:
            # try to use thumb (scale up to preview size)
            thumb = next((s for ident,s in self._thumb_surfaces if ident == self.char_selected_p1), None)
            if thumb:
                img_s = pygame.transform.smoothscale(thumb, (preview_w - 8, preview_h - 8))
                self.screen.blit(img_s, img_s.get_rect(center=p1_preview_rect.center))
            else:
                txt = self.font_normal.render("No Image", True, theme.text_color)
                self.screen.blit(txt, txt.get_rect(center=p1_preview_rect.center))

        # P2 border
        pygame.draw.rect(self.screen, (20,20,20,60), p2_preview_rect, border_radius=14)
        pygame.draw.rect(self.screen, border_color_p2, p2_preview_rect, width=4, border_radius=14)
        if self.char_selected_p2 and self.char_selected_p2 in self._large_surfaces:
            img = self._large_surfaces[self.char_selected_p2]
            img_s = pygame.transform.smoothscale(img, (preview_w - 8, preview_h - 8))
            self.screen.blit(img_s, img_s.get_rect(center=p2_preview_rect.center))
        else:
            if self.char_selected_p2 == "bot" and "bot" in self._large_surfaces:
                img = self._large_surfaces["bot"]
                img_s = pygame.transform.smoothscale(img, (preview_w - 8, preview_h - 8))
                self.screen.blit(img_s, img_s.get_rect(center=p2_preview_rect.center))
            else:
                thumb = next((s for ident,s in self._thumb_surfaces if ident == self.char_selected_p2), None)
                if thumb:
                    img_s = pygame.transform.smoothscale(thumb, (preview_w - 8, preview_h - 8))
                    self.screen.blit(img_s, img_s.get_rect(center=p2_preview_rect.center))
                else:
                    txt = self.font_normal.render("No Image", True, theme.text_color)
                    self.screen.blit(txt, txt.get_rect(center=p2_preview_rect.center))

        # Thumbnails row near bottom (show up to 20) - use 40x40 thumbnails
        thumbs_box_h = self.THUMBS_BOX_H
        thumbs_y = self.H - thumbs_box_h - 80  # moved up a bit to leave room for Start Match button
        thumbs_x = 80
        gap = self.THUMB_GAP
        thumb_w = self.THUMB_W
        thumb_h = self.THUMB_H

        # Draw background bar
        bar_rect = pygame.Rect(thumbs_x - 20, thumbs_y - 14, self.W - 2*(thumbs_x-20), thumbs_box_h + 28)
        pygame.draw.rect(self.screen, (0,0,0,40), bar_rect, border_radius=12)
        # hint
        hint = self.font_small.render("Click a character to assign to active player. Click preview or P1/P2 to switch active.", True, theme.text_color)
        self.screen.blit(hint, (self.W//2 - hint.get_width()//2, thumbs_y - 34))

        # Render each thumb; scale thumbnails to exactly 40x40
        x = thumbs_x
        y = thumbs_y
        # reset transient click list
        self._thumb_click_list = []
        for ident, surf in self._thumb_surfaces:
            thumb_rect = pygame.Rect(x, y, thumb_w, thumb_h)
            # draw border if selected for either player
            border_col = None
            if ident == self.char_selected_p1:
                border_col = (80, 200, 80)  # green
            if ident == self.char_selected_p2:
                # if both players picked same, show split highlight (use purple)
                border_col = (150, 80, 200) if border_col else (70, 130, 220)
            pygame.draw.rect(self.screen, (30,30,30), thumb_rect, border_radius=8)
            # scale thumb to exact size (leave tiny padding)
            img_s = pygame.transform.smoothscale(surf, (thumb_w - 4, thumb_h - 4))
            self.screen.blit(img_s, img_s.get_rect(center=thumb_rect.center))
            if border_col:
                pygame.draw.rect(self.screen, border_col, thumb_rect, width=3, border_radius=8)
            # store rect for click detection
            self._thumb_click_list.append((thumb_rect.copy(), ident))
            x += thumb_w + gap
            if x + thumb_w > self.W - thumbs_x:
                x = thumbs_x
                y += thumb_h + gap

        # Draw active-player indicator
        active_txt = f"Active: {'P1' if self._char_select_active_player == 1 else 'P2'}"
        at = self.font_small.render(active_txt, True, theme.accent_color)
        self.screen.blit(at, (self.W//2 - at.get_width()//2, thumbs_y + thumbs_box_h + 6))

        # Draw confirm/back buttons
        mouse_pos = pygame.mouse.get_pos()
        if self._char_select_confirm_btn:
            self._char_select_confirm_btn.draw(self.screen, self.font_normal, mouse_pos)
        if self._char_select_back_btn:
            self._char_select_back_btn.draw(self.screen, self.font_normal, mouse_pos)

    # ---- overrides for menu escape/exit
    def _request_exit(self):
        """Open the confirmation modal instead of quitting instantly."""
        self._confirming_exit = True
        self._build_exit_buttons()

    def _cancel_exit(self):
        """Close the confirmation modal (do not quit)."""
        self._confirming_exit = False
        self._exit_yes_btn = None
        self._exit_no_btn = None

    def _confirm_exit(self):
        """Actually quit."""
        self._stop_menu_music()
        self.running = False
        self.result = None

    def _build_exit_buttons(self):
        """Create Yes/No buttons for the modal, sized/placed centrally."""
        btn_w, btn_h, spacing = 160, 56, 30
        cx, cy = self.W // 2, self.H // 2 + 40
        self._exit_yes_btn = Button(
            "Yes", cx - btn_w - spacing // 2, cy, btn_w, btn_h,
            action=self._confirm_exit, color=RED, hover_color=(255, 120, 120), text_color=BLACK
        )
        self._exit_no_btn = Button(
            "No", cx + spacing // 2, cy, btn_w, btn_h,
            action=self._cancel_exit, color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK
        )

    def _draw_exit_modal(self, mouse_pos):
        """Dim the scene and draw the themed confirmation box."""
        theme = self._get_current_theme()

        # darken background
        dim = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        self.screen.blit(dim, (0, 0))

        # modal rect (uses board color)
        box_w, box_h = 560, 260
        box_x = (self.W - box_w) // 2
        box_y = (self.H - box_h) // 2
        box = pygame.Rect(box_x, box_y, box_w, box_h)

        # board-like panel
        pygame.draw.rect(self.screen, theme.board_color, box, border_radius=14)
        pygame.draw.rect(self.screen, theme.accent_color, box, width=3, border_radius=14)

        # text
        title = self.font_subtitle.render("Exit Game?", True, theme.text_color)
        title_rect = title.get_rect(center=(self.W // 2, box_y + 60))
        self.screen.blit(title, title_rect)

        msg = self.font_normal.render("Are you sure you want to quit?", True, theme.text_color)
        msg_rect = msg.get_rect(center=(self.W // 2, box_y + 110))
        self.screen.blit(msg, msg_rect)

        # draw buttons
        if self._exit_yes_btn and self._exit_no_btn:
            self._exit_yes_btn.draw(self.screen, self.font_normal, mouse_pos)
            self._exit_no_btn.draw(self.screen, self.font_normal, mouse_pos)

    def _exit(self):
        # old behavior quit immediately; now we ask first
        self._request_exit()

    def _handle_escape(self):
        # If modal is open, ESC cancels it
        if self._confirming_exit:
            self._cancel_exit()
            return

        if self.state == MenuState.MAIN:
            self._request_exit()
        elif self.state == MenuState.DIFFICULTY:
            self._change_state(MenuState.MAIN)
        elif self.state in [MenuState.SETTINGS, MenuState.RULES]:
            self._change_state(MenuState.MAIN)
        elif self.state in [MenuState.BOARD_SIZE, MenuState.TIME_SELECT, MenuState.THEME_SELECT]:
            self._change_state(MenuState.SETTINGS)
        elif self.state == MenuState.CREDITS:
            self._change_state(MenuState.SETTINGS)
        elif self.state == MenuState.CHAR_SELECT:
            # back to main menu
            self._change_state(MenuState.MAIN)
        else:
            self._change_state(MenuState.MAIN)

    def _draw_background(self):
        theme = self._get_current_theme()
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        else:
            self.screen.fill(theme.background_color)

    def _draw_title(self, y_offset: int = 80):
        theme = self._get_current_theme()
        title = self.font_title.render("GOMOKU", True, theme.accent_color)
        title_rect = title.get_rect(center=(self.W // 2, y_offset))

        shadow = self.font_title.render("GOMOKU", True, (100, 100, 100))
        shadow_rect = shadow.get_rect(center=(self.W // 2 + 3, y_offset + 3))
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(title, title_rect)

        pygame.draw.line(self.screen, theme.accent_color,
                         (self.W // 2 - 250, y_offset + 60),
                         (self.W // 2 + 250, y_offset + 60), 4)

    def _draw_subtitle(self, text: str, y: int = 170):
        theme = self._get_current_theme()
        subtitle = self.font_subtitle.render(text, True, theme.text_color)
        subtitle_rect = subtitle.get_rect(center=(self.W // 2, y))
        self.screen.blit(subtitle, subtitle_rect)

    def _draw_info_text(self, lines: List[str], start_y: int = 250):
        theme = self._get_current_theme()
        for i, line in enumerate(lines):
            text = self.font_normal.render(line, True, theme.text_color)
            text_rect = text.get_rect(center=(self.W // 2, start_y + i * 35))
            self.screen.blit(text, text_rect)

    def _draw_current_settings(self):
        theme = self._get_current_theme()
        box_height = 50
        box_y = 150

        box_surface = pygame.Surface((self.W - 100, box_height))
        box_surface.set_alpha(230)
        box_surface.fill((250, 250, 250) if theme.background_color[0] > 128 else (50, 50, 55))
        self.screen.blit(box_surface, (50, box_y))

        pygame.draw.rect(self.screen, theme.accent_color,
                         (50, box_y, self.W - 100, box_height), 2, border_radius=10)

        settings_text = [
            f"Board: {self.settings['board_size']}×{self.settings['board_size']}",
            f"Time: {self.settings['per_move_seconds']}s/move",
            f"Theme: {theme.name}"
        ]

        section_width = (self.W - 100) / 3
        for i, text in enumerate(settings_text):
            surf = self.font_small.render(text, True, theme.text_color)
            x = 50 + section_width * i + section_width / 2
            rect = surf.get_rect(center=(x, box_y + box_height / 2))
            self.screen.blit(surf, rect)

    def _draw_footer(self):
        footer_text = "Press ESC to go back"
        if self.state == MenuState.MAIN:
            footer_text = "Press ESC to exit"

        surf = self.font_small.render(footer_text, True, GRAY)
        rect = surf.get_rect(center=(self.W // 2, self.H - 25))
        self.screen.blit(surf, rect)

    def _draw_rules(self):
        theme = self._get_current_theme()
        self._draw_subtitle("Game Rules", 100)

        rules = [
            "• Connect 5 pieces in a row to win (horizontal, vertical, or diagonal)",
            "• Each player gets limited time per move",
            "• Earn 1 skill point for every 5 stones placed",
            "",
            "Skill Abilities:",
            "  [B] Place a blocking tile (expires after 5 turns)",
            "  [U] Undo opponent's last move",
            "",
            "Controls:",
            "  [Left Click] Place stone",
            "  [B] Toggle block mode",
            "  [U] Undo opponent move (costs 1 skill point)",
            "  [R] Restart game",
            "  [ESC] Back to menu",
        ]

        y = 160
        for rule in rules:
            if rule.startswith("•") or rule.startswith("  ["):
                color = theme.accent_color
            else:
                color = theme.text_color
            font = self.font_normal if rule.startswith("•") else self.font_small
            text = font.render(rule, True, color)
            self.screen.blit(text, (100, y))
            y += 30 if rule else 15

        back_btn = Button("Back to Menu", self.W // 2 - 150, self.H - 90, 300, 50,
                          lambda: self._change_state(MenuState.MAIN),
                          color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK)
        back_btn.draw(self.screen, self.font_normal, pygame.mouse.get_pos())

        mouse_pressed = pygame.mouse.get_pressed()[0]
        if hasattr(self, '_last_mouse_pressed'):
            if mouse_pressed and not self._last_mouse_pressed:
                if back_btn.is_hovered(pygame.mouse.get_pos()) and back_btn.action:
                    back_btn.action()
        self._last_mouse_pressed = mouse_pressed

    def run(self) -> Optional[dict]:
        self._last_mouse_pressed = False

        while self.running:
            dt = self.clock.tick(60) / 1000.0
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._request_exit()

                elif event.type == pygame.KEYDOWN and self._confirming_exit:
                    if event.key in (pygame.K_RETURN, pygame.K_y):
                        self._confirm_exit()
                    elif event.key in (pygame.K_ESCAPE, pygame.K_n):
                        self._cancel_exit()
                    continue  # don't propagate to normal handlers when modal is up

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._handle_escape()

                    # TIME_SELECT: typing + Enter go to the numeric field
                    if (not self._confirming_exit) and self.state == MenuState.TIME_SELECT and hasattr(self, 'time_input'):
                        if self.time_input.handle_event(event):
                            # Enter pressed -> confirm
                            self._set_time(self.time_input.get_value())

                    # Character select quick keys
                    if self.state == MenuState.CHAR_SELECT:
                        if event.key == pygame.K_1:
                            self._char_select_active_player = 1
                        elif event.key == pygame.K_2:
                            self._char_select_active_player = 2
                        # Name input handling
                        if self.name_input_p1 and self.name_input_p1.handle_event(event):
                            pass
                        if self.name_input_p2 and self.name_input_p2.handle_event(event):
                            pass

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._confirming_exit:
                        # modal consumes the click
                        if self._exit_yes_btn and self._exit_yes_btn.is_hovered(mouse_pos):
                            self._exit_yes_btn.action()  # type: ignore
                        elif self._exit_no_btn and self._exit_no_btn.is_hovered(mouse_pos):
                            self._exit_no_btn.action()  # type: ignore
                    else:
                        # TIME_SELECT: click to focus the numeric field
                        if self.state == MenuState.TIME_SELECT and hasattr(self, 'time_input'):
                            self.time_input.handle_event(event)

                        # normal buttons
                        if self.state in self.buttons:
                            for button in self.buttons[self.state]:
                                if button.is_hovered(mouse_pos) and button.enabled and button.action:
                                    button.action()

                        # CHAR_SELECT interactions
                        if self.state == MenuState.CHAR_SELECT:
                            # 1) preview clicks / toggle clicks to switch active player
                            handled = False
                            if self._p1_preview_rect and self._p1_preview_rect.collidepoint(mouse_pos):
                                self._char_select_active_player = 1
                                handled = True
                            elif self._p2_preview_rect and self._p2_preview_rect.collidepoint(mouse_pos):
                                self._char_select_active_player = 2
                                handled = True

                            if not handled and self._p1_toggle_rect and self._p1_toggle_rect.collidepoint(mouse_pos):
                                self._char_select_active_player = 1
                                handled = True
                            if not handled and self._p2_toggle_rect and self._p2_toggle_rect.collidepoint(mouse_pos):
                                self._char_select_active_player = 2
                                handled = True

                            if handled:
                                # consume click so we don't also pick a thumbnail underneath
                                continue

                            # 2) thumbnail clicks -> assign to active player (respect pvcpu bot behavior)
                            if hasattr(self, "_thumb_click_list"):
                                for rect, ident in self._thumb_click_list:
                                    if rect.collidepoint(mouse_pos):
                                        if self.settings.get("mode") == "pvcpu" and self._char_select_active_player == 2:
                                            # p2 is bot; ignore selection for P2
                                            pass
                                        else:
                                            if self._char_select_active_player == 1:
                                                self.char_selected_p1 = ident
                                            else:
                                                self.char_selected_p2 = ident
                                        break

                            # 3) name inputs focus (click into them)
                            if self.name_input_p1:
                                self.name_input_p1.handle_event(event)
                            if self.name_input_p2:
                                self.name_input_p2.handle_event(event)

                            # 4) confirm/back btn clicks
                            if self._char_select_confirm_btn and self._char_select_confirm_btn.is_hovered(mouse_pos):
                                if self._char_select_confirm_btn.action:
                                    self._char_select_confirm_btn.action()
                            if self._char_select_back_btn and self._char_select_back_btn.is_hovered(mouse_pos):
                                if self._char_select_back_btn.action:
                                    self._char_select_back_btn.action()

            self._draw_background()

            if self.state == MenuState.RULES:
                self._draw_rules()
                self._draw_footer()
            elif self.state == MenuState.CREDITS:
                self._draw_credits()
                self._draw_footer()
            elif self.state == MenuState.CHAR_SELECT:
                # draw the character select screen
                self._draw_char_select()
                self._draw_footer()
            else:
                self._draw_title()
                self._draw_current_settings()
                # TIME_SELECT: draw the numeric input box
                if self.state == MenuState.TIME_SELECT and hasattr(self, 'time_input'):
                    self.time_input.draw(self.screen)

                if self.state in self.buttons:
                    for button in self.buttons[self.state]:
                        button.draw(self.screen, self.font_normal, mouse_pos)
                self._draw_footer()

            if self._confirming_exit:
                self._draw_exit_modal(mouse_pos)

            pygame.display.flip()

        return self.result


def show_menu() -> Optional[dict]:
    menu = Menu()
    return menu.run()