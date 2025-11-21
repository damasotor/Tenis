import pygame
import os

class Net:
    """
    Red de tenis dibujada en 2D (pantalla), pero usando coordenadas de mundo
    solo para la física y colisiones.
    """

    def __init__(self, field, color=(255, 0, 0)):
        self.field = field
        self.color = color

        # Altura de la red en unidades de mundo (para física)
        self.height = 12.0

        # La red está exactamente a la mitad de la cancha
        self.y = field.height / 2.0

        # Cargar textura 2D
        texture_path = os.path.join("assets", "texturas", "red.png")
        try:
            self.texture = pygame.image.load(texture_path).convert_alpha()
        except Exception:
            print("[Net] No se pudo cargar red.png, usando fallback.")
            self.texture = None

        self.rect = None
        self.debug = False

    def update(self):
        """Actualiza rect de colisión (en mundo)."""
        self.y = self.field.height / 2.0
        self.rect = pygame.Rect(
            0,
            self.y - self.height / 2,
            self.field.width,
            self.height
        )

    def draw(self, screen):
        """Dibujo en 2D (pantalla), sin isométrico."""
        if not self.texture:
            if self.rect:
                # fallback rojo visible
                scr_rect = pygame.Rect(
                    screen.get_width()//2 - self.rect.width//2,
                    screen.get_height()//2 - 2,  # ajustado para centrar
                    self.rect.width,
                    4
                )
                pygame.draw.rect(screen, (255,0,0), scr_rect)
            return

        court_rect = self.field._last_court_rect
        if court_rect is None:
            return

        # Centrar horizontalmente
        net_x = court_rect.centerx - self.texture.get_width() // 2

        # Ubicar sobre el centro del court (ajuste probado para 800x600)
        NET_Y_FACTOR = 0.47
        net_y = int(court_rect.y + court_rect.height * NET_Y_FACTOR
                    - self.texture.get_height() // 2)

        screen.blit(self.texture, (net_x, net_y))

    def draw_debug(self, screen):
        """Línea simple indicando dónde está la red (debug)."""
        if self.rect:
            pygame.draw.line(
                screen, (255, 0, 0),
                (0, screen.get_height()//2),
                (screen.get_width(), screen.get_height()//2),
                2
            )

    def ball_hits_net(self, ball_pos, ball_radius_world):
        """Colisión física en coordenadas del mundo."""
        bx, by, bz = ball_pos
        near_y = abs(by - self.y) <= ball_radius_world
        low_enough = bz <= self.height

        return near_y and low_enough
