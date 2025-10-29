from __future__ import annotations
import os, pygame
from typing import Tuple, Optional
from models import BOARD_SIZES
from engine import Engine
import storage

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
        self.engine = engine
        self.cell = 40  # px
        self.margin_top = 104
        self.margin_bottom = 54
        self.margin_left = 40
        self.margin_right = 40

        self.theme_name = storage.load_themes().get("theme", "light")
        self.theme = THEMES[self.theme_name]

        self._update_window_size()
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Gomoku — Gokumo UI")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("consolas", 18)
        self.font = pygame.font.SysFont("consolas", 19, bold=True)
        self.font_big = pygame.font.SysFont("consolas", 23, bold=True)
        self.place_block_mode = False
        self.message: Optional[str] = None
        self.message_t = 0.0

        self.piece_images = {
            'X': self._load_img(os.path.join("assets","images","pieces","X.png")),
            'O': self._load_img(os.path.join("assets","images","pieces","O.png"))
        }
        self.block_img = self._load_img(os.path.join("assets","images","block","hash_block.png"))

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
        x = self.margin_left
        y = self.margin_top
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
        pygame.draw.rect(self.screen, self.theme["shadow"], shadow_rect, border_radius=18)
        pygame.draw.rect(self.screen, self.theme["grid"], r, border_radius=18)
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
        hud_rect = pygame.Rect(8, 8, self.W-16, self.margin_top-16)
        surf = pygame.Surface((hud_rect.w, hud_rect.h), pygame.SRCALPHA)
        surf.fill(self.theme["hud_bg"])
        self.screen.blit(surf, (hud_rect.x, hud_rect.y))

        self._draw_text(f"Board: {st.board_size}x{st.board_size}  ( [ / ] để đổi )", 24, 24, self.font, color=self.theme["accent"])
        turn_name = self.engine.current_player().nickname or self.engine.current_player().full_name
        self._draw_text(f"Turn: {turn_name}  Piece: {self.engine.current_player().piece}", 24, 54, self.font, color=self.theme["piece_x"] if self.engine.current_player().piece == "X" else self.theme["piece_o"])
        secs = max(0, int(st.remaining_seconds))
        timetxt = self.font_big.render(f"{secs:02d}", True, self.theme["block"] if secs <= 5 else self.theme["piece_x"])
        self.screen.blit(timetxt, (24, 80))
        p1, p2 = self.engine.players
        self._draw_text(f"{p1.nickname} skill: {p1.skill_points}", 220, 80, self.font, color=self.theme["piece_x"])
        self._draw_text(f"{p2.nickname} skill: {p2.skill_points}", 420, 80, self.font, color=self.theme["piece_o"])
        if st.winner_piece:
            winner = p1 if p1.piece == st.winner_piece else p2
            self._draw_text(f"Winner: {winner.nickname} ({st.winner_piece}) — Nhấn R để chơi lại", 24, self.margin_top-10, self.font_big, color=self.theme["accent"])
        if self.message:
            self.message_t -= dt
            if self.message_t <= 0:
                self.message = None
            else:
                self._draw_text(self.message, 24, self.H - self.margin_bottom - 24, self.font_small, color=self.theme["accent"])
        self._draw_text("LMB: đặt quân | B: block mode | U: undo opp | R: chơi lại", 24, self.H-self.margin_bottom+10, self.font_small, color=self.theme["accent"])
        self._draw_text("T: đổi theme | Esc: thoát", 27, self.H-self.margin_bottom+30, self.font_small, color=self.theme["accent"])

    def _draw_text(self, text: str, x: int, y: int, font: pygame.font.Font, color=None):
        color = color if color is not None else self.theme["piece_x"]
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x,y))

    def note(self, msg: str, t: float = 2.0):
        self.message = msg
        self.message_t = t

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    # Chỉ ESC thì mới thoát
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_b:
                        self.place_block_mode = not self.place_block_mode
                    elif event.key == pygame.K_u:
                        if self.engine.undo_opponent_last_move():
                            self.note("Undid opponent's last move (spent 1 skill).")
                        else:
                            self.note("Cannot undo (no point or no opponent move).")
                    elif event.key == pygame.K_r:
                        self.engine.reset()
                        self.place_block_mode = False
                        self.note("Restarted.")
                    elif event.key == pygame.K_LEFTBRACKET:
                        self._change_board_size(-1)
                    elif event.key == pygame.K_RIGHTBRACKET:
                        self._change_board_size(1)
                    elif event.key == pygame.K_t:
                        self._toggle_theme()  # Chỉ đổi theme, KHÔNG thoát!
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
            pygame.display.flip()
        pygame.quit()

    def _change_board_size(self, delta: int):
        n = self.engine.state.board_size
        sizes = BOARD_SIZES
        idx = max(0, min(len(sizes)-1, sizes.index(n) + delta))
        new_n = sizes[idx]
        if new_n != n:
            self.engine.reset(new_n)
            self._update_window_size()
            self.screen = pygame.display.set_mode((self.W, self.H))
            self.place_block_mode = False
            self.note(f"Board đổi thành {new_n}x{new_n}.")

    def _toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.theme = THEMES[self.theme_name]
        themes = storage.load_themes()
        themes["theme"] = self.theme_name
        storage.save_themes(themes)
        self.note(f"Đã chuyển sang chế độ {'Tối' if self.theme_name == 'dark' else 'Sáng'}.")
