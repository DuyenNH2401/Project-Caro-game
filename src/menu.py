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
    def __init__(self, width: int = 900, height: int = 700):
        pygame.init()
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

        # Load saved theme preference
        import storage
        prefs = storage.load_preferences()
        theme_name = prefs.get("theme", "default")
        self.theme_manager.set_current_theme(theme_name)

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
        self._load_background()

        # Initialize buttons
        self.buttons = {}
        self._init_buttons()

    def _load_background(self):
        """Load background image for current theme"""
        print(f"[Menu] _load_background called for theme: {self.theme_manager.current_theme_name}")
        theme = self.theme_manager.get_current_theme()
        print(f"[Menu]   -> Theme name: {theme.name}")
        print(f"[Menu]   -> Background image: {theme.background_image}")

        self.background_image = self.theme_manager.load_background(
            self.theme_manager.current_theme_name,
            self.W,
            self.H
        )

        if self.background_image:
            print(
                f"[Menu]   -> Background loaded successfully: {self.background_image.get_width()}x{self.background_image.get_height()}")
        else:
            print(f"[Menu]   -> No background image loaded, using solid color: {theme.background_color}")

    def _set_theme(self, theme_name: str):
        """Change the current theme"""
        self.theme_manager.set_current_theme(theme_name)
        self.settings["theme"] = theme_name
        self._load_background()
        self._init_buttons()

    def _get_current_theme(self) -> ThemeConfig:
        """Get current theme config"""
        return self.theme_manager.get_current_theme()

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
                   lambda: self._set_mode("pvp"), color=GREEN, hover_color=(120, 255, 120), text_color=BLACK),
            Button("Player vs CPU", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._change_state(MenuState.DIFFICULTY), color=BLUE, hover_color=(100, 170, 255),
                   text_color=BLACK),
            Button("Settings", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._change_state(MenuState.SETTINGS), color=accent, text_color=text_color),
            Button("Rules", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._change_state(MenuState.RULES), color=accent, text_color=text_color),
            Button("Exit", center_x, start_y + spacing * 4, btn_width, btn_height,
                   self._exit, color=RED, hover_color=(255, 100, 100), text_color=BLACK),
        ]

        # Difficulty Selection
        self.buttons[MenuState.DIFFICULTY] = [
            Button("Easy", center_x, start_y, btn_width, btn_height,
                   lambda: self._set_difficulty("easy"), color=GREEN, hover_color=(120, 255, 120), text_color=BLACK),
            Button("Medium", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._set_difficulty("medium"), color=accent, text_color=text_color),
            Button("Hard", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._set_difficulty("hard"), color=RED, hover_color=(255, 100, 100), text_color=BLACK),
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
        self.buttons[MenuState.BOARD_SIZE] = [
            Button("9 x 9", center_x, start_y, btn_width, btn_height,
                   lambda: self._set_board_size(9), color=accent, text_color=text_color),
            Button("13 x 13", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._set_board_size(13), color=accent, text_color=text_color),
            Button("15 x 15", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._set_board_size(15), color=accent, text_color=text_color),
            Button("19 x 19", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._set_board_size(19), color=accent, text_color=text_color),
            Button("Back", center_x, start_y + spacing * 4, btn_width, btn_height,
                   lambda: self._change_state(MenuState.SETTINGS), color=GRAY, hover_color=LIGHT_GRAY,
                   text_color=BLACK),
        ]

        # Time Selection
        self.buttons[MenuState.TIME_SELECT] = [
            Button("10 seconds", center_x, start_y, btn_width, btn_height,
                   lambda: self._set_time(10), color=accent, text_color=text_color),
            Button("15 seconds", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._set_time(15), color=accent, text_color=text_color),
            Button("20 seconds", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._set_time(20), color=accent, text_color=text_color),
            Button("30 seconds", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._set_time(30), color=accent, text_color=text_color),
            Button("45 seconds", center_x, start_y + spacing * 4, btn_width, btn_height,
                   lambda: self._set_time(45), color=accent, text_color=text_color),
            Button("60 seconds", center_x, start_y + spacing * 5, btn_width, btn_height,
                   lambda: self._set_time(60), color=accent, text_color=text_color),
            Button("Back", center_x, start_y + spacing * 6 + 20, btn_width, btn_height,
                   lambda: self._change_state(MenuState.SETTINGS), color=GRAY, hover_color=LIGHT_GRAY,
                   text_color=BLACK),
        ]

        # Theme Selection
        theme_buttons = []
        small_btn_width = 220
        small_btn_height = 55
        themes_per_row = 3
        start_x = self.W // 2 - (themes_per_row * small_btn_width + (themes_per_row - 1) * 20) // 2
        row_y = start_y

        all_themes = self.theme_manager.get_all_themes()
        theme_list = list(all_themes.keys())

        for idx, theme_name in enumerate(theme_list):
            theme_obj = all_themes[theme_name]
            col = idx % themes_per_row
            row = idx // themes_per_row

            x = start_x + col * (small_btn_width + 20)
            y = row_y + row * (small_btn_height + 15)

            # Show indicator if this is current theme
            display_name = theme_obj.name
            if theme_name == self.theme_manager.current_theme_name:
                display_name = f"✓ {display_name}"

            btn = Button(display_name, x, y, small_btn_width, small_btn_height,
                         lambda tn=theme_name: self._set_theme_and_back(tn),
                         color=theme_obj.accent_color,
                         hover_color=tuple(min(c + 40, 255) for c in theme_obj.accent_color),
                         text_color=theme_obj.text_color)
            theme_buttons.append(btn)

        # Add back button
        theme_buttons.append(
            Button("Back", center_x,
                   row_y + ((len(theme_list) - 1) // themes_per_row + 1) * (small_btn_height + 15) + 30,
                   btn_width, btn_height,
                   lambda: self._change_state(MenuState.SETTINGS),
                   color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK)
        )

        self.buttons[MenuState.THEME_SELECT] = theme_buttons

    def _change_state(self, new_state: MenuState):
        self.state = new_state

    def _set_mode(self, mode: str):
        self.settings["mode"] = mode
        self.result = self.settings.copy()
        self.running = False

    def _set_difficulty(self, difficulty: str):
        self.settings["difficulty"] = difficulty
        self.settings["mode"] = "pvcpu"
        self.result = self.settings.copy()
        self.running = False

    def _set_board_size(self, size: int):
        self.settings["board_size"] = size
        self._change_state(MenuState.SETTINGS)

    def _set_time(self, seconds: int):
        self.settings["per_move_seconds"] = seconds
        self._change_state(MenuState.SETTINGS)

    def _set_theme_and_back(self, theme_name: str):
        self._set_theme(theme_name)
        self._change_state(MenuState.SETTINGS)

    def _exit(self):
        self.running = False
        self.result = None

    def _handle_escape(self):
        if self.state == MenuState.MAIN:
            self._exit()
        elif self.state == MenuState.DIFFICULTY:
            self._change_state(MenuState.MAIN)
        elif self.state in [MenuState.SETTINGS, MenuState.RULES]:
            self._change_state(MenuState.MAIN)
        elif self.state in [MenuState.BOARD_SIZE, MenuState.TIME_SELECT, MenuState.THEME_SELECT]:
            self._change_state(MenuState.SETTINGS)
        elif self.state == MenuState.CREDITS:
            self._change_state(MenuState.SETTINGS)
        else:
            self._change_state(MenuState.MAIN)

    def _draw_background(self):
        theme = self._get_current_theme()
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        else:
            self.screen.fill(theme.background_color)

    def _draw_title(self):
        theme = self._get_current_theme()
        title = self.font_title.render("GOMOKU", True, theme.accent_color)
        title_rect = title.get_rect(center=(self.W // 2, 80))

        shadow = self.font_title.render("GOMOKU", True, (100, 100, 100))
        shadow_rect = shadow.get_rect(center=(self.W // 2 + 3, 83))
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(title, title_rect)

        pygame.draw.line(self.screen, theme.accent_color,
                         (self.W // 2 - 250, 140),
                         (self.W // 2 + 250, 140), 4)

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

    def _draw_credits(self):
        theme = self._get_current_theme()
        self._draw_subtitle("Credits", 100)

        credits = [
            "Gomoku Game",
            "Version 1.0",
            "",
            "Developed by: DuyenNH2401",
            "Engine: Python + Pygame",
            "AI: Minimax with Alpha-Beta Pruning",
            "",
            "Special Thanks:",
            "• Pattern-based evaluation system",
            "• Strategic blocking mechanics",
            "• Skill point rotation system",
            "",
            "© 2025 - All rights reserved",
        ]

        self._draw_info_text(credits, 160)

        back_btn = Button("Back to Settings", self.W // 2 - 150, self.H - 90, 300, 50,
                          lambda: self._change_state(MenuState.SETTINGS),
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
                    self.running = False
                    self.result = None

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._handle_escape()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state in self.buttons:
                        for button in self.buttons[self.state]:
                            if button.is_hovered(mouse_pos) and button.enabled and button.action:
                                button.action()

            self._draw_background()

            if self.state == MenuState.RULES:
                self._draw_rules()
                self._draw_footer()
            elif self.state == MenuState.CREDITS:
                self._draw_credits()
                self._draw_footer()
            else:
                self._draw_title()
                self._draw_current_settings()

                if self.state in self.buttons:
                    for button in self.buttons[self.state]:
                        button.draw(self.screen, self.font_normal, mouse_pos)

                self._draw_footer()

            pygame.display.flip()

        return self.result


def show_menu() -> Optional[dict]:
    menu = Menu()
    return menu.run()