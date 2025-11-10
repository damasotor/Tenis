import os
import random
from typing import Optional, Tuple

import pygame

from engine.ball import world_to_iso
from engine.net import Net
from engine.utils import screen
from engine.utils.screen import to_pixels, world_to_screen, ANCHO, ALTO, SCALE

# Loader de texturas con fallback seguro
try:
    from engine.assets.texture_loader import load_texture as _load_texture
except Exception:
    _load_texture = None


def compute_offset(field_width: float, field_height: float, scale: float) -> Tuple[int, int]:
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


class Field:
    def __init__(self, width: int, height: int, texture_path: Optional[str] = None):
        self.width = width
        self.height = height

        # === Límites y centro del campo (coordenadas lógicas del mundo) ===
        self.left = 0
        self.top = 0
        self.right = width
        self.bottom = height
        self.center_x = self.left + self.width / 2
        self.center_y = self.top + self.height / 2

        # net
        self.net_y = (height // 2) + 64
        self.net_height = 50
        self.net = Net(self)

        # --- Zonas lógicas (mundo) ---
        self.zones = {
            "deep_back_left": (-45, 230, 150, 125),
            "back_left":  (-45, 105, 150, 125),
            "deep_front_left": (-45, -145, 150, 125),
            "front_left": (-45, -20, 150, 125),
            "deep_front_right": (105, -145, 150, 125),
            "front_right": (105, -20, 150, 125),
            "deep_back_right": (105, 230, 150, 125),
            "back_right": (105, 105, 150, 125),
            "center_back": (30, 105, 150, 250),
            "center_front": (30, -145, 150, 250),
        }

        # Offset de centrado
        self.offset_x, self.offset_y = compute_offset(width, height, SCALE)

        # Factor de escala visual para la textura
        self.scale_factor = 0.8

        # Cache de court rect del último draw
        self._last_court_rect: Optional[pygame.Rect] = None

        # Debug opcional (podés setearlo desde Game)
        self.debug = False

        # -------- Textura de fondo de la cancha --------
        # Soportamos ruta custom (texture_path) o tu ruta por defecto en español.
        if texture_path:
            base = os.path.join("assets", "textures")
            cand = os.path.join(base, os.path.basename(texture_path))
        else:
            cand = os.path.join("assets", "texturas", "Cancha.png")

        self.texture: Optional[pygame.Surface] = None
        self._scaled_texture: Optional[pygame.Surface] = None
        self._scaled_size: Optional[Tuple[int, int]] = None

        try:
            if _load_texture:
                # loader unificado (convert() ya se hace allí)
                self.texture = _load_texture(cand)
            else:
                self.texture = pygame.image.load(cand).convert_alpha()
        except Exception as e:
            print(f"[Field] No se pudo cargar la textura de la cancha '{cand}': {e}")
            self.texture = None

    # ---------- Límites reales del court y red ----------
    def get_court_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """
        Devuelve el área jugable del court en coordenadas de pantalla.
        Si hay textura, usa su tamaño escalado (cacheado) y centrado; si no, fallback sólido.
        """
        if self._last_court_rect is not None:
            return self._last_court_rect.copy()

        W, H = screen.get_width(), screen.get_height()

        if self.texture:
            # Si ya tenemos textura, calculamos su rect destino según scale_factor
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

    def get_net_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """
        Rect que representa la red (vertical y centrado). Debe coincidir con lo que se dibuja.
        """
        court = self.get_court_rect(screen)
        net_w = max(4, int(court.width * 0.008))
        net_h = court.height
        net_x = court.centerx - net_w // 2
        net_y = court.y
        return pygame.Rect(net_x, net_y, net_w, net_h)
        
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Devuelve los límites del campo en unidades del mundo (coherente con la escala)"""
        # factor de escala: del Field lógico a mundo “real”
        scale_x = 800 / self.width
        scale_y = 600 / self.height
        return 0, self.width * scale_x, 0, self.height * scale_y
    
    def draw_debug_bounds(self, surface: pygame.Surface) -> None:
        """Overlay de depuración para ver court, red y cinta."""
        court = self.get_court_rect(surface)
        #net = self.get_net_rect(surface)
        pygame.draw.rect(surface, (30, 200, 255), court, width=2)  # contorno court
        pygame.draw.rect(surface, (255, 0, 0), (0, 0, self.width, self.height), 2)
        #pygame.draw.rect(surface, (255, 80, 80), net, width=2)     # red

    def get_target_zone(self, side, zone="center"):
        """
        Devuelve una coordenada (x, y) dentro del campo, en UNIDADES del Field (no píxeles).
        side: 'top' o 'bottom'
        zone: 'left', 'center' o 'right'
        """

        mid_x = self.width / 2
        mid_y = self.height / 2

        # Dividimos el ancho del campo en 3 zonas
        left_range   = (0, mid_x - mid_x / 3)
        center_range = (mid_x - mid_x / 3, mid_x + mid_x / 3)
        right_range  = (mid_x + mid_x / 3, self.width)

        # Elegimos X según zona
        if zone == "left":
            rx = random.uniform(*left_range)
        elif zone == "right":
            rx = random.uniform(*right_range)
        else:
            rx = random.uniform(*center_range)

        # Elegimos Y según el lado opuesto del jugador
        if side == "top":
            ry = random.uniform(0.5, mid_y - 0.5)
        else:
            ry = random.uniform(mid_y + 0.5, self.height - 0.5)

        return rx, ry

    # ---------- Dibujo ----------
    def draw(self, screen: pygame.Surface) -> None:
        """
        Dibuja la cancha con textura centrada y la red en el centro.
        Además, cachea el rect del court para que Ball lo pueda usar en este frame.
        """
        # Fondo fuera de la cancha
        screen.fill((60, 160, 60))  # verde

        W, H = screen.get_width(), screen.get_height()

        # --- Fondo / textura ---
        if self.texture:
            tw, th = self.texture.get_size()
            target_size = (int(tw * self.scale_factor), int(th * self.scale_factor))

            # Cache: si no hay escalado previo o cambió el tamaño objetivo, recalcular
            if self._scaled_texture is None or self._scaled_size != target_size:
                try:
                    self._scaled_texture = pygame.transform.smoothscale(self.texture, target_size)
                except Exception:
                    # Fallback si smoothscale no está disponible
                    self._scaled_texture = pygame.transform.scale(self.texture, target_size)
                self._scaled_size = target_size

            rect = self._scaled_texture.get_rect(center=(W // 2, H // 2))
            screen.blit(self._scaled_texture, rect)

            # Cacheamos el rect como "court real"
            self._last_court_rect = rect.copy()
        else:
            # Fallback: relleno sólido si no hay textura
            screen.fill((0, 180, 0))
            self._last_court_rect = self.get_court_rect(screen)

        # --- Zonas isométricas (dibujo original) ---
        # === DEBUG VISUAL DE ZONAS ===
        debug = False  # 🔧 activar/desactivar rápidamente

        if debug:
            color_map = {
                "deep_back_left": (128, 0, 0),      # rojo oscuro
                "back_left": (255, 0, 0),           # rojo
                "deep_front_left": (0, 128, 0),     # verde oscuro
                "front_left": (0, 255, 0),          # verde
                "deep_front_right": (0, 0, 128),    # azul oscuro
                "front_right": (0, 0, 255),         # azul
                "deep_back_right": (128, 128, 0),   # amarillo oscuro
                "back_right": (255, 255, 0),        # amarillo
                "center_back": (0, 0, 0),
                "center_front": (250, 250, 250),
            }
            for name, (x, y, w, h) in self.zones.items():
                # Calcular esquinas del rectángulo en coordenadas del mundo
                corners = [
                    (x, y),
                    (x + w, y),
                    (x + w, y + h),
                    (x, y + h)
                ]

                # Convertir cada punto a coordenadas isométricas
                iso_points = []
                for wx, wy in corners:
                    iso_x, iso_y = world_to_iso(wx - self.width / 2, wy - self.height / 2)
                    iso_x += screen.get_width() // 2
                    iso_y += screen.get_height() // 3
                    iso_points.append((iso_x, iso_y))

                # Dibujar el contorno isométrico
                pygame.draw.polygon(screen, color_map[name], iso_points, 2)

                # Etiqueta de zona
                font = pygame.font.SysFont("arial", 16)
                label = font.render(name, True, color_map[name])
                lx = sum(p[0] for p in iso_points) / 4
                ly = sum(p[1] for p in iso_points) / 4
                screen.blit(label, (lx - label.get_width() // 2, ly - label.get_height() // 2))

        """for name, (x, y, w, h) in self.zones.items():
            corners = [
                to_pixels(*world_to_screen(x, y),       SCALE, self.offset_x, self.offset_y),
                to_pixels(*world_to_screen(x + w, y),   SCALE, self.offset_x, self.offset_y),
                to_pixels(*world_to_screen(x + w, y+h), SCALE, self.offset_x, self.offset_y),
                to_pixels(*world_to_screen(x, y + h),   SCALE, self.offset_x, self.offset_y),
            ]

            # Color por tipo de zona
            color = {
                "back_left":  (0, 255, 0),
                "front_left": (0, 200, 255),
                "net_zone":   (255, 255, 0),
                "front_right": (255, 100, 0),
                "back_right": (255, 0, 0),
            }.get(name, (255, 255, 255))

            pygame.draw.polygon(screen, color, corners, 2)"""

        #self.net.update()
        #self.net.draw_debug(screen, SCALE, self.offset_x, self.offset_y)
        self.net.update_net(self._last_court_rect)
        self.net.draw(screen)


    def get_net_world_line(self):
        """
        Devuelve la línea de la red en coordenadas del mundo (x, y).
        """
        return (0, self.net_y), (self.width, self.net_y)

    def get_net_iso_line(self):
        """
        Devuelve la línea de la red en coordenadas de pantalla isométricas (píxeles).
        """
        (x1, y1), (x2, y2) = self.get_net_world_line()
        iso1 = world_to_screen(x1, y1)
        iso2 = world_to_screen(x2, y2)
        p1 = to_pixels(*iso1, SCALE, self.offset_x, self.offset_y)
        p2 = to_pixels(*iso2, SCALE, self.offset_x, self.offset_y)
        return p1, p2

    def ball_hits_net(self, ball_pos_screen: Tuple[float, float], ball_radius: float = 5.0) -> bool:
        """
        Determina si la pelota cruza la red isométrica.
        (Se mantiene por compatibilidad con lógica antigua de pruebas; la colisión principal
         ahora la hacemos contra get_net_rect / get_net_tape_rect en Ball.update()).
        """
        (x1, y1), (x2, y2) = self.get_net_iso_line()
        bx, by = ball_pos_screen

        # Distancia punto-línea en 2D
        num = abs((y2 - y1) * bx - (x2 - x1) * by + x2*y1 - y2*x1)
        den = ((y2 - y1)**2 + (x2 - x1)**2)**0.5
        dist = num / max(1e-6, den)

        # Si la pelota está a menos de cierto margen (radio) => colisión
        return dist <= ball_radius
    

    def draw_debug_full(self, surface: pygame.Surface, ball=None, show_target=True):
        """
        Dibuja overlay de depuración completo:
        - Cancha (contorno)
        - Red
        - Límites de la cancha
        - Pelota y objetivo (si se pasa)
        """
        # --- Contorno de la cancha ---
        court = self.get_court_rect(surface)
        pygame.draw.rect(surface, (30, 200, 255), court, width=2)  # azul

        # --- Límites reales de la cancha (en world coords) ---
        left, top = 0, 0
        right, bottom = self.width, self.height
        corners = [
            world_to_iso(left, top),
            world_to_iso(right, top),
            world_to_iso(right, bottom),
            world_to_iso(left, bottom),
        ]
        corners_px = [(x + ANCHO // 2, y + ALTO // 3) for x, y in corners]
        pygame.draw.polygon(surface, (255, 255, 0), corners_px, width=2)  # amarillo

        # --- Red ---
        self.net.draw_debug(surface)

        # --- Pelota y objetivo ---
        if ball:
            # Pelota
            px, py = ball.screen_x, ball.screen_y
            pygame.draw.circle(surface, (255, 255, 0), (int(px), int(py)), ball.radio)

            # Objetivo
            if show_target and hasattr(ball, "_target_pos"):
                tx, ty = ball._target_pos
                pygame.draw.circle(surface, (0, 255, 0), (int(tx), int(ty)), 5)
                pygame.draw.line(surface, (0, 255, 0), (px, py), (tx, ty), 1)
