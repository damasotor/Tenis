import pygame
import os
from engine.utils.screen import world_to_screen, ANCHO, ALTO, SCALE


def compute_offset(field_width, field_height, scale):
    """
    Calcula el desplazamiento (offset) necesario para centrar la cancha
    en la pantalla, según su tamaño en coordenadas del mundo e isométricas.
    """
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
    """
    Convierte coordenadas isométricas a coordenadas de pantalla (píxeles).
    """
    sx = int(offset_x + iso_x * scale)
    sy = int(offset_y + iso_y * scale)
    return sx, sy


class Field:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.net_y = (height // 2) + 64

        # Precalcular el offset de centrado de la cancha
        self.offset_x, self.offset_y = compute_offset(width, height, SCALE)

        # ----------------------------------------------------------
        # Cargar la textura de fondo de la cancha
        # ----------------------------------------------------------
        # Ruta de la textura: assets/texturas/tennis_court_background.jpg
        texture_path = os.path.join("assets", "texturas", "tennis_court_background.jpg")

        # Cargar la imagen y convertirla al formato interno de Pygame (más rápido)
        try:
            self.texture = pygame.image.load(texture_path).convert()
            # Escalar la textura al tamaño completo de la pantalla
            self.texture = pygame.transform.scale(self.texture, (ANCHO, ALTO))
        except Exception as e:
            print(f"No se pudo cargar la textura de la cancha: {e}")
            self.texture = None

    def draw(self, screen):
        """
        Dibuja la cancha con textura y la red en el centro.
        """
        # ----------------------------------------------------------
        # Dibujar la textura de fondo
        # ----------------------------------------------------------
        if self.texture:
            # Si la textura se cargó correctamente, usarla como fondo
            screen.blit(self.texture, (0, 0))
        else:
            # Si no hay textura, usar color verde por defecto
            screen.fill((0, 180, 0))

        # ----------------------------------------------------------
        # Dibujar el contorno de la cancha (en isométrico)
        # ----------------------------------------------------------
        corners = [
            to_pixels(*world_to_screen(0, 0), SCALE, self.offset_x, self.offset_y),
            to_pixels(*world_to_screen(self.width, 0), SCALE, self.offset_x, self.offset_y),
            to_pixels(*world_to_screen(self.width, self.height), SCALE, self.offset_x, self.offset_y),
            to_pixels(*world_to_screen(0, self.height), SCALE, self.offset_x, self.offset_y),
        ]

        # Dibuja el contorno de la cancha con un borde blanco fino
        pygame.draw.polygon(screen, (255, 255, 255), corners, 3)

        # ----------------------------------------------------------
        # Dibujar la red de tenis en el centro del campo
        # ----------------------------------------------------------
        left = to_pixels(*world_to_screen(0, self.net_y), SCALE, self.offset_x, self.offset_y)
        right = to_pixels(*world_to_screen(self.width, self.net_y), SCALE, self.offset_x, self.offset_y)
        pygame.draw.line(screen, (255, 255, 255), left, right, 2)

