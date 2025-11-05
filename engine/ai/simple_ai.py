import random
import time
from math import hypot
import pygame

try:
    from engine.utils.screen import screen_to_world
except Exception:
    screen_to_world = None


class SimpleTennisAI:
    def __init__(
        self,
        player,
        ball,
        side: str = "top",
        react_ms: int = 40, #Cuanto más bajo, más rápido
    ):
        self.player = player
        self.ball = ball
        self.side = side
        self.react_ms = react_ms
        self._next_tick = time.time() + self.react_ms / 1000.0

    def _read_ball_world(self):
        if self.ball is None:
            return 0, 0
        if hasattr(self.ball, "world_x") and hasattr(self.ball, "world_y"):
            return float(self.ball.world_x), float(self.ball.world_y)
        try:
            cx, cy = self.ball.rect.center
            if screen_to_world:
                return screen_to_world(cx, cy)
            return float(cx), float(cy)
        except Exception:
            return 0, 0

    def _read_player_world(self):
        if hasattr(self.player, "world_x") and hasattr(self.player, "world_y"):
            return float(self.player.world_x), float(self.player.world_y)
        return 0, 0

    def get_simulated_keys(self):
        # =============================
        # Si todavía no toca actualizar
        # =============================
        now = time.time()
        if now < self._next_tick:
            class FakeKeys:
                def __getitem__(self, key): return False
            return FakeKeys()
        self._next_tick = now + self.react_ms / 1000.0

        # =============================
        # IA: decide teclas a presionar
        # =============================
        keys = {
            pygame.K_w: False,
            pygame.K_s: False,
            pygame.K_a: False,
            pygame.K_d: False,
            pygame.K_f: False,
            pygame.K_RSHIFT: False,
            pygame.K_RCTRL: False,
        }

        bx, by = self._read_ball_world()
        px, py = self._read_player_world()

        # Línea media (ajustá si tu cancha tiene otra Y)
        net_y = 50  # si tu eje y=0 está arriba; si no, poné la mitad de la cancha

        # ✅ Solo moverse si la pelota está de su lado
        if (self.side == "top" and by < net_y) or (self.side == "bottom" and by > net_y):
            # Movimiento horizontal
            if abs(bx - px) > 5:
                if bx > px:
                    keys[pygame.K_d] = True
                else:
                    keys[pygame.K_a] = True

            # Movimiento vertical
            if abs(by - py) > 5:
                if (self.side == "bottom" and by > py) or (self.side == "top" and by < py):
                    keys[pygame.K_w] = True
                else:
                    keys[pygame.K_s] = True

            # Golpear si está cerca
            dist = hypot(bx - px, by - py)
            if dist < 25:
                keys[pygame.K_f] = True

        # =============================
        # Objeto que simula pygame.key.get_pressed()
        # =============================
        class FakeKeys:
            def __getitem__(self, key):
                return keys.get(key, False)

        return FakeKeys()
