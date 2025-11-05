"""
Overlays de depuración para eventos temporales (p.ej., piques IN/OUT).
Diseño:
- DebugOverlays.add_bounce(x, y, inside)  -> registra un marcador temporal
- DebugOverlays.update(dt_ms)             -> decrementa vida
- DebugOverlays.draw(surface)             -> dibuja marcadores vigentes

No tiene dependencias del resto del motor (solo pygame).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame


@dataclass
class BounceMarker:
    x: int
    y: int
    inside: bool         # True = IN, False = OUT
    ttl_ms: int = 450    # vida útil en ms
    max_ttl_ms: int = 450

    def alive(self) -> bool:
        return self.ttl_ms > 0

    def alpha(self) -> int:
        # Fade-out lineal
        a = max(0.0, min(1.0, self.ttl_ms / float(self.max_ttl_ms)))
        return int(255 * a)


class DebugOverlays:
    def __init__(self):
        self._bounces: List[BounceMarker] = []
        self._font_small: Optional[pygame.font.Font] = None

    # ---------- API ----------
    def add_bounce(self, x: int, y: int, inside: bool, ttl_ms: int = 450) -> None:
        """
        Agrega un marcador de pique. 'inside' indica si fue dentro (IN) o fuera (OUT).
        """
        self._bounces.append(BounceMarker(x=x, y=y, inside=inside, ttl_ms=ttl_ms, max_ttl_ms=ttl_ms))

    def clear(self) -> None:
        self._bounces.clear()

    def update(self, dt_ms: int) -> None:
        """
        dt_ms: milisegundos transcurridos desde el último frame.
        """
        if not self._bounces:
            return
        for m in self._bounces:
            m.ttl_ms = max(0, m.ttl_ms - int(dt_ms))
        # eliminar muertos
        self._bounces = [m for m in self._bounces if m.alive()]

    def draw(self, surface: pygame.Surface) -> None:
        if not self._bounces:
            return

        # Lazy font
        if self._font_small is None:
            try:
                self._font_small = pygame.font.SysFont("arial", 14)
            except Exception:
                self._font_small = pygame.font.Font(None, 14)

        for m in self._bounces:
            self._draw_bounce_marker(surface, m)

    # ---------- Internos ----------
    def _draw_bounce_marker(self, surface: pygame.Surface, m: BounceMarker) -> None:
        a = m.alpha()
        # Colores con alpha
        col_fill = (40, 220, 120, a) if m.inside else (240, 70, 70, a)
        col_edge = (25, 140, 75, a) if m.inside else (170, 40, 40, a)
        label = "IN" if m.inside else "OUT"

        # Círculo + cruz
        radius = 8
        seg = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        center = (seg.get_width() // 2, seg.get_height() // 2)

        # Disco translúcido
        pygame.draw.circle(seg, col_fill, center, radius + 2)
        # Borde
        pygame.draw.circle(seg, col_edge, center, radius + 2, 2)
        # Cruz sutil
        pygame.draw.line(seg, col_edge, (center[0] - radius, center[1]), (center[0] + radius, center[1]), 2)
        pygame.draw.line(seg, col_edge, (center[0], center[1] - radius), (center[0], center[1] + radius), 2)

        seg_rect = seg.get_rect(center=(m.x, m.y))
        surface.blit(seg, seg_rect)

        # Etiqueta
        if self._font_small:
            txt_col = (255, 255, 255)
            txt = self._font_small.render(label, True, txt_col)
            # Sombra
            sh = self._font_small.render(label, True, (0, 0, 0))
            off = 1
            surface.blit(sh, txt.get_rect(midtop=(m.x + off, m.y + radius + 4 + off)))
            surface.blit(txt, txt.get_rect(midtop=(m.x, m.y + radius + 4)))
