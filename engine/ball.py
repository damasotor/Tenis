import os
import json
import math
import random
import collections
from typing import Optional, List, Tuple

import pygame

from engine.utils.screen import ALTO, ANCHO, screen_to_world

TrailPoint = Tuple[int, int]
FrameRect = Tuple[int, int, int, int]

# Helpers opcionales
try:
    from engine.assets.image_loader import load_image as _load_image
except Exception:
    _load_image = None

try:
    from engine.animation.animator import Animator
except Exception:
    Animator = None  # type: ignore

# Física de spin (fallbacks si no existe config)
try:
    from engine.config.physics import (
        SPIN_GRAVITY_SCALE, SPIN_DRIFT_SCALE, SPIN_DECAY
    )
except Exception:
    SPIN_GRAVITY_SCALE, SPIN_DRIFT_SCALE, SPIN_DECAY = 0.12, 0.06, 0.96

def world_to_iso(x: float, y: float, z: float = 0.0) -> Tuple[float, float]:
    """
    Convierte coordenadas del mundo (x, y, z) a coordenadas de pantalla isométricas.
    """
    iso_x = x - y
    iso_y = (x + y) * 0.5 - z
    return iso_x, iso_y

# Parámetros físicos
GRAVEDAD = -0.5
COEF_REBOTE = 0.7
FACTOR_ISO_X = 0.5   # qué tanto se "desplaza" la sombra en X por altura
FACTOR_ISO_Y = 0.3   # qué tanto se "desplaza" la sombra en Y por altura

class Ball(pygame.sprite.Sprite):
    """
    Pelota con:
    - Sprite opcional; fallback a círculo
    - Trail, sombra, squash/stretch
    - Spin con efecto en trayectoria (grav extra/menos y deriva)
    """
    def __init__(self, x: int, y: int, game, vx: float, vy: float):
        super().__init__()
        self.game = game

        # Posición base (x, y) en el suelo
        self.x = x
        self.y = y
        # Altura en el eje vertical (z)
        self.z = 80
        # Velocidades
        self.vx = random.choice([-5, 5])
        self.vy = random.choice([-2, 2])
        self.vz = 0
        # Radio visual
        self.radio = 10
        self.image = pygame.Surface((self.radio * 2, self.radio * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 255, 255), (self.radio, self.radio), self.radio)
        self.rect = self.image.get_rect()
        self.rect.center = (self.screen_x, self.screen_y)

        
        """
        # ----------------- Física -----------------
        # Posición y velocidad en espacio 3D
        self.x = float(x)
        self.y = float(y)
        self.z = 0.0  # altura actual sobre el suelo
        #self.vx = 4.0
        #self.vy = 2.5  # movimiento hacia adelante en la cancha
        #self.vz = -6.0 # impulso inicial hacia arriba
        self.vx = vx
        self.vy = vy
        self._min_speed = 2.0
        self._max_speed = 9.0

        # Spin (valor escalar; + topspin, - slice). Decae cada frame.
        self.spin = 0.0

        # Cooldown para red
        self._net_cd_ms = 90
        self._last_net_hit = -10**9

        # ----------------- Visual -----------------
        self._use_sprite = False
        self._sprite_sheet: Optional[pygame.Surface] = None
        self._animations = collections.defaultdict(list)  # type: ignore
        self._current_anim = "spin"
        self._frame_index = 0
        self._animator: Optional["Animator"] = Animator(default_fps=14) if Animator else None

        # Sombra
        self._shadow_enabled = True
        self._shadow_alpha = 70

        # Trail
        self._trail_enabled = True
        self._trail_len = 10
        self._trail: collections.deque[TrailPoint] = collections.deque(maxlen=self._trail_len)

        # Squash/Stretch
        self._squash_timer = 0
        self._squash_duration = 90
        self._squash_amount = 0.20

        # Imagen / rect
        self._load_sprite_or_fallback()
        self.rect.center = (x, y)

        # Gravedad y rebote
        self.gravity = 0.35     # fuerza de gravedad
        self.bounce_factor = 0.65  # energía retenida al rebotar
        self.ground_y = game.PANTALLA.get_height() * 0.78  # altura del suelo
        
        # Altura vertical (distancia sobre el suelo)
        self.altura = 20.0
        self.vz = -20.0  # velocidad vertical (eje Z)
        self.MAX_ALTURA = 80.0
        """

        # ----------------- Propiedades útiles -----------------
    #@property
    #def radius(self) -> float:
    #    """Radio de la pelota (para colisiones isométricas)."""
    #    return self.rect.width / 2

    #@property
    #def screen_x(self) -> float:
    #    """Posición X en pantalla (centro)."""
    #    return float(self.rect.centerx)

    #@property
    #def screen_y(self) -> float:
    #    """Posición Y en pantalla (centro)."""
    #    return float(self.rect.centery)
    @property
    def screen_x(self) -> float:
        iso_x, iso_y = world_to_iso(self.x, self.y, self.z)
        # centramos en la pantalla
        return iso_x + ANCHO // 2

    @property
    def screen_y(self) -> float:
        iso_x, iso_y = world_to_iso(self.x, self.y, self.z)
        # bajamos un poco para centrar cancha visualmente
        return iso_y + ALTO // 3


    # ----------------- Carga sprite opcional -----------------
    def _load_sprite_or_fallback(self):
        json_path = os.path.join("assets", "sprites", "ball", "ball.json")
        try:
            if not os.path.exists(json_path):
                raise FileNotFoundError

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            sheet_cfg = data.get("spritesheet_path")
            if not sheet_cfg:
                raise ValueError("ball.json sin 'spritesheet_path'")

            base_dir = os.path.dirname(json_path)
            if os.path.isabs(sheet_cfg):
                candidate = os.path.join(base_dir, os.path.basename(sheet_cfg))
            else:
                candidate = os.path.normpath(os.path.join(base_dir, sheet_cfg))
                if not os.path.exists(candidate):
                    candidate = os.path.join(base_dir, os.path.basename(sheet_cfg))

            if not os.path.exists(candidate):
                raise FileNotFoundError(candidate)

            if _load_image:
                self._sprite_sheet = _load_image(candidate)
            else:
                self._sprite_sheet = pygame.image.load(candidate).convert_alpha()

            self._animations = collections.defaultdict(list)
            for anim_name, anim_list in (data.get("animations") or {}).items():
                if not isinstance(anim_list, list):
                    continue
                for s in anim_list:
                    self._animations[anim_name].append((int(s["x"]), int(s["y"]), int(s["width"]), int(s["height"])))

            self._current_anim = "spin" if "spin" in self._animations else list(self._animations.keys())[0]
            first = self._animations[self._current_anim][0]
            fw, fh = first[2], first[3]

            self.image = pygame.Surface((fw, fh), pygame.SRCALPHA)
            self.rect = self.image.get_rect()
            self._use_sprite = True
        except Exception:
            r = 8
            self.image = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (250, 250, 250), (r, r), r)
            self.rect = self.image.get_rect()
            self._use_sprite = False

    # ----------------- API -----------------
    def start_rally(self):
        if hasattr(self.game, "audio"):
            self.game.audio.duck_music(0.18)
            self.game.audio.play_sound("serve")
            self.game.audio.unduck_music()

    def apply_shot_spin(self, spin_value: float):
        """Se llama desde Player al impactar: setea spin inicial del tiro."""
        self.spin = float(spin_value)

    # ----------------- Helpers audio -----------------
    def _calc_pan(self) -> float:
        W = self.game.PANTALLA.get_width()
        x = self.rect.centerx
        return (x / max(1, W)) * 2.0 - 1.0


    def launch_toward_zone(self, zone: str = None, speed: float = 5.0):
        """
        Lanza la pelota hacia una zona del campo rival (izquierda, centro, derecha).
        Si no se indica zona, elige una aleatoria.
        """
        if zone is None:
            zone = random.choice(["izquierda", "centro", "derecha"])

        # Dirección base (en coordenadas del mundo, no pantalla)
        if zone == "izquierda":
            dir_x, dir_y = -1, 1   # hacia arriba-izquierda en mundo (fondo izq)
        elif zone == "derecha":
            dir_x, dir_y = 1, 1    # hacia abajo-derecha en mundo (fondo der)
        else:
            dir_x, dir_y = 0, 1    # recto al fondo

        # Normalizamos para que la velocidad total sea "speed"
        length = (dir_x**2 + dir_y**2) ** 0.5
        self.vx = (dir_x / length) * speed
        self.vy = (dir_y / length) * speed

        # Pequeño impulso inicial en altura
        self.vz = speed * 0.6
        print(f"[DEBUG] Lanzamiento hacia {zone}: vx={self.vx:.2f}, vy={self.vy:.2f}, vz={self.vz:.2f}")
    
    def launch_toward_random_zone(self):
        # Zonas dentro de la cancha (en coordenadas del espacio 3D)
        zones = [
            (random.uniform(100, 400), random.uniform(100, 200)),  # izquierda-delantera
            (random.uniform(400, 700), random.uniform(100, 200)),  # derecha-delantera
            (random.uniform(100, 400), random.uniform(300, 500)),  # izquierda-fondo
            (random.uniform(400, 700), random.uniform(300, 500)),  # derecha-fondo
        ]
        target_x, target_y = random.choice(zones)

        dx = target_x - self.x
        dy = target_y - self.y
        dist = (dx ** 2 + dy ** 2) ** 0.5

        # Escalar velocidades para un vuelo natural
        self.vx = dx / dist * random.uniform(4.5, 6.0)
        self.vy = dy / dist * random.uniform(4.5, 6.0)
        self.vz = -random.uniform(6.0, 9.0)

        print(f"Lanzando hacia zona ({target_x:.1f}, {target_y:.1f}) con vx={self.vx:.2f}, vy={self.vy:.2f}, vz={self.vz:.2f}")
    
    # ----------------- Eventos -----------------
    def _on_bounce_court(self):
        if hasattr(self.game, "audio"):
            self.game.audio.play_sound_panned("bounce_court", self._calc_pan())
        self._trigger_squash()

    def _trigger_squash(self):
        self._squash_timer = self._squash_duration

    def on_racket_hit(self):
        if hasattr(self.game, "audio"):
            cands = [k for k in ("hit_racket", "hit_racket2", "hit_racket3")
                     if k in self.game.audio.sounds]
            key = random.choice(cands) if cands else "hit_racket"
            self.game.audio.play_sound_panned(key, self._calc_pan())

        AMORTIGUACION = 0.65
        self.vy *= -1
        self.vx *= AMORTIGUACION
        self.vy *= AMORTIGUACION

        MIN_VEL_AFTER_HIT = 3.0
        if abs(self.vy) < MIN_VEL_AFTER_HIT:
            self.vy = MIN_VEL_AFTER_HIT * (1 if self.vy >= 0 else -1)

        self._trigger_squash()

    def on_body_hit(self):
        # Choque con cuerpo es “error” del jugador impactado; Game se encarga del punto
        if hasattr(self.game, "audio"):
            self.game.audio.play_sound_panned("bounce_court", self._calc_pan())
        DEAD_BOUNCE_FACTOR = 0.25
        self.vx *= -DEAD_BOUNCE_FACTOR
        self.vy *= -DEAD_BOUNCE_FACTOR
        # Jingle/UI del punto (la asignación la hará Game via Player)
        self.on_point_scored()
        self._trigger_squash()

    def on_out(self):
        # SFX
        if hasattr(self.game, "audio"):
            self.game.audio.play_sound("out_whistle")
            if "crowd_ahh" in self.game.audio.sounds and random.random() < 0.6:
                self.game.audio.play_sound("crowd_ahh")
        # Asignar punto según último que golpeó
        last = getattr(self.game, "last_hitter", None)
        if hasattr(self.game, "point_for"):
            if last == "P1":
                self.game.point_for("P2")
            elif last == "P2":
                self.game.point_for("P1")
            else:
                # Si no sabemos, darle el punto a P2 por defecto para no bloquear el flujo
                self.game.point_for("P2")

    def on_point_scored(self):
        if hasattr(self.game, "audio"):
            self.game.audio.duck_music(0.12)
            self.game.audio.play_sound("score_jingle")
            if "crowd_ooh" in self.game.audio.sounds:
                self.game.audio.play_sound("crowd_ooh")
            self.game.audio.unduck_music()


    def update(self):
        # ===== Movimiento en el mundo =====
        self.x += self.vx
        self.y += self.vy
        self.z += self.vz

        # Gravedad y rebote vertical
        self.vz -= 0.5  # gravedad
        if self.z <= 0:
            self.z = 0
            self.vz = -self.vz * 0.7  # rebote amortiguado
            if abs(self.vz) < 0.8:
                self.vz = 0

        # ===== Límites del campo =====
        FIELD_LEFT = -50
        FIELD_RIGHT = 250
        FIELD_TOP = -150
        FIELD_BOTTOM = 350

        #Si se sale de la cancha, punto
        if self.x < FIELD_LEFT or self.x > FIELD_RIGHT or self.y < FIELD_TOP or self.y > FIELD_BOTTOM:
            self.out_of_bounds = True
            print("🎾 Pelota fuera de la cancha!")

        # ===== Convertir a pantalla =====
        iso_x, iso_y = world_to_iso(self.x, self.y, self.z)
        self.rect.center = (iso_x + ANCHO // 2, iso_y + ALTO // 3)

    def draw(self, screen):
        # Sombra proyectada (más cerca del suelo)
        sombra_x, sombra_y = world_to_iso(self.x, self.y, 0)
        sombra_x += ANCHO // 2
        sombra_y += ALTO // 3
        pygame.draw.circle(screen, (50, 50, 50), (int(sombra_x), int(sombra_y)), self.radio)

        # Pelota (más alta según z)
        px, py = self.screen_x, self.screen_y
        pygame.draw.circle(screen, (255, 255, 0), (int(px), int(py)), self.radio)
        # Debug opcional
        #print(f"x={self.x:.2f}, y={self.y:.2f}, z={self.z:.2f}, vz={self.vz:.2f}")

        #if hasattr(field.net, "ball_hits_net"):
        #    if field.net.ball_hits_net((self.world_x, self.world_y, self.z), self.radius):
        if hasattr(self.game, "field"):
            if self.game.field.net.ball_hits_net((self.x, self.y, self.z), self.radio):
                # Rebote más realista
                self.vz = abs(self.vz) * 0.5  # rebote hacia arriba
                self.vx *= 0.8
                self.vy *= 0.8
                self.z += 2  # ligera corrección visual
                print("🔴 Rebote en la red")


    def hit_by_player(self, player_pos: Tuple[float, float], target_zone: Optional[str] = None):
        """
        Simula el golpe de un jugador con opción de apuntar a una zona del campo rival.
        target_zone puede ser: 'left', 'center' o 'right'
        """
        print(f"🎾 Pelota golpeada desde {player_pos}")

        bx, by = self.x, self.y

        # Determinar hacia qué lado va el golpe
        if player_pos[1] > by:
            # Jugador 1 (abajo) golpea → apuntar al campo superior
            side = "top"
        else:
            side = "bottom"

        # Si tenés acceso al campo, usalo
        if hasattr(self.game, "field"):
            tx, ty = self.game.field.get_target_zone(side, target_zone or "center")
        else:
            # fallback simple si no hay field
            tx, ty = bx + random.uniform(-200, 200), by + (-200 if side == "top" else 200)

        # Vector de dirección
        dx = tx - bx
        dy = ty - by
        dist = max((dx**2 + dy**2) ** 0.5, 1)
        dir_x, dir_y = dx / dist, dy / dist

        # Velocidad y altura
        speed = random.uniform(7, 9)
        self.vx = dir_x * speed
        self.vy = dir_y * speed
        self.vz = random.uniform(7, 9)

        print(f"📍 Objetivo {side}-{target_zone or 'center'} → ({tx:.1f}, {ty:.1f})")
        print(f"📐 Dirección: vx={self.vx:.2f}, vy={self.vy:.2f}, vz={self.vz:.2f}")