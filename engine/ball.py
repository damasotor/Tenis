import math
import random
from typing import Tuple

import pygame

try:
    from engine.utils.screen import ALTO, ANCHO, screen_to_world
except ImportError:
    ANCHO, ALTO = 800, 600
    def screen_to_world(x, y): return x, y

SPIN_GRAVITY_SCALE, SPIN_DRIFT_SCALE, SPIN_DECAY = 0.12, 0.06, 0.96
GRAVEDAD = -0.5
COEF_REBOTE = 0.7
FACTOR_ISO_X = 0.5
FACTOR_ISO_Y = 0.3


# ----------------- HELPERS -----------------
def world_to_iso(x: float, y: float, z: float = 0.0) -> Tuple[float, float]:
    iso_x = x - y
    iso_y = (x + y) * 0.5 - z
    return iso_x, iso_y


# ============================================================
#                         BALL CLASS
# ============================================================
class Ball(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int, game, vx: float, vy: float):
        super().__init__()
        self.game = game

        # Posición
        self.x = x
        self.y = y
        self.z = 80

        # Velocidades
        self.vx = vx
        self.vy = vy
        self.vz = 0.0

        # Visual
        self.radio = 7
        self.spin = 0.0
        self.image = pygame.Surface((self.radio * 2, self.radio * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 255, 255), (self.radio, self.radio), self.radio)
        self.rect = self.image.get_rect()

        # Estado
        self._net_cd_ms = 100
        self._last_net_hit = -10**9
        self.is_serving = False
        self.serve_stage = None
        self.server = None
        self.bounce_count = 0
        self.waiting_hit = False
        self.out_of_bounds = False

        self._squash_timer = 0
        self._squash_duration = 5

    # ============================================================
    #                 SCREEN POSITION PROPERTIES
    # ============================================================
    @property
    def screen_x(self) -> float:
        iso_x, _ = world_to_iso(self.x, self.y, self.z)
        return iso_x + ANCHO // 2

    @property
    def screen_y(self) -> float:
        _, iso_y = world_to_iso(self.x, self.y, self.z)
        return iso_y + ALTO // 3

    # Paneo estéreo
    def _calc_pan(self) -> float:
        W = self.game.PANTALLA.get_width()
        x = self.rect.centerx
        return (x / max(1, W)) * 2.0 - 1.0

    # ============================================================
    #                         AUDIO HELPERS
    # ============================================================
    def _play(self, name: str):
        try:
            self.game.audio.play_sound(name)
        except Exception:
            pass

    def _play_pan(self, name: str):
        try:
            pan = self._calc_pan()
            self.game.audio.play_sound_panned(name, pan)
        except Exception:
            pass


    # ============================================================
    #                  ACTIONS & GAME EVENTS
    # ============================================================
    def start_rally(self):
        pass  # opcional fade de música

    def apply_shot_spin(self, spin_value: float):
        self.spin = float(spin_value)

    def _trigger_squash(self):
        self._squash_timer = self._squash_duration

    def _on_bounce_court(self):
        self._play_pan("bounce_court")
        self._trigger_squash()

    def on_racket_hit(self):
        self._play_pan("hit_racket")

        AMORTIGUACION = 0.65
        self.vy *= -1
        self.vx *= AMORTIGUACION
        self.vy *= AMORTIGUACION

        MIN_VEL_AFTER_HIT = 3.0
        if abs(self.vy) < MIN_VEL_AFTER_HIT:
            self.vy = MIN_VEL_AFTER_HIT * (1 if self.vy >= 0 else -1)

        self._trigger_squash()

    def on_body_hit(self):
        if "net_body" in self.game.audio.sounds:
            self._play_pan("net_body")
        elif "net_touch" in self.game.audio.sounds:
            self._play_pan("net_touch")

        DEAD = 0.25
        self.vx *= -DEAD
        self.vy *= -DEAD
        self._trigger_squash()
        self.on_point_scored()

        try:
            last = getattr(self.game, "last_hitter", None)
            if last == "P1":
                self.game.point_for("P2")
            elif last == "P2":
                self.game.point_for("P1")
            else:
                self.game.point_for("P2")
        except Exception:
            pass

    def on_out(self):
        self._play("out_whistle")

        last = getattr(self.game, "last_hitter", None)
        if hasattr(self.game, "point_for"):
            if last == "P1":
                self.game.point_for("P2")
            elif last == "P2":
                self.game.point_for("P1")
            else:
                self.game.point_for("P2")

    def on_point_scored(self):
        self._play("score_jingle")


    # ============================================================
    #                    RANDOM RALLY LAUNCHER
    # ============================================================
    def launch_toward_random_zone(self):
        """
        Usado al comenzar un rally nuevo.
        Movimiento realista hacia zona aleatoria del cuadro.
        """
        zones = [
            (random.uniform(-40, 60), random.uniform(50, 150)),
            (random.uniform(60, 180), random.uniform(50, 150)),
            (random.uniform(-40, 60), random.uniform(-150, -50)),
            (random.uniform(60, 180), random.uniform(-150, -50)),
        ]

        target_x, target_y = random.choice(zones)

        dx = target_x - self.x
        dy = target_y - self.y
        dist = (dx ** 2 + dy ** 2) ** 0.5 or 1.0

        speed = random.uniform(4.5, 6.0)

        self.vx = dx / dist * speed
        self.vy = dy / dist * speed
        self.vz = random.uniform(5.0, 7.5)

        print(f"[DEBUG] launch_toward_random_zone → "
              f"({target_x:.1f}, {target_y:.1f})  "
              f"vx={self.vx:.2f}, vy={self.vy:.2f}, vz={self.vz:.2f}")


    # ============================================================
    #                         SERVE LOGIC
    # ============================================================
    def prepare_for_serve(self, server, x, y):
        self.is_serving = True
        self.serve_stage = "ready"
        self.server = server

        world_x, world_y = screen_to_world(x, y)
        self.x = world_x
        self.y = world_y
        self.z = 0
        self.vx = self.vy = self.vz = 0

    def start_toss(self, server_id: str, start_x: float, start_y: float):
        self.server_id = server_id
        self.x = start_x
        self.y = start_y
        self.z = 0
        self.vx = 0
        self.vy = 0
        self.vz = 10
        self.serve_stage = "toss"
        self.waiting_hit = True
        self.out_of_bounds = False

    def update_toss(self):
        self.z += self.vz
        self.vz -= 0.6

        if self.vz <= 0 and self.serve_stage == "toss":
            self.serve_stage = "falling"

        if self.z <= 0 and self.waiting_hit:
            self.z = 0
            self.vz = 0
            self.waiting_hit = False
            self.serve_stage = "fault"
            self.on_out()


    # ============================================================
    #                           UPDATE LOOP
    # ============================================================
    def update(self):

        # --- Saque / Toss ---
        if getattr(self, "serve_stage", None) in ("toss", "falling"):
            self.update_toss()
            iso_x, iso_y = world_to_iso(self.x, self.y, self.z)
            self.rect.center = (iso_x + ANCHO // 2, iso_y + ALTO // 3)
            return

        if self.serve_stage == "ready":
            iso_x, iso_y = world_to_iso(self.x, self.y, self.z)
            self.rect.center = (iso_x + ANCHO // 2, iso_y + ALTO // 3)
            return

        if self.serve_stage == "fault":
            return

        # --- Movimiento general ---
        self.x += self.vx
        self.y += self.vy
        self.z += self.vz
        self.vz -= 0.5

        # --- Rebote en cancha ---
        if self.z <= 0:
            self.z = 0
            self.vz = -self.vz * 0.7

            FIELD_LEFT = -50
            FIELD_RIGHT = 250
            FIELD_TOP = -150
            FIELD_BOTTOM = 350

            dentro = FIELD_LEFT <= self.x <= FIELD_RIGHT and FIELD_TOP <= self.y <= FIELD_BOTTOM
            last = getattr(self.game, "last_hitter", None)

            if dentro:
                self.bounce_count += 1
                self._on_bounce_court()

                if self.bounce_count >= 2:
                    if last == "P1": self.game.point_for("P2")
                    elif last == "P2": self.game.point_for("P1")
                    else: self.game.point_for("P2")
                    self.out_of_bounds = True
                    return

            else:
                self.on_out()
                self.out_of_bounds = True
                return

            if abs(self.vz) < 0.8:
                self.vz = 0

        # --- Out más allá de los límites ---
        if self.z == 0 and not self.out_of_bounds:
            if self.x < -50 or self.x > 250 or self.y < -150 or self.y > 350:
                self.out_of_bounds = True
                self.on_out()

        # --- Colisión con red ---
        if hasattr(self.game, "field") and self.z > 0:
            net = self.game.field.net
            now = pygame.time.get_ticks()

            if now >= self._last_net_hit + self._net_cd_ms:
                if net.ball_hits_net((self.x, self.y, self.z), self.radio):
                    self._last_net_hit = now

                    if abs(self.z) < 12 and "net_tape" in self.game.audio.sounds:
                        self._play_pan("net_tape")
                    elif "net_body" in self.game.audio.sounds:
                        self._play_pan("net_body")
                    elif "net_touch" in self.game.audio.sounds:
                        self._play_pan("net_touch")

                    self.vx = 0.0
                    self.vy = 0.0
                    self.vz *= 0.2

                    net_y_pos = 105.0
                    CLEAR = 5.0

                    if self.y > net_y_pos:
                        self.y = net_y_pos + self.radio + CLEAR
                    else:
                        self.y = net_y_pos - (self.radio + CLEAR)

        # --- Actualizar rect ---
        iso_x, iso_y = world_to_iso(self.x, self.y, self.z)
        self.rect.center = (iso_x + ANCHO // 2, iso_y + ALTO // 3)

    # ============================================================
    #                           DRAW
    # ============================================================
    def draw(self, screen):
        sombra_x, sombra_y = world_to_iso(self.x, self.y, 0)
        sombra_x += ANCHO // 2
        sombra_y += ALTO // 3

        sombra_radio = max(1, self.radio - int(self.z * 0.05))
        sombra_color = (50, 50, 50, max(0, 150 - int(self.z * 1.5)))

        sombra_surf = pygame.Surface((sombra_radio * 2, sombra_radio * 2), pygame.SRCALPHA)
        pygame.draw.circle(sombra_surf, sombra_color, (sombra_radio, sombra_radio), sombra_radio)
        screen.blit(sombra_surf, (int(sombra_x - sombra_radio), int(sombra_y - sombra_radio)))

        px, py = self.screen_x, self.screen_y
        pygame.draw.circle(screen, (255, 255, 0), (int(px), int(py)), self.radio)

    # ============================================================
    #                       PLAYER HIT
    # ============================================================
    def hit_by_player(self, player_pos, zone="center", is_player2=False):
        self._play_pan("hit_racket")

        if getattr(self, "serve_stage", None) in ("toss", "falling"):
            self.waiting_hit = False
            self.serve_stage = "served"
            self.start_rally()

        self.bounce_count = 0
        field = self.game.field

        if zone not in field.zones:
            target_x, target_y = 0, 0
        else:
            zx, zy, zw, zh = field.zones[zone]
            target_x = zx + random.uniform(0.2, 0.8) * zw
            target_y = zy + random.uniform(0.2, 0.8) * zh

        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.sqrt(dx**2 + dy**2)
        if dist == 0:
            dist = 1e-5

        base = random.uniform(8, 11)
        boost = 1.5 if base < 9 else 1.0

        self.vx = (dx / dist) * base * boost
        self.vy = (dy / dist) * base * boost
        self.vz = random.uniform(6, 8)
