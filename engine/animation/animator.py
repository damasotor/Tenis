# Animator mínimo/dummy:
# - update(anim_name) -> bool  (True = avanzar al siguiente frame)
# - set_fps(anim_name, fps)    (ajusta fps por anim)
#
# Usa pygame.time.get_ticks() y una tabla interna de fps/último tick por anim.

from typing import Dict
import pygame


class Animator:
    def __init__(self, default_fps: int = 10):
        self.default_fps: int = max(1, int(default_fps))
        self._fps: Dict[str, int] = {}          # fps por anim
        self._last_tick: Dict[str, int] = {}    # último tick por anim
        self._accum: Dict[str, float] = {}      # no necesario, pero queda listo por si querés dt real

    def set_fps(self, anim_name: str, fps: int) -> None:
        """Ajusta los FPS de una anim concreta (mínimo 1)."""
        self._fps[anim_name] = max(1, int(fps))

    def _get_fps(self, anim_name: str) -> int:
        return self._fps.get(anim_name, self.default_fps)

    def update(self, anim_name: str) -> bool:
        """
        Devuelve True cuando corresponde avanzar 1 frame de la anim 'anim_name'.
        Política: al primer llamado inicializa el last_tick y NO avanza (evita saltos).
        """
        now = pygame.time.get_ticks()
        fps = self._get_fps(anim_name)
        frame_ms = 1000 // max(1, fps)

        last = self._last_tick.get(anim_name)
        if last is None:
            # Primer llamado: marcar tiempo y no avanzar aún
            self._last_tick[anim_name] = now
            return False

        if (now - last) >= frame_ms:
            # Toca avanzar; rearmamos ventana de tiempo
            # (evitamos drift acumulando múltiplos completos)
            steps = (now - last) // frame_ms
            self._last_tick[anim_name] = last + steps * frame_ms
            return True

        return False
