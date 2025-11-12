import os
import json
import math
import random
import collections
from typing import Optional, List, Tuple

import pygame

# Asumimos que estas están definidas en otro lado
try:
    from engine.utils.screen import ALTO, ANCHO, screen_to_world
except ImportError:
    # Fallback para que el código sea runnable de forma aislada
    ANCHO, ALTO = 800, 600
    def screen_to_world(x, y): return x, y

TrailPoint = Tuple[int, int]
FrameRect = Tuple[int, int, int, int]

# Parámetros físicos (fallbacks)
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
FACTOR_ISO_X = 0.5    # qué tanto se "desplaza" la sombra en X por altura
FACTOR_ISO_Y = 0.3    # qué tanto se "desplaza" la sombra en Y por altura

class Ball(pygame.sprite.Sprite):
    """
    Pelota con física 3D/isométrica.
    """
    def __init__(self, x: int, y: int, game, vx: float, vy: float):
        super().__init__()
        self.game = game

        # Posición base (x, y) en el mundo (suelo)
        self.x = x
        self.y = y
        # Altura en el eje vertical (z)
        self.z = 80
        
        # 🔑 CORRECCIÓN: Usar las velocidades iniciales pasadas
        self.vx = vx
        self.vy = vy
        self.vz = 0.0 # Impulso vertical inicial
        
        # Propiedades físicas/visuales
        self.radio = 7
        self.spin = 0.0 # Spin (topspin > 0, backspin < 0)
        
        # Sprite de fallback (círculo simple)
        self.image = pygame.Surface((self.radio * 2, self.radio * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 255, 255), (self.radio, self.radio), self.radio)
        self.rect = self.image.get_rect()
        
        # Estado de colisión de red
        self._net_cd_ms = 100        # Cooldown para evitar rebotes múltiples en la red
        self._last_net_hit = -10**9  # Marca de tiempo del último golpe a la red
        
        # Estado del juego
        self.is_serving = False
        self.serve_stage = None   # "toss", "falling", "served", "fault", "ready"
        self.server = None
        self.bounce_count = 0
        self.waiting_hit = False
        self.out_of_bounds = False

        # Propiedades visuales
        self._squash_timer = 0
        self._squash_duration = 5

    @property
    def screen_x(self) -> float:
        iso_x, _ = world_to_iso(self.x, self.y, self.z)
        # centramos en la pantalla
        return iso_x + ANCHO // 2

    @property
    def screen_y(self) -> float:
        _, iso_y = world_to_iso(self.x, self.y, self.z)
        # bajamos un poco para centrar cancha visualmente
        return iso_y + ALTO // 3

    # ... (Se omite _load_sprite_or_fallback por simplicidad si no hay assets) ...
    def _load_sprite_or_fallback(self):
        r = 8
        self.image = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (250, 250, 250), (r, r), r)
        self.rect = self.image.get_rect()
        self._use_sprite = False
    
    # ----------------- API -----------------
    def start_rally(self):
        if hasattr(self.game, "audio"):
            # Lógica de audio (ducking, sonido de saque)
            pass

    def apply_shot_spin(self, spin_value: float):
        """Se llama desde Player al impactar: setea spin inicial del tiro."""
        self.spin = float(spin_value)

    # ----------------- Helpers audio -----------------
    def _calc_pan(self) -> float:
        W = self.game.PANTALLA.get_width()
        x = self.rect.centerx
        return (x / max(1, W)) * 2.0 - 1.0


    def launch_toward_zone(self, zone: str = None, speed: float = 5.0):
        # ... (Lógica de lanzamiento, se mantiene igual) ...
        if zone is None:
            zone = random.choice(["izquierda", "centro", "derecha"])

        if zone == "izquierda":
            dir_x, dir_y = -1, 1
        elif zone == "derecha":
            dir_x, dir_y = 1, 1
        else:
            dir_x, dir_y = 0, 1

        length = (dir_x**2 + dir_y**2) ** 0.5
        self.vx = (dir_x / length) * speed
        self.vy = (dir_y / length) * speed

        self.vz = speed * 0.6
        print(f"[DEBUG] Lanzamiento hacia {zone}: vx={self.vx:.2f}, vy={self.vy:.2f}, vz={self.vz:.2f}")
    
    def launch_toward_random_zone(self):
        # ... (Lógica de lanzamiento, se mantiene igual) ...
        zones = [
            (random.uniform(100, 400), random.uniform(100, 200)),
            (random.uniform(400, 700), random.uniform(100, 200)),
            (random.uniform(100, 400), random.uniform(300, 500)),
            (random.uniform(400, 700), random.uniform(300, 500)),
        ]
        target_x, target_y = random.choice(zones)

        dx = target_x - self.x
        dy = target_y - self.y
        dist = (dx ** 2 + dy ** 2) ** 0.5

        self.vx = dx / dist * random.uniform(4.5, 6.0)
        self.vy = dy / dist * random.uniform(4.5, 6.0)
        self.vz = -random.uniform(6.0, 9.0)

        print(f"Lanzando hacia zona ({target_x:.1f}, {target_y:.1f}) con vx={self.vx:.2f}, vy={self.vy:.2f}, vz={self.vz:.2f}")
    
    # ----------------- Eventos -----------------
    def _trigger_squash(self):
        self._squash_timer = self._squash_duration

    # ... (Métodos on_racket_hit, on_body_hit, on_out, on_point_scored se mantienen igual) ...

    def _on_bounce_court(self):
        if hasattr(self.game, "audio"):
            # Lógica de audio
            pass
        self._trigger_squash()

    def on_racket_hit(self):
        if hasattr(self.game, "audio"):
            # Lógica de audio
            pass

        AMORTIGUACION = 0.65
        self.vy *= -1
        self.vx *= AMORTIGUACION
        self.vy *= AMORTIGUACION

        MIN_VEL_AFTER_HIT = 3.0
        if abs(self.vy) < MIN_VEL_AFTER_HIT:
            self.vy = MIN_VEL_AFTER_HIT * (1 if self.vy >= 0 else -1)

        self._trigger_squash()

    def on_body_hit(self):
        if hasattr(self.game, "audio"):
            # Lógica de audio
            pass

        DEAD_BOUNCE_FACTOR = 0.25
        self.vx *= -DEAD_BOUNCE_FACTOR
        self.vy *= -DEAD_BOUNCE_FACTOR
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
        if hasattr(self.game, "audio"):
            # Lógica de audio si queres
            pass
        
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
            # Lógica de audio si queres y sino bueno
            pass

    def prepare_for_serve(self, server, x, y):
        """Coloca la pelota lista para ser servida, sin movimiento."""
        self.is_serving = True
        self.serve_stage = "ready"
        self.server = server
        
        world_x, world_y = screen_to_world(x, y)
        self.x = world_x
        self.y = world_y

        self.z = 0
        self.vx = self.vy = self.vz = 0
        print(f"🎾 Pelota lista para saque de {server} en ({self.x:.1f}, {self.y:.1f})")

    # ----------------- Lógica de saque (toss y golpe) -----------------
    def start_toss(self, server_id: str, start_x: float, start_y: float):
        self.server_id = server_id
        self.x = start_x
        self.y = start_y
        print("Posicion pelota: ", self.x, self.y)
        self.z = 0
        self.vx = 0
        self.vy = 0
        self.vz = 10
        self.serve_stage = "toss"
        self.waiting_hit = True
        self.out_of_bounds = False
        print(f"🎾 Toss iniciado por {server_id} en ({start_x:.1f}, {start_y:.1f})")

    def update_toss(self):
        """
        Actualiza la física del lanzamiento de saque (toss).
        """
        self.z += self.vz
        self.vz -= 0.6

        if self.vz <= 0 and self.serve_stage == "toss":
            self.serve_stage = "falling"
            print("⬇️ La pelota empieza a caer...")
            
        if self.z <= 0 and self.waiting_hit:
            self.z = 0
            self.vz = 0
            self.waiting_hit = False
            self.serve_stage = "fault"
            print("❌ Saque fallido (la pelota cayó sin ser golpeada)")
            self.on_out()  # o algún método de reinicio

        if self.z <= 0 and self.waiting_hit:
            self.z = 0
            self.vz = 0
            self.waiting_hit = False
            self.serve_stage = "fault"
            print("❌ Saque fallido (la pelota cayó sin ser golpeada)")
            if hasattr(self.game, "audio"):
                # Lógica de audio para falta
                pass

    def update(self):
        # --------------------------
        # ETAPAS DEL SAQUE
        # --------------------------
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
            # Si es falta, se queda quieta en el suelo
            return

        # ===== Movimiento en el mundo =====
        self.x += self.vx
        self.y += self.vy
        self.z += self.vz

        # Gravedad y rebote vertical
        self.vz -= 0.5
        if self.z <= 0:
            self.z = 0
            self.vz = -self.vz * 0.7
            if abs(self.vz) < 0.8:
                self.vz = 0

        # ===== Límites del campo (Out) =====
        FIELD_LEFT = -50
        FIELD_RIGHT = 250
        FIELD_TOP = -150
        FIELD_BOTTOM = 350

        if self.z == 0 and not self.out_of_bounds:
            # Chequear OUT solo después de un pique
            if self.x < FIELD_LEFT or self.x > FIELD_RIGHT or self.y < FIELD_TOP or self.y > FIELD_BOTTOM:
                self.out_of_bounds = True
                self.on_out() # Llama a la lógica de punto

        # 🔑 CORRECCIÓN CRÍTICA: Lógica de colisión de red movida de draw() a update()
        if hasattr(self.game, "field") and self.z > 0: # Solo chequear si está en el aire
            net = self.game.field.net
            now = pygame.time.get_ticks()

            if now >= self._last_net_hit + self._net_cd_ms:
                if self.game.field.net.ball_hits_net((self.x, self.y, self.z), self.radio):
                    self._last_net_hit = now

                    # 1. Aplicar rebote y amortiguación
                    self.vx = 0.0 # Detiene el movimiento lateral (eje X)
                    self.vy = 0.0 # Detiene el movimiento de profundidad (eje Y)
                    self.vz *= 0.2

                    # 2. Reajuste Geométrico (Mover la pelota fuera del obstáculo)
                    net_y_pos = 105.0 
                    CLEARANCE = 5.0 

                    if self.y > net_y_pos:
                        # Si está en el lado Y positivo (P1), empujar hacia su lado (más positivo Y)
                        self.y = net_y_pos + self.radio + CLEARANCE
                    else:
                        # Si está en el lado Y negativo (P2), empujar hacia su lado (más negativo Y)
                        self.y = net_y_pos - (self.radio + CLEARANCE)
                        
                    print(f"🔴 Rebote en la red. Posición final (x,y,z): ({self.x:.2f}, {self.y:.2f}, {self.z:.2f})")
        # --------------------------------------------------------------------------

        # ===== Convertir a pantalla =====
        iso_x, iso_y = world_to_iso(self.x, self.y, self.z)
        self.rect.center = (iso_x + ANCHO // 2, iso_y + ALTO // 3)

    def draw(self, screen):
        # Sombra proyectada (más cerca del suelo)
        sombra_x, sombra_y = world_to_iso(self.x, self.y, 0)
        sombra_x += ANCHO // 2
        sombra_y += ALTO // 3
        
        # El tamaño de la sombra se reduce con la altura
        sombra_radio = max(1, self.radio - int(self.z * 0.05))
        sombra_color = (50, 50, 50, max(0, 150 - int(self.z * 1.5))) # Transparencia según altura

        sombra_surf = pygame.Surface((sombra_radio * 2, sombra_radio * 2), pygame.SRCALPHA)
        pygame.draw.circle(sombra_surf, sombra_color, (sombra_radio, sombra_radio), sombra_radio)
        
        screen.blit(sombra_surf, (int(sombra_x - sombra_radio), int(sombra_y - sombra_radio)))

        # Pelota (más alta según z)
        px, py = self.screen_x, self.screen_y
        pygame.draw.circle(screen, (255, 255, 0), (int(px), int(py)), self.radio)
        
    def hit_by_player(self, player_pos, zone="center", is_player2=False):
        if getattr(self, "serve_stage", None) in ("toss", "falling"):
            self.waiting_hit = False
            self.serve_stage = "served"
            self.start_rally()

        field = self.game.field
        
        if zone not in field.zones:
            print(f"[⚠️] Zona '{zone}' no encontrada, usando centro por defecto.")
            target_x, target_y = 0, 0
        else:
            zx, zy, zw, zh = field.zones[zone]

            target_x = zx + random.uniform(0.2, 0.8) * zw
            target_y = zy + random.uniform(0.2, 0.8) * zh

        # --- Calcular dirección del golpe ---
        dx = target_x - self.x
        dy = target_y - self.y
        # dz = 0 - self.z # Eliminamos esto, el golpe ya se encarga de la altura

        dist = math.sqrt(dx**2 + dy**2)
        if dist == 0:
            dist = 1e-5

        # --- Ajustar fuerza y velocidad del golpe ---
        base_speed = random.uniform(8, 11)

        horizontal_boost = 1.5 if base_speed < 9 else 1.0

        self.vx = (dx / dist) * base_speed * horizontal_boost
        self.vy = (dy / dist) * base_speed * horizontal_boost

        # Altura suficiente para pasar la red
        self.vz = random.uniform(6, 8)

        print(f"🎾 Golpe de {'P2' if is_player2 else 'P1'} hacia '{zone}' → ({target_x:.1f}, {target_y:.1f}) con vx={self.vx:.2f}, vy={self.vy:.2f}, vz={self.vz:.2f}")
