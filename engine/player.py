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

        self.swing_active = False
        self.swing_timer = 0
        self.swing_duration = 600  # milisegundos de ventana para golpear

        # Golpe actual (se setea en mover() leyendo teclas)
        self._shot_mode = "flat"   # "flat" | "topspin" | "slice"

        if not self.rect:
            self.rect = pygame.Rect(self.world_x, self.world_y, 32, 48)

        # Cajas
        self.racket_rect = self.rect.copy()
        self._update_collision_boxes()


        #Colision del jugador
        self.hit_rect = self.rect.copy()
        self.hit_rect.width = self.rect.width * 0.4 #40% del ancho original
        self.hit_rect.height = self.rect.height * 0.6 # 60% del alto original
        self.hit_rect.center = self.rect.center

        #Colision de la raqueta
        self.racket_active = False
        self.racket_width = self.rect.width // 2
        self.racket_height = self.rect.height // 1.3
        self.racket_offset_x = self.rect.width // 3
        self.racket_offset_y = 0
        self.racket_rect = pygame.Rect(0, 0, self.racket_width, self.racket_height)

        # --- Estado del jugador --- 
        self.estado = "idle" 
        self.direccion1 = "right" 
        self.direccion2 = "right" 
        self.anim_timer = 0 
        self.frame_index = 0


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
        self._hit_flash_duration = 600  # ms

        self._project_to_screen()


    def update_racket(self): 
        # Determinar offset horizontal según dirección y golpe
        if self.is_player2:
            mirando = self.direccion2
        else:
            mirando = self.direccion1

        # Distancia base desde el cuerpo
        base_offset = self.racket_offset_x

        # Si está golpeando, movemos más la raqueta hacia afuera
        if self.estado == "golpeando":
            base_offset *= 1.6   # reach aumentado pero razonable
            # Seguridad extra: limitar el reach si alguien lo re-tunea
            base_offset = max(min(base_offset, 2.0), 0.8)

        # Aplicar dirección
        if mirando == "right":
            offset_x = abs(base_offset)
        else:
            offset_x = -abs(base_offset)

        # Actualizar posición de la hitbox
        self.racket_rect.centerx = self.rect.centerx + offset_x
        self.racket_rect.centery = self.rect.centery + self.racket_offset_y
        """
        # Determinar offset horizontal según dirección 
        if (self.is_player2 and self.direccion2 == "right") or (not self.is_player2 and self.direccion1 == "right"):
            offset_x = abs(self.racket_offset_x) 
        else: 
            offset_x = -abs(self.racket_offset_x) 
            
        self.racket_rect.centerx = self.rect.centerx + offset_x 
        self.racket_rect.top = self.rect.top + self.racket_offset_y
        """
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

        # --- 🔁 Offset lateral dinámico según dirección ---
        if self.is_player2:
            mirando = getattr(self, "direccion2", "right")
        else:
            mirando = getattr(self, "direccion1", "right")

        # desplazamiento lateral (en px)
        offset_x = int(w * 0.3)  # podés ajustar 0.3 → cuanto más grande, más se separa del cuerpo

        if mirando == "left":
            racket.centerx = self.rect.centerx - offset_x
        else:
            racket.centerx = self.rect.centerx + offset_x

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

        # --- Animación de golpe --- 
        if self.estado == "golpeando": 
            self.anim_timer += 1 
            frames = self.animations[self.current_animation] 
            anim_length = len(frames) 
            self.frame_index = min(self.anim_timer, anim_length - 1) 
            
            if self.anim_timer >= anim_length: 
                self.estado = "idle" 
                self.anim_timer = 0 
                self.frame_index = 0 
                self.current_animation = "idle-P2" if self.is_player2 else "idle" 
            # --- Dirección de golpe según input ---
            if self.racket_active:
                if not self.is_player2:  # Jugador 1
                    if teclas[pygame.K_LEFT]:
                        self.shot_dir = "left"
                    elif teclas[pygame.K_RIGHT]:
                        self.shot_dir = "right"
                    else:
                        self.shot_dir = "center"
                else:  # Jugador 2 (usa A/D)
                    if teclas[pygame.K_a]:
                        self.shot_dir = "left"
                    elif teclas[pygame.K_d]:
                        self.shot_dir = "right"
                    else:
                        self.shot_dir = "center"
            else:
                self.shot_dir = None
            return

        if self.swing_active:
            if pygame.time.get_ticks() - self.swing_timer > self.swing_duration:
                self.swing_active = False
                self.racket_active = False
                print("⏱️ Fin de ventana de golpe.")


        if self.is_player2:
            k_left, k_right, k_up, k_down, k_swing = pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_f
        else:
            k_left, k_right, k_up, k_down, k_swing = pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_SPACE

        press_up    = bool(teclas[k_up])
        press_down  = bool(teclas[k_down])
        press_left  = bool(teclas[k_left])
        press_right = bool(teclas[k_right])
        press_swing = bool(teclas[k_swing])

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
            dx, dy = world_to_screen(-1, -1)
            dir_x += dx
            dir_y += dy
        if press_down:
            dx, dy = world_to_screen(1, 1)
            dir_x += dx
            dir_y += dy

        # Izquierda/derecha
        if press_left:
            dx, dy = world_to_screen(-1, 1)
            dir_x += dx
            dir_y += dy
        if press_right:
            dx, dy = world_to_screen(1, -1)
            dir_x += dx
            dir_y += dy

        # Normalizar vector para que la diagonal no sea más rápida
        if dir_x != 0 or dir_y != 0:
            length = math.hypot(dir_x, dir_y)
            dir_x /= length
            dir_y /= length

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
                    if "walk-left-P2" in self.current_animation:
                        self.direccion2 = "left"
                    else:
                        self.direccion1 = "left"
                elif dir_x > 0:
                    self.current_animation = "walk-right-P2" if (self.is_player2 and "walk-right-P2" in self.animations) else \
                                             ("walk-right" if "walk-right" in self.animations else self.current_animation)
                    if "walk-right-P2" in self.current_animation:
                        self.direccion2 = "right"
                    else:
                        self.direccion1 = "right"
        else:
            self.current_animation = "idle-P2" if (self.is_player2 and "idle-P2" in self.animations) else \
                                     ("idle" if "idle" in self.animations else self.current_animation)

        self._last_ix = dir_x
        self._last_iy = dir_y

        # --- Golpe --- 
        if press_swing: 
            self.estado = "golpeando" 
            self.racket_active = True 

            self.swing_active = True
            self.swing_timer = pygame.time.get_ticks()
            self.racket_active = True
            print("🏸 Swing iniciado!")
            
            self.anim_timer = 0 
            if self.is_player2: 
                self.current_animation = "stroke-left-P2" if self.direccion2 == "left" else "stroke-right-P2" 
            else: 
                self.current_animation = "stroke-left" if self.direccion1 == "left" else "stroke-right" 
            self.frame_index = 0 
            return # no mover en este frame 
        else: 
            self.racket_active = False

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
            self.frame_index = (self.frame_index + 1) % len(self.animations[self.current_animation])
            #frames = self.animations[self.current_animation]
            #if frames:
            #    self.frame_index = (self.frame_index + 1) % len(frames)

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
    def check_ball_collision(self, ball, tolerance=25):
        """Chequea si la pelota colisiona con la raqueta activa (USANDO COORDENADAS DE PANTALLA)."""
        if not self.racket_active:
            return False

        # Asegurarnos que ball.rect y las propiedades screen_x/screen_y estén actualizadas
        # (Ball.update() debería actualizar rect.center usando screen_x/screen_y)
        try:
            bx = int(getattr(ball, "screen_x"))
            by = int(getattr(ball, "screen_y"))
        except Exception:
            # fallback si no existen las propiedades
            bx = int(ball.rect.centerx)
            by = int(ball.rect.centery)

        r = getattr(ball, "radio", 10)
        ball_2d_rect = pygame.Rect(bx - r, by - r, r*2, r*2)

        # Debug: ver posiciones en pantalla
        if getattr(self, "_debug_collision", False):
            print(f"📍 [ISO] Player rect: {self.racket_rect} | Ball screen: ({bx},{by})")

        # Solo durante la ventana de swing
        if self.swing_active:
            if ball_2d_rect.colliderect(self.racket_rect):
                print("🔥 Colisión detectada entre raqueta y pelota!")
                if(self.is_player2):
                    zone = self.direccion2 or random.choice(["left", "center", "right"])
                else:
                    zone = self.direccion1 or random.choice(["left", "center", "right"])

                # Pasamos la posición del jugador en MUNDO (world_x/world_y) para calcular la dirección del tiro
                ball.hit_by_player((self.world_x, self.world_y), zone)
                print(f"💥 Golpe hacia zona: {zone}")
                self.swing_active = False
                self.racket_active = False
                return True

        # debug de distancia (útil si querés ajustar tolerancia)
        # calcular distancia en pantalla entre centros:
        dx = (self.racket_rect.centerx - bx)
        dy = (self.racket_rect.centery - by)
        dist = (dx*dx + dy*dy) ** 0.5
        # ajustá tolerancia si querés
        # print(f"💨 Sin colisión con pelota. Distancia pantalla={dist:.1f}, tolerancia=25")
        return False

