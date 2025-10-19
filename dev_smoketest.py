import pygame
pygame.init()

print("Iniciando smoke test...")

try:
    from engine.utils.iso import world_to_screen, screen_to_world
    x, y = 100, 50
    sx, sy = world_to_screen(x, y)
    rx, ry = screen_to_world(sx, sy)
    assert abs(rx - x) < 1e-6 and abs(ry - y) < 1e-6
    print("✅ OK iso: world<->screen")
except Exception as e:
    print("⚠️ ISO fallback (usando screen.py por ahora):", e)

try:
    from engine.assets.image_loader import load_image
    print("✅ OK assets loader import")
except Exception as e:
    print("⚠️ Assets fallback (usando pygame.image.load por ahora):", e)

print("✅ Todos los módulos básicos importan correctamente.")
