import random
import time
from math import hypot

class SimpleTennisAI:
    """
    IA muy simple para P2:
      - Intenta alinear world_x/world_y del jugador con la pelota.
      - Tiene una pequeña latencia de reacción y tope de velocidad para sentirse humano.
      - Comete leves "errores" (desvío) para no ser perfecta.
    """
    def __init__(self, player, ball, side="top", 
                 max_speed=2.2,           # píxeles por frame (ajusta a tu escala)
                 react_ms=120,            # latencia de reacción
                 jitter=6,                # desvío aleatorio de puntería
                 catchup_boost=1.35,      # acelera si está muy lejos
                 dead_zone=2.0):          # si está muy cerca, no se mueve
        self.player = player
        self.ball = ball
        self.side = side
        self.max_speed = max_speed
        self.react_ms = react_ms
        self.jitter = jitter
        self.catchup_boost = catchup_boost
        self.dead_zone = dead_zone
        self._next_tick = time.time() + self.react_ms/1000.0
        self._vx = 0.0
        self._vy = 0.0

    def _should_chase(self):
        """
        Lógica simple según el lado de la red:
        - Si la pelota está del lado del rival, nos reubicamos al centro.
        - Si cruza a nuestro lado, la seguimos.
        """
        # Asume que world_y crece hacia "abajo". Ajusta si tu eje es distinto.
        # "top": P2 arriba; "bottom": P2 abajo.
        ball_y = self.ball.world_y
        me_y   = self.player.world_y

        if self.side == "top":
            return ball_y < me_y  # persigue solo si la bola está arriba de él
        else:
            return ball_y > me_y  # persigue solo si la bola está abajo de él

    def update(self):
        now = time.time()
        if now < self._next_tick:
            # Mantiene velocidad anterior hasta próximo "tick" para simular latencia.
            self.player.vx = self._vx
            self.player.vy = self._vy
            return
        self._next_tick = now + self.react_ms/1000.0

        px, py = self.player.world_x, self.player.world_y
        bx, by = self.ball.world_x,   self.ball.world_y

        # Objetivo: si no toca perseguir, posicionarse hacia un "home_y" levemente propio
        # para no quedar clavado. Ajustá estos valores a tu cancha.
        if not self._should_chase():
            target_x = (self.player.home_x if hasattr(self.player, "home_x") else px)
            target_y = (self.player.home_y if hasattr(self.player, "home_y") else py)
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
            # Normaliza y aplica velocidad con pequeño "boost" si está lejos
            vx = (dx / dist)
            vy = (dy / dist)
            speed = self.max_speed * (self.catchup_boost if dist > 40 else 1.0)
            vx *= speed
            vy *= speed

        # Guarda y aplica
        self._vx, self._vy = vx, vy
        self.player.vx = vx
        self.player.vy = vy
