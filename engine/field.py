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
        self.net_height = 50

        # --- Definir zonas lógicas en coordenadas del mundo ---
        self.zones = {
            "back_left":  (0, 0, width, height * 0.23),
            "front_left": (0, height * 0.23, width, height * 0.27),
            "front_right":(0, height * 0.50, width, height * 0.28),
            "back_right": (0, height * 0.78, width, height * 0.23),
        }

        # Precalcular el offset de centrado de la cancha
        self.offset_x, self.offset_y = compute_offset(width, height, SCALE)

        # Factor de escala visual para la textura (lo usaremos para calcular el rect del court)
        self.scale_factor = 0.8

        # Rect del court calculado en el último draw (cache)
        self._last_court_rect = None

        # ----------------------------------------------------------
        # Cargar la textura de fondo de la cancha
        # ----------------------------------------------------------
        texture_path = os.path.join("assets", "texturas", "Cancha.png")
        try:
            self.texture = pygame.image.load(texture_path).convert()
        except Exception as e:
            print(f"No se pudo cargar la textura de la cancha: {e}")
            self.texture = None

    # ---------- NUEVO: límites reales del court y red ----------
    def get_court_rect(self, screen) -> pygame.Rect:
        """
        Devuelve el área jugable del court en coordenadas de pantalla.
        Si hay textura, usa su tamaño escalado y centrado; si no, usa un fallback.
        """
        # Si ya se calculó en draw() este frame, reaprovechamos
        if self._last_court_rect is not None:
            return self._last_court_rect.copy()

        W, H = screen.get_width(), screen.get_height()

        if self.texture:
            tw, th = self.texture.get_size()
            new_w = int(tw * self.scale_factor)
            new_h = int(th * self.scale_factor)
            rect = pygame.Rect(0, 0, new_w, new_h)
            rect.center = (W // 2, H // 2)
            return rect
        else:
            # Fallback si no hay textura
            court_w = int(W * 0.70)
            court_h = int(H * 0.78)
            court_x = (W - court_w) // 2
            court_y = (H - court_h) // 2 + int(H * 0.04)  # leve corrección visual
            return pygame.Rect(court_x, court_y, court_w, court_h)

    def get_net_rect(self, screen) -> pygame.Rect:
        """
        Devuelve un rectángulo angosto que representa la red.
        Por coherencia con el placeholder usado en Ball, lo hacemos VERTICAL y centrado
        (si luego querés una red inclinada/isométrica real, cambiamos a colisión custom).
        """
        court = self.get_court_rect(screen)
        net_w = max(4, int(court.width * 0.008))
        net_h = court.height
        net_x = court.centerx - net_w // 2
        net_y = court.y
        return pygame.Rect(net_x, net_y, net_w, net_h)

    def draw_debug_bounds(self, surface):
        """Overlay de depuración para ver court y red."""
        court = self.get_court_rect(surface)
        net = self.get_net_rect(surface)
        # contorno del court
        pygame.draw.rect(surface, (30, 200, 255), court, width=2)
        # red
        pygame.draw.rect(surface, (255, 80, 80), net, width=2)

    # ---------- Dibujo ----------
    def draw(self, screen):
        """
        Dibuja la cancha con textura centrada y la red en el centro.
        Además, cachea el rect del court para que Ball lo pueda usar en este frame.
        """
        # --- Fondo / textura ---
        if self.texture:
            tw, th = self.texture.get_size()
            new_size = (int(tw * self.scale_factor), int(th * self.scale_factor))
            scaled_texture = pygame.transform.smoothscale(self.texture, new_size)

            # Centrar la textura en la pantalla
            rect = scaled_texture.get_rect(center=(ANCHO // 2, ALTO // 2))
            screen.blit(scaled_texture, rect)

            # Cacheamos el rect como "court real"
            self._last_court_rect = rect.copy()
        else:
            screen.fill((0, 180, 0))
            # Si no hay textura, generamos y cacheamos un rect aproximado
            self._last_court_rect = self.get_court_rect(screen)

        # --- Zonas en perspectiva isométrica (tu dibujo original) ---
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
