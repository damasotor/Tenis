import pygame
from pygame import Rect

def aabb_overlap(a: Rect, b: Rect) -> bool:
    return a.colliderect(b)

def circle_rect_collision(circle_center, radius: int, rect: Rect) -> bool:
    cx, cy = circle_center
    rx = max(rect.left,  min(cx, rect.right))
    ry = max(rect.top,   min(cy, rect.bottom))
    dx = cx - rx
    dy = cy - ry
    return (dx*dx + dy*dy) <= (radius*radius)

def resolve_side_penetration(moving: Rect, solid: Rect, vx: float):
    if vx > 0:
        moving.right = solid.left - 1
    else:
        moving.left = solid.right + 1
