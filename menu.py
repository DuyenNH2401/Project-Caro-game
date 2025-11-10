# src/menu.py
from __future__ import annotations
import pygame
import os
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum
from theme_manager import get_theme_manager, ThemeConfig
import char_select

try:
    from char_select import show_character_select
except Exception:
    # nếu không thể import (tạm thời) giữ variable bằng None để không crash
    show_character_select = None

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
    BO_SELECT = "bo_select"  # Best Of selection (BO1, BO3, BO5)
    SETTINGS = "settings"
    DIFFICULTY = "difficulty"
    BOARD_SIZE = "board_size"
    TIME_SELECT = "time_select"
    THEME_SELECT = "theme_select"
    VOLUME_SETTINGS = "volume_settings"
    RULES = "rules"
    CREDITS = "credits"


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


class VolumeSlider:
    def __init__(self, center_x, y, width, height, default_volume=0.6,
                 color=(230,230,230), track_color=(100,100,100), accent_color=ACCENT):
        self.rect = pygame.Rect(center_x - width // 2, y, width, height)
        self.track_rect = pygame.Rect(self.rect.x + 10, self.rect.centery - 4, self.rect.width - 20, 8)
        self.volume = max(0.0, min(1.0, default_volume))  # Clamp between 0 and 1
        self.dragging = False
        self.color = color
        self.track_color = track_color
        self.accent_color = accent_color
        self.font = pygame.font.Font(None, 24)
        self.slider_width = 20
        self.slider_height = 24

    def handle_event(self, event):
        """Handle mouse events for dragging the slider"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            slider_pos = self._get_slider_pos()
            slider_rect = pygame.Rect(
                slider_pos - self.slider_width // 2,
                self.rect.centery - self.slider_height // 2,
                self.slider_width,
                self.slider_height
            )
            if slider_rect.collidepoint(mouse_pos) or self.track_rect.collidepoint(mouse_pos):
                self.dragging = True
                self._update_volume_from_pos(mouse_pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_volume_from_pos(event.pos[0])
            return True
        return False

    def _update_volume_from_pos(self, x):
        """Update volume based on mouse x position"""
        track_start = self.track_rect.left
        track_end = self.track_rect.right
        relative_x = max(0, min(1, (x - track_start) / (track_end - track_start)))
        self.volume = relative_x
        # Apply volume to music immediately
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass

    def _get_slider_pos(self):
        """Get the x position of the slider based on current volume"""
        return self.track_rect.left + int(self.volume * (self.track_rect.width))

    def set_volume(self, volume):
        """Set volume programmatically (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass

    def get_volume(self):
        """Get current volume (0.0 to 1.0)"""
        return self.volume

    def draw(self, surface, theme):
        """Draw the volume slider"""
        # Draw label
        label_text = "Volume"
        label_surf = self.font.render(label_text, True, theme.text_color)
        label_y = self.rect.y - 30
        surface.blit(label_surf, (self.rect.x, label_y))

        # Draw track background
        pygame.draw.rect(surface, self.track_color, self.track_rect, border_radius=4)
        
        # Draw filled portion
        filled_width = int(self.volume * self.track_rect.width)
        if filled_width > 0:
            filled_rect = pygame.Rect(self.track_rect.left, self.track_rect.top, filled_width, self.track_rect.height)
            pygame.draw.rect(surface, self.accent_color, filled_rect, border_radius=4)

        # Draw slider handle
        slider_x = self._get_slider_pos()
        slider_y = self.rect.centery
        slider_rect = pygame.Rect(
            slider_x - self.slider_width // 2,
            slider_y - self.slider_height // 2,
            self.slider_width,
            self.slider_height
        )
        pygame.draw.rect(surface, self.accent_color, slider_rect, border_radius=6)
        pygame.draw.rect(surface, theme.text_color, slider_rect, width=2, border_radius=6)

        # Draw volume percentage
        volume_text = f"{int(self.volume * 100)}%"
        volume_surf = self.font.render(volume_text, True, theme.text_color)
        volume_x = self.rect.right - volume_surf.get_width() - 10
        surface.blit(volume_surf, (volume_x, label_y))


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

    def _darken_color(self, color: Tuple[int, int, int], factor: float = 0.75) -> Tuple[int, int, int]:
        """Darken a color by multiplying RGB values by factor"""
        return tuple(max(0, int(c * factor)) for c in color)

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, mouse_pos: Tuple[int, int]):
        if not self.enabled:
            color = GRAY
        elif self.is_hovered(mouse_pos):
            # Darken the base color when hovered instead of using hover_color
            color = self._darken_color(self.color, 0.7)
        else:
            color = self.color

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

class RulesScreen:
    """
    RulesScreen: 8 pages, large image center, description text at left,
    prev/next buttons at right, page indicators below image, and Back button.
    - To provide images: put assets/rules/1.png, 2.png, ... N.png (or page1.png ... pageN.png)
    - To set text for pages, call menu.rules_screen.set_page_text(idx, lines)
    """
    def __init__(self, owner, num_pages: int = 8, assets_dir=os.path.abspath("assets/rules")):
        self.owner = owner
        self.screen = getattr(owner, "screen", None)
        self.W = getattr(owner, "W", 1280)
        self.H = getattr(owner, "H", 720)
        self.font = getattr(owner, "font_normal", pygame.font.SysFont("consolas", 20))
        self.font_small = getattr(owner, "font_small", pygame.font.SysFont("consolas", 16))
        self.font_big = getattr(owner, "font_big", pygame.font.SysFont("consolas", 28, bold=True))
        # Ensure assets_dir is an absolute path
        self.assets_dir = os.path.abspath(assets_dir)

        self.num_pages = num_pages
        self.pages = [ {"image": None, "text": []} for _ in range(self.num_pages) ]
        self.current = 0

        # Try to load images named 1.png, 2.png, ... N.png (or page1.png, page2.png, ... pageN.png as fallback)
        for i in range(self.num_pages):
            # First try: 1.png, 2.png, 3.png (matching actual files)
            p = os.path.join(self.assets_dir, f"{i+1}.png")
            # Fallback: page1.png, page2.png, page3.png (for backward compatibility)
            if not os.path.exists(p):
                p = os.path.join(self.assets_dir, f"page{i+1}.png")
            print("Checking:", p, os.path.exists(p))

            if os.path.exists(p):
                try:
                    img = pygame.image.load(p).convert_alpha()
                    self.pages[i]["image"] = img
                except Exception:
                    self.pages[i]["image"] = None
            else:
                self.pages[i]["image"] = None  # will use placeholder

        self._last_mouse_pressed = False
        self._back_rect = None
        self._left_btn_rect = None
        self._right_btn_rect = None
        self._page_indicator_positions = []

    def set_page_text(self, idx: int, lines: list):
        if 0 <= idx < self.num_pages:
            self.pages[idx]["text"] = list(lines)

    def set_page_image(self, idx: int, path: str):
        if 0 <= idx < self.num_pages and os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                self.pages[idx]["image"] = img
            except Exception:
                pass

    def layout(self):
        self.screen = getattr(self.owner, "screen", self.screen)
        if self.screen:
            self.W, self.H = self.screen.get_size()

        gap = 30
        # Reduced layout: smaller text and image areas
        text_w = min(400, int(self.W * 0.30))
        img_w = min(500, int(self.W * 0.35))
        img_h = min(400, int(self.H * 0.55))
        
        # Calculate total width of content panel (text + gap + image)
        panel_content_w = text_w + gap + img_w
        panel_w = panel_content_w + 40  # Add padding for panel
        panel_h = img_h + 30  # Add padding for panel
        
        # Center the panel on screen
        panel_x = (self.W - panel_w) // 2
        panel_y = max(60, int(self.H * 0.08))
        
        # Calculate positions relative to centered panel
        content_start_x = panel_x + 20  # Start after panel padding
        
        # Text area: smaller
        self.text_rect = pygame.Rect(content_start_x, panel_y + 15, text_w, img_h)
        # Image area: smaller
        self.image_rect = pygame.Rect(self.text_rect.right + gap, panel_y + 15, img_w, img_h)
        
        # Store panel dimensions and center for use in drawing
        self.panel_x = panel_x
        self.panel_y = panel_y
        self.panel_w = panel_w
        self.panel_h = panel_h
        self.panel_center_x = panel_x + panel_w // 2
        self.panel_bottom = panel_y + panel_h

        # Page indicators: centered relative to panel (not image)
        indicators_y = self.panel_bottom + 8
        indicator_gap = 18
        indicator_total_w = self.num_pages * 28 + (self.num_pages - 1) * indicator_gap
        start_ind_x = self.panel_center_x - indicator_total_w // 2
        self._page_indicator_positions = []
        for i in range(self.num_pages):
            x = start_ind_x + i * (28 + indicator_gap)
            r = pygame.Rect(x, indicators_y, 28, 28)
            self._page_indicator_positions.append(r)

        # Navigation buttons (left/right arrows) - positioned between indicators and Back button
        btn_size = 56
        nav_y = indicators_y + 40  # Below indicators
        nav_gap = 20
        nav_total_w = btn_size * 2 + nav_gap
        nav_start_x = self.panel_center_x - nav_total_w // 2
        self._left_btn_rect = pygame.Rect(nav_start_x, nav_y, btn_size, btn_size)
        self._right_btn_rect = pygame.Rect(nav_start_x + btn_size + nav_gap, nav_y, btn_size, btn_size)

        # Back button: centered relative to panel, below navigation arrows
        back_w, back_h = 280, 52
        back_x = self.panel_center_x - back_w // 2
        back_y = nav_y + btn_size + 20  # Below navigation arrows
        self._back_rect = pygame.Rect(back_x, back_y, back_w, back_h)

    def _draw_button(self, rect: pygame.Rect, label: str = "", hover=False, arrow=None):
        theme = self.owner._get_current_theme()
        accent_color = getattr(theme, "accent_color", ACCENT)
        
        # Use accent color for buttons, darker when hovered
        if hover:
            # Darken the accent color when hovered
            bg = tuple(max(0, int(c * 0.7)) for c in accent_color)
        else:
            bg = accent_color
        
        pygame.draw.rect(self.screen, (20, 20, 20), rect.move(3,3), border_radius=8)  # shadow
        pygame.draw.rect(self.screen, bg, rect, border_radius=8)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=8)  # white border

        if arrow in ("left","right"):
            cx, cy = rect.center
            s = rect.w // 3
            if arrow == "left":
                points = [(cx + s//2, cy - s), (cx + s//2, cy + s), (cx - s, cy)]
            else:
                points = [(cx - s//2, cy - s), (cx - s//2, cy + s), (cx + s, cy)]
            # Use white/light color for arrow on dark background
            pygame.draw.polygon(self.screen, (255, 255, 255), points)
        else:
            # Use white/light color for text on dark background
            lab_s = self.font.render(label, True, (255, 255, 255))
            self.screen.blit(lab_s, lab_s.get_rect(center=rect.center))

    def _draw_image_placeholder(self, rect: pygame.Rect, page_index: int):
        theme = self.owner._get_current_theme()
        pygame.draw.rect(self.screen, (50,50,50), rect.move(6,6), border_radius=10)  # shadow
        pygame.draw.rect(self.screen, (240,240,240), rect, border_radius=10)
        pygame.draw.rect(self.screen, getattr(theme, "accent_color", ACCENT), rect, width=3, border_radius=10)
        txt = self.font_big.render(f"Page {page_index+1}", True, getattr(theme, "text_color", BLACK))
        self.screen.blit(txt, txt.get_rect(center=rect.center))

    def update_and_draw(self):
        if not self.screen:
            return

        self.layout()
        theme = self.owner._get_current_theme()

        # Draw panel using stored dimensions (centered on screen)
        # Use dark background with slight transparency for better contrast
        panel = pygame.Surface((self.panel_w, self.panel_h), pygame.SRCALPHA)
        panel.fill((30, 30, 35, 220))  # Dark gray-black with transparency
        self.screen.blit(panel, (self.panel_x, self.panel_y))

        page = self.pages[self.current]
        if page.get("image"):
            img = page["image"]
            iw, ih = img.get_size()
            # Calculate scale to fit within image_rect while maintaining aspect ratio
            scale = min(self.image_rect.w / iw, self.image_rect.h / ih)
            # Don't scale up, only scale down if needed
            scale = min(scale, 1.0)
            new_size = (max(1, int(iw*scale)), max(1, int(ih*scale)))
            img_s = pygame.transform.smoothscale(img, new_size)
            # Center image within image_rect
            img_r = img_s.get_rect(center=self.image_rect.center)
            
            # Draw shadow for image
            shadow_rect = img_r.move(5, 5)
            shadow = pygame.Surface((img_r.width, img_r.height), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, 80))
            self.screen.blit(shadow, shadow_rect)
            
            # Draw image with border - ensure it's centered in image_rect
            self.screen.blit(img_s, img_r)
            pygame.draw.rect(self.screen, getattr(theme, "accent_color", ACCENT), img_r, width=2, border_radius=8)
        else:
            self._draw_image_placeholder(self.image_rect, self.current)

        # Heading
        heading = self.font_big.render(f"Rule — Page {self.current+1}", True, (240, 240, 240))
        heading_y = self.text_rect.y + 10
        self.screen.blit(heading, (self.text_rect.x + 10, heading_y))
        
        # Text content with word wrapping and padding
        text_lines = self.pages[self.current].get("text", [])
        if not text_lines:
            # Show placeholder if no text
            placeholder = self.font_small.render("No text content available for this page.", True, (200, 200, 200))
            self.screen.blit(placeholder, (self.text_rect.x + 10, heading_y + 50))
        
        y = heading_y + 50
        line_h = 26
        text_x = self.text_rect.x + 15
        max_width = self.text_rect.width - 30
        
        for line in text_lines:
            # Word wrap if line is too long
            words = line.split(' ')
            current_line = ""
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_surf = self.font.render(test_line, True, (240, 240, 240))
                if test_surf.get_width() <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        txt_surf = self.font.render(current_line, True, (240, 240, 240))
                        self.screen.blit(txt_surf, (text_x, y))
                        y += line_h
                    current_line = word
            
            # Draw remaining line
            if current_line:
                txt_surf = self.font.render(current_line, True, (240, 240, 240))
                self.screen.blit(txt_surf, (text_x, y))
                y += line_h
            
            # Stop if text goes beyond text area
            if y > self.text_rect.bottom - 20:
                break

        mouse = pygame.mouse.get_pos()
        
        # Draw page indicators first (top)
        for i, r in enumerate(self._page_indicator_positions):
            active = (i == self.current)
            if active:
                col = getattr(theme, "accent_color", ACCENT)
                num_col = (255, 255, 255)  # white text for active indicator
            else:
                col = (100, 100, 100)  # dark gray for inactive
                num_col = (180, 180, 180)  # light gray text for inactive
            pygame.draw.circle(self.screen, col, r.center, r.w//2)
            n_s = self.font_small.render(str(i+1), True, num_col)
            self.screen.blit(n_s, n_s.get_rect(center=r.center))

        # Draw navigation arrows (middle, between indicators and back button)
        left_hover = self._left_btn_rect.collidepoint(mouse)
        right_hover = self._right_btn_rect.collidepoint(mouse)
        self._draw_button(self._left_btn_rect, arrow="left", hover=left_hover)
        self._draw_button(self._right_btn_rect, arrow="right", hover=right_hover)

        # Draw back button (bottom)
        back_hover = self._back_rect.collidepoint(mouse)
        accent_color = getattr(theme, "accent_color", ACCENT)
        
        # Use accent color for Back button, darker when hovered
        if back_hover:
            back_bg = tuple(max(0, int(c * 0.7)) for c in accent_color)
        else:
            back_bg = accent_color
        
        pygame.draw.rect(self.screen, (20, 20, 20), self._back_rect.move(3,3), border_radius=10)  # shadow
        pygame.draw.rect(self.screen, back_bg, self._back_rect, border_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), self._back_rect, width=2, border_radius=10)  # white border
        lab = self.font_big.render("Back", True, (255, 255, 255))  # white text
        self.screen.blit(lab, lab.get_rect(center=self._back_rect.center))

        mouse_pressed = pygame.mouse.get_pressed()[0]
        clicked = mouse_pressed and not self._last_mouse_pressed
        if clicked:
            mpos = pygame.mouse.get_pos()
            if self._left_btn_rect.collidepoint(mpos):
                self.current = (self.current - 1) % self.num_pages
            elif self._right_btn_rect.collidepoint(mpos):
                self.current = (self.current + 1) % self.num_pages
            else:
                for i, r in enumerate(self._page_indicator_positions):
                    if r.collidepoint(mpos):
                        self.current = i
                        break
                if self._back_rect.collidepoint(mpos):
                    # go back to main menu
                    try:
                        self.owner._change_state(MenuState.MAIN)
                    except Exception:
                        # fallback: try any back method
                        if hasattr(self.owner, "back_to_menu"):
                            self.owner.back_to_menu()

        self._last_mouse_pressed = mouse_pressed

        # keyboard support (left/right) with small debounce
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.current = (self.current - 1) % self.num_pages
            pygame.time.delay(120)
        elif keys[pygame.K_RIGHT]:
            self.current = (self.current + 1) % self.num_pages
            pygame.time.delay(120)



class Menu:
    def __init__(self, width: int = 1200, height: int = 700):
        pygame.init()
        icon_image = pygame.image.load(r'assets\images\pieces\pong.ico')
        pygame.display.set_icon(icon_image)
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
        self.theme_manager.set_current_theme(theme_name)

        # Settings
        self.settings = {
            "board_size": prefs.get("board_size", 13),
            "difficulty": prefs.get("difficulty", "medium"),
            "per_move_seconds": prefs.get("per_move_seconds", 20),
            "mode": None,
            "best_of": prefs.get("best_of", 1),  # BO1, BO3, or BO5
            "theme": theme_name,
            "volume": prefs.get("volume", 0.6),
        }
        self._pending_mode = None  # Store mode while selecting BO
        self._saved_difficulty = None  # Store difficulty for pvcpu mode

        # Background
        self.background_image = None
        self._load_background()

        #start music
        self._update_menu_music()

        # Initialize buttons
        self.buttons = {}
        self._init_buttons()
        
        # Initialize volume slider
        self.volume_slider = None
        self._init_volume_slider()

        self.rules_screen = RulesScreen(self, num_pages=3, assets_dir="assets/rules")
        
        # ========================================================================
        # HƯỚNG DẪN THÊM TEXT CHO CÁC TRANG RULES:
        # ========================================================================
        # Để thêm hoặc chỉnh sửa text cho các trang rules, bạn có thể:
        #
        # 1. Sửa trực tiếp các dòng bên dưới (từ dòng set_page_text):
        #    - set_page_text(0, [...]) -> Text cho trang 1
        #    - set_page_text(1, [...]) -> Text cho trang 2
        #    - set_page_text(2, [...]) -> Text cho trang 3
        #
        # 2. Mỗi trang nhận một danh sách các chuỗi (list of strings)
        #    - Mỗi chuỗi là một dòng text
        #    - Để tạo dòng trống, dùng chuỗi rỗng: ""
        #    - Text sẽ tự động xuống dòng nếu quá dài
        #
        # 3. Ví dụ:
        #self.rules_screen.set_page_text(0, [
        #    "Tiêu đề trang 1",
        #    "",
        #    "Nội dung dòng 1",
        #    "Nội dung dòng 2"
        #])
        #
        # 4. Bạn cũng có thể thêm text từ file hoặc từ database bằng cách
        #    gọi self.rules_screen.set_page_text() ở bất kỳ đâu trong code
        # ========================================================================
        
        # Text mặc định cho các trang rules
        self.rules_screen.set_page_text(0, [
            "Game Objective:",

            "Gomoku is a classic board game.",
            "A player wins by getting",
            "five stones in a row,",
            "horizontally, vertically, or diagonally.",

            "Basic Rules:",
            "• Players take turns placing a stone",
            "• Stones cannot be placed on",
            "• an occupied spot",
            "• Time limit for each move"
        ])
        
        self.rules_screen.set_page_text(1, [
            "How to win:",
            "A player wins immediately upon placing a mark that completes",
            "an unbroken line of five of their own marks.",
        ])
        
        self.rules_screen.set_page_text(2, [
            "How to Draw?"
        ])

        #exit confirming
        self._confirming_exit = False
        self._exit_yes_btn: Optional[Button] = None
        self._exit_no_btn: Optional[Button] = None

        # Credits image
        self.credit_image = None
        self._load_credit_image()

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

    def _load_credit_image(self):
        """Load credit image from assets/credit folder"""
        credit_dir = os.path.join("assets", "credit")
        if not os.path.exists(credit_dir):
            print(f"[Menu] Credit directory not found: {credit_dir}")
            return
        
        # Look for image files in the credit folder
        image_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
        credit_files = [f for f in os.listdir(credit_dir) 
                       if f.lower().endswith(image_extensions)]
        
        if not credit_files:
            print(f"[Menu] No image files found in {credit_dir}")
            return
        
        # Load the first image found
        credit_path = os.path.join(credit_dir, credit_files[0])
        try:
            self.credit_image = pygame.image.load(credit_path).convert_alpha()
            print(f"[Menu] Credit image loaded: {credit_path}")
        except Exception as e:
            print(f"[Menu] Failed to load credit image: {e}")
            self.credit_image = None

    def _set_theme(self, theme_name: str):
        theme = self.theme_manager.get_theme(theme_name)
        if not theme or not getattr(theme, "selectable", True):
            return  # ignore music-only or invalid themes
        self.theme_manager.set_current_theme(theme_name)
        self.settings["theme"] = theme_name
        self._load_background()
        self._update_menu_music()
        self._init_buttons()
        self._init_volume_slider()

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
                # Use saved volume or default
                volume = self.settings.get("volume", 0.6)
                pygame.mixer.music.set_volume(volume)
                self._current_music_theme = self.theme_manager.current_theme_name
                print(f"[Menu] Now looping music: {music_path} at volume {volume}")
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
                   lambda: self._change_state(MenuState.BO_SELECT, mode="pvp"), color=GREEN, hover_color=(120, 255, 120), text_color=BLACK),
            Button("Player vs CPU", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._change_state(MenuState.DIFFICULTY), color=BLUE, hover_color=(100, 170, 255),
                   text_color=BLACK),
            Button("Settings", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._change_state(MenuState.SETTINGS), color=accent, text_color=text_color),
            Button("Rules", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._change_state(MenuState.RULES), color=accent, text_color=text_color),
            Button("Credits", center_x, start_y + spacing * 4, btn_width, btn_height,
                   lambda: self._change_state(MenuState.CREDITS), color=accent, text_color=text_color),
            Button("Exit", center_x, start_y + spacing * 5, btn_width, btn_height,
                   self._request_exit, color=RED, hover_color=(255, 100, 100), text_color=BLACK),

        ]

        # BO Selection (Best Of)
        self.buttons[MenuState.BO_SELECT] = [
            Button("BO1 (Single Game)", center_x, start_y, btn_width, btn_height,
                   lambda: self._set_best_of(1), color=GREEN, hover_color=(120, 255, 120), text_color=BLACK),
            Button("BO3 (Best of 3)", center_x, start_y + spacing, btn_width, btn_height,
                   lambda: self._set_best_of(3), color=accent, text_color=text_color),
            Button("BO5 (Best of 5)", center_x, start_y + spacing * 2, btn_width, btn_height,
                   lambda: self._set_best_of(5), color=accent, text_color=text_color),
            Button("Back", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._back_from_bo_select(), color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK),
        ]

        # Difficulty Selection (for PvCPU mode - goes to BO selection next)
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
            Button("Volume Setting", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._change_state(MenuState.VOLUME_SETTINGS), color=accent, text_color=text_color),
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
            Button("Back", center_x, start_y + spacing * 3, btn_width, btn_height,
                   lambda: self._change_state(MenuState.MAIN), color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK),
        ]

        # Time Selection
        """self.buttons[MenuState.TIME_SELECT] = [
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
        ]"""
        # field at the same x/y as your first button
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

        # Volume Settings Menu
        self.buttons[MenuState.VOLUME_SETTINGS] = [
            Button("Back", center_x, start_y + spacing * 4, btn_width, btn_height,
                   lambda: self._change_state(MenuState.SETTINGS), color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK),
        ]

    def _init_volume_slider(self):
        """Initialize the volume slider for volume settings menu"""
        btn_width = 500
        center_x = self.W // 2
        slider_y = self.H // 2 - 50  # Center vertically
        theme = self._get_current_theme()
        
        volume = self.settings.get("volume", 0.6)
        self.volume_slider = VolumeSlider(
            center_x,
            slider_y,
            btn_width,
            60,
            default_volume=volume,
            accent_color=theme.accent_color,
            track_color=GRAY
        )
        # Apply volume immediately
        self.volume_slider.set_volume(volume)

    def _back_from_bo_select(self):
        """Handle back button from BO_SELECT - go to DIFFICULTY if pvcpu, else MAIN"""
        if self._pending_mode == "pvcpu":
            self._change_state(MenuState.DIFFICULTY)
        else:
            self._change_state(MenuState.MAIN)

    def _change_state(self, new_state: MenuState, mode: Optional[str] = None):
        self.state = new_state
        if mode:
            self._pending_mode = mode

    def _set_best_of(self, best_of: int):
        """Called when user selects BO1, BO3, or BO5"""
        self.settings["best_of"] = best_of
        mode = self._pending_mode or "pvp"
        self._pending_mode = None
        
        # stop/transition music
        try:
            pygame.mixer.music.fadeout(250)
        except Exception:
            pass

        self.settings["mode"] = mode
        
        # Ensure difficulty is set and valid for pvcpu mode
        if mode == "pvcpu":
            if "difficulty" not in self.settings or self.settings["difficulty"] not in ["easy", "medium", "hard"]:
                # Use saved difficulty or default to medium
                if self._saved_difficulty and self._saved_difficulty in ["easy", "medium", "hard"]:
                    self.settings["difficulty"] = self._saved_difficulty
                else:
                    self.settings["difficulty"] = "medium"
                    print(f"[Menu] Difficulty not set or invalid for pvcpu mode, defaulting to 'medium'")
            # Also update saved difficulty to ensure it's preserved
            if self.settings.get("difficulty") in ["easy", "medium", "hard"]:
                self._saved_difficulty = self.settings["difficulty"]

        # If the external char select helper exists, use it
        if 'show_character_select' in globals() and show_character_select:
            try:
                # Pass difficulty to character select for pvcpu mode
                difficulty_for_char_select = None
                if mode == "pvcpu":
                    difficulty_for_char_select = self.settings.get("difficulty") or self._saved_difficulty or "medium"
                res = show_character_select(mode=mode, difficulty=difficulty_for_char_select)
            except Exception as e:
                print(f"[Menu] show_character_select failed: {e}")
                res = None

            if res is None:
                # user cancelled char select -> go back to BO selection
                self._change_state(MenuState.BO_SELECT, mode=mode)
                return

            # merge returned values into settings (res should contain player names and chars)
            # But preserve difficulty for pvcpu mode (don't let it be overwritten)
            saved_diff = self.settings.get("difficulty") or self._saved_difficulty
            # Remove difficulty from res if it exists and is invalid, so we can preserve the saved one
            if mode == "pvcpu" and res.get("difficulty") not in ["easy", "medium", "hard"]:
                res.pop("difficulty", None)  # Remove invalid difficulty from res
            self.settings.update(res)
            # make sure mode/difficulty are set (preserve difficulty for pvcpu)
            self.settings["mode"] = mode
            if mode == "pvcpu":
                # Always preserve difficulty for pvcpu mode - don't let it be None or invalid
                if saved_diff and saved_diff in ["easy", "medium", "hard"]:
                    self.settings["difficulty"] = saved_diff
                elif "difficulty" not in self.settings or self.settings.get("difficulty") not in ["easy", "medium", "hard"]:
                    self.settings["difficulty"] = "medium"
                    print(f"[Menu] Ensuring difficulty is set to 'medium' for pvcpu mode")
                # Final validation - ensure it's always valid
                if self.settings.get("difficulty") not in ["easy", "medium", "hard"]:
                    self.settings["difficulty"] = "medium"
                    print(f"[Menu] Final validation: setting difficulty to 'medium'")

            # Save volume before closing
            if self.volume_slider:
                self.settings["volume"] = self.volume_slider.get_volume()

            # finalize and close menu -> start match
            self.result = self.settings.copy()
            self.running = False
            return

        # fallback: old immediate-start behaviour
        self.result = self.settings.copy()
        self.running = False

    def _set_mode(self, mode: str):
        """
        Called when user chooses Player vs Player from main menu.
        If char selector is available we open it first; otherwise fallback to old behavior.
        """
        # stop/transition music as before
        try:
            pygame.mixer.music.fadeout(250)
        except Exception:
            pass

        self.settings["mode"] = mode

        # If the external char select helper exists, use it
        if 'show_character_select' in globals() and show_character_select:
            try:
                res = show_character_select(mode=mode)
            except Exception as e:
                print(f"[Menu] show_character_select failed: {e}")
                res = None

            if res is None:
                # user cancelled char select -> stay in main menu
                self._change_state(MenuState.MAIN)
                return

            # merge returned values into settings (res should contain player names and chars)
            self.settings.update(res)
            # make sure mode/difficulty are set
            self.settings["mode"] = mode
            if "difficulty" not in self.settings:
                self.settings["difficulty"] = self.settings.get("difficulty", None)

            # Save volume before closing
            if self.volume_slider:
                self.settings["volume"] = self.volume_slider.get_volume()

            # finalize and close menu -> start match
            self.result = self.settings.copy()
            self.running = False
            return

        # fallback: old immediate-start behaviour
        self.result = self.settings.copy()
        self.running = False


    def _set_difficulty(self, difficulty: str):
        """
        Called when user selects difficulty from DIFFICULTY menu (Player vs CPU).
        Now goes to BO selection first, then character select.
        """
        # Validate difficulty
        if difficulty not in ["easy", "medium", "hard"]:
            print(f"[Menu] Invalid difficulty '{difficulty}', defaulting to 'medium'")
            difficulty = "medium"
        self.settings["difficulty"] = difficulty
        self._saved_difficulty = difficulty  # Save for later use
        self._change_state(MenuState.BO_SELECT, mode="pvcpu")

    def _set_board_size(self, size: int):
        self.settings["board_size"] = size
        self._change_state(MenuState.SETTINGS)

    def _set_time(self, seconds: int):
        self.settings["per_move_seconds"] = seconds
        self._change_state(MenuState.SETTINGS)

    def _save_volume(self):
        """Save current volume to preferences"""
        if self.volume_slider:
            self.settings["volume"] = self.volume_slider.get_volume()
            import storage
            prefs = storage.load_preferences()
            prefs["volume"] = self.settings["volume"]
            storage.save_preferences(prefs)

    def _set_theme_and_back(self, theme_name: str):
        self._set_theme(theme_name)
        self._change_state(MenuState.SETTINGS)

        # ===== Exit confirmation helpers =====
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
        # Save volume before exiting
        if self.volume_slider:
            self.settings["volume"] = self.volume_slider.get_volume()
            import storage
            prefs = storage.load_preferences()
            prefs["volume"] = self.settings["volume"]
            storage.save_preferences(prefs)
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
        elif self.state == MenuState.BO_SELECT:
            # If we came from DIFFICULTY (pvcpu mode), go back to DIFFICULTY
            # Otherwise go back to MAIN (pvp mode)
            if self._pending_mode == "pvcpu":
                self._change_state(MenuState.DIFFICULTY)
            else:
                self._change_state(MenuState.MAIN)
        elif self.state == MenuState.DIFFICULTY:
            self._change_state(MenuState.MAIN)
        elif self.state in [MenuState.SETTINGS, MenuState.RULES]:
            self._change_state(MenuState.MAIN)
        elif self.state in [MenuState.BOARD_SIZE, MenuState.TIME_SELECT, MenuState.THEME_SELECT, MenuState.VOLUME_SETTINGS]:
            self._change_state(MenuState.SETTINGS)
        elif self.state == MenuState.CREDITS:
            self._change_state(MenuState.MAIN)
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
        subtitle = self.font_subtitle.render(text, True, WHITE)  # Use white color for better visibility
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
        
        # Draw dimmed background overlay
        dim = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))  # Dark overlay (alpha 180 out of 255)
        self.screen.blit(dim, (0, 0))
        
        # Draw credit image if available
        if self.credit_image:
            # Scale image to fit screen while maintaining aspect ratio
            img_width, img_height = self.credit_image.get_size()
            
            # Calculate scaling to fit within screen with some margin
            max_width = self.W - 100
            max_height = self.H - 150  # Leave space for back button
            
            scale_w = max_width / img_width
            scale_h = max_height / img_height
            scale = min(scale_w, scale_h)  # Scale to fit, allow upscaling if needed
            
            scaled_width = int(img_width * scale)
            scaled_height = int(img_height * scale)
            
            # Scale the image
            scaled_image = pygame.transform.smoothscale(self.credit_image, (scaled_width, scaled_height))
            
            # Center the image on screen
            img_x = (self.W - scaled_width) // 2
            img_y = (self.H - scaled_height - 50) // 2  # Offset a bit upward for back button
            
            self.screen.blit(scaled_image, (img_x, img_y))
        else:
            # If no image, show a message
            no_image_text = self.font_normal.render("No credit image found in assets/credit folder", True, theme.text_color)
            text_rect = no_image_text.get_rect(center=(self.W // 2, self.H // 2))
            self.screen.blit(no_image_text, text_rect)

        # Draw back button (fixed position at bottom)
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

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._confirming_exit:
                        # modal consumes the click
                        if self._exit_yes_btn and self._exit_yes_btn.is_hovered(mouse_pos):
                            self._exit_yes_btn.action()  # type: ignore
                        elif self._exit_no_btn and self._exit_no_btn.is_hovered(mouse_pos):
                            self._exit_no_btn.action()  # type: ignore
                    else:
                        # Volume slider handling
                        if self.state == MenuState.VOLUME_SETTINGS and self.volume_slider:
                            if self.volume_slider.handle_event(event):
                                self._save_volume()
                        
                        # TIME_SELECT: click to focus the numeric field
                        if self.state == MenuState.TIME_SELECT and hasattr(self, 'time_input'):
                            self.time_input.handle_event(event)

                        # normal buttons
                        if self.state in self.buttons:
                            for button in self.buttons[self.state]:
                                if button.is_hovered(mouse_pos) and button.enabled and button.action:
                                    button.action()
                
                elif event.type == pygame.MOUSEMOTION:
                    # Handle volume slider dragging
                    if self.state == MenuState.VOLUME_SETTINGS and self.volume_slider:
                        if self.volume_slider.handle_event(event):
                            self._save_volume()
                
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    # Handle volume slider release
                    if self.state == MenuState.VOLUME_SETTINGS and self.volume_slider:
                        if self.volume_slider.handle_event(event):
                            self._save_volume()


            self._draw_background()

            if self.state == MenuState.RULES:
                self.rules_screen.update_and_draw()
                self._draw_footer()
            elif self.state == MenuState.CREDITS:
                self._draw_credits()
                self._draw_footer()
            else:
                self._draw_title()
                
                # Draw subtitle for volume settings
                if self.state == MenuState.VOLUME_SETTINGS:
                    self._draw_subtitle("Volume Setting", 170)
                elif self.state == MenuState.BO_SELECT:
                    mode_text = "Player vs Player" if self._pending_mode == "pvp" else "Player vs CPU"
                    difficulty_text = ""
                    if self._pending_mode == "pvcpu" and self.settings.get("difficulty"):
                        diff = self.settings.get("difficulty", "").capitalize()
                        difficulty_text = f" - {diff} Difficulty"
                    self._draw_subtitle(f"Select Match Format - {mode_text}{difficulty_text}", 170)
                elif self.state == MenuState.DIFFICULTY:
                    self._draw_subtitle("Select Difficulty - Player vs CPU", 170)
                else:
                    self._draw_current_settings()
                
                # TIME_SELECT: draw the numeric input box
                if self.state == MenuState.TIME_SELECT and hasattr(self, 'time_input'):
                    self.time_input.draw(self.screen)
                
                # VOLUME_SETTINGS: draw the volume slider
                if self.state == MenuState.VOLUME_SETTINGS and self.volume_slider:
                    theme = self._get_current_theme()
                    self.volume_slider.draw(self.screen, theme)

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