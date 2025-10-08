ANCHO, ALTO = 800, 600
SCALE = 50


def world_to_screen(x, y):
    iso_x = x - y
    iso_y = (x + y) / 2
    return iso_x, iso_y