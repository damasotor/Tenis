ANCHO, ALTO = 800, 600
SCALE = 50


def world_to_screen(x, y):
    iso_x = x - y
    iso_y = (x + y) / 2
    return iso_x, iso_y

def to_pixels(iso_x, iso_y, scale, offset_x=ANCHO // 2, offset_y=ALTO // 2):
    
    #Convierte coordenadas isométricas a coordenadas de pantalla (píxeles).
    
    sx = int(offset_x + iso_x * scale)
    sy = int(offset_y + iso_y * scale)
    return sx, sy
     