from __future__ import annotations
import os, pygame
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


        self.piece_images = {
            'X': self._load_img(os.path.join("assets","images","pieces","X.png")),
            'O': self._load_img(os.path.join("assets","images","pieces","O.png"))
        }
        self.block_img = self._load_img(os.path.join("assets","images","block","hash_block.png"))

        self._start_difficulty_music()


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

            # kill any fanfare, restart BGM
            self._winner_music_played = False
            self._stop_music(150)
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
        mode = self._get_mode()

        # Normalize a few aliases
        mode_alias = {
            "p1v1": "pvp", "pvp_mode": "pvp",
            "ai": "pvcpu", "cpu": "pvcpu", "vs_ai": "pvcpu",
        }
        if mode:
            mode = mode_alias.get(mode, mode)

        # If it's PvP: prefer a dedicated pvp.* track; otherwise stay quiet.
        if mode == "pvp":
            for ext in MUSIC_EXTS:
                path = os.path.join(MUSIC_DIR, "pvp" + ext)
                if os.path.exists(path):
                    return path
            return None  # graceful silence in PvP if no pvp.* file

        # Otherwise (AI game): map difficulty -> file
        diff = self._get_difficulty()
        if not diff:
            return None

        diff_alias = {
            "ez": "easy", "beginner": "easy",
            "normal": "medium", "med": "medium", "mid": "medium",
            "expert": "hard", "insane": "hard"
        }
        diff = diff_alias.get(diff.lower(), diff.lower())
        if diff not in ("easy", "medium", "hard"):
            return None

        for ext in MUSIC_EXTS:
            path = os.path.join(MUSIC_DIR, diff + ext)
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

        # center the board area dynamically
        x = (win_w - size) // 2
        y = (win_h - size + 30) // 2

        return pygame.Rect(x, y, size, size)

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
            r = self.board_rect()
            winner = p1 if p1.piece == st.winner_piece else p2
            win_text = f"Winner: {winner.nickname} ({st.winner_piece}) — Press R to restart"

            accent = self.theme["accent"]
            txt_color = self._contrast_text_for(accent)

            # blink by changing banner brightness
            blink_on = (pygame.time.get_ticks() // 500) % 2 == 0
            glow_alpha = 90 if blink_on else 50

            # center it on the board
            self.font_emoji = pygame.font.SysFont("segoeuisymbol", 23, bold=True)  # Windows
            win_surf = self.font_emoji.render("🏆 " + win_text, True, txt_color)
            banner_rect = pygame.Rect(
                r.centerx - win_surf.get_width() // 2 - 16,
                r.centery - win_surf.get_height() // 2 - 10,
                win_surf.get_width() + 32,
                win_surf.get_height() + 20
            )

            # glowing translucent box + border
            pygame.draw.rect(self.screen, (*accent, glow_alpha), banner_rect, border_radius=12)
            pygame.draw.rect(self.screen, accent, banner_rect, 3, border_radius=12)

            # drop shadow for readability
            shadow = self.font_big.render(win_text, True, (0, 0, 0))
            shadow.set_alpha(0)
            self.screen.blit(shadow, (banner_rect.x + 13, banner_rect.y + 7))
            self.screen.blit(win_surf, (banner_rect.x + 12, banner_rect.y + 5))

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

                    pos = pygame.mouse.get_pos()
                    rc = self.pixel_to_cell(*pos)
                    if rc:
                        r, c = rc
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
            self.draw_grid()
            self.draw_pieces()
            self.draw_hud(dt)

            # draw modal last so it sits on top
            self._draw_confirm_modal()

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