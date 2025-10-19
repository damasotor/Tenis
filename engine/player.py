import os
import math
import random
import pygame
from engine.game_object import GameObject
from engine.utils.screen import world_to_screen  # proyección isométrica

# ⚙️ parámetros tunables centralizados (colisiones)
try:
    from engine.config.collisions import (
        BODY_W_SCALE, BODY_H_SCALE, BODY_Y_OFFSET,
        RACKET_W_SCALE, RACKET_H_SCALE, RACKET_Y_OFFSET
    )
except Exception:
    BODY_W_SCALE, BODY_H_SCALE, BODY_Y_OFFSET = 0.55, 0.80, 4
    RACKET_W_SCALE, RACKET_H_SCALE, RACKET_Y_OFFSET = 0.40, 0.28, -6

# ⚙️ controles de golpe
try:
    from engine.config.controls import KEY_FLAT, KEY_TOPSPIN, KEY_SLICE
except Exception:
    KEY_FLAT, KEY_TOPSPIN, KEY_SLICE = pygame.K_SPACE, pygame.K_z, pygame.K_x

# ⚙️ física de spin
try:
    from engine.config.physics import SPIN_TOPSPIN, SPIN_SLICE, SPIN_FLAT
except Exception:
    SPIN_TOPSPIN, SPIN_SLICE, SPIN_FLAT = +0.9, -0.7, 0.0


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Player(GameObject):
    """
    Player con:
    - Input isométrico (↑↓←→ => diagonales de mundo)
    - Sprint (Shift) y Walk (Ctrl)
    - Dos cajas (cuerpo + raqueta) tunables vía engine/config/collisions.py
    - Golpe direccional + hit flash y selección de efecto (flat/topspin/slice)
    - Animator con FPS adaptables (si existe)
    """

    def __init__(self, x, y, field, jugador2=False):
        json_path = os.path.join('assets', 'sprites', 'player_animation', 'player.json')
        super().__init__(x, y, json_path=json_path)

        self.world_x = float(x)
        self.world_y = float(y)
        self.field = field
        self.is_player2 = jugador2

        # Velocidad base + modificadores
        self.base_speed = 8.0
        self.sprint_mult = 1.35
        self.walk_mult = 0.60

        # Animator (si existe) ajusta FPS de caminata
        self._walk_fps_sprint = 14
        self._walk_fps_normal = 10
        self._walk_fps_slow = 7

        self._last_ix = 0.0
        self._last_iy = 0.0

        # Golpe actual (se setea en mover() leyendo teclas)
        self._shot_mode = "flat"   # "flat" | "topspin" | "slice"

        if not self.rect:
            self.rect = pygame.Rect(self.world_x, self.world_y, 32, 48)

        # Cajas
        self.racket_rect = self.rect.copy()
        self._update_collision_boxes()

        # Animación inicial
        if self.is_player2 and "idle-P2" in self.animations:
            self.current_animation = "idle-P2"
        elif "idle" in self.animations:
            self.current_animation = "idle"
        self.frame_index = 0

        # Swing / flash
        self._swing_cd_ms = 160
        self._last_swing = -10**9
        self._hit_flash_active = False
        self._hit_flash_start = 0
        self._hit_flash_duration = 100  # ms

        self._project_to_screen()

    # ---------------------------
    # Helpers internos
    # ---------------------------
    def _project_to_screen(self):
        if not self.rect:
            return
        iso_x, iso_y = world_to_screen(self.world_x, self.world_y)
        self.rect.center = (iso_x, iso_y)
        self._update_collision_boxes()

    def _update_collision_boxes(self):
        w, h = self.rect.width, self.rect.height

        # cuerpo
        body_w = max(8, int(w * BODY_W_SCALE))
        body_h = max(8, int(h * BODY_H_SCALE))
        body = pygame.Rect(0, 0, body_w, body_h)
        body.centerx = self.rect.centerx
        body.bottom  = self.rect.bottom - BODY_Y_OFFSET
        self.body_rect = body

        # raqueta
        rw = max(4, int(w * RACKET_W_SCALE))
        rh = max(4, int(h * RACKET_H_SCALE))
        racket = pygame.Rect(0, 0, rw, rh)
        racket.centerx = self.rect.centerx
        racket.top = self.rect.top + RACKET_Y_OFFSET
        self.racket_rect = racket

    def _play_swing(self):
        now = pygame.time.get_ticks()
        if (now - self._last_swing) >= self._swing_cd_ms:
            if "swing" in self.animations:
                self.current_animation = "swing"
                self.frame_index = 0
            self._last_swing = now

    def _tune_walk_fps(self, mode: str):
        animator = getattr(self, "_animator", None)
        if not animator or not hasattr(animator, "set_fps"):
            return
        fps = self._walk_fps_normal
        if mode == "sprint":
            fps = self._walk_fps_sprint
        elif mode == "slow":
            fps = self._walk_fps_slow
        for name in (
            "walk-left", "walk-right", "walk-up", "walk-down",
            "walk-left-P2", "walk-right-P2", "walk-up-P2", "walk-down-P2",
        ):
            if name in self.animations:
                animator.set_fps(name, fps)

    # ---------------------------
    # Movimiento (+ leer teclas de golpe)
    # ---------------------------
    def mover(self, teclas):
        moved = False

        if self.is_player2:
            k_left, k_right, k_up, k_down = pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s
        else:
            k_left, k_right, k_up, k_down = pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN

        press_up    = bool(teclas[k_up])
        press_down  = bool(teclas[k_down])
        press_left  = bool(teclas[k_left])
        press_right = bool(teclas[k_right])

        # Modo de velocidad
        press_shift = bool(teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT])
        press_ctrl  = bool(teclas[pygame.K_LCTRL]  or teclas[pygame.K_RCTRL])

        if press_shift:
            speed = self.base_speed * self.sprint_mult
            self._tune_walk_fps("sprint")
        elif press_ctrl:
            speed = self.base_speed * self.walk_mult
            self._tune_walk_fps("slow")
        else:
            speed = self.base_speed
            self._tune_walk_fps("normal")

        # Modo de golpe (se mantiene hasta que sueltes/cambies)
        if teclas[KEY_TOPSPIN]:
            self._shot_mode = "topspin"
        elif teclas[KEY_SLICE]:
            self._shot_mode = "slice"
        elif teclas[KEY_FLAT]:
            self._shot_mode = "flat"

        # Mapeo isométrico a mundo
        dir_x = 0.0
        dir_y = 0.0
        if press_up:
            dir_x += -1.0; dir_y += -1.0
        if press_down:
            dir_x +=  1.0; dir_y +=  1.0
        if press_left:
            dir_x += -1.0; dir_y +=  1.0
        if press_right:
            dir_x +=  1.0; dir_y += -1.0

        if dir_x or dir_y:
            length = math.hypot(dir_x, dir_y)
            if length > 0:
                dir_x /= length; dir_y /= length
            self.world_x += dir_x * speed
            self.world_y += dir_y * speed
            moved = True

            # Selección anim
            use_up   = abs(dir_y) >= abs(dir_x) and dir_y < 0
            use_down = abs(dir_y) >= abs(dir_x) and dir_y > 0
            if use_up and ("walk-up-P2" if self.is_player2 else "walk-up") in self.animations:
                self.current_animation = "walk-up-P2" if self.is_player2 else "walk-up"
            elif use_down and ("walk-down-P2" if self.is_player2 else "walk-down") in self.animations:
                self.current_animation = "walk-down-P2" if self.is_player2 else "walk-down"
            else:
                if dir_x < 0:
                    self.current_animation = "walk-left-P2" if (self.is_player2 and "walk-left-P2" in self.animations) else \
                                             ("walk-left" if "walk-left" in self.animations else self.current_animation)
                elif dir_x > 0:
                    self.current_animation = "walk-right-P2" if (self.is_player2 and "walk-right-P2" in self.animations) else \
                                             ("walk-right" if "walk-right" in self.animations else self.current_animation)
        else:
            self.current_animation = "idle-P2" if (self.is_player2 and "idle-P2" in self.animations) else \
                                     ("idle" if "idle" in self.animations else self.current_animation)

        self._last_ix = dir_x
        self._last_iy = dir_y

        # Limitar por la red
        if self.field and hasattr(self.field, "net_y"):
            net_y = float(self.field.net_y)
            if self.is_player2:
                if self.world_y > net_y - 1:
                    self.world_y = net_y - 1
            else:
                if self.world_y < net_y + 1:
                    self.world_y = net_y + 1

        # Avance de frame por movimiento (fallback sin Animator)
        if moved and self.current_animation in self.animations:
            frames = self.animations[self.current_animation]
            if frames:
                self.frame_index = (self.frame_index + 1) % len(frames)

        self._project_to_screen()

    def update(self):
        self._project_to_screen()
        # Llamar al update de GameObject si existe
        try:
            super().update()  # type: ignore
        except Exception:
            pass
        # hit flash timeout
        if self._hit_flash_active:
            now = pygame.time.get_ticks()
            if now - self._hit_flash_start > self._hit_flash_duration:
                self._hit_flash_active = False

    def draw(self, surface):
        if not self.sprite_sheet or not self.animations or not self.rect:
            return
        frames = self.animations.get(self.current_animation, [])
        if not frames:
            return
        self.frame_index %= len(frames)
        fx, fy, fw, fh = frames[self.frame_index]
        frame_surf = self.sprite_sheet.subsurface(pygame.Rect(fx, fy, fw, fh))

        if self._hit_flash_active:
            flash = frame_surf.copy()
            flash.fill((255, 255, 255, 70), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(flash, self.rect)
        else:
            surface.blit(frame_surf, self.rect)

    # ---------------------------
    # Colisiones con pelota
    # ---------------------------
    def check_ball_collision(self, ball):
        if not ball or not hasattr(ball, "rect"):
            return False

        # 1) Raqueta
        if ball.rect.colliderect(self.racket_rect):
            if ball.rect.centerx < self.racket_rect.centerx:
                ball.rect.right = self.racket_rect.left - 1
            else:
                ball.rect.left = self.racket_rect.right + 1

            # Dirección base del golpe
            h_span = max(1, self.racket_rect.width // 2)
            h_ratio = _clamp((ball.rect.centerx - self.racket_rect.centerx) / h_span, -1.0, 1.0)
            push_x = self._last_ix * 2.0
            push_y = self._last_iy * 1.2
            spin_rand = random.uniform(-0.25, 0.25)  # leve variación

            max_spd = getattr(ball, "_max_speed", 9.0)
            min_spd = getattr(ball, "_min_speed", 2.0)

            vx_new = _clamp((h_ratio * 6.0) + push_x + spin_rand, -max_spd + 0.5, max_spd - 0.5)
            vy_base = 4.0 + abs(push_y) * 1.2
            vy_new = -(max(min_spd + 1.0, vy_base))

            # Asignar spin según modo
            if self._shot_mode == "topspin":
                spin_val = SPIN_TOPSPIN
            elif self._shot_mode == "slice":
                spin_val = SPIN_SLICE
            else:
                spin_val = SPIN_FLAT

            # Audio + feedback
            if hasattr(ball, "on_racket_hit"):
                ball.on_racket_hit()

            self._hit_flash_active = True
            self._hit_flash_start = pygame.time.get_ticks()

            # Aplicar velocidades y spin
            ball.vx = vx_new
            ball.vy = vy_new
            if hasattr(ball, "apply_shot_spin"):
                ball.apply_shot_spin(spin_val)

            self._play_swing()
            return True

        # 2) Cuerpo (penalización: punto para el rival)
        if ball.rect.colliderect(self.body_rect):
            if ball.rect.centerx < self.body_rect.centerx:
                ball.rect.right = self.body_rect.left - 1
            else:
                ball.rect.left = self.body_rect.right + 1
            if hasattr(ball, "on_body_hit"):
                ball.on_body_hit()

            # Asignar punto al oponente inmediatamente si Game expone point_for
            try:
                if hasattr(ball.game, "point_for"):
                    winner = "P1" if self.is_player2 else "P2"
                    ball.game.point_for(winner)
            except Exception:
                pass
            return True

        return False
