import os
import json
import math
import random
import collections
from typing import Optional, List, Tuple

import pygame

from engine.utils.screen import screen_to_world

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


class Ball(pygame.sprite.Sprite):
    """
    Pelota con:
    - Sprite opcional; fallback a círculo
    - Trail, sombra, squash/stretch
    - Spin con efecto en trayectoria (grav extra/menos y deriva)
    - Colisión de red realista: cinta (pasa con roce) vs cuerpo (rebota)
    - Pique IN/OUT: decide según rect del court con margen tolerante
    """
    def __init__(self, x: int, y: int, game, vx: float = 4, vy: float = -5):
        super().__init__()
        self.game = game

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
        self.gravity = 0.35        # fuerza de gravedad
        self.bounce_factor = 0.65  # energía retenida al rebotar

        # Piso real del court (sincronizado con textura/rect de Field)
        self._ground_margin = 6  # separación pequeña para no “pegarse” a la línea
        self.ground_y = 0  # se setea abajo
        self._sync_ground_y()

    # ----------------- Propiedades útiles -----------------
    @property
    def radius(self) -> float:
        """Radio de la pelota (para colisiones)."""
        return self.rect.width / 2

    @property
    def screen_x(self) -> float:
        """Posición X en pantalla (centro)."""
        return float(self.rect.centerx)

    @property
    def screen_y(self) -> float:
        """Posición Y en pantalla (centro)."""
        return float(self.rect.centery)

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

    # ----------------- Update -----------------
    def update(self):
        # Mantener el piso sincronizado (por si se reescala/recentra la cancha)
        self._sync_ground_y()

        # Movimiento base
        self.rect.x += self.vx
        self.rect.y += self.vy

        # Trail
        if self._trail_enabled:
            self._trail.append((self.rect.centerx, self.rect.centery))

        # Spin effect → modifica trayectoria
        if abs(self.spin) > 1e-3:
            # Aceleración vertical por spin (topspin “empuja” hacia abajo; slice hacia arriba)
            self.vy += self.spin * SPIN_GRAVITY_SCALE
            # Deriva lateral leve (dirección según signo de spin y sentido de avance)
            drift_dir = 1 if self.vx >= 0 else -1
            self.vx += (self.spin * SPIN_DRIFT_SCALE) * drift_dir
            # Decaimiento
            self.spin *= SPIN_DECAY

        # Velocidades mín/máx
        if 0 < abs(self.vx) < self._min_speed:
            self.vx = self._min_speed * (1 if self.vx >= 0 else -1)
        if 0 < abs(self.vy) < self._min_speed:
            self.vy = self._min_speed * (1 if self.vy >= 0 else -1)
        self.vx = max(-self._max_speed, min(self._max_speed, self.vx))
        self.vy = max(-self._max_speed, min(self._max_speed, self.vy))

        # Animator por tiempo
        if self._use_sprite and self._animator and self._current_anim in self._animations:
            if self._animator.update(self._current_anim):
                frames = self._animations[self._current_anim]
                if frames:
                    self._frame_index = (self._frame_index + 1) % len(frames)

        # ======= LÍMITES REALES DEL COURT (laterales/techo) =======
        screen = self.game.PANTALLA
        field = self.game.field
        court_rect = field.get_court_rect(screen) if hasattr(field, "get_court_rect") else screen.get_rect()

        if self.rect.left <= court_rect.left:
            self.rect.left = court_rect.left
            self.vx *= -1
            self._on_bounce_court()

        if self.rect.right >= court_rect.right:
            self.rect.right = court_rect.right
            self.vx *= -1
            self._on_bounce_court()

        if self.rect.top <= court_rect.top:
            self.rect.top = court_rect.top
            self.vy *= -1
            self._on_bounce_court()

        # *** NOTA: NO hacemos OUT aquí por bottom.
        # El pique/OUT se decide en la sección de "GRAVEDAD Y REBOTE".

        # ======= RED REALISTA: cinta vs cuerpo =======
        # Requiere que Field exponga get_net_rect() y get_net_tape_rect()
        if hasattr(field, "get_net_rect"):
            net_rect = field.get_net_rect(screen)
            tape_rect = field.get_net_tape_rect(screen) if hasattr(field, "get_net_tape_rect") else net_rect

            bx, by = self.rect.centerx, self.rect.centery
            rad = max(4, self.rect.width // 2)
            now = pygame.time.get_ticks()

            def _hit(rect):
                if circle_rect_collision:
                    return circle_rect_collision((bx, by), rad, rect)
                # fallback simple si no está el helper importado
                rx = max(rect.left,  min(bx, rect.right))
                ry = max(rect.top,   min(by, rect.bottom))
                dx, dy = bx - rx, by - ry
                return (dx*dx + dy*dy) <= (rad*rad)

            # 1) ¿rozó la CINTA?
            if _hit(tape_rect):
                # Efecto “corda”: deja pasar con pérdida de energía
                going_down = self.vy > 0
                self.vy *= 0.4 if going_down else -0.25
                self.vx *= 0.9
                self.rect.y -= 1  # micro-corrección para no “pegarse”
                if (now - self._last_net_hit) >= self._net_cd_ms and hasattr(self.game, "audio"):
                    self.game.audio.play_sound_panned("net_tape", self._calc_pan())
                    self._last_net_hit = now
                self._trigger_squash()

            # 2) Si no tocó cinta, ¿pegó en el CUERPO?
            elif _hit(net_rect):
                # Rebote amortiguado hacia atrás
                self.vx = -self.vx * 0.6
                self.vy = -abs(self.vy) * 0.3

                # Expulsión mínima para evitar jitter
                if circle_rect_mtv:
                    mtv = circle_rect_mtv((bx, by), rad, net_rect)
                    self.rect.x += int(mtv.x) if mtv and mtv.x else 0
                    self.rect.y += int(mtv.y) if mtv and mtv.y else 0
                else:
                    if bx >= net_rect.centerx:
                        self.rect.left = net_rect.right + 1
                    else:
                        self.rect.right = net_rect.left - 1

                if (now - self._last_net_hit) >= self._net_cd_ms and hasattr(self.game, "audio"):
                    self.game.audio.play_sound("net_body")
                    self._last_net_hit = now
                self._trigger_squash()

        # ======= GRAVEDAD Y REBOTE (suelo) =======
        self.vy += self.gravity  # aplica gravedad

        if self.rect.bottom >= self.ground_y:
            # Aseguramos contacto con el "suelo" visual real del court
            self.rect.bottom = int(self.ground_y)

            # --- Decidir si el pique fue adentro/afuera ---
            inside = False
            if hasattr(field, "is_point_inside_court"):
                inside = field.is_point_inside_court(screen, self.rect.centerx, self.rect.bottom, margin_px=6)

            # Overlay de pique (si existe el sistema de debug)
            if hasattr(self.game, "debug_overlays") and self.game.debug_overlays:
                self.game.debug_overlays.add_bounce(self.rect.centerx, self.rect.bottom, inside)

            if inside:
                # Rebote normal + SFX
                self.vy = -abs(self.vy) * self.bounce_factor
                if hasattr(self.game, "audio"):
                    self.game.audio.play_sound_panned("bounce_court", self._calc_pan())

                # Si el rebote ya es pequeño, la dejamos muerta
                if abs(self.vy) < 1.2:
                    self.vy = 0
            else:
                # OUT inmediato por pique
                self.on_out()
                # Respawn al centro
                cx, cy = screen.get_width() // 2, screen.get_height() // 2
                self.rect.center = (cx, cy)
                self.vx = random.choice([-5, 5])
                self.vy = -5
                self.spin = 0.0
                return

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

    # ----------------- Draw -----------------
    def draw(self, surface: pygame.Surface):
        # Sombra
        if self._shadow_enabled:
            # Altura real (distancia al suelo)
            altura = max(0, int(self.ground_y) - self.rect.bottom)

            # La sombra se achica y aclara cuanto más alta está la pelota
            scale = max(0.4, 1.0 - altura / 400.0)
            alpha = int(120 * scale)

            shadow_w = int(self.rect.width * 1.1 * scale)
            shadow_h = max(3, int(self.rect.height * 0.25 * scale))

            shadow = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, alpha), shadow.get_rect())

            # La sombra se dibuja fija en el suelo (ground_y)
            shadow_rect = shadow.get_rect(center=(self.rect.centerx, int(self.ground_y)))
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
    """
    def _fallback_net_rect(self, screen) -> pygame.Rect:
        W = screen.get_width()
        H = screen.get_height()
        net_w = 6
        net_h = int(H * 0.6)
        net_x = (W - net_w) // 2
        net_y = (H - net_h) // 2
        return pygame.Rect(net_x, net_y, net_w, net_h)
    """
