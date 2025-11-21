import os
import pygame
from typing import Optional

from engine.net import Net
from engine.utils.screen import ANCHO, ALTO

class Field:
    """
    Cancha de tenis (2D), zonas lógicas y red.
    Render en pantalla sin isométrico.
    """

    def __init__(self, width: int, height: int, texture_path: Optional[str] = None):
        self.width = width
        self.height = height

        self.left = 0
        self.top = 0
        self.right = width
        self.bottom = height

        # Red (con física real, dibujada en 2D)
        self.net = Net(self)

        # ---------------------------
        # ZONAS LÓGICAS (restauradas)
        # ---------------------------
        self.zones = {
            "deep_back_left":   (-45, 230, 150, 125),
            "back_left":        (-45, 105, 150, 125),
            "deep_front_left":  (-45, -145, 150, 125),
            "front_left":       (-45, -20, 150, 125),

            "deep_front_right": (105, -145, 150, 125),
            "front_right":      (105, -20, 150, 125),
            "deep_back_right":  (105, 230, 150, 125),
            "back_right":       (105, 105, 150, 125),

            "center_back":      (30, 105, 150, 250),
            "center_front":     (30, -145, 150, 250),
        }

        # Textura principal
        cand = os.path.join("assets", "texturas", "Cancha.png")

        self.texture = None
        self._scaled_texture = None
        self._scaled_size = None
        self.scale_factor = 0.80

        try:
            self.texture = pygame.image.load(cand).convert_alpha()
        except Exception:
            print(f"[Field] No se pudo cargar textura '{cand}', usando fallback.")
            self.texture = None

        self._last_court_rect = None
        self.debug = False

    # ---------------------------
    # Court rect centrado
    # ---------------------------
    def _get_court_rect(self, screen: pygame.Surface) -> pygame.Rect:
        W, H = screen.get_width(), screen.get_height()

        if self.texture:
            tw, th = self.texture.get_size()
            new_w = int(tw * self.scale_factor)
            new_h = int(th * self.scale_factor)

            rect = pygame.Rect(0, 0, new_w, new_h)
            rect.center = (W // 2, H // 2)
            return rect

        court_w = int(W * 0.70)
        court_h = int(H * 0.78)
        court_x = (W - court_w) // 2
        court_y = (H - court_h) // 2
        return pygame.Rect(court_x, court_y, court_w, court_h)

    # ---------------------------
    # Dibujo de cancha + red
    # ---------------------------
    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((60, 160, 60))

        if self.texture:
            tw, th = self.texture.get_size()
            target_size = (int(tw * self.scale_factor), int(th * self.scale_factor))

            if self._scaled_texture is None or self._scaled_size != target_size:
                self._scaled_texture = pygame.transform.smoothscale(self.texture, target_size)
                self._scaled_size = target_size

            rect = self._scaled_texture.get_rect(
                center=(screen.get_width() // 2, screen.get_height() // 2)
            )
            self._last_court_rect = rect.copy()
            screen.blit(self._scaled_texture, rect)

        else:
            rect = self._get_court_rect(screen)
            pygame.draw.rect(screen, (0, 180, 0), rect)
            self._last_court_rect = rect

        # Red (actualiza física + dibuja 2D recta)
        self.net.update()
        self.net.draw(screen)

    # ---------------------------
    # DEBUG
    # ---------------------------
    def draw_debug_bounds(self, surface: pygame.Surface):
        if self._last_court_rect:
            pygame.draw.rect(surface, (0, 200, 255), self._last_court_rect, 2)

        self.net.draw_debug(surface)
