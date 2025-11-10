import pygame

class RestartCountdown:
    """
    Overlay de cuenta regresiva simple (3-2-1) en ms.
    Llamar a start() para iniciar. update(dt) y draw(surface) en cada frame.
    Cuando termina, dispara el callback on_finished().
    """
    def __init__(self, on_finished, total_ms=3000):
        self.on_finished = on_finished
        self.total_ms = int(total_ms)
        self.remaining = 0
        self.active = False
        self._font_big = pygame.font.Font(None, 140)
        self._font_small = pygame.font.Font(None, 36)

    def start(self, total_ms=None):
        if total_ms is not None:
            self.total_ms = int(total_ms)
        self.remaining = self.total_ms
        self.active = True

    def cancel(self):
        self.active = False
        self.remaining = 0

    def update(self, dt_ms):
        if not self.active:
            return
        self.remaining = max(0, self.remaining - int(dt_ms))
        if self.remaining == 0:
            self.active = False
            if self.on_finished:
                self.on_finished()

    def draw(self, surface: pygame.Surface, msg_top="Reiniciando partida"):
        if not self.active:
            return
        # número actual (ceil de segundos restantes)
        secs = max(1, (self.remaining + 999) // 1000)
        W, H = surface.get_width(), surface.get_height()

        # oscurecer fondo sutil
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        # textos
        t_top = self._font_small.render(msg_top, True, (255, 255, 255))
        t_n   = self._font_big.render(str(secs), True, (255, 255, 255))

        surface.blit(t_top, t_top.get_rect(center=(W // 2, H // 2 - 90)))
        surface.blit(t_n,   t_n.get_rect(center=(W // 2, H // 2)))
