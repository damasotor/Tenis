ANCHO, ALTO = 800, 600
SCALE = 50


def world_to_screen(x, y):
    iso_x = x - y
    iso_y = (x + y) / 2
    sx = ANCHO // 2 + int(iso_x * SCALE)
    sy = ALTO // 2 + int(iso_y * SCALE)
    return iso_x, iso_y