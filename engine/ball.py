import os
import json
import math
import random
import collections
from typing import Optional, List, Tuple

import pygame

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


class Ball(pygame.sprite.Sprite):
    """
    Pelota con:
    - Sprite opcional; fallback a círculo
    - Trail, sombra, squash/stretch
    - Spin con efecto en trayectoria (grav extra/menos y deriva)
    """

    # ----------------- HELPERS INTERNOS / PROYECCIÓN ⭐️ MOVIDO AQUÍ ⭐️ -----------------

    def _project_to_screen(self):
        """Convierte las coordenadas de mundo (world_x, world_y) a coordenadas de pantalla (rect).
        Esto debe ejecutarse ANTES de cualquier colisión basada en el rect."""
        try:
             # Si el objeto 'game' tiene un método de conversión (ej: isométrica), úsalo.
             # Asumimos que el método se llama world_to_screen y está en el objeto game.
             iso_x, iso_y = self.game.world_to_screen(self.world_x, self.world_y)
             self.rect.center = (iso_x, iso_y)
        except (AttributeError, NameError):
             # Fallback: juego 2D puro. Las coordenadas de mundo son las de pantalla.
             self.rect.center = (int(self.world_x), int(self.world_y))
    
    # Este método auxiliar sirve para sincronizar world_x/y cuando rect es ajustado
    def _sync_world_from_rect(self):
        """Sincroniza world_x/y con rect.center. Usado después de colisiones."""
        # Esto solo es correcto en juegos 2D puros. Si es isométrica, necesitarás un 
        # screen_to_world que tu juego podría no tener. Usamos la simplificación 2D por ahora.
        self.world_x = float(self.rect.centerx)
        self.world_y = float(self.rect.centery)


    # ----------------- INICIALIZACIÓN -----------------
    def __init__(self, x: int, y: int, game, vx: float = 4, vy: float = -5):
        super().__init__()
        self.game = game

        # ⭐️ Coordenadas de Mundo (world_x/y) - Necesarias para la IA ⭐️
        self.world_x = float(x)
        self.world_y = float(y)

        # ----------------- Física -----------------
        self.vx = vx
        self.vy = vy
        self._min_speed = 2.0
        self._max_speed = 9.0

        # Spin (valor escalar; + topspin, - slice). Decae cada frame.
        self.spin = 0.0

        # Cooldown para red
        self._net_cd_ms = 90
        self._last_net_hit = -10**9

        # ----------------- Visual (Se mantiene igual) -----------------
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
        
        # ⭐️ LLAMADA CORRECTA: El método _project_to_screen ya está definido arriba ⭐️
        self._project_to_screen()

    # ----------------- Carga sprite opcional (Se mantiene igual) -----------------
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

    # ----------------- API (Se mantiene igual) -----------------
    def start_rally(self):
        if hasattr(self.game, "audio"):
            self.game.audio.duck_music(0.18)
            self.game.audio.play_sound("serve")
            self.game.audio.unduck_music()

    def apply_shot_spin(self, spin_value: float):
        """Se llama desde Player al impactar: setea spin inicial del tiro."""
        self.spin = float(spin_value)

    # ----------------- Helpers audio (Se mantiene igual) -----------------
    def _calc_pan(self) -> float:
        W = self.game.PANTALLA.get_width()
        x = self.rect.centerx
        return (x / max(1, W)) * 2.0 - 1.0

    # ----------------- Update ⭐️ MODIFICADO ⭐️ -----------------
    def update(self):
        # ⭐️ CAMBIO: Movimiento base afecta world_x/y ⭐️
        self.world_x += self.vx
        self.world_y += self.vy

        # ⭐️ LLAMADA CRÍTICA: Proyectar la posición de mundo a rect para colisiones ⭐️
        self._project_to_screen() 

        # Trail
        if self._trail_enabled:
            # Usamos self.rect.center, ya que es la posición en pantalla
            self._trail.append((self.rect.centerx, self.rect.centery))

        # Spin effect → modifica trayectoria (Se mantiene igual, modificando vx/vy)
        if abs(self.spin) > 1e-3:
            # Aceleración vertical por spin (topspin “empuja” hacia abajo; slice hacia arriba)
            self.vy += self.spin * SPIN_GRAVITY_SCALE
            # Deriva lateral leve (dirección según signo de spin y sentido de avance)
            drift_dir = 1 if self.vx >= 0 else -1
            self.vx += (self.spin * SPIN_DRIFT_SCALE) * drift_dir
            # Decaimiento
            self.spin *= SPIN_DECAY

        # Velocidades mín/máx (Se mantiene igual, ajustando vx/vy)
        if 0 < abs(self.vx) < self._min_speed:
            self.vx = self._min_speed * (1 if self.vx >= 0 else -1)
        if 0 < abs(self.vy) < self._min_speed:
            self.vy = self._min_speed * (1 if self.vy >= 0 else -1)
        self.vx = max(-self._max_speed, min(self._max_speed, self.vx))
        self.vy = max(-self._max_speed, min(self._max_speed, self.vy))

        # Animator por tiempo (Se mantiene igual)
        if self._use_sprite and self._animator and self._current_anim in self._animations:
            if self._animator.update(self._current_anim):
                frames = self._animations[self._current_anim]
                if frames:
                    self._frame_index = (self._frame_index + 1) % len(frames)

        # ======= LÍMITES REALES DEL COURT =======
        screen = self.game.PANTALLA
        field = self.game.field
        court_rect = field.get_court_rect(screen) if hasattr(field, "get_court_rect") else screen.get_rect()

        # Colisiones y rebotes
        if self.rect.left <= court_rect.left:
            self.rect.left = court_rect.left
            self.vx *= -1
            self._on_bounce_court()
            self._sync_world_from_rect() # ⭐️ Sincronizar world_x/y después de ajustar rect ⭐️

        if self.rect.right >= court_rect.right:
            self.rect.right = court_rect.right
            self.vx *= -1
            self._on_bounce_court()
            self._sync_world_from_rect() # ⭐️ Sincronizar world_x/y después de ajustar rect ⭐️

        if self.rect.top <= court_rect.top:
            self.rect.top = court_rect.top
            self.vy *= -1
            self._on_bounce_court()
            self._sync_world_from_rect() # ⭐️ Sincronizar world_x/y después de ajustar rect ⭐️

        if self.rect.bottom >= court_rect.bottom:
            # OUT: punto para el rival del último que golpeó
            self.rect.bottom = court_rect.bottom
            self.on_out()
            
            # ⭐️ CAMBIO: Respawn al centro afecta world_x/y y se proyecta ⭐️
            cx, cy = screen.get_width() // 2, screen.get_height() // 2
            self.world_x = cx
            self.world_y = cy
            self.vx = random.choice([-5.0, 5.0]) # Usamos float
            self.vy = -5.0
            self.spin = 0.0
            self._project_to_screen() # Actualiza el rect
            return

        # ======= RED =======
        net_rect = field.get_net_rect(screen) if hasattr(field, "get_net_rect") else self._fallback_net_rect(screen)
        if self.rect.colliderect(net_rect):
            # ... (Lógica de rebote en la red se mantiene igual, ajustando rect y vx/vy)
            if abs(self.vx) < 1e-6:
                if self.rect.centerx >= net_rect.centerx:
                    self.rect.left = net_rect.right + 1
                    self.vx = abs(self._min_speed)
                else:
                    self.rect.right = net_rect.left - 1
                    self.vx = -abs(self._min_speed)
            else:
                if self.vx > 0:
                    self.rect.right = net_rect.left - 1
                else:
                    self.rect.left = net_rect.right + 1
                self.vx *= -1

            self.vy *= 0.95  # leve amortiguación
            now = pygame.time.get_ticks()
            if (now - self._last_net_hit) >= self._net_cd_ms:
                if hasattr(self.game, "audio"):
                    self.game.audio.play_sound_panned("net_touch", self._calc_pan())
                    if "crowd_ooh" in self.game.audio.sounds and random.random() < 0.4:
                        self.game.audio.play_sound("crowd_ooh")
                self._last_net_hit = now

            self._trigger_squash()
            self._sync_world_from_rect() # ⭐️ Sincronizar world_x/y después de ajustar rect ⭐️
            
        # ⭐️ El último punto de la trail siempre debe ser la posición final ⭐️
        if self._trail_enabled and len(self._trail) > 0:
             self._trail[-1] = (self.rect.centerx, self.rect.centery)


    # ----------------- Eventos (Se mantienen iguales) -----------------
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

    # ----------------- Draw (Se mantiene igual) -----------------
    def draw(self, surface: pygame.Surface):
        # Sombra
        if self._shadow_enabled:
            shadow_w = int(self.rect.width * 0.7)
            shadow_h = max(3, int(self.rect.height * 0.20))
            shadow = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
            shadow_rect = shadow.get_rect(midtop=(self.rect.centerx, self.rect.bottom - shadow_h // 2))
            surface.blit(shadow, shadow_rect)

        # Trail
        if self._trail_enabled and len(self._trail) > 1:
            for i in range(1, len(self._trail)):
                x1, y1 = self._trail[i-1]
                x2, y2 = self._trail[i]
                a = int(180 * (i / len(self._trail)))
                col = (255, 255, 255, max(20, min(200, a)))
                seg = pygame.Surface((max(1, abs(x2-x1) + 2), max(1, abs(y2-y1) + 2)), pygame.SRCALPHA)
                pygame.draw.line(seg, col, (1, 1), (x2 - x1 + 1, y2 - y1 + 1), 2)
                surface.blit(seg, (min(x1, x2) - 1, min(y1, y2) - 1))

        # Pelota
        if self._use_sprite and self._sprite_sheet and self._current_anim in self._animations:
            frames = self._animations[self._current_anim]
            if frames:
                self._frame_index %= len(frames)
                fx, fy, fw, fh = frames[self._frame_index]
                frame = self._sprite_sheet.subsurface(pygame.Rect(fx, fy, fw, fh))
                frame_to_draw = self._apply_squash(frame)
                surface.blit(frame_to_draw, frame_to_draw.get_rect(center=self.rect.center))
                return

        # Fallback: círculo
        r = self.rect.width // 2
        temp = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.circle(temp, (250, 250, 250), (r, r), r)
        temp = self._apply_squash(temp)
        surface.blit(temp, temp.get_rect(center=self.rect.center))

    def _apply_squash(self, surf: pygame.Surface) -> pygame.Surface:
        if self._squash_timer <= 0:
            return surf
        # decaimiento por frame básico
        self._squash_timer = max(0, self._squash_timer - (1000 // max(30, 60)))
        t = self._squash_timer / max(1, self._squash_duration)
        amt = self._squash_amount * t
        sx = 1.0 + (amt if abs(self.vx) > abs(self.vy) else -amt)
        sy = 1.0 + (amt if abs(self.vy) > abs(self.vx) else -amt)
        w = max(2, int(surf.get_width() * sx))
        h = max(2, int(surf.get_height() * sy))
        return pygame.transform.smoothscale(surf, (w, h))

    # Fallback net
    def _fallback_net_rect(self, screen) -> pygame.Rect:
        W = screen.get_width()
        H = screen.get_height()
        net_w = 6
        net_h = int(H * 0.6)
        net_x = (W - net_w) // 2
        net_y = (H - net_h) // 2
        return pygame.Rect(net_x, net_y, net_w, net_h)
