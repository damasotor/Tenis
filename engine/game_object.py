import os
import json
import collections
from typing import Dict, List, Tuple, Optional

import pygame

# Intentamos usar el helper centralizado; si no está disponible,
# caemos a pygame.image.load convert_alpha() como hasta ahora.
try:
    from engine.assets.image_loader import load_image as _load_image
except Exception:
    _load_image = None

# Animator (opcional). Si no existe, seguimos funcionando sin animación por tiempo.
try:
    from engine.animation.animator import Animator
except Exception:
    Animator = None  # type: ignore

FrameRect = Tuple[int, int, int, int]  # x, y, w, h


class GameObject:
    def __init__(self, x: float, y: float, json_path: str):
        self.x = x
        self.y = y

        self.sprite_sheet: Optional[pygame.Surface] = None
        self.animations: Dict[str, List[FrameRect]] = {}
        self.current_animation: str = 'idle'
        self.frame_index: int = 0
        self.rect: Optional[pygame.Rect] = None

        # Opcionales de presentación
        self._shadow_enabled: bool = True  # sombra elíptica bajo el objeto
        self._shadow_alpha: int = 70       # 0..255

        # Animator por tiempo (si está disponible)
        self._animator: Optional["Animator"] = Animator(default_fps=10) if Animator else None

        self.load_from_json(json_path)

    # --------------------------------------------------------------------- #
    # CARGA
    # --------------------------------------------------------------------- #
    def load_from_json(self, json_path: str) -> None:
        """
        Carga la spritesheet y los datos de animación desde un archivo JSON.
        Maneja la ruta relativa/absoluta de forma segura y usa el loader
        centralizado si está disponible.
        """
        try:
            base_dir = os.path.dirname(os.path.abspath(json_path))
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Ruta a spritesheet: soporta absoluta o relativa (respetando subcarpetas)
            spritesheet_path_cfg = data.get('spritesheet_path')
            if not spritesheet_path_cfg:
                raise ValueError("El JSON no contiene 'spritesheet_path'.")

            if os.path.isabs(spritesheet_path_cfg):
                # Si viniera absoluta, la normalizamos a basename dentro del JSON dir
                candidate = os.path.join(base_dir, os.path.basename(spritesheet_path_cfg))
            else:
                # Si es relativa, intentamos primero relativa real (con subcarpetas)
                candidate = os.path.normpath(os.path.join(base_dir, spritesheet_path_cfg))
                if not os.path.exists(candidate):
                    # Fallback a basename por portabilidad si no existe
                    candidate = os.path.join(base_dir, os.path.basename(spritesheet_path_cfg))

            if not os.path.exists(candidate):
                raise FileNotFoundError(f"Spritesheet no encontrada: {candidate}")

            # Cargar la imagen con helper (si está) o fallback a pygame
            if _load_image:
                self.sprite_sheet = _load_image(candidate)
            else:
                self.sprite_sheet = pygame.image.load(candidate).convert_alpha()

            # Animaciones: default dict de listas
            self.animations = collections.defaultdict(list)
            for anim_name, anim_list in (data.get('animations') or {}).items():
                if not isinstance(anim_list, list):
                    continue
                for sprite_data in anim_list:
                    x = int(sprite_data['x'])
                    y = int(sprite_data['y'])
                    w = int(sprite_data['width'])
                    h = int(sprite_data['height'])
                    # Guardamos las coordenadas de cada sprite como una tupla
                    self.animations[anim_name].append((x, y, w, h))

            if not self.animations:
                raise ValueError("No se encontraron animaciones válidas en el JSON.")

            # Animación inicial y rect de colisión
            self.current_animation = 'idle' if 'idle' in self.animations else list(self.animations.keys())[0]
            first_frames = self.animations[self.current_animation]
            if not first_frames:
                raise ValueError(f"La animación inicial '{self.current_animation}' no tiene frames.")
            fx, fy, fw, fh = first_frames[0]
            self.rect = pygame.Rect(self.x, self.y, fw, fh)

        except FileNotFoundError as e:
            print(f"[GameObject] Error de archivo: {e}")
            self.sprite_sheet = None
            self.animations = {}
            self.rect = None
        except Exception as e:
            print(f"[GameObject] Error al cargar '{json_path}': {e}")
            self.sprite_sheet = None
            self.animations = {}
            self.rect = None

    # --------------------------------------------------------------------- #
    # UPDATE (animación por tiempo)
    # --------------------------------------------------------------------- #
    def update(self) -> None:
        """
        Avanza la animación según el tiempo si hay Animator disponible.
        Si no hay Animator, no hace nada (el Player puede avanzar frames manualmente).
        """
        if not self._animator:
            return
        if not self.animations or self.current_animation not in self.animations:
            return

        if self._animator.update(self.current_animation):
            frames = self.animations[self.current_animation]
            if frames:
                self.frame_index = (self.frame_index + 1) % len(frames)

    # --------------------------------------------------------------------- #
    # RENDER
    # --------------------------------------------------------------------- #
    def draw(self, surface: pygame.Surface) -> None:
        """
        Dibuja el fotograma actual en la pantalla (con sombra opcional).
        """
        if not self.sprite_sheet or not self.animations or not self.rect:
            return

        # Asegurar animación válida
        if self.current_animation not in self.animations:
            # Fallback a alguna animación disponible
            self.current_animation = next(iter(self.animations.keys()))

        frames = self.animations.get(self.current_animation, [])
        if not frames:
            return

        # Evitar IndexError si el frame_index quedó fuera de rango
        self.frame_index %= len(frames)
        fx, fy, fw, fh = frames[self.frame_index]

        # Validar que el rect del frame esté dentro de la spritesheet
        if not self._frame_in_bounds(fx, fy, fw, fh, self.sprite_sheet):
            # Si el JSON trae coords fuera de la hoja, evitamos ValueError
            # e intentamos dibujar el primer frame seguro.
            fx, fy, fw, fh = frames[0]
            if not self._frame_in_bounds(fx, fy, fw, fh, self.sprite_sheet):
                return  # nada que dibujar

        # ---------- Sombra (elipse) bajo el objeto ----------
        if self._shadow_enabled:
            shadow_w = int(self.rect.width * 0.6)
            shadow_h = max(4, int(self.rect.height * 0.18))
            if shadow_w > 4 and shadow_h > 2:
                shadow = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow, (0, 0, 0, self._shadow_alpha), shadow.get_rect())
                sh_rect = shadow.get_rect(midtop=(self.rect.centerx, self.rect.bottom - shadow_h // 2))
                surface.blit(shadow, sh_rect)

        # ---------- Dibujar frame actual ----------
        frame_surf = self.sprite_sheet.subsurface(pygame.Rect(fx, fy, fw, fh))
        surface.blit(frame_surf, self.rect)

    # --------------------------------------------------------------------- #
    # HELPERS
    # --------------------------------------------------------------------- #
    @staticmethod
    def _frame_in_bounds(x: int, y: int, w: int, h: int, sheet: pygame.Surface) -> bool:
        sw, sh = sheet.get_width(), sheet.get_height()
        return (0 <= x < sw) and (0 <= y < sh) and (w > 0) and (h > 0) and (x + w <= sw) and (y + h <= sh)
