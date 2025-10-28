"""
Reglas puras relacionadas al "court" (sin dependencias del juego).
Útil para decidir si un pique fue dentro o fuera, con tolerancia al grosor de líneas.
"""

from typing import Tuple
import pygame

def is_point_inside_court(court_rect: pygame.Rect, x: int, y: int, margin_px: int = 6) -> bool:
    """
    Devuelve True si el punto (x, y) cae dentro del court considerando un margen
    hacia adentro para evitar contar las líneas/grosor como "in".

    - court_rect: área jugable en coordenadas de pantalla.
    - margin_px: margen hacia DENTRO del rect (inflate negativo).
    """
    if not isinstance(court_rect, pygame.Rect):
        raise TypeError("court_rect debe ser pygame.Rect")

    inner = court_rect.inflate(-margin_px * 2, -margin_px * 2)
    # Si el margen es demasiado grande y deja un rect inválido, caemos al rect original
    if inner.width <= 0 or inner.height <= 0:
        inner = court_rect.copy()
    return inner.collidepoint(x, y)


def clamp_point_to_rect(court_rect: pygame.Rect, x: int, y: int) -> Tuple[int, int]:
    """
    Recorta (x, y) para quedar dentro de court_rect. Útil para overlays.
    """
    if not isinstance(court_rect, pygame.Rect):
        raise TypeError("court_rect debe ser pygame.Rect")

    cx = max(court_rect.left, min(x, court_rect.right))
    cy = max(court_rect.top,  min(y, court_rect.bottom))
    return cx, cy
