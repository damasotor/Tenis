import pygame
import os
from engine.utils.screen import SCALE, to_pixels, world_to_screen


class Net:
    def __init__(self, field_width, field_height, scale=1.0):
        self.field_width = field_width
        self.field_height = field_height
        self.scale = scale

        # Rect para colisiones y posición en pantalla
        self.rect = pygame.Rect(0, 0, 4, 100)

        # Cargar textura de la red
        texture_path = os.path.join("assets", "texturas", "red.png")
        try:
            self.texture = pygame.image.load(texture_path).convert_alpha()
        except Exception as e:
            print(f"No se pudo cargar la textura de la red: {e}")
            self.texture = None

    def update_rect(self, court_rect):
        """Actualiza el rect de la red centrado en la cancha"""
        net_w = max(4, int(court_rect.width * 0.008))
        net_h = court_rect.height
        net_x = court_rect.centerx - net_w // 2
        net_y = court_rect.y
        self.rect = pygame.Rect(net_x, net_y, net_w, net_h)

    def draw(self, screen):
        if self.texture:
            tw, th = self.texture.get_size()
            scale_factor = self.rect.height / th
            new_w = int(tw * scale_factor)
            new_h = int(th * scale_factor)
            scaled = pygame.transform.smoothscale(self.texture, (new_w, new_h))
            rect = scaled.get_rect(center=self.rect.center)
            screen.blit(scaled, rect)
        else:
            pygame.draw.rect(screen, (255, 0, 0), self.rect)
