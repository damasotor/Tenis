import pygame
import os
from engine.utils.screen import world_to_screen, ANCHO, ALTO, SCALE



def compute_offset(field_width, field_height, scale):
    
    #Calcula el desplazamiento (offset) necesario para centrar la cancha
    #en la pantalla, según su tamaño en coordenadas del mundo e isométricas.
    
    # Calcular las esquinas en coordenadas isométricas
    corners_iso = [
        world_to_screen(0, 0),
        world_to_screen(field_width, 0),
        world_to_screen(field_width, field_height),
        world_to_screen(0, field_height),
    ]

    # Escalar las coordenadas al tamaño visual del juego
    corners_scaled = [(iso_x * scale, iso_y * scale) for iso_x, iso_y in corners_iso]

    # Determinar el área (bounding box) que ocupa la cancha en pantalla
    min_x = min(c[0] for c in corners_scaled)
    max_x = max(c[0] for c in corners_scaled)
    min_y = min(c[1] for c in corners_scaled)
    max_y = max(c[1] for c in corners_scaled)

    # Calcular el centro del área ocupada
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # Offset necesario para centrar la cancha en la pantalla
    offset_x = ANCHO // 2 - int(center_x)
    offset_y = ALTO // 2 - int(center_y)
    return offset_x, offset_y


def to_pixels(iso_x, iso_y, scale, offset_x=ANCHO // 2, offset_y=ALTO // 2):
    
    #Convierte coordenadas isométricas a coordenadas de pantalla (píxeles).
    
    sx = int(offset_x + iso_x * scale)
    sy = int(offset_y + iso_y * scale)
    return sx, sy


class Field:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.net_y = (height // 2) + 64
        self.net_height = 50

        # --- Definir zonas lógicas en coordenadas del mundo ---
        self.zones = {
            "back_left":  (0, 0, width, height * 0.23),
            "front_left": (0, height * 0.23, width, height * 0.27),
            "front_right":(0, height * 0.5, width, height * 0.28),
            "back_right": (0, height * 0.78, width, height * 0.23),
        }

        # Precalcular el offset de centrado de la cancha
        self.offset_x, self.offset_y = compute_offset(width, height, SCALE)
        
        # ----------------------------------------------------------
        # Cargar la textura de fondo de la cancha
        # ----------------------------------------------------------
        # Ruta de la textura: assets/texturas/tennis_court_background.jpg
        texture_path = os.path.join("assets", "texturas", "Cancha.png")

        # Cargar la imagen y convertirla al formato interno de Pygame (más rápido)
        try:
            self.texture = pygame.image.load(texture_path).convert()
            # Escalar la textura al tamaño completo de la pantalla
            #self.texture = pygame.transform.scale(self.texture, (ANCHO, ALTO))
        except Exception as e:
            print(f"No se pudo cargar la textura de la cancha: {e}")
            self.texture = None

    def draw(self, screen):
        """
        Dibuja la cancha con textura centrada y la red en el centro.
        """
        
        if self.texture:
            # Elegí el factor de reducción
            scale_factor = 0.8  # 90% del tamaño original (probá 0.8, 0.7, etc.)

            w, h = self.texture.get_size()
            new_size = (int(w * scale_factor), int(h * scale_factor))
            scaled_texture = pygame.transform.smoothscale(self.texture, new_size)

            # Centrar la textura en la pantalla
            rect = scaled_texture.get_rect(center=(ANCHO // 2, ALTO // 2))
            screen.blit(scaled_texture, rect)
        else:
            screen.fill((0, 180, 0))


    # Dibujar zonas en perspectiva isométrica
        for name, (x, y, w, h) in self.zones.items():
            corners = [
                to_pixels(*world_to_screen(x, y), SCALE, self.offset_x, self.offset_y),
                to_pixels(*world_to_screen(x + w, y), SCALE, self.offset_x, self.offset_y),
                to_pixels(*world_to_screen(x + w, y + h), SCALE, self.offset_x, self.offset_y),
                to_pixels(*world_to_screen(x, y + h), SCALE, self.offset_x, self.offset_y),
            ]

            # Color por tipo de zona
            color = {
                "back_left": (0, 255, 0),
                "front_left": (0, 200, 255),
                "net_zone": (255, 255, 0),
                "front_right": (255, 100, 0),
                "back_right": (255, 0, 0),
            }[name]

            pygame.draw.polygon(screen, color, corners, 2)
