from __future__ import annotations
import os, pygame
import random
from typing import Tuple, Optional
from models import BOARD_SIZES
from engine import Engine
import storage

#your music lives + allowed extensions
MUSIC_DIR = os.path.join("assets", "music")
MUSIC_EXTS = (".ogg", ".mp3", ".flac", ".wav")


THEMES = {
    "light": {
        "bg": (240, 240, 240),
        "grid": (200, 180, 140),
        "border": (160, 130, 70),
        "piece_x": (30, 30, 30),
        "piece_o": (220, 170, 60),
        "block": (200, 70, 70),
        "hud_bg": (255, 255, 255, 220),
        "shadow": (220, 200, 140),
        "accent": (220, 170, 60),
        "text": (30, 30, 30)
    },
    "dark": {
        "bg": (32, 36, 46),
        "grid": (90, 100, 110),
        "border": (60, 70, 80),
        "piece_x": (240, 240, 240),
        "piece_o": (255, 215, 100),
        "block": (240, 80, 80),
        "hud_bg": (48, 53, 65, 220),
        "shadow": (60, 70, 80),
        "accent": (255, 215, 100),
        "text": (220, 220, 220)
    }
}

class UI:
    def __init__(self, engine: Engine):
        pygame.init()

        # --- AUDIO ATTRS (must exist before any start) ---
        self._music_ready = False
        self._current_music_key: Optional[str] = None
        self._winner_music_played = False

        # Mixer can fail on some setups; guard it
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._music_ready = True
        except Exception as e:
            print(f"[UI] Mixer init failed: {e}")
            

        self.engine = engine
        self.cell = 40  # px
        self.margin_top = 124
        self.margin_bottom = 75
        self.margin_left = 120
        self.margin_right = 120

        self.theme_name = storage.load_themes().get("theme", "light")
        self.theme = THEMES[self.theme_name]

        self._update_window_size()

        # --- Start the window in fullscreen ---
        # If you prefer to start windowed, set start_fullscreen to False.
        # This tries to open a fullscreen display; on failure it falls back to a resizable window.
        try:
            # (0,0) often tells pygame to use the current display resolution for fullscreen
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self._started_fullscreen = True
        except Exception:
            self.screen = pygame.display.set_mode((self.W, self.H), pygame.RESIZABLE)
            self._started_fullscreen = False

        # minimum window size (tweak if you like)
        # when starting fullscreen, set minimum to current display size to avoid shrinking below fullscreen
        win_w, win_h = self.screen.get_size()
        self.min_w = max(self.W, 900) if not self._started_fullscreen else win_w
        self.min_h = max(self.H, 700) if not self._started_fullscreen else win_h

        # if pygame has native min-size support, lock it (only when not fullscreen)
        if not self._started_fullscreen and hasattr(pygame.display, "set_window_min_size"):
            pygame.display.set_window_min_size(self.min_w, self.min_h)

        pygame.display.set_caption("Gomoku — Gokumo UI")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("consolas", 18)
        self.font = pygame.font.SysFont("consolas", 19, bold=True)
        self.font_big = pygame.font.SysFont("consolas", 23, bold=True)
        self.place_block_mode = False
        self.message: Optional[str] = None
        self.message_t = 0.0
        
        # --- in-match confirmation modal ---
        self._confirming = False            # modal visible?
        self._confirm_kind = None           # "exit" or "restart"
        self._confirm_yes_rect = None       # pygame.Rect
        self._confirm_no_rect = None        # pygame.Rect
        self._leave_requested = False       # break loop when true
        
        # --- winner popup menu ---
        self._winner_popup_visible = False
        self._winner_popup_continue_rect = None
        self._winner_popup_new_game_rect = None
        self._winner_popup_report_rect = None
        self._winner_popup_back_to_menu_rect = None
        self._winner_popup_close_rect = None
        self._winner_name = None
        self._winner_popup_alpha = 0.0  # For fade-in animation
        self._winner_popup_time = 0.0  # Track time since popup shown
        
        # --- replay viewer ---
        self._replay_viewer_visible = False
        self._replay_current_move = 0
        self._replay_history = []  # Full game history for replay
        self._replay_previous_rect = None
        self._replay_next_rect = None
        self._replay_back_rect = None


        self.piece_images = {
            'X': self._load_img(os.path.join("assets","images","pieces","X.png")),
            'O': self._load_img(os.path.join("assets","images","pieces","O.png"))
        }
        self.block_img = self._load_img(os.path.join("assets","images","block","hash_block.png"))

        self._start_difficulty_music()


    def _show_winner_popup(self, winner_name: str):
        """Show winner popup menu"""
        print(f"[UI] Showing winner popup for: {winner_name}")  # Debug
        self._winner_popup_visible = True
        self._winner_name = winner_name
        self._winner_popup_alpha = 0.0  # Start from transparent
        self._winner_popup_time = 0.0  # Reset timer
        self._build_winner_popup_buttons()

    def _show_game_report(self):
        """Show game report - opens integrated replay viewer"""
        # Copy current game state for replay
        self._replay_history = []
        # Make a copy of moves for replay
        import copy
        for move in self.engine.state.history:
            self._replay_history.append(copy.copy(move))
        self._replay_current_move = len(self._replay_history) if self._replay_history else 0
        self._replay_viewer_visible = True
        # Store winner name before hiding popup
        winner_name = self._winner_name
        self._hide_winner_popup()
        self._winner_name = winner_name  # Restore for back button
        self._build_replay_buttons()

    def _hide_winner_popup(self):
        """Hide winner popup menu"""
        self._winner_popup_visible = False
        self._winner_name = None
        self._winner_popup_alpha = 0.0
        self._winner_popup_time = 0.0
        self._winner_popup_new_game_rect = None
        self._winner_popup_report_rect = None
        self._winner_popup_back_to_menu_rect = None
        self._winner_popup_close_rect = None
    
    def _build_replay_buttons(self):
        """Build button rectangles for replay viewer"""
        win_w, win_h = self.screen.get_size()
        # Larger, more prominent buttons
        btn_w, btn_h = 180, 65
        btn_y = win_h - 160  # Moved up higher
        
        # Previous button (left)
        self._replay_previous_rect = pygame.Rect(win_w // 2 - btn_w - 30, btn_y, btn_w, btn_h)
        # Next button (right)
        self._replay_next_rect = pygame.Rect(win_w // 2 + 30, btn_y, btn_w, btn_h)
        # Back button (center bottom) - slightly smaller
        back_w, back_h = 140, 55
        self._replay_back_rect = pygame.Rect(win_w // 2 - back_w // 2, btn_y + btn_h + 20, back_w, back_h)

    def _build_winner_popup_buttons(self):
        """Build button rectangles for winner popup"""
        win_w, win_h = self.screen.get_size()
        popup_w, popup_h = 550, 500  # Reduced height since we removed elements
        popup_x = (win_w - popup_w) // 2
        popup_y = (win_h - popup_h) // 2
        
        # Continue/New Game button (larger, prominent)
        btn_w, btn_h = 320, 60
        self._winner_popup_continue_rect = pygame.Rect(
            popup_x + (popup_w - btn_w) // 2,
            popup_y + popup_h - 240,
            btn_w, btn_h
        )
        self._winner_popup_new_game_rect = self._winner_popup_continue_rect  # Same button, different text
        
        # Game Report button
        report_w, report_h = 160, 50
        self._winner_popup_report_rect = pygame.Rect(
            popup_x + (popup_w - report_w) // 2,
            popup_y + popup_h - 170,
            report_w, report_h
        )
        
        # Back to Menu button
        menu_w, menu_h = 160, 50
        self._winner_popup_back_to_menu_rect = pygame.Rect(
            popup_x + (popup_w - menu_w) // 2,
            popup_y + popup_h - 110,
            menu_w, menu_h
        )
        
        # Close button (X) at top right
        close_size = 40
        self._winner_popup_close_rect = pygame.Rect(
            popup_x + popup_w - close_size - 15,
            popup_y + 15,
            close_size, close_size
        )

    def _draw_winner_popup(self, dt: float = 0.016):
        """Draw the winner popup menu with chess.com-like style"""
        if not self._winner_popup_visible or not self._winner_name:
            return
        
        # Debug: Print once when drawing starts
        if self._winner_popup_time < dt * 2:  # Only print in first frame
            print(f"[UI] Drawing winner popup for: {self._winner_name}, alpha: {self._winner_popup_alpha}")
        
        # Update animation
        self._winner_popup_time += dt
        if self._winner_popup_alpha < 1.0:
            self._winner_popup_alpha = min(1.0, self._winner_popup_alpha + dt * 3.0)  # Fade in over ~0.33s
        
        win_w, win_h = self.screen.get_size()
        popup_w, popup_h = 550, 500  # Reduced height
        popup_x = (win_w - popup_w) // 2
        popup_y = (win_h - popup_h) // 2
        
        # Apply alpha to all drawing
        alpha_int = int(255 * self._winner_popup_alpha)
        
        # Dim background with fade
        dim = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, int(180 * self._winner_popup_alpha)))
        self.screen.blit(dim, (0, 0))
        
        # Popup helpers for color blending
        def _blend(c1, c2, amount):
            return tuple(int(c1[i] + (c2[i] - c1[i]) * amount) for i in range(3))

        def _lighten(color, amount):
            return _blend(color, (255, 255, 255), amount)

        def _darken(color, amount):
            return _blend(color, (0, 0, 0), amount)

        accent = self.theme.get("accent", (255, 215, 100))
        accent_soft = _lighten(accent, 0.35)
        accent_deep = _darken(accent, 0.45)
        base_bg = self.theme.get("bg", (32, 36, 46))

        # Popup background surface with a rich gradient
        popup_surf = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
        for y in range(popup_h):
            t = y / max(1, popup_h - 1)
            color = _blend(accent_deep, accent_soft, t)
            pygame.draw.line(popup_surf, color, (0, y), (popup_w, y))

        # Add diagonal light sweep
        sweep = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
        for x in range(popup_w):
            alpha = int(120 * (1 - x / popup_w))
            pygame.draw.line(sweep, (255, 255, 255, alpha), (x, 0), (x, popup_h))
        popup_surf.blit(sweep, (0, 0))

        # Subtle texture overlay
        texture = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
        for y in range(0, popup_h, 6):
            alpha = 14 if (y // 6) % 2 == 0 else 6
            pygame.draw.line(texture, (255, 255, 255, alpha), (0, y), (popup_w, y))
        popup_surf.blit(texture, (0, 0))

        # Draw border with shadow effect
        shadow_surf = pygame.Surface((popup_w + 6, popup_h + 6), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, int(80 * self._winner_popup_alpha)))
        self.screen.blit(shadow_surf, (popup_x - 3, popup_y - 3))
        
        # Blit popup background directly (no alpha blending needed for background)
        self.screen.blit(popup_surf, (popup_x, popup_y))
        
        # Draw border with rounded corners (draw directly on screen)
        border_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
        # Outer border inspired by board colors
        pygame.draw.rect(self.screen, _lighten(accent_soft, 0.15), border_rect, width=4, border_radius=24)
        # Inner dark border for depth
        inner_rect = border_rect.inflate(-2, -2)
        pygame.draw.rect(self.screen, _blend(base_bg, accent_deep, 0.25), inner_rect, width=2, border_radius=22)

        # Halo highlight behind the crown
        halo_radius = 110
        halo_surf = pygame.Surface((halo_radius * 2, halo_radius * 2), pygame.SRCALPHA)
        for r in range(halo_radius, 0, -1):
            alpha = int(180 * (1 - (r / halo_radius)))
            pygame.draw.circle(halo_surf, (_lighten(accent, 0.4) + (alpha,)), (halo_radius, halo_radius), r)
        self.screen.blit(halo_surf, (popup_x + popup_w // 2 - halo_radius, popup_y - 10))

        # Crown icon
        crown_w, crown_h = 150, 90
        crown_surf = pygame.Surface((crown_w, crown_h), pygame.SRCALPHA)
        crown_points = [
            (10, crown_h - 15),
            (35, 40),
            (55, crown_h - 35),
            (75, 25),
            (95, crown_h - 35),
            (115, 40),
            (140, crown_h - 15),
        ]
        pygame.draw.polygon(crown_surf, _lighten(accent, 0.1), crown_points)
        pygame.draw.polygon(crown_surf, _darken(accent, 0.3), crown_points, width=4)
        pygame.draw.circle(crown_surf, (255, 255, 255, 200), (35, 40), 7)
        pygame.draw.circle(crown_surf, (255, 255, 255, 200), (75, 25), 8)
        pygame.draw.circle(crown_surf, (255, 255, 255, 200), (115, 40), 7)
        self.screen.blit(crown_surf, (popup_x + popup_w // 2 - crown_w // 2, popup_y + 10))
        
        # Title area
        # Try arial first, fallback to default font
        try:
            hero_font = pygame.font.SysFont("arial", 28, bold=True)
            title_font = pygame.font.SysFont("arial", 56, bold=True)
        except:
            hero_font = pygame.font.Font(None, 28)
            title_font = pygame.font.Font(None, 56)

        victory_text = "Victory!"
        victory_surf = hero_font.render(victory_text, True, (255, 255, 255))
        victory_rect = victory_surf.get_rect(center=(popup_x + popup_w // 2, popup_y + 100))
        self.screen.blit(victory_surf, victory_rect)

        title_text = f"{self._winner_name} Won!"
        try:
            title_shadow = title_font.render(title_text, True, (0, 0, 0))
            title_surf = title_font.render(title_text, True, (255, 255, 255))
        except:
            # Fallback if font rendering fails
            title_surf = self.font_big.render(title_text, True, (255, 255, 255))
            title_shadow = self.font_big.render(title_text, True, (0, 0, 0))
        title_rect = title_surf.get_rect(center=(popup_x + popup_w // 2, popup_y + 150))
        # Draw shadow first, then text
        self.screen.blit(title_shadow, title_rect.move(3, 3))
        self.screen.blit(title_surf, title_rect)

        # Decorative confetti (deterministic positions)
        confetti_rng = random.Random(8721)
        for _ in range(18):
            cx = popup_x + confetti_rng.randint(50, popup_w - 50)
            cy = popup_y + confetti_rng.randint(40, 180)
            size = confetti_rng.randint(3, 6)
            hue = _blend(accent, (255, 255, 255), confetti_rng.random() * 0.5)
            pygame.draw.circle(self.screen, hue, (cx, cy), size)
        
        # Match score display
        p1_score, p2_score = self.engine.get_match_score()
        p1_name = self.engine.players[0].nickname or self.engine.players[0].full_name
        p2_name = self.engine.players[1].nickname or self.engine.players[1].full_name
        score_text = f"{p1_name} {p1_score} - {p2_score} {p2_name}"
        if self.engine.best_of > 1:
            score_text += f" (BO{self.engine.best_of})"
        
        try:
            score_font = pygame.font.SysFont("arial", 24, bold=True)
        except:
            score_font = self.font
        score_surf = score_font.render(score_text, True, (255, 255, 255))
        score_rect = score_surf.get_rect(center=(popup_x + popup_w // 2, popup_y + 195))
        score_bg = pygame.Surface((score_rect.width + 32, score_rect.height + 10), pygame.SRCALPHA)
        pygame.draw.rect(score_bg, (255, 255, 255, 40), score_bg.get_rect(), border_radius=16)
        self.screen.blit(score_bg, score_bg.get_rect(center=score_rect.center))
        self.screen.blit(score_surf, score_rect)

        # Separator line
        pygame.draw.line(
            self.screen,
            _lighten(base_bg, 0.65),
            (popup_x + 60, popup_y + 220),
            (popup_x + popup_w - 60, popup_y + 220),
            width=2,
        )
        
        # Game stats section (only Moves)
        stats_y = popup_y + 240
        stat_w, stat_h = 160, 80
        stat_spacing = 30
        total_moves = len(self.engine.state.history)
        stats = [
            ("Moves", str(total_moves), _lighten(accent, 0.2)),
        ]
        
        # Calculate total width of stats row
        total_stats_width = len(stats) * stat_w + (len(stats) - 1) * stat_spacing
        stats_start_x = popup_x + (popup_w - total_stats_width) // 2
        
        for i, (label, value, color) in enumerate(stats):
            stat_x = stats_start_x + i * (stat_w + stat_spacing)
            stat_rect = pygame.Rect(stat_x, stats_y, stat_w, stat_h)
            
            # Stat box with rounded corners and gradient fill
            stat_surf = pygame.Surface((stat_w, stat_h), pygame.SRCALPHA)
            for y in range(stat_h):
                t = y / max(1, stat_h - 1)
                row_color = _blend(_lighten(color, 0.25), _darken(color, 0.35), t)
                pygame.draw.line(stat_surf, row_color, (0, y), (stat_w, y))
            pygame.draw.rect(stat_surf, (255, 255, 255, 32), stat_surf.get_rect(), width=2, border_radius=16)
            pygame.draw.rect(stat_surf, (255, 255, 255, 60), stat_surf.get_rect(), border_radius=16)
            self.screen.blit(stat_surf, stat_rect.topleft)
            pygame.draw.rect(self.screen, _lighten(color, 0.1), stat_rect, width=2, border_radius=16)
            
            # Value (large, bold)
            try:
                value_font = pygame.font.SysFont("arial", 28, bold=True)
            except:
                value_font = self.font_big
            value_surf = value_font.render(value, True, (255, 255, 255))
            value_rect = value_surf.get_rect(center=(stat_x + stat_w // 2, stats_y + stat_h // 2 - 8))
            self.screen.blit(value_surf, value_rect)
            
            # Label (small)
            try:
                label_font = pygame.font.SysFont("arial", 14)
            except:
                label_font = self.font_small
            label_surf = label_font.render(label, True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=(stat_x + stat_w // 2, stats_y + stat_h - 18))
            self.screen.blit(label_surf, label_rect)
        
        # Continue/New Game button - large, prominent, green
        mouse = pygame.mouse.get_pos()
        continue_hover = self._winner_popup_continue_rect and self._winner_popup_continue_rect.collidepoint(mouse)
        
        # Determine button text based on match status
        is_match_over = self.engine.is_match_over()
        button_text = "New Match" if is_match_over else "Continue"
        
        if self._winner_popup_continue_rect:
            btn_rect = self._winner_popup_continue_rect
            # Button shadow
            shadow_rect = btn_rect.move(0, 4)
            shadow_surf = pygame.Surface((btn_rect.w, btn_rect.h), pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 60))
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Button background - follow accent color
            base_color = accent
            if continue_hover:
                btn_color = _lighten(base_color, 0.18)
                btn_border = _darken(base_color, 0.25)
            else:
                btn_color = base_color
                btn_border = _darken(base_color, 0.3)
            
            pygame.draw.rect(self.screen, btn_color, btn_rect, border_radius=12)
            pygame.draw.rect(self.screen, btn_border, btn_rect, width=3, border_radius=12)
            
            # Button text
            try:
                btn_font = pygame.font.SysFont("arial", 32, bold=True)
            except:
                btn_font = self.font_big
            btn_text_surf = btn_font.render(button_text, True, (255, 255, 255))
            text_rect = btn_text_surf.get_rect(center=btn_rect.center)
            self.screen.blit(btn_text_surf, text_rect)
        
        # Game Report button - smaller, secondary
        if self._winner_popup_report_rect:
            report_hover = self._winner_popup_report_rect.collidepoint(mouse)
            report_rect = self._winner_popup_report_rect
            report_color = (200, 200, 200) if report_hover else (180, 180, 180)
            
            pygame.draw.rect(self.screen, report_color, report_rect, border_radius=10)
            pygame.draw.rect(self.screen, (140, 140, 140), report_rect, width=2, border_radius=10)
            
            try:
                report_font = pygame.font.SysFont("arial", 18)
            except:
                report_font = self.font_small
            report_text = report_font.render("Game Report", True, (40, 40, 40))
            report_text_rect = report_text.get_rect(center=report_rect.center)
            self.screen.blit(report_text, report_text_rect)
        
        # Back to Menu button
        if self._winner_popup_back_to_menu_rect:
            menu_hover = self._winner_popup_back_to_menu_rect.collidepoint(mouse)
            menu_rect = self._winner_popup_back_to_menu_rect
            menu_color = (200, 200, 200) if menu_hover else (180, 180, 180)
            
            pygame.draw.rect(self.screen, menu_color, menu_rect, border_radius=10)
            pygame.draw.rect(self.screen, (140, 140, 140), menu_rect, width=2, border_radius=10)
            
            try:
                menu_font = pygame.font.SysFont("arial", 18)
            except:
                menu_font = self.font_small
            menu_text = menu_font.render("Back to Menu", True, (40, 40, 40))
            menu_text_rect = menu_text.get_rect(center=menu_rect.center)
            self.screen.blit(menu_text, menu_text_rect)
        
        # Close button (X) - top right
        if self._winner_popup_close_rect:
            close_hover = self._winner_popup_close_rect.collidepoint(mouse)
            close_rect = self._winner_popup_close_rect
            close_color = (220, 220, 220) if close_hover else (200, 200, 200)
            
            pygame.draw.rect(self.screen, close_color, close_rect, border_radius=6)
            try:
                close_font = pygame.font.SysFont("arial", 20, bold=True)
            except:
                close_font = self.font
            close_text = close_font.render("X", True, (60, 60, 60))
            close_text_rect = close_text.get_rect(center=close_rect.center)
            self.screen.blit(close_text, close_text_rect)

    # ==== confirmation modal: core API ====
    def _request_exit(self):
        self._open_confirm("exit")

    def _request_restart(self):
        self._open_confirm("restart")

    def _open_confirm(self, kind: str):
        self._confirming = True
        self._confirm_kind = kind
        self._build_confirm_buttons()

    def _cancel_confirm(self):
        self._confirming = False
        self._confirm_kind = None
        self._confirm_yes_rect = None
        self._confirm_no_rect = None
        self.note("Canceled.")

    def _confirm_yes(self):
        kind = self._confirm_kind
        self._cancel_confirm()

        if kind == "restart":
            # do the same reset ritual you already use
            self.engine.reset()
            self.place_block_mode = False
            # PvP vs PvCPU note: pick a nice message based on mode
            msg = "Restarted PvCPU match." if (self._get_mode() == "pvcpu") else "Restarted. Block mode: OFF."
            self.note(msg)

            # kill any fanfare, restart BGM with new random music
            self._winner_music_played = False
            self._stop_music(150)
            # Reset music key to allow new random selection
            self._current_music_key = None
            try:
                pygame.time.delay(50)
            except Exception:
                pass
            self._start_difficulty_music()

        elif kind == "exit":
            # leave this UI loop; menu/music cleanup mirrors your existing behavior
            self._stop_music()
            self._leave_requested = True

    # ==== confirmation modal: drawing + layout ====
    def _build_confirm_buttons(self):
        btn_w, btn_h, spacing = 160, 56, 30
        win_w, win_h = self.screen.get_size()
        cx, cy = win_w // 2, win_h // 2 + 10
        self._confirm_yes_rect = pygame.Rect(cx - btn_w - spacing // 2 + 10, cy, btn_w, btn_h)
        self._confirm_no_rect  = pygame.Rect(cx + spacing // 2 + 10, cy, btn_w, btn_h)

    def _draw_confirm_modal(self):
        if not self._confirming:
            return

        win_w, win_h = self.screen.get_size()
        # darken the world
        dim = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        self.screen.blit(dim, (0, 0))

        # modal box
        box_w, box_h = 560, 260
        box_x = (win_w - box_w) // 2
        box_y = (win_h - box_h) // 2
        box = pygame.Rect(box_x, box_y, box_w, box_h)

        # bg + border (use HUD bg & accent to match your theme)
        bg = self.theme["hud_bg"]
        if len(bg) == 4:
            bg_no_alpha = (bg[0], bg[1], bg[2], 230)
        else:
            bg_no_alpha = (*bg, 230)
        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        panel.fill(bg_no_alpha)
        self.screen.blit(panel, (box_x, box_y))
        pygame.draw.rect(self.screen, self.theme["accent"], box, width=3, border_radius=14)

        # title + message
        title_txt = "Leave match?" if self._confirm_kind == "exit" else "Restart match?"
        msg_txt   = "Are you sure? Unsaved progress will be lost."
        title = self.font_big.render(title_txt, True, self.theme["text"])
        msg   = self.font.render(msg_txt,   True, self.theme["text"])
        self.screen.blit(title, title.get_rect(center=(win_w // 2, box_y + 60)))
        self.screen.blit(msg,   msg.get_rect(center=(win_w // 2, box_y + 105)))

        # buttons (hover states)
        mouse = pygame.mouse.get_pos()
        def _draw_btn(rect: pygame.Rect, label: str, base, hover):
            hovered = rect.collidepoint(mouse)
            color = hover if hovered else base
            # shadow
            pygame.draw.rect(self.screen, (50, 50, 50), rect.move(4, 4), border_radius=8)
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, self.theme["text"], rect, width=2, border_radius=8)
            lab = self.font.render(label, True, (30, 30, 30) if sum(color) > 380 else (240, 240, 240))
            self.screen.blit(lab, lab.get_rect(center=rect.center))

        yes_col  = (200, 70, 70) if self._confirm_kind == "exit" else self.theme["accent"]
        yes_hover= (255,120,120) if self._confirm_kind == "exit" else tuple(min(255, c+40) for c in self.theme["accent"])
        no_col   = (120, 120, 120)
        no_hover = (180, 180, 180)

        _draw_btn(self._confirm_yes_rect, "Yes", yes_col, yes_hover)
        _draw_btn(self._confirm_no_rect,  "No",  no_col,  no_hover)

        # tiny hint
        hint = self.font_small.render("Enter/Y = Yes   •   Esc/N = No", True, self.theme["text"])
        self.screen.blit(hint, hint.get_rect(center=(win_w // 2, box_y + box_h - 28)))


    #pick a winner music file. Priority:
    #   1) winner_<mode> (e.g., winner_pvp.* / winner_pvcpu.*)
    #   2) winner_<piece> (winner_x.* / winner_o.*)
    #   3) winner.*
    def _resolve_winner_music(self, winner_piece: Optional[str]) -> Optional[str]:
        mode = self._get_mode() or ""
        piece = (winner_piece or "").lower()

        candidates = []
        if mode:
            candidates.append(f"winner_{mode}")
        if piece in ("x", "o"):
            candidates.append(f"winner_{piece}")
        candidates.append("winner")

        for base in candidates:
            for ext in MUSIC_EXTS:
                p = os.path.join(MUSIC_DIR, base + ext)
                if os.path.exists(p):
                    return p
        return None

    #stop bg loop and play victory one-shot
    def _play_winner_music(self, winner_piece: Optional[str]):
        if not pygame.mixer.get_init():
            return
        path = self._resolve_winner_music(winner_piece)
        if not path:
            print("[UI] No winner.* track found; staying with silence after fade.")
            self._stop_music(200)
            return

        try:
            pygame.mixer.music.fadeout(450)
        except Exception:
            pass

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.8)   # a little louder for the dub
            pygame.mixer.music.play(0)           # one-shot, no loop
            self._current_music_key = os.path.basename(path).lower()
            print(f"[UI] Winner music: {path}")
        except Exception as e:
            print(f"[UI] Failed to play winner music '{path}': {e}")



    #figure out the current mode (pvp or pvcpu/ai)
    def _get_mode(self) -> Optional[str]:
        # Try common engine fields first
        for path in [
            ("engine", "mode"),
            ("engine", "state", "mode"),
        ]:
            obj = self
            ok = True
            for p in path:
                obj = getattr(obj, p, None)
                if obj is None:
                    ok = False
                    break
            if ok and isinstance(obj, str):
                return obj.lower()

        # Fallback: read from preferences if your menu piped it there
        try:
            prefs = storage.load_preferences()
            val = prefs.get("mode")
            if isinstance(val, str):
                return val.lower()
        except Exception:
            pass

        return None


    #try to read difficulty from a few sensible places
    def _get_difficulty(self) -> Optional[str]:
        # 1) Engine attributes most folks use
        for path in [
            ("engine", "difficulty"),
            ("engine", "level"),
            ("engine", "ai_difficulty"),
            ("engine", "state", "difficulty"),
        ]:
            obj = self
            ok = True
            for p in path:
                obj = getattr(obj, p, None)
                if obj is None:
                    ok = False
                    break
            if ok and isinstance(obj, str):
                return obj.lower()

        # 2) Fallback to saved preferences (menu likely wrote this at some point)
        try:
            prefs = storage.load_preferences()
            val = prefs.get("difficulty")
            if isinstance(val, str):
                return val.lower()
        except Exception:
            pass

        return None

    # resolve easy/medium/hard to a file path under assets/music/
    def _resolve_difficulty_music(self) -> Optional[str]:
        difficulty = self._get_difficulty()
        if not difficulty:
            return None
        
        difficulty_lower = difficulty.lower()
        for ext in MUSIC_EXTS:
            path = os.path.join(MUSIC_DIR, difficulty_lower + ext)
            if os.path.exists(path):
                return path
        return None


    # start/loop music (no restart if the same file is already playing)
    def _start_difficulty_music(self):
        if not pygame.mixer.get_init():
            return
        path = self._resolve_difficulty_music()
        if not path:
            print("[UI] No difficulty music file found; staying quiet.")
            return

        key = os.path.basename(path).lower()

        # safety: make sure the field exists
        if not hasattr(self, "_current_music_key"):
            self._current_music_key = None

        if key == self._current_music_key:
            return

        try:
            pygame.mixer.music.fadeout(150)
        except Exception:
            pass

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.6)
            pygame.mixer.music.play(-1)
            self._current_music_key = key
            print(f"[UI] Now looping: {path}")
        except Exception as e:
            print(f"[UI] Failed to play '{path}': {e}")
            self._current_music_key = None

    # stop with a tiny fade
    def _stop_music(self, fade_ms: int = 200):
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()     # hard stop
                pygame.mixer.music.fadeout(fade_ms)  # vibe-out
            except:
                pass
        self._current_music_key = None


    def _load_img(self, path: str) -> Optional[pygame.Surface]:
        try:
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                return img
        except Exception:
            pass
        return None

    def _update_window_size(self):
        n = self.engine.state.board_size
        self.W = n * self.cell + self.margin_left + self.margin_right
        self.H = n * self.cell + self.margin_top + self.margin_bottom

    def board_rect(self) -> pygame.Rect:
        n = self.engine.state.board_size
        size = n * self.cell

        # get current window size in case of fullscreen or resize
        win_w, win_h = self.screen.get_size()

        # Reserve space for move history panel on the right (280px wide)
        history_panel_width = 280
        available_width = win_w - history_panel_width - 40  # 40px margin
        
        # center the board area dynamically (accounting for history panel)
        x = (available_width - size) // 2
        y = (win_h - size + 30) // 2

        return pygame.Rect(x, y, size, size)
    
    def _draw_replay_viewer(self):
        """Draw replay viewer with board state at current move"""
        win_w, win_h = self.screen.get_size()
        
        # Draw title
        title_font = self.font_big
        title_text = "Game Report - Replay"
        title_surf = title_font.render(title_text, True, self.theme["accent"])
        title_rect = title_surf.get_rect(center=(win_w // 2, 40))
        self.screen.blit(title_surf, title_rect)
        
        # Draw move counter
        move_info_text = f"Move {self._replay_current_move} / {len(self._replay_history)}"
        move_info_surf = self.font.render(move_info_text, True, self.theme["text"])
        move_info_rect = move_info_surf.get_rect(center=(win_w // 2, 80))
        self.screen.blit(move_info_surf, move_info_rect)
        
        # Reconstruct board state up to current move
        n = self.engine.state.board_size
        replay_grid = [[None for _ in range(n)] for _ in range(n)]
        replay_blocks = {}  # (row, col) -> expires_at_global_turn
        # Track moves by player for undo
        player_moves = {self.engine.players[0].pid: [], self.engine.players[1].pid: []}
        global_turn_counter = 0  # Track global turns (only stones count)
        
        for i in range(self._replay_current_move):
            if i >= len(self._replay_history):
                break
            move = self._replay_history[i]
            
            if move.action_type == "stone":
                replay_grid[move.row][move.col] = move.piece
                player_moves[move.player_id].append((move.row, move.col))
                global_turn_counter += 1
                # Check if any blocks should expire
                expired_blocks = [pos for pos, expiry in replay_blocks.items() if expiry <= global_turn_counter]
                for pos in expired_blocks:
                    del replay_blocks[pos]
            elif move.action_type == "block":
                # Block expires after 5 global turns from placement
                replay_blocks[(move.row, move.col)] = global_turn_counter + 5
            elif move.action_type == "undo":
                # Remove the most recent stone of this player
                if player_moves[move.player_id]:
                    # Get the last move of this player and remove it
                    last_row, last_col = player_moves[move.player_id][-1]
                    replay_grid[last_row][last_col] = None
                    player_moves[move.player_id].pop()
                    global_turn_counter -= 1  # Undo reduces global turn
                    # Recalculate block expiries (simplified - blocks that would expire are removed)
                    expired_blocks = [pos for pos, expiry in replay_blocks.items() if expiry <= global_turn_counter]
                    for pos in expired_blocks:
                        del replay_blocks[pos]
        
        # Draw board with replay state
        r = self.board_rect()
        # Draw grid
        shadow_offset = 8
        shadow_rect = pygame.Rect(r.x + shadow_offset, r.y + shadow_offset, r.w, r.h)
        pygame.draw.rect(self.screen, self.theme["shadow"], shadow_rect, border_radius=8)
        pygame.draw.rect(self.screen, self.theme["grid"], r, border_radius=8)
        for i in range(n+1):
            y = r.y + i*self.cell
            pygame.draw.line(self.screen, self.theme["border"], (r.x, y), (r.x + r.w, y), 2)
            x = r.x + i*self.cell
            pygame.draw.line(self.screen, self.theme["border"], (x, r.y), (x, r.y + r.h), 2)
        pygame.draw.rect(self.screen, self.theme["border"], r, 4, border_radius=18)
        
        # Draw pieces and blocks from replay state
        for row in range(n):
            for col in range(n):
                cx = r.x + col*self.cell + self.cell//2
                cy = r.y + row*self.cell + self.cell//2
                
                # Check for blocks first (but don't draw if there's a piece)
                if (row, col) in replay_blocks and replay_grid[row][col] is None:
                    if self.block_img:
                        img = pygame.transform.smoothscale(self.block_img, (self.cell-12, self.cell-12))
                        rect = img.get_rect(center=(cx,cy))
                        self.screen.blit(img, rect)
                    else:
                        pygame.draw.rect(self.screen, self.theme["block"], (cx-14, cy-14, 28, 28), 2, border_radius=8)
                
                # Draw pieces
                v = replay_grid[row][col]
                if v:
                    img = self.piece_images.get(v)
                    if img:
                        img = pygame.transform.smoothscale(img, (self.cell-16, self.cell-16))
                        self.screen.blit(img, img.get_rect(center=(cx,cy)))
                    else:
                        color = self.theme["piece_x"] if v == 'X' else self.theme["piece_o"]
                        pygame.draw.circle(self.screen, color, (cx, cy), self.cell//2-6)
                        txt = self.font.render(v, True, self.theme["bg"])
                        self.screen.blit(txt, txt.get_rect(center=(cx,cy)))
        
        # Draw move history panel with skills
        self._draw_replay_move_history()
        
        # Draw navigation buttons - enhanced, more prominent design
        mouse = pygame.mouse.get_pos()
        
        # Previous button - vibrant blue with gradient effect
        if self._replay_previous_rect:
            prev_hover = self._replay_previous_rect.collidepoint(mouse)
            prev_disabled = self._replay_current_move == 0
            
            if prev_disabled:
                prev_color = (120, 120, 120)
                prev_shadow_color = (80, 80, 80)
                prev_border_color = (100, 100, 100)
            else:
                if prev_hover:
                    prev_color = (70, 180, 255)  # Bright blue when hovered
                    prev_shadow_color = (50, 140, 220)
                    prev_border_color = (40, 120, 200)
                else:
                    prev_color = (52, 152, 219)  # Nice blue
                    prev_shadow_color = (40, 120, 180)
                    prev_border_color = (30, 100, 160)
            
            btn_rect = self._replay_previous_rect
            # Shadow effect
            shadow_rect = btn_rect.move(0, 5)
            shadow_surf = pygame.Surface((btn_rect.w, btn_rect.h), pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 80))
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Button background with gradient-like effect
            pygame.draw.rect(self.screen, prev_color, btn_rect, border_radius=12)
            # Highlight on top
            highlight_rect = pygame.Rect(btn_rect.x, btn_rect.y, btn_rect.w, btn_rect.h // 3)
            highlight_surf = pygame.Surface((highlight_rect.w, highlight_rect.h), pygame.SRCALPHA)
            highlight_surf.fill((255, 255, 255, 40))
            self.screen.blit(highlight_surf, highlight_rect)
            # Border
            pygame.draw.rect(self.screen, prev_border_color, btn_rect, width=3, border_radius=12)
            
            # Button text - larger and bold (use text arrows instead of unicode)
            try:
                btn_font = pygame.font.SysFont("arial", 28, bold=True)
            except:
                btn_font = self.font_big
            prev_text = btn_font.render("< Previous", True, (255, 255, 255) if not prev_disabled else (200, 200, 200))
            prev_text_rect = prev_text.get_rect(center=btn_rect.center)
            self.screen.blit(prev_text, prev_text_rect)
        
        # Next button - vibrant blue with gradient effect
        if self._replay_next_rect:
            next_hover = self._replay_next_rect.collidepoint(mouse)
            next_disabled = self._replay_current_move >= len(self._replay_history)
            
            if next_disabled:
                next_color = (120, 120, 120)
                next_shadow_color = (80, 80, 80)
                next_border_color = (100, 100, 100)
            else:
                if next_hover:
                    next_color = (70, 180, 255)  # Bright blue when hovered
                    next_shadow_color = (50, 140, 220)
                    next_border_color = (40, 120, 200)
                else:
                    next_color = (52, 152, 219)  # Nice blue
                    next_shadow_color = (40, 120, 180)
                    next_border_color = (30, 100, 160)
            
            btn_rect = self._replay_next_rect
            # Shadow effect
            shadow_rect = btn_rect.move(0, 5)
            shadow_surf = pygame.Surface((btn_rect.w, btn_rect.h), pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 80))
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Button background with gradient-like effect
            pygame.draw.rect(self.screen, next_color, btn_rect, border_radius=12)
            # Highlight on top
            highlight_rect = pygame.Rect(btn_rect.x, btn_rect.y, btn_rect.w, btn_rect.h // 3)
            highlight_surf = pygame.Surface((highlight_rect.w, highlight_rect.h), pygame.SRCALPHA)
            highlight_surf.fill((255, 255, 255, 40))
            self.screen.blit(highlight_surf, highlight_rect)
            # Border
            pygame.draw.rect(self.screen, next_border_color, btn_rect, width=3, border_radius=12)
            
            # Button text - larger and bold (use text arrows instead of unicode)
            try:
                btn_font = pygame.font.SysFont("arial", 28, bold=True)
            except:
                btn_font = self.font_big
            next_text = btn_font.render("Next >", True, (255, 255, 255) if not next_disabled else (200, 200, 200))
            next_text_rect = next_text.get_rect(center=btn_rect.center)
            self.screen.blit(next_text, next_text_rect)
        
        # Back button - elegant gray with hover effect
        if self._replay_back_rect:
            back_hover = self._replay_back_rect.collidepoint(mouse)
            
            if back_hover:
                back_color = (220, 220, 220)
                back_shadow_color = (180, 180, 180)
                back_border_color = (140, 140, 140)
            else:
                back_color = (200, 200, 200)
                back_shadow_color = (160, 160, 160)
                back_border_color = (120, 120, 120)
            
            btn_rect = self._replay_back_rect
            # Shadow effect
            shadow_rect = btn_rect.move(0, 4)
            shadow_surf = pygame.Surface((btn_rect.w, btn_rect.h), pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 60))
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Button background
            pygame.draw.rect(self.screen, back_color, btn_rect, border_radius=10)
            # Highlight on top
            highlight_rect = pygame.Rect(btn_rect.x, btn_rect.y, btn_rect.w, btn_rect.h // 3)
            highlight_surf = pygame.Surface((highlight_rect.w, highlight_rect.h), pygame.SRCALPHA)
            highlight_surf.fill((255, 255, 255, 30))
            self.screen.blit(highlight_surf, highlight_rect)
            # Border
            pygame.draw.rect(self.screen, back_border_color, btn_rect, width=2, border_radius=10)
            
            # Button text - larger
            try:
                back_font = pygame.font.SysFont("arial", 24, bold=True)
            except:
                back_font = self.font
            back_text = back_font.render("Back", True, (40, 40, 40))
            back_text_rect = back_text.get_rect(center=btn_rect.center)
            self.screen.blit(back_text, back_text_rect)
    
    def _draw_replay_move_history(self):
        """Draw move history panel with skills for replay viewer"""
        win_w, win_h = self.screen.get_size()
        panel_width = 280
        panel_x = win_w - panel_width - 20
        panel_y = self.margin_top + 10
        panel_height = win_h - panel_y - self.margin_bottom - 180  # Leave more room for buttons (moved up)
        
        # Panel background
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        surf.fill(self.theme["hud_bg"])
        self.screen.blit(surf, panel_rect)
        pygame.draw.rect(self.screen, self.theme["accent"], panel_rect, width=2, border_radius=8)
        
        # Title
        title_text = "Move History"
        title_surf = self.font_big.render(title_text, True, self.theme["accent"])
        title_rect = title_surf.get_rect(center=(panel_x + panel_width // 2, panel_y + 25))
        self.screen.blit(title_surf, title_rect)
        
        # Draw moves with skills
        move_y = panel_y + 55
        line_height = 24
        max_visible = (panel_height - 60) // line_height
        
        # Show moves up to current move in replay
        start_idx = max(0, self._replay_current_move - max_visible)
        
        for i in range(start_idx, min(self._replay_current_move, len(self._replay_history))):
            if move_y + line_height > panel_y + panel_height - 10:
                break
            
            move = self._replay_history[i]
            
            # Move notation with action type
            if move.action_type == "stone":
                move_text = f"{i+1}. {move.piece} {chr(ord('a') + move.col)}{move.row + 1}"
            elif move.action_type == "block":
                move_text = f"{i+1}. {move.piece} Block {chr(ord('a') + move.col)}{move.row + 1}"
            elif move.action_type == "undo":
                move_text = f"{i+1}. {move.piece} Undo {chr(ord('a') + move.col)}{move.row + 1}"
            else:
                move_text = f"{i+1}. {move.piece} {chr(ord('a') + move.col)}{move.row + 1}"
            
            # Highlight current move
            if i == self._replay_current_move - 1:
                move_color = (255, 255, 0)  # Yellow for current move
            else:
                move_color = self.theme["piece_x"] if move.piece == 'X' else self.theme["piece_o"]
            
            move_surf = self.font_small.render(move_text, True, move_color)
            self.screen.blit(move_surf, (panel_x + 10, move_y))
            
            move_y += line_height

    def _draw_move_history(self):
        """Draw move history panel on the right side of the screen"""
        win_w, win_h = self.screen.get_size()
        panel_width = 280
        panel_x = win_w - panel_width - 20
        panel_y = self.margin_top + 10
        panel_height = win_h - panel_y - self.margin_bottom - 20
        
        # Panel background
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        surf.fill(self.theme["hud_bg"])
        self.screen.blit(surf, panel_rect)
        pygame.draw.rect(self.screen, self.theme["accent"], panel_rect, width=2, border_radius=8)
        
        # Title
        title_font = self.font_big
        title_text = "Move History"
        title_surf = title_font.render(title_text, True, self.theme["accent"])
        title_rect = title_surf.get_rect(center=(panel_x + panel_width // 2, panel_y + 25))
        self.screen.blit(title_surf, title_rect)
        
        # Draw moves
        history = self.engine.state.history
        move_y = panel_y + 55
        line_height = 22
        max_visible = (panel_height - 60) // line_height
        
        # Show last N moves (scrollable would be better, but simple for now)
        start_idx = max(0, len(history) - max_visible)
        
        for i, move in enumerate(history[start_idx:], start=start_idx + 1):
            if move_y + line_height > panel_y + panel_height - 10:
                break
            
            # Move number and notation with action type
            if move.action_type == "stone":
                move_text = f"{i}. {move.piece} {chr(ord('a') + move.col)}{move.row + 1}"
            elif move.action_type == "block":
                move_text = f"{i}. {move.piece} Block {chr(ord('a') + move.col)}{move.row + 1}"
            elif move.action_type == "undo":
                move_text = f"{i}. {move.piece} Undo {chr(ord('a') + move.col)}{move.row + 1}"
            else:
                move_text = f"{i}. {move.piece} {chr(ord('a') + move.col)}{move.row + 1}"
            
            move_color = self.theme["piece_x"] if move.piece == 'X' else self.theme["piece_o"]
            
            move_surf = self.font_small.render(move_text, True, move_color)
            self.screen.blit(move_surf, (panel_x + 10, move_y))
            
            move_y += line_height
        
        # If there are more moves, show indicator
        if len(history) > max_visible:
            indicator_text = f"... ({len(history) - max_visible} more)"
            indicator_surf = self.font_small.render(indicator_text, True, self.theme["text"])
            self.screen.blit(indicator_surf, (panel_x + 10, move_y))

    def pixel_to_cell(self, x: int, y: int) -> Optional[Tuple[int,int]]:
        r = self.board_rect()
        if not r.collidepoint(x,y):
            return None
        cx = (x - r.x) // self.cell
        cy = (y - r.y) // self.cell
        return (int(cy), int(cx))  # row, col

    def draw_grid(self) -> None:
        r = self.board_rect()
        n = self.engine.state.board_size
        shadow_offset = 8
        shadow_rect = pygame.Rect(r.x + shadow_offset, r.y + shadow_offset, r.w, r.h)
        pygame.draw.rect(self.screen, self.theme["shadow"], shadow_rect, border_radius=8)
        pygame.draw.rect(self.screen, self.theme["grid"], r, border_radius=8)
        for i in range(n+1):
            y = r.y + i*self.cell
            pygame.draw.line(self.screen, self.theme["border"], (r.x, y), (r.x + r.w, y), 2)
            x = r.x + i*self.cell
            pygame.draw.line(self.screen, self.theme["border"], (x, r.y), (x, r.y + r.h), 2)
        pygame.draw.rect(self.screen, self.theme["border"], r, 4, border_radius=18)
        
        # Draw row and column labels
        self._draw_board_labels(r, n)

    def _draw_board_labels(self, board_rect: pygame.Rect, board_size: int) -> None:
        """Draw row numbers (left side) and column letters (top)"""
        # Font for labels - slightly smaller than normal font
        label_font = pygame.font.SysFont("consolas", 16, bold=True)
        label_color = self.theme["text"]
        
        # Offset from board edges
        label_offset = 25
        
        # Draw row numbers on the left (vertical)
        for row in range(board_size):
            y = board_rect.y + row * self.cell + self.cell // 2
            label_text = str(row + 1)  # 1-indexed
            label_surf = label_font.render(label_text, True, label_color)
            label_x = board_rect.x - label_offset
            label_rect = label_surf.get_rect(center=(label_x, y))
            self.screen.blit(label_surf, label_rect)
        
        # Draw column letters on the top (horizontal)
        for col in range(board_size):
            x = board_rect.x + col * self.cell + self.cell // 2
            # Convert column index to letter (a, b, c, ...)
            label_text = chr(ord('a') + col)
            label_surf = label_font.render(label_text, True, label_color)
            label_y = board_rect.y - label_offset
            label_rect = label_surf.get_rect(center=(x, label_y))
            self.screen.blit(label_surf, label_rect)

    def draw_pieces(self) -> None:
        st = self.engine.state
        r = self.board_rect()
        for row in range(st.board_size):
            for col in range(st.board_size):
                v = st.grid[row][col]
                cx = r.x + col*self.cell + self.cell//2
                cy = r.y + row*self.cell + self.cell//2

                if (row, col) in st.blocked_expiry:
                    if self.block_img:
                        img = pygame.transform.smoothscale(self.block_img, (self.cell-12, self.cell-12))
                        rect = img.get_rect(center=(cx,cy))
                        self.screen.blit(img, rect)
                    else:
                        pygame.draw.rect(self.screen, self.theme["block"], (cx-14, cy-14, 28, 28), 2, border_radius=8)
                        txt = self.font_small.render("#", True, self.theme["block"])
                        self.screen.blit(txt, txt.get_rect(center=(cx,cy)))
                    continue

                if v is None:
                    continue

                img = self.piece_images.get(v)
                if img:
                    img = pygame.transform.smoothscale(img, (self.cell-16, self.cell-16))
                    self.screen.blit(img, img.get_rect(center=(cx,cy)))
                else:
                    color = self.theme["piece_x"] if v == 'X' else self.theme["piece_o"]
                    pygame.draw.circle(self.screen, color, (cx, cy), self.cell//2-6)
                    txt = self.font.render(v, True, self.theme["bg"])
                    self.screen.blit(txt, txt.get_rect(center=(cx,cy)))

    def draw_hud(self, dt: float) -> None:
        st = self.engine.state
        win_w, win_h = self.screen.get_size()
        self.font_emoji = pygame.font.SysFont("segoeuisymbol", 23, bold=True)  # Windows
        # --- HUD background (centered) ---
        hud_width = min(self.W - 16, int(win_w * 0.8))
        hud_height = self.margin_top - 16
        hud_x = (win_w - hud_width) // 2
        hud_y = 8

        hud_rect = pygame.Rect(hud_x, hud_y, hud_width, hud_height)
        surf = pygame.Surface((hud_rect.w, hud_rect.h), pygame.SRCALPHA)
        surf.fill(self.theme["hud_bg"])
        self.screen.blit(surf, hud_rect)

        # --- players / turn / piece (top line, centered) ---
        p1, p2 = self.engine.players
        turn_name = self.engine.current_player().nickname or self.engine.current_player().full_name
        info_text = f"Board: {st.board_size}x{st.board_size}     Turn: {turn_name}     Piece: {self.engine.current_player().piece}"
        info_surf = self.font.render(info_text, True, self.theme["accent"])
        info_rect = info_surf.get_rect(center=(win_w // 2, hud_y + 24))
        self.screen.blit(info_surf, info_rect)

        # --- skill points (left & right, same row) ---
        sp_left  = f"You's skill points: {p1.skill_points}"
        sp_right = f"P2's skill points: {p2.skill_points}"
        sp_left_s  = self.font.render(sp_left,  True, self.theme["piece_x"])
        sp_right_s = self.font.render(sp_right, True, self.theme["piece_o"])

        row_y = hud_y + 50
        margin_side = 40
        self.screen.blit(sp_left_s,  (hud_x + margin_side - 10, row_y))
        self.screen.blit(sp_right_s, (hud_x + hud_width - sp_right_s.get_width() - margin_side + 10, row_y))

        # --- winner notification OR transient message (centered inside HUD) ---
        banner_y = hud_y + hud_height - 32  # fixed inside the HUD
        if st.winner_piece:
            # Show popup instead of banner (only show once)
            if not self._winner_popup_visible:
                winner = p1 if p1.piece == st.winner_piece else p2
                winner_name = winner.nickname or winner.full_name
                self._show_winner_popup(winner_name)
                # Save match history when winner is determined
                try:
                    self.engine.save_match_history()
                except Exception as e:
                    print(f"[UI] Failed to save match history: {e}")
        elif self.message:
            # regular transient messages stay inside HUD
            self.message_t -= dt
            if self.message_t <= 0:
                self.message = None
            else:
                msg_surf = self.font_small.render(self.message, True, self.theme["accent"])
                msg_rect = msg_surf.get_rect(center=(win_w // 2, hud_y + hud_height // 2 + 15))
                self.screen.blit(msg_surf, msg_rect)



        # --- footer (centered bottom of window) ---
        footer1 = "LMB: Place Stone | B: block mode | U: undo opp | R: restart"
        footer2 = "T: change theme | Esc: exit"
        surf1 = self.font_small.render(footer1, True, self.theme["accent"])
        surf2 = self.font_small.render(footer2, True, self.theme["accent"])
        self.screen.blit(surf1, (win_w // 2 - surf1.get_width() // 2, win_h - self.margin_bottom + 30))
        self.screen.blit(surf2, (win_w // 2 - surf2.get_width() // 2, win_h - self.margin_bottom + 50))






    def _draw_text(self, text: str, x: int, y: int, font: pygame.font.Font, color=None):
        color = color if color is not None else self.theme["piece_x"]
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x,y))

    def _contrast_text_for(self, rgb):
        # YIQ luma; >150 is “light”, so use dark text; otherwise use light text
        r, g, b = rgb
        yiq = (r * 299 + g * 587 + b * 114) / 1000
        return (30, 30, 30) if yiq > 150 else (240, 240, 240)

    def note(self, msg: str, t: float = 2.0):
        self.message = msg
        self.message_t = t

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._request_exit()

                elif event.type == pygame.KEYDOWN and self._confirming:
                    if event.key in (pygame.K_RETURN, pygame.K_y):
                        self._confirm_yes()
                    elif event.key in (pygame.K_ESCAPE, pygame.K_n):
                        self._cancel_confirm()
                    continue  # modal eats key events

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._request_exit()

                    elif event.key == pygame.K_b:
                        self.place_block_mode = not self.place_block_mode
                        self.note("Block mode: ON" if self.place_block_mode else "Block mode: OFF")

                    elif event.key == pygame.K_u:
                        if self.engine.undo_opponent_last_move():
                            self.note("Undid (spent 1 skill).")
                        else:
                            self.note("Cannot undo (no point or no opponent move).")

                    elif event.key == pygame.K_r:
                        self._request_restart()

                    elif event.key == pygame.K_LEFTBRACKET:
                        self._change_board_size(-1)
                    elif event.key == pygame.K_RIGHTBRACKET:
                        self._change_board_size(1)
                    elif event.key == pygame.K_t:
                        self._toggle_theme()
                    elif event.type == pygame.VIDEORESIZE:
                        new_w = max(self.min_w, event.w)
                        new_h = max(self.min_h, event.h)
                        self.screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._confirming:
                        # modal consumes the click
                        pos = pygame.mouse.get_pos()
                        if self._confirm_yes_rect and self._confirm_yes_rect.collidepoint(pos):
                            self._confirm_yes()
                        elif self._confirm_no_rect and self._confirm_no_rect.collidepoint(pos):
                            self._cancel_confirm()
                        continue

                    # Handle winner popup clicks
                    if self._winner_popup_visible:
                        pos = pygame.mouse.get_pos()
                        if self._winner_popup_close_rect and self._winner_popup_close_rect.collidepoint(pos):
                            self._hide_winner_popup()
                            continue
                        elif self._winner_popup_continue_rect and self._winner_popup_continue_rect.collidepoint(pos):
                            # Continue to next game or start new match
                            self._hide_winner_popup()
                            is_match_over = self.engine.is_match_over()
                            if is_match_over:
                                # Reset entire match
                                self.engine.reset(reset_match=True)
                            else:
                                # Continue to next game in match
                                self.engine.reset(reset_match=False)
                            self.place_block_mode = False
                            self._winner_music_played = False
                            self._stop_music(150)
                            try:
                                pygame.time.delay(50)
                            except Exception:
                                pass
                            self._start_difficulty_music()
                            continue
                        elif self._winner_popup_report_rect and self._winner_popup_report_rect.collidepoint(pos):
                            # Show game report
                            self._show_game_report()
                            continue
                        elif self._winner_popup_back_to_menu_rect and self._winner_popup_back_to_menu_rect.collidepoint(pos):
                            # Back to menu
                            self._leave_requested = True
                            continue
                        # Don't process board clicks when popup is visible
                        continue
                    
                    # Handle replay viewer clicks
                    if self._replay_viewer_visible:
                        pos = pygame.mouse.get_pos()
                        if self._replay_previous_rect and self._replay_previous_rect.collidepoint(pos):
                            # Go to previous move
                            if self._replay_current_move > 0:
                                self._replay_current_move -= 1
                            continue
                        elif self._replay_next_rect and self._replay_next_rect.collidepoint(pos):
                            # Go to next move
                            if self._replay_current_move < len(self._replay_history):
                                self._replay_current_move += 1
                            continue
                        elif self._replay_back_rect and self._replay_back_rect.collidepoint(pos):
                            # Back to winner popup
                            self._replay_viewer_visible = False
                            if self._winner_name:
                                self._show_winner_popup(self._winner_name)
                            continue
                        continue

                    # Don't process board clicks if winner popup is visible or game is over
                    pos = pygame.mouse.get_pos()
                    rc = self.pixel_to_cell(*pos)
                    if rc:
                        r, c = rc
                        # Don't allow moves if game is over
                        st = self.engine.state
                        if st.winner_piece:
                            continue
                        if self.place_block_mode:
                            if self.engine.place_block(r, c):
                                self.note("Placed # (1 point spent).")
                                self.place_block_mode = False
                            else:
                                self.note("Cannot place # there.")
                        else:
                            if self.engine.place_stone(r, c):
                                try:
                                    storage.append_replay_jsonl("demo_match", [self.engine.state.history[-1]])
                                except Exception:
                                    pass
                            else:
                                self.note("Invalid move.")

            self.engine.tick(dt)
            self.screen.fill(self.theme["bg"])
            
            # Draw replay viewer if visible, otherwise draw normal game
            if self._replay_viewer_visible:
                self._draw_replay_viewer()
            else:
                self.draw_grid()
                self.draw_pieces()
                self.draw_hud(dt)
                self._draw_move_history()  # Draw move history panel on the right

            # draw modal last so it sits on top
            self._draw_confirm_modal()
            
            # draw winner popup on top of everything (pass dt for animation)
            if not self._replay_viewer_visible:
                self._draw_winner_popup(dt)

            pygame.display.flip()

            st = self.engine.state
            if st.winner_piece and not self._winner_music_played:
                self._winner_music_played = True
                self._play_winner_music(st.winner_piece)

            if self._leave_requested:
                running = False

        self._stop_music()
        pygame.quit()


    def _change_board_size(self, delta: int):
        n = self.engine.state.board_size
        sizes = BOARD_SIZES
        idx = max(0, min(len(sizes)-1, sizes.index(n) + delta))
        new_n = sizes[idx]
        if new_n != n:
            self.engine.reset(new_n)
            self._update_window_size()
            # refresh min size when board size changes
            self.min_w = max(self.W, 1100)
            self.min_h = max(self.H, 700)
            if hasattr(pygame.display, "set_window_min_size"):
                pygame.display.set_window_min_size(self.min_w, self.min_h)
            self.screen = pygame.display.set_mode((self.W, self.H), pygame.RESIZABLE)
            self.place_block_mode = False
            self.note(f"Board đổi thành {new_n}x{new_n}.")

    def _toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.theme = THEMES[self.theme_name]
        themes = storage.load_themes()
        themes["theme"] = self.theme_name
        storage.save_themes(themes)
        self.note(f"theme changed to: {'dark' if self.theme_name == 'dark' else 'light'}.")