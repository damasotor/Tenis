import os
import json
import math
import random
import collections
from typing import Optional, List, Tuple

import pygame

from engine.utils.screen import ALTO, ANCHO, screen_to_world

# Helpers de colisión geométrica
try:
    from engine.physics.collision import circle_rect_collision, circle_rect_mtv
except Exception:
    circle_rect_collision = None
    circle_rect_mtv = None

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
    - Colisión de red realista: cinta (pasa con roce) vs cuerpo (rebota)
    - Pique IN/OUT: decide según rect del court con margen tolerante
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
        # 💡 CAMBIOS NUEVOS: Cooldown para evitar rebotes múltiples
        self._net_cd_ms = 100        # 100 milisegundos de espera
        self._last_net_hit = -10**9  # Inicializa el último golpe en un tiempo muy pasado
        pygame.draw.circle(self.image, (255, 255, 255), (self.radio, self.radio), self.radio)
        self.rect = self.image.get_rect()
        self.rect.center = (self.screen_x, self.screen_y)   
        # 💡 CAMBIOS NUEVOS: Cooldown para evitar rebotes múltiples
        self._net_cd_ms = 100        # 100 milisegundos de espera
        self._last_net_hit = -10**9  # Inicializa el último golpe en un tiempo muy pasado

  

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

    # ----------------- Helpers de estado -----------------
    def _sync_ground_y(self):
        """Sincroniza ground_y con el rect real del court (bottom - margen)."""
        try:
            screen = self.game.PANTALLA
            field = self.game.field
            court_rect = field.get_court_rect(screen)
            self.ground_y = court_rect.bottom - self._ground_margin
        except Exception:
            # Fallback si algo falla
            self.ground_y = int(self.game.PANTALLA.get_height() * 0.78)

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
        """
        Choque con el cuerpo de un jugador.
        Regla: cuenta como error del último que golpeó la pelota → punto para el rival.
        También reproducimos un rebote amortiguado (feedback visual/sonoro) y jingle de punto.
        """
        # Feedback inmediato
        if hasattr(self.game, "audio"):
            self.game.audio.play_sound_panned("bounce_court", self._calc_pan())

        DEAD_BOUNCE_FACTOR = 0.25
        self.vx *= -DEAD_BOUNCE_FACTOR
        self.vy *= -DEAD_BOUNCE_FACTOR
        self._trigger_squash()

        # Jingle/UI del punto (igual que en OUT)
        self.on_point_scored()

        # Adjudicar punto según el último que golpeó
        try:
            last = getattr(self.game, "last_hitter", None)
            if last == "P1":
                self.game.point_for("P2")
            elif last == "P2":
                self.game.point_for("P1")
            else:
                # Si no sabemos quién pegó último, por defecto punto para P2
                self.game.point_for("P2")
        except Exception as _e:
            # print(f"[Ball] on_body_hit sin score manager: {_e}")
            pass

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

        #if hasattr(field.net, "si colisiona con la red"):
        #    if field.net.ball_hits_net((self.world_x, self.world_y, self.z), self.radius):
        if hasattr(self.game, "field"):
            # 💡 CORRECCIÓN: Definir 'net' aquí, asegurando la indentación correcta.
            net = self.game.field.net
            # 1. 💡 Lógica de Cooldown: Si ya chocó recientemente, salir.
            now = pygame.time.get_ticks()
            if now < self._last_net_hit + self._net_cd_ms:
                return

            if self.game.field.net.ball_hits_net((self.x, self.y, self.z), self.radio):
                # 2. Activar cooldown: Registrar el golpe.
                self._last_net_hit = now

                # Detención total en el plano horizontal (x, y)
                self.vx = 0.0 # Detiene el movimiento lateral (eje X)
                self.vy = 0.0 # Detiene el movimiento de profundidad (eje Y)
                self.vz *= 0.2
                net_y_pos = net.y # 105.0, la Y central de la red.
                CLEARANCE = 5.0 # Aumento del margen de seguridad (ej: 3 unidades)
                net_y_pos = 105.0
                
                # 3. 🔑 CORRECCIÓN CRÍTICA: Reajuste Geométrico (¡No usar self.vy!)
                if self.y > net_y_pos:
                    # Pelota en el lado Y positivo (Jugador 1), empujar hacia afuera.
                    self.y = net_y_pos - (self.radio + CLEARANCE) 
                else: 
                    # Pelota en el lado Y negativo (Jugador 2), empujar hacia afuera.
                    self.y = net_y_pos + self.radio + CLEARANCE
                    
                print(f"🔴 Rebote en la red. Posición final (x,y,z): ({self.x:.2f}, {self.y:.2f}, {self.z:.2f})")


    def hit_by_player(self, player_pos, zone="center", is_player2=False):
        field = self.game.field
        
        if zone not in field.zones:
            print(f"[⚠️] Zona '{zone}' no encontrada, usando centro por defecto.")
            target_x, target_y = 0, 0
        else:
            zx, zy, zw, zh = field.zones[zone]

            # Elegir un punto aleatorio dentro de la zona destino
            target_x = zx + random.uniform(0.2, 0.8) * zw
            target_y = zy + random.uniform(0.2, 0.8) * zh

        # --- Calcular dirección del golpe ---
        dx = target_x - self.x
        dy = target_y - self.y
        dz = 0 - self.z  # hacia el suelo

        dist = math.sqrt(dx**2 + dy**2)
        if dist == 0:
            dist = 1e-5

        # --- Ajustar fuerza y velocidad del golpe ---
        speed = random.uniform(8, 11)
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed
        self.vz = random.uniform(7, 10)

        print(f"🎾 Golpe de {'P2' if is_player2 else 'P1'} hacia '{zone}' → ({target_x:.1f}, {target_y:.1f}) con vx={self.vx:.2f}, vy={self.vy:.2f}, vz={self.vz:.2f}")
