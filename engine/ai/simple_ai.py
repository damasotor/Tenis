import random
import time
from math import hypot

# Usamos screen_to_world para obtener coords del mundo desde la pelota (que vive en pantalla)
try:
    from engine.utils.screen import screen_to_world
except Exception:
    screen_to_world = None  # type: ignore


class SimpleTennisAI:
    """
    IA muy simple para P2:
      - Intenta alinear world_x/world_y del jugador con la pelota.
      - Tiene una pequeña latencia de reacción y tope de velocidad para sentirse humano.
      - Comete leves "errores" (desvío) para no ser perfecta.

    Requisitos suaves:
      - player.world_x / player.world_y (si no existen, se infieren de player.x / player.y / player.rect.center)
      - player._project_to_screen() para reflejar en pantalla (si no está, se actualiza x/y como fallback)
      - ball.rect.center (coordenadas de pantalla); si hay screen_to_world, se convierten a mundo
    """

    def __init__(
        self,
        player,
        ball,
        side: str = "top",
        max_speed: float = 2.2,     # píxeles por frame aprox. (ajustar a tu escala)
        react_ms: int = 120,        # latencia de reacción
        jitter: float = 6.0,        # desvío aleatorio de puntería
        catchup_boost: float = 1.35,  # acelera si está muy lejos
        dead_zone: float = 2.0       # si está muy cerca, no se mueve
    ):
        self.player = player
        self.ball = ball
        self.side = side
        self.max_speed = float(max_speed)
        self.react_ms = int(react_ms)
        self.jitter = float(jitter)
        self.catchup_boost = float(catchup_boost)
        self.dead_zone = float(dead_zone)

        self._next_tick = time.time() + self.react_ms / 1000.0
        self._vx = 0.0
        self._vy = 0.0

        # Fijamos "home" por si no viene del Game
        if not hasattr(self.player, "home_x"):
            self.player.home_x = getattr(self.player, "world_x", getattr(self.player, "x", 0))
        if not hasattr(self.player, "home_y"):
            self.player.home_y = getattr(self.player, "world_y", getattr(self.player, "y", 0))

        # Normalizamos world_x/world_y si no existen
        if not hasattr(self.player, "world_x") or not hasattr(self.player, "world_y"):
            px, py = self._read_player_world_fallback()
            self.player.world_x = px
            self.player.world_y = py

    # ----------------- helpers de lectura/escritura -----------------
    def _read_player_world_fallback(self):
        """Intenta obtener (world_x, world_y) desde atributos alternativos."""
        if hasattr(self.player, "world_x") and hasattr(self.player, "world_y"):
            return float(self.player.world_x), float(self.player.world_y)
        if hasattr(self.player, "x") and hasattr(self.player, "y"):
            return float(self.player.x), float(self.player.y)
        if hasattr(self.player, "rect"):
            return float(self.player.rect.centerx), float(self.player.rect.centery)
        return 0.0, 0.0

    def _write_player_world_and_project(self, nx: float, ny: float):
        """Actualiza world_x/world_y y proyecta a pantalla si el player lo soporta."""
        self.player.world_x = float(nx)
        self.player.world_y = float(ny)

        # Proyectar a pantalla si existe helper interno
        if hasattr(self.player, "_project_to_screen") and callable(self.player._project_to_screen):
            try:
                self.player._project_to_screen()
                return
            except Exception:
                pass

        # Fallback: actualizar x/y o rect si no hay proyector
        if hasattr(self.player, "x") and hasattr(self.player, "y"):
            self.player.x = float(nx)
            self.player.y = float(ny)
        elif hasattr(self.player, "rect"):
            try:
                self.player.rect.center = (int(nx), int(ny))
            except Exception:
                pass

    def _read_ball_world(self):
        """
        Lee la posición de la pelota en mundo.
        Si existe screen_to_world, convierte desde rect.center (pantalla) a mundo.
        Si no, usa las coords de pantalla como si fueran mundo (fallback).
        """
        if self.ball is None:
            # Sin pelota no hacemos nada útil; quedarse en home
            return self.player.home_x, self.player.home_y

        # Si la pelota expone world_x/world_y, usarlas directo
        if hasattr(self.ball, "world_x") and hasattr(self.ball, "world_y"):
            return float(self.ball.world_x), float(self.ball.world_y)

        # Caso normal: la pelota vive en pantalla → convertir a mundo si podemos
        try:
            cx, cy = self.ball.rect.center
            if screen_to_world:
                wx, wy = screen_to_world(cx, cy)
                return float(wx), float(wy)
            # Fallback: tratar coords de pantalla como mundo
            return float(cx), float(cy)
        except Exception:
            # Último recurso: posición del jugador (no moverse)
            return self.player.world_x, self.player.world_y

    # ----------------- lógica de decisión -----------------
    def _should_chase(self, me_y: float, ball_y: float) -> bool:
        """
        Lógica simple según el lado de la red:
        - 'top': P2 arriba. Persigue si la bola está "arriba" de él.
        - 'bottom': P2 abajo. Persigue si la bola está "abajo" de él.

        Nota: asumimos eje Y creciente hacia abajo (típico en pantalla).
        """
        if self.side == "top":
            return ball_y < me_y
        else:
            return ball_y > me_y

    # ----------------- ciclo principal -----------------
    def update(self):
        now = time.time()
        if now < self._next_tick:
            # Mantener velocidad anterior hasta el próximo "tick" para simular latencia
            self.player.vx = self._vx
            self.player.vy = self._vy
            return

        self._next_tick = now + self.react_ms / 1000.0

        # Posición actual del jugador en mundo
        px, py = self._read_player_world_fallback()

        # Posición de la pelota en mundo (o pantalla si no hay conversión)
        bx, by = self._read_ball_world()

        # ¿Perseguir o reubicarse a home?
        if not self._should_chase(py, by):
            target_x = getattr(self.player, "home_x", px)
            target_y = getattr(self.player, "home_y", py)
        else:
            target_x = bx + random.uniform(-self.jitter, self.jitter)
            target_y = by + random.uniform(-self.jitter, self.jitter)

        dx = target_x - px
        dy = target_y - py
        dist = hypot(dx, dy)

        if dist <= self.dead_zone:
            vx = 0.0
            vy = 0.0
        else:
            # Normaliza dirección y aplica velocidad (con pequeño boost si está lejos)
            vx = dx / dist
            vy = dy / dist
            speed = self.max_speed * (self.catchup_boost if dist > 40.0 else 1.0)
            vx *= speed
            vy *= speed

        # Guardar y publicar velocidad (por si alguien la usa para animaciones)
        self._vx, self._vy = vx, vy
        self.player.vx = vx
        self.player.vy = vy

        # Avanzar en mundo y proyectar a pantalla
        self._write_player_world_and_project(px + vx, py + vy)
