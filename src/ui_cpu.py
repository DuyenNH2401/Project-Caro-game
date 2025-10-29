import pygame, time
from ui import UI
from ai import CPU

class UICPU(UI):
    def __init__(self, engine, cpu_difficulty="easy"):
        super().__init__(engine)
        cpu_piece = engine.players[1].piece if engine.players[1].nickname.lower() == "cpu" else "O"
        self.cpu = CPU(cpu_difficulty, piece=cpu_piece)
        self.last_cpu_move_time = 0.0

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            st = self.engine.state
            cur = self.engine.current_player()
            is_cpu = cur.nickname.lower() == "cpu"

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.engine.reset()
                        self.note("Restarted PvCPU match.")
                    elif event.key == pygame.K_LEFTBRACKET:
                        self._change_board_size(-1)
                    elif event.key == pygame.K_RIGHTBRACKET:
                        self._change_board_size(1)
                    elif event.key == pygame.K_t:
                        self._toggle_theme()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not is_cpu:
                    pos = pygame.mouse.get_pos()
                    rc = self.pixel_to_cell(*pos)
                    if rc and self.engine.place_stone(*rc):
                        self.note(f"You placed at {rc}")
                    else:
                        self.note("Invalid move.")

            # CPU move (no skills)
            if is_cpu and not st.winner_piece:
                now = time.time()
                if now - self.last_cpu_move_time > 0.25:
                    r, c = self.cpu.choose_move(st)
                    if r >= 0:
                        self.engine.place_stone(r, c)
                        self.note(f"CPU ({self.cpu.difficulty}) → ({r+1},{c+1})")
                    self.last_cpu_move_time = now

            self.engine.tick(dt)
            self.screen.fill(self.theme["bg"])
            self.draw_grid()
            self.draw_pieces()
            self.draw_hud(dt)
            pygame.display.flip()

        pygame.quit()