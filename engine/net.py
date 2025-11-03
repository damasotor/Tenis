import pygame
import os
from engine.ball import world_to_iso
from engine.utils.screen import ALTO, ANCHO, SCALE, world_to_screen, to_pixels



class Net:
    def __init__(self, field, color=(255, 0, 0)):
        self.field = field
        self.color = color
        self.height = 1.0  # Altura de la red en unidades de mundo
        self.rect = None
        self.world_line = None

        self.width = field.width  # ancho de la cancha
        self.x = field.width / 2  # centro de la red en X
        self.y = field.height / 2  # posición de la red en Y (mitad del campo)

        # Cargar textura
        texture_path = os.path.join("assets", "texturas", "red.png")
        try:
            self.texture = pygame.image.load(texture_path).convert_alpha()
        except Exception as e:
            print(f"No se pudo cargar la textura de la red: {e}")
            self.texture = None

    
    def update(self):
         # Desplazamiento lógico hacia jugador 1
        NET_OFFSET = 100.0  # ajustar este valor para moveer la red adelante o atrás
        net_y = (self.field.height / 2) + NET_OFFSET
        self.y = net_y

        # Línea base de colisión
        self.world_line = ((0, net_y), (self.field.width, net_y))
        self.rect = pygame.Rect(0, net_y - self.height / 2, self.field.width, self.height)

        print("Rect red lógica:", self.rect)
        print("Línea red debug:", self.world_line)

    """
    def draw_debug(self, screen, scale, offset_x, offset_y):
        if not self.world_line:
            return

        (x1, y1), (x2, y2) = self.world_line

        # Proyectar extremos base
        iso_x1, iso_y1 = world_to_screen(x1, y1)
        iso_x2, iso_y2 = world_to_screen(x2, y2)
        sx1, sy1 = to_pixels(iso_x1, iso_y1, scale, offset_x, offset_y)
        sx2, sy2 = to_pixels(iso_x2, iso_y2, scale, offset_x, offset_y)

        # Dibujar línea base
        pygame.draw.line(screen, self.color, (sx1, sy1), (sx2, sy2), 2)

        # Dibujar parte superior (altura visual)
        height_iso = self.height * scale * 2  # escala visual, ajustá según necesites
        pygame.draw.line(screen, self.color, (sx1, sy1 - height_iso), (sx2, sy2 - height_iso), 2)


        
        if not self.world_line:
            return

        (x1, y1), (x2, y2) = self.world_line
        # Base
        iso_x1, iso_y1 = world_to_screen(x1, y1)
        iso_x2, iso_y2 = world_to_screen(x2, y2)
        sx1, sy1 = to_pixels(iso_x1, iso_y1, scale, offset_x, offset_y)
        sx2, sy2 = to_pixels(iso_x2, iso_y2, scale, offset_x, offset_y)

        # Superior (debug)
        vertical_shift = self.height
        horizontal_shift = 1.0
        x1_top = x1 - horizontal_shift
        y1_top = y1 - vertical_shift
        x2_top = x2 - horizontal_shift
        y2_top = y2 - vertical_shift
        iso_x1_top, iso_y1_top = world_to_screen(x1_top, y1_top)
        iso_x2_top, iso_y2_top = world_to_screen(x2_top, y2_top)
        sx1_top, sy1_top = to_pixels(iso_x1_top, iso_y1_top, scale, offset_x, offset_y)
        sx2_top, sy2_top = to_pixels(iso_x2_top, iso_y2_top, scale, offset_x, offset_y)

        pygame.draw.line(screen, self.color, (sx1, sy1), (sx2, sy2), 2)
        pygame.draw.line(screen, self.color, (sx1_top, sy1_top), (sx2_top, sy2_top), 2)
        """
    def draw_debug(self, screen):
        """Dibuja el área de colisión de la red para depuración."""
        color = (255, 0, 0)  # rojo para debug

        # Asumimos que la red está centrada en el eje Y del campo (y = 0)
        # y ocupa una anchura fija (en coordenadas del mundo)
        NET_WIDTH = self.width
        NET_HEIGHT = self.height
        NET_Y = self.y  # posición base en el eje Y

        # Convertimos los puntos del rectángulo a coordenadas isométricas
        corners = [
            (0, NET_Y, 0),
            (NET_WIDTH, NET_Y, 0),
            (NET_WIDTH, NET_Y, NET_HEIGHT),
            (0, NET_Y, NET_HEIGHT),
        ]

        iso_points = [world_to_iso(x, y, z) for x, y, z in corners]
        iso_points = [(ix + ANCHO // 2, iy + ALTO // 3) for ix, iy in iso_points]

        # Dibujamos el contorno del área de colisión
        pygame.draw.polygon(screen, color, iso_points, width=2)



    def update_net(self, court_rect):
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

    def ball_hits_net(self, ball_pos, ball_radius):
        """
        Determina si la pelota colisiona con la red (en espacio de mundo).
        ball_pos: (x, y, z)
        ball_radius: radio de la pelota
        """
        bx, by, bz = ball_pos
        NET_OFFSET = 100.0  # mismo valor que arriba
        net_y = (self.field.height / 2) + NET_OFFSET

        net_height = self.height * 50  # altura lógica

        near_net = abs(by - net_y) < ball_radius
        low_enough = bz <= net_height

        if near_net and low_enough:
            print(f"💥 Pelota impacta la red! (by={by:.1f}, net_y={net_y:.1f}, z={bz:.1f})")
            return True
        return False