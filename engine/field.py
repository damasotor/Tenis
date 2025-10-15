import pygame
import os
from engine.net import Net
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

class Field:
    def __init__(self, width, height, texture_path=None, scale_factor=0.8):
        self.width = width
        self.height = height
        self.scale_factor = scale_factor

        # Precalcular offset para centrar la cancha
        self.offset_x, self.offset_y = compute_offset(width, height, SCALE)

        # Rect del court de este frame
        self._last_court_rect = None
        self._last_rect = None
        self.texture = None
        self.net = Net(width, height, scale=1.0)

        # Cargar textura de cancha
        if texture_path is None:
            texture_path = os.path.join("assets", "texturas", "Cancha.png")
        try:
            self.texture = pygame.image.load(texture_path).convert_alpha()
        except Exception as e:
            print(f"No se pudo cargar la textura de la cancha: {e}")
            self.texture = None

        # Definir zonas lógicas
        self.zones = {
            "back_left":  (0, 0, width, height * 0.23),
            "front_left": (0, height * 0.23, width, height * 0.27),
            "front_right":(0, height * 0.50, width, height * 0.28),
            "back_right": (0, height * 0.78, width, height * 0.23),
        }

        # Red
        self.net = Net(width, height)

    def get_court_rect(self, screen) -> pygame.Rect:
        """Devuelve el rect de la cancha en pantalla, usado para centrar la red"""
        if self._last_court_rect is not None:
            return self._last_court_rect.copy()

        W, H = screen.get_width(), screen.get_height()
        if self.texture:
            tw, th = self.texture.get_size()
            new_w = int(tw * self.scale_factor)
            new_h = int(th * self.scale_factor)
            rect = pygame.Rect(0, 0, new_w, new_h)
            rect.center = (W // 2, H // 2)
        else:
            # fallback
            court_w = int(W * 0.7)
            court_h = int(H * 0.78)
            court_x = (W - court_w) // 2
            court_y = (H - court_h) // 2 + int(H * 0.04)
            rect = pygame.Rect(court_x, court_y, court_w, court_h)

        self._last_court_rect = rect.copy()
        return rect

    def draw_debug_bounds(self, surface):
        court_rect = self.get_court_rect(surface)
        self.net.update_rect(court_rect)
        pygame.draw.rect(surface, (30, 200, 255), court_rect, width=2)
        pygame.draw.rect(surface, (255, 80, 80), self.net.rect, width=2)

    def draw(self, screen):
        # Fondo fuera de la cancha
        screen.fill((60, 160, 60))  # verde

        # Dibujar cancha
        if self.texture:
            tw, th = self.texture.get_size()
            new_size = (int(tw * self.scale_factor), int(th * self.scale_factor))
            scaled = pygame.transform.smoothscale(self.texture, new_size)
            rect = scaled.get_rect(center=(ANCHO // 2, ALTO // 2))
            screen.blit(scaled, rect)
            self._last_court_rect = rect.copy()
        else:
            self._last_rect = pygame.Rect(0, 0, ANCHO, ALTO)
            pygame.draw.rect(screen, (50, 200, 50), self.get_court_rect(screen))

        # Dibujar red
        self.net.update_rect(self._last_court_rect)
        self.net.draw(screen)
