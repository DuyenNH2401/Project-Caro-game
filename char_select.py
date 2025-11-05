# Note: this is an updated version of src/char_select.py with layout fixes to center elements,
# avoid overlap, and keep the thumbnails bar and buttons well spaced.
# Replace your existing file with this content.
from __future__ import annotations
import pygame
import os
from typing import Optional, Tuple, List, Dict

# UI sizes required by you (large = 320x320, thumbs = 40x40)
LARGE_W = 280
LARGE_H = 280
THUMB_W = 40
THUMB_H = 40
THUMBS_GAP = 12
PREVIEW_GAP = 180

# Asset dirs (relative paths used by project)
CHAR_DIR = os.path.join("assets", "images", "characters")
THUMBS_DIR = os.path.join(CHAR_DIR, "thumbs")
LARGE_DIR = os.path.join(CHAR_DIR, "large")
BOT_LARGE = os.path.join(LARGE_DIR, "zzbot.png")


# Simple Button and TextInput helpers (self-contained)
class Button:
    def __init__(self, text: str, x: int, y: int, w: int, h: int, action=None, color=(220,170,60), hover=(255,200,80)):
        self.text = text
        self.rect = pygame.Rect(x, y, w, h)
        self.action = action
        self.color = color
        self.hover = hover
        self.text_color = (30,30,30)

    def draw(self, surf: pygame.Surface, font: pygame.font.Font):
        mouse = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mouse)
        col = self.hover if hovered else self.color
        # shadow
        pygame.draw.rect(surf, (50,50,50), self.rect.move(4,4), border_radius=8)
        pygame.draw.rect(surf, col, self.rect, border_radius=8)
        pygame.draw.rect(surf, (0,0,0), self.rect, 2, border_radius=8)
        txt = font.render(self.text, True, self.text_color)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def is_hovered(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


class TextInput:
    def __init__(self, center_x, y, width, height, default="", placeholder="Name", bg=(255,255,255), text_color=(0,0,0)):
        self.rect = pygame.Rect(center_x - width//2, y, width, height)
        self.bg = bg
        self.text_color = text_color
        self.placeholder = placeholder
        self.font = pygame.font.Font(None, 28)
        self.text = str(default)
        self.active = False
        self.cursor = len(self.text)
        self._blink = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor > 0:
                    self.text = self.text[:self.cursor-1] + self.text[self.cursor:]
                    self.cursor -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor < len(self.text):
                    self.text = self.text[:self.cursor] + self.text[self.cursor+1:]
            elif event.key == pygame.K_LEFT:
                self.cursor = max(0, self.cursor - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor = min(len(self.text), self.cursor + 1)
            else:
                if event.unicode and event.unicode.isprintable():
                    self.text = self.text[:self.cursor] + event.unicode + self.text[self.cursor:]
                    self.cursor += 1
        return False

    def draw(self, surf: pygame.Surface):
        pygame.draw.rect(surf, self.bg, self.rect, border_radius=8)
        pygame.draw.rect(surf, (80,80,80), self.rect, width=2, border_radius=8)
        display = self.text if self.text else self.placeholder
        color = self.text_color if self.text else (120,120,120)
        txt = self.font.render(display, True, color)
        text_x = self.rect.x + 10
        text_y = self.rect.y + (self.rect.h - txt.get_height())//2
        surf.blit(txt, (text_x, text_y))
        if self.active:
            self._blink = (self._blink + 1) % 60
            if self._blink < 30:
                cx = text_x + self.font.size(self.text[:self.cursor])[0]
                pygame.draw.line(surf, self.text_color, (cx, text_y), (cx, text_y + txt.get_height()), 1)

    def get_value(self, fallback=""):
        return self.text if self.text else fallback


# Character select screen class
class CharacterSelect:
    def __init__(self, fullscreen: bool = True, width:int = 1200, height:int = 700):
        pygame.init()
        # remember previous display (to attempt restore when exiting)
        self._prev_screen = pygame.display.get_surface()
        self._prev_size = None
        try:
            if self._prev_screen:
                self._prev_size = self._prev_screen.get_size()
        except Exception:
            self._prev_size = None

        self.fullscreen = fullscreen
        if fullscreen:
            info = pygame.display.Info()
            self.W, self.H = info.current_w or width, info.current_h or height
            # create fullscreen window
            try:
                self.screen = pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN)
            except Exception:
                # fallback to windowed if fullscreen fails
                self.W, self.H = width, height
                self.screen = pygame.display.set_mode((self.W, self.H))
        else:
            self.W, self.H = width, height
            self.screen = pygame.display.set_mode((self.W, self.H))

        # pygame.display.set_caption("Choose Your Fighters")
        self.clock = pygame.time.Clock()

        # fonts
        self.font_title = pygame.font.SysFont("consolas", 48, bold=True)
        self.font_sub = pygame.font.SysFont("consolas", 24, bold=True)
        self.font_normal = pygame.font.SysFont("consolas", 20)

        # load assets
        self.thumb_surfaces: List[Tuple[str, pygame.Surface]] = []
        self.large_surfaces: Dict[str, pygame.Surface] = {}
        self._load_assets()

        # UI state
        self.mode = "pvp"
        self.difficulty: Optional[str] = None
        self.p1_char: Optional[str] = self.thumb_surfaces[0][0] if self.thumb_surfaces else None
        self.p2_char: Optional[str] = self.thumb_surfaces[1][0] if len(self.thumb_surfaces)>1 else "bot"
        self.active_player = 1

        # inputs & buttons (positions assigned on enter)
        self.name_input_p1: Optional[TextInput] = None
        self.name_input_p2: Optional[TextInput] = None
        self.start_btn: Optional[Button] = None
        self.back_btn: Optional[Button] = None

        # transient clickable thumb rects
        self.thumb_clicks: List[Tuple[pygame.Rect, str]] = []

    def _load_assets(self):
        # thumbs
        if os.path.exists(THUMBS_DIR):
            files = sorted([f for f in os.listdir(THUMBS_DIR) if f.lower().endswith(('.png','.jpg','.jpeg'))])
            files = files[:20]
            for t in files:
                ident = os.path.splitext(t)[0]
                path = os.path.join(THUMBS_DIR, t)
                try:
                    surf = pygame.image.load(path).convert_alpha()
                    self.thumb_surfaces.append((ident, surf))
                except Exception as e:
                    print(f"[CharSelect] Failed to load thumb {path}: {e}")
        else:
            print(f"[CharSelect] Thumbs dir not found: {THUMBS_DIR}")

        # large
        if os.path.exists(LARGE_DIR):
            for ident, _ in self.thumb_surfaces:
                p = os.path.join(LARGE_DIR, ident + ".png")
                if os.path.exists(p):
                    try:
                        self.large_surfaces[ident] = pygame.image.load(p).convert_alpha()
                    except Exception:
                        pass
        # bot fallback
        if os.path.exists(BOT_LARGE):
            try:
                self.large_surfaces["bot"] = pygame.image.load(BOT_LARGE).convert_alpha()
            except Exception:
                pass

    def _restore_display(self):
        # Try to restore previous display mode/size if we recorded it
        try:
            if self._prev_size:
                pygame.display.set_mode(self._prev_size)
        except Exception:
            # best-effort only
            pass

    def show(self, mode: str = "pvp", difficulty: Optional[str] = None) -> Optional[Dict]:
        """Main loop. Returns settings dict on Start, None on Back/Cancel."""
        self.mode = mode
        self.difficulty = difficulty
        # defaults
        default_p1 = "You"
        default_p2 = "P2" if mode == "pvp" else "CPU"

        # compute layout top area for two large previews centered horizontally
        # total width is two LARGE + gap; center that block in window
        total_preview_width = LARGE_W * 2 + PREVIEW_GAP
        start_x = max(40, (self.W - total_preview_width) // 2)
        preview_y = 180

        # P1 rect (left)
        p1_rect = pygame.Rect(start_x, preview_y, LARGE_W, LARGE_H)
        # P2 rect (right)
        p2_rect = pygame.Rect(start_x + LARGE_W + PREVIEW_GAP, preview_y, LARGE_W, LARGE_H)

        # centers used for name inputs / toggles — keep them aligned with previews
        p1_cx = p1_rect.centerx
        p2_cx = p2_rect.centerx

        # create inputs & buttons positioned relative to previews
        name_input_w = int(LARGE_W * 1.12)  # slightly wider than preview for comfortable space
        name_input_h = 44
        name_input_y = preview_y - 70  # place above previews, with good spacing

        self.name_input_p1 = TextInput(p1_cx, name_input_y, name_input_w, name_input_h, default=default_p1, placeholder="Player 1")
        self.name_input_p2 = TextInput(p2_cx, name_input_y, name_input_w, name_input_h, default=default_p2, placeholder="Player 2")
        if mode == "pvcpu":
            # enforce CPU name for P2 (not editable)
            self.name_input_p2.text = default_p2
            self.name_input_p2.active = False

        # Back and Start placed with safe margins and centered horizontally for Start
        self.back_btn = Button("Back", 40, 40, 120, 44, color=(180,180,180), hover=(200,200,200))
        self.start_btn = Button("Start Match", self.W//2 - 110, self.H - 90, 220, 56, color=(80,200,80), hover=(120,255,120))

        running = True
        result = None
        while running:
            dt = self.clock.tick(60) / 1000.0
            mouse = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    result = None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # exit char select and restore display
                        running = False
                        result = None
                    elif event.key == pygame.K_F11:
                        # toggle fullscreen - best-effort (recreate display)
                        self.fullscreen = not self.fullscreen
                        try:
                            if self.fullscreen:
                                info = pygame.display.Info()
                                self.W, self.H = info.current_w, info.current_h
                                self.screen = pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN)
                            else:
                                self.W, self.H = 1200, 700
                                self.screen = pygame.display.set_mode((self.W, self.H))
                        except Exception:
                            pass
                    elif event.key == pygame.K_1:
                        self.active_player = 1
                    elif event.key == pygame.K_2:
                        self.active_player = 2
                    else:
                        # forward to text inputs
                        if self.name_input_p1:
                            self.name_input_p1.handle_event(event)
                        # only allow typing in P2 when not pvcpu
                        if self.name_input_p2 and mode != "pvcpu":
                            self.name_input_p2.handle_event(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.start_btn.is_hovered(mouse):
                        # collect settings and return
                        p1_name = self.name_input_p1.get_value("Player 1")
                        p2_name = self.name_input_p2.get_value("Player 2")
                        settings = {
                            "mode": self.mode,
                            "difficulty": self.difficulty,
                            "player1_name": p1_name,
                            "player2_name": p2_name,
                            "p1_char": self.p1_char,
                            "p2_char": (self.p2_char if self.mode == "pvp" else "bot"),
                        }
                        self._restore_display()
                        return settings
                    if self.back_btn.is_hovered(mouse):
                        self._restore_display()
                        return None

                    # click name inputs
                    if self.name_input_p1:
                        self.name_input_p1.handle_event(event)
                    if self.name_input_p2 and mode != "pvcpu":
                        self.name_input_p2.handle_event(event)

                    # thumbnails clicks
                    for rect, ident in list(self.thumb_clicks):
                        if rect.collidepoint(mouse):
                            # if pvcpu and active is 2, ignore (p2 must be bot)
                            if self.mode == "pvcpu" and self.active_player == 2:
                                # ignore
                                pass
                            else:
                                if self.active_player == 1:
                                    self.p1_char = ident
                                else:
                                    self.p2_char = ident
                            break

            # draw UI
            self.screen.fill((34,34,40))
            # Title
            title = self.font_title.render("Choose Your Fighters", True, (240,240,240))
            self.screen.blit(title, title.get_rect(center=(self.W//2, 55)))

            # draw labels for each preview
            # lbl1 = self.font_sub.render("Player 1", True, (220,220,220))
            # lbl2 = self.font_sub.render("Player 2", True, (220,220,220))
            # self.screen.blit(lbl1, (p1_rect.centerx - lbl1.get_width()//2, name_input_y - 36))
            # self.screen.blit(lbl2, (p2_rect.centerx - lbl2.get_width()//2, name_input_y - 36))

            # Draw the name inputs (already centered via center_x)
            if self.name_input_p1:
                self.name_input_p1.draw(self.screen)
            if self.name_input_p2:
                self.name_input_p2.draw(self.screen)

            # toggles P1/P2 near top of previews (small badges)
            toggle_w, toggle_h = 42, 28
            t_y = name_input_y +370
            p1_toggle = pygame.Rect(p1_rect.centerx - toggle_w//2, t_y, toggle_w, toggle_h)
            p2_toggle = pygame.Rect(p2_rect.centerx - toggle_w//2, t_y, toggle_w, toggle_h)
            pygame.draw.rect(self.screen, (220,170,60) if self.active_player==1 else (120,120,120), p1_toggle, border_radius=8)
            pygame.draw.rect(self.screen, (220,170,60) if self.active_player==2 else (120,120,120), p2_toggle, border_radius=8)
            t1 = self.font_normal.render("P1", True, (0,0,0))
            t2 = self.font_normal.render("P2", True, (0,0,0))
            self.screen.blit(t1, t1.get_rect(center=p1_toggle.center))
            self.screen.blit(t2, t2.get_rect(center=p2_toggle.center))

            # preview boxes with border highlight for active player
            border_p1 = (220,170,60) if self.active_player==1 else (60,60,60)
            border_p2 = (220,170,60) if self.active_player==2 else (60,60,60)
            pygame.draw.rect(self.screen, (10,10,10), p1_rect, border_radius=14)
            pygame.draw.rect(self.screen, border_p1, p1_rect, width=4, border_radius=14)
            pygame.draw.rect(self.screen, (10,10,10), p2_rect, border_radius=14)
            pygame.draw.rect(self.screen, border_p2, p2_rect, width=4, border_radius=14)

            # blit large images (scaled precisely to fit interior)
            inner_w, inner_h = LARGE_W - 8, LARGE_H - 8
            # p1
            if self.p1_char and self.p1_char in self.large_surfaces:
                img = self.large_surfaces[self.p1_char]
                img_s = pygame.transform.smoothscale(img, (inner_w, inner_h))
                self.screen.blit(img_s, img_s.get_rect(center=p1_rect.center))
            else:
                thumb = next((s for ident,s in self.thumb_surfaces if ident==self.p1_char), None)
                if thumb:
                    img_s = pygame.transform.smoothscale(thumb, (inner_w, inner_h))
                    self.screen.blit(img_s, img_s.get_rect(center=p1_rect.center))
                else:
                    no = self.font_normal.render("No Image", True, (200,200,200))
                    self.screen.blit(no, no.get_rect(center=p1_rect.center))

            # p2
            if self.mode == "pvcpu" and "bot" in self.large_surfaces:
                img = self.large_surfaces["bot"]
                img_s = pygame.transform.smoothscale(img, (inner_w, inner_h))
                self.screen.blit(img_s, img_s.get_rect(center=p2_rect.center))
            else:
                if self.p2_char and self.p2_char in self.large_surfaces:
                    img = self.large_surfaces[self.p2_char]
                    img_s = pygame.transform.smoothscale(img, (inner_w, inner_h))
                    self.screen.blit(img_s, img_s.get_rect(center=p2_rect.center))
                else:
                    thumb = next((s for ident,s in self.thumb_surfaces if ident==self.p2_char), None)
                    if thumb:
                        img_s = pygame.transform.smoothscale(thumb, (inner_w, inner_h))
                        self.screen.blit(img_s, img_s.get_rect(center=p2_rect.center))
                    else:
                        no = self.font_normal.render("No Image", True, (200,200,200))
                        self.screen.blit(no, no.get_rect(center=p2_rect.center))

            # thumbnails bar - centered and single row with wrapping if window smaller
            thumbs_bar_max_w = self.W - 130
            thumbs_total_w = max(thumbs_bar_max_w, 0)
            thumbs_x = (self.W - thumbs_total_w)//2 + 40
            thumbs_y = self.H - 150
            # container rect
            bar_rect = pygame.Rect((self.W - thumbs_total_w)//2 + 10, thumbs_y - 10, thumbs_total_w, THUMB_H + 28)
            # translucent background for bar
            s = pygame.Surface((bar_rect.w, bar_rect.h), pygame.SRCALPHA)
            s.fill((0,0,0,120))
            self.screen.blit(s, (bar_rect.x, bar_rect.y))

            # hint text above thumbs
            hint = self.font_normal.render(" Press button 1 or 2 to switch.", True, (220,220,220))
            self.screen.blit(hint, hint.get_rect(center=(self.W//2, thumbs_y - 36)))

            # render thumbs into rows but keep bar centered
            x = bar_rect.x + 12
            y = thumbs_y
            self.thumb_clicks = []
            max_x = bar_rect.x + bar_rect.w - 16
            for ident, surf in self.thumb_surfaces:
                thumb_rect = pygame.Rect(x, y, THUMB_W, THUMB_H)
                pygame.draw.rect(self.screen, (30,30,30), thumb_rect, border_radius=8)
                img_s = pygame.transform.smoothscale(surf, (THUMB_W-4, THUMB_H-4))
                self.screen.blit(img_s, img_s.get_rect(center=thumb_rect.center))
                # border if selected
                if ident == self.p1_char or ident == self.p2_char:
                    col = (80,200,80) if ident==self.p1_char else (70,130,220)
                    if ident==self.p1_char and ident==self.p2_char:
                        col = (150,80,200)
                    pygame.draw.rect(self.screen, col, thumb_rect, width=3, border_radius=8)
                self.thumb_clicks.append((thumb_rect.copy(), ident))
                x += THUMB_W + THUMBS_GAP
                if x + THUMB_W > max_x:
                    x = bar_rect.x + 12
                    y += THUMB_H + THUMBS_GAP

            # draw Start / Back
            self.start_btn.draw(self.screen, self.font_normal)
            self.back_btn.draw(self.screen, self.font_normal)

            pygame.display.flip()

        # restore display if we changed it
        self._restore_display()
        return result


# convenience function
def show_character_select(mode: str = "pvp", difficulty: Optional[str] = None, fullscreen: bool = True) -> Optional[Dict]:
    cs = CharacterSelect(fullscreen=fullscreen)
    return cs.show(mode=mode, difficulty=difficulty)


if __name__ == "__main__":
    # quick manual test
    res = show_character_select("pvp", fullscreen=True)
    print("Result:", res)
