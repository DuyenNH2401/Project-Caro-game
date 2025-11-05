import pygame, time
from ui import UI
from ai import CPU

class UICPU(UI):
    def __init__(self, engine, cpu_difficulty="easy"):
        super().__init__(engine)
        cpu_piece = engine.players[1].piece if engine.players[1].nickname.lower() == "cpu" else "O"
        self.cpu = CPU(cpu_difficulty, piece=cpu_piece)
        self.last_cpu_move_time = 0.0
        self._start_difficulty_music()

    def run(self):
        running = True
        if not hasattr(self, "place_block_mode"):
            self.place_block_mode = False

        while running:
            dt = self.clock.tick(60) / 1000.0
            st = self.engine.state
            cur = self.engine.current_player()
            is_cpu = (cur.nickname.lower() == "cpu")

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._request_exit()

                elif event.type == pygame.KEYDOWN and self._confirming:
                    if event.key in (pygame.K_RETURN, pygame.K_y):
                        self._confirm_yes()
                    elif event.key in (pygame.K_ESCAPE, pygame.K_n):
                        self._cancel_confirm()
                    continue  # modal eats keys

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._request_exit()

                    elif event.key == pygame.K_r:
                        self._request_restart()

                    elif event.key == pygame.K_LEFTBRACKET:
                        self._change_board_size(-1)
                    elif event.key == pygame.K_RIGHTBRACKET:
                        self._change_board_size(1)
                    elif event.key == pygame.K_t:
                        self._toggle_theme()

                    elif event.key == pygame.K_b:
                        if not is_cpu:
                            self.place_block_mode = not self.place_block_mode
                            self.note("Block mode: ON" if self.place_block_mode else "Block mode: OFF")
                        else:
                            self.note("Hold up — CPU’s turn. Wait to block.")

                    elif event.key == pygame.K_u:
                        if self.engine.undo_opponent_last_move():
                            self.note("Undid (spent 1 skill).")
                            self.place_block_mode = False
                        else:
                            self.note("Cannot undo (no point or no CPU move).")

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._confirming:
                        pos = pygame.mouse.get_pos()
                        if self._confirm_yes_rect and self._confirm_yes_rect.collidepoint(pos):
                            self._confirm_yes()
                        elif self._confirm_no_rect and self._confirm_no_rect.collidepoint(pos):
                            self._cancel_confirm()
                        continue

                    pos = pygame.mouse.get_pos()
                    rc = self.pixel_to_cell(*pos)
                    if not rc:
                        continue

                    r, c = rc
                    if not is_cpu:
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
                                self.note(f"You placed at {(r, c)}")
                            else:
                                self.note("Invalid move.")
                    else:
                        pass  # ignore clicks on CPU turn

            # CPU move — paused while modal is open
            if is_cpu and not st.winner_piece and not self._confirming:
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

            self._draw_confirm_modal()  # on top

            pygame.display.flip()

            if st.winner_piece and not self._winner_music_played:
                self._winner_music_played = True
                self._play_winner_music(st.winner_piece)

            if self._leave_requested:
                running = False

        self._stop_music()
        pygame.quit()

