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
        self.has_hit_this_turn = False
        self.last_ball_side = None

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
        now = time.time()
        if now < self._next_tick:
            class FakeKeys:
                def __getitem__(self, key): return False
            return FakeKeys()
        self._next_tick = now + self.react_ms / 1000.0

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

        # ⚙️ Ajustá esto según la mitad de tu cancha
        net_y = 100

        # Detectar de qué lado está la pelota
        current_side = "top" if by < net_y else "bottom"

        # Si la pelota cambió de lado → resetear el permiso de golpe
        if self.last_ball_side and current_side != self.last_ball_side:
            self.has_hit_this_turn = False

        self.last_ball_side = current_side

        # 🏠 Posición central de referencia (puede ser distinta para cada lado)
        if self.side == "top":
            home_x, home_y = 470, -100   # posición de espera del jugador 2

            #print("JUGADOR IA ", self.player.world_x, self.player.world_y)
        else:
            home_x, home_y = 30, 400   # posición de espera del jugador 1

        # ✅ Si la pelota está en su lado → perseguirla
        if (self.side == "top" and by < net_y) or (self.side == "bottom" and by > net_y):
            if abs(bx - px) > 5:
                if bx > px:
                    keys[pygame.K_d] = True
                else:
                    keys[pygame.K_a] = True

            if abs(by - py) > 5:
                if (self.side == "bottom" and by > py) or (self.side == "top" and by < py):
                    keys[pygame.K_w] = True
                else:
                    keys[pygame.K_s] = True

            dist = hypot(bx - px, by - py)
            if dist < 25 and not self.has_hit_this_turn:
                keys[pygame.K_f] = True
                self.has_hit_this_turn = True

        else:
            # 🧠 Pelota en el otro lado → volver a "home"
            if abs(home_x - px) > 5:
                if home_x > px:
                    keys[pygame.K_d] = True
                else:
                    keys[pygame.K_a] = True

            if abs(home_y - py) > 5:
                if home_y < py:
                    keys[pygame.K_w] = True
                else:
                    keys[pygame.K_s] = True

        # (Opcional) animaciones básicas
        moving = any([keys[pygame.K_w], keys[pygame.K_s], keys[pygame.K_a], keys[pygame.K_d]])
        if hasattr(self.player, "current_animation"):
            if moving:
                anim = "walk-down-P2" if getattr(self.player, "is_player2", False) else "walk-up"
            else:
                anim = "idle-P2" if getattr(self.player, "is_player2", False) else "idle"
            if self.player.current_animation != anim:
                self.player.current_animation = anim
                self.player.frame_index = 0
                self.player.anim_timer = 0

        # 🎮 Devolver objeto tipo pygame.key.get_pressed()
        class FakeKeys:
            def __getitem__(self, key):
                return keys.get(key, False)

        return FakeKeys()
