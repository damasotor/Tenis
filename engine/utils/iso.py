from typing import Tuple

def world_to_screen(x: float, y: float) -> Tuple[float, float]:
    # proyección isométrica clásica (rombo 2:1)
    iso_x = x - y
    iso_y = (x + y) / 2
    return iso_x, iso_y

def screen_to_world(iso_x: float, iso_y: float) -> Tuple[float, float]:
    # inversa del sistema:
    # iso_x = x - y
    # iso_y = (x + y)/2  => x + y = 2*iso_y
    # sumando: 2x = iso_x + 2*iso_y
    x = (iso_x + 2*iso_y) / 2
    y = x - iso_x
    return x, y
