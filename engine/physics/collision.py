import pygame
from pygame import Rect
from typing import Tuple, Union

VectorLike = Union[Tuple[float, float], pygame.math.Vector2]


# -----------------------------
# Utilidades internas
# -----------------------------
def _clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value


def _closest_point_on_rect(px: float, py: float, rect: Rect) -> Tuple[float, float]:
    """
    Devuelve el punto del rectángulo 'rect' más cercano al punto (px, py).
    Útil para colisión círculo–rect.
    """
    rx = _clamp(px, rect.left, rect.right)
    ry = _clamp(py, rect.top, rect.bottom)
    return rx, ry


# -----------------------------
# Tests de intersección
# -----------------------------
def aabb_overlap(a: Rect, b: Rect) -> bool:
    """Colisión AABB estándar (rect–rect)."""
    return a.colliderect(b)


def circle_rect_collision(circle_center: VectorLike, radius: int, rect: Rect) -> bool:
    """
    Devuelve True si el círculo (center, radius) intersecta el rectángulo 'rect'.
    """
    if isinstance(circle_center, pygame.math.Vector2):
        cx, cy = float(circle_center.x), float(circle_center.y)
    else:
        cx, cy = float(circle_center[0]), float(circle_center[1])

    rx, ry = _closest_point_on_rect(cx, cy, rect)
    dx = cx - rx
    dy = cy - ry
    return (dx * dx + dy * dy) <= (radius * radius)


# -----------------------------
# Separación / resolución
# -----------------------------
def circle_rect_mtv(circle_center: VectorLike, radius: int, rect: Rect) -> pygame.math.Vector2:
    """
    Minimum Translation Vector (MTV) para separar un círculo de un rectángulo.
    Si no hay intersección, devuelve (0, 0).

    Útil si querés expulsar la pelota del cuerpo de la red sin “pegarse”.
    """
    if isinstance(circle_center, pygame.math.Vector2):
        cx, cy = float(circle_center.x), float(circle_center.y)
    else:
        cx, cy = float(circle_center[0]), float(circle_center[1])

    rx, ry = _closest_point_on_rect(cx, cy, rect)
    dx = cx - rx
    dy = cy - ry
    dist2 = dx * dx + dy * dy
    r = float(radius)

    if dist2 == 0.0:
        # El centro está exactamente en el borde/ángulo: elegimos la mínima
        # traslación hacia el lado más cercano del rect
        left_pen  = abs(cx - rect.left)
        right_pen = abs(rect.right - cx)
        top_pen   = abs(cy - rect.top)
        bot_pen   = abs(rect.bottom - cy)

        # Elegimos el eje con menor penetración
        min_pen = min(left_pen, right_pen, top_pen, bot_pen)
        if min_pen == left_pen:
            return pygame.math.Vector2(-(r or 1.0), 0.0)
        if min_pen == right_pen:
            return pygame.math.Vector2((r or 1.0), 0.0)
        if min_pen == top_pen:
            return pygame.math.Vector2(0.0, -(r or 1.0))
        return pygame.math.Vector2(0.0, (r or 1.0))

    if dist2 <= (r * r):
        dist = dist2 ** 0.5
        # Normal desde el punto más cercano hacia el centro
        nx = dx / (dist if dist != 0 else 1.0)
        ny = dy / (dist if dist != 0 else 1.0)
        # Penetración radial
        penetration = r - dist
        return pygame.math.Vector2(nx * penetration, ny * penetration)

    return pygame.math.Vector2(0.0, 0.0)


def resolve_side_penetration(moving: Rect, solid: Rect, vx: float) -> None:
    """
    Mantiene compatibilidad con tu firma original.
    Empuja 'moving' a la izquierda o derecha de 'solid' según el signo de vx.
    """
    if vx > 0:
        moving.right = solid.left - 1
    else:
        moving.left = solid.right + 1


def resolve_axis_penetration(moving: Rect, solid: Rect, vx: float, vy: float) -> None:
    """
    Resolución simple por eje: si la velocidad horizontal domina, resuelve por X;
    si no, resuelve por Y. Útil para plataformas y paredes.

    NOTA: si necesitás más precisión, podés comparar la penetración real por eje.
    """
    abs_vx, abs_vy = abs(vx), abs(vy)
    if abs_vx >= abs_vy:
        # Resolver por X
        if vx > 0:
            moving.right = solid.left - 1
        else:
            moving.left = solid.right + 1
    else:
        # Resolver por Y
        if vy > 0:
            moving.bottom = solid.top - 1
        else:
            moving.top = solid.bottom + 1
