import pygame
from typing import Optional, Tuple, Dict, Any, List

try:
    # Colores y tamaño de pantalla si existen en tu proyecto
    from engine.utils.colors import BLANCO
    from engine.utils.screen import ANCHO, ALTO
except Exception:
    BLANCO = (255, 255, 255)
    ANCHO, ALTO = 1280, 720  # fallback


class MenuScreen:
    """
    Menú principal con selección de modo 1P/2P (opcional).
    Integra audio UI si se provee un AudioManager (play_sound).

    Uso típico desde Game:
      self.menu = MenuScreen(self.PANTALLA, self.audio)
      self.menu.open()
      # en loop:
      action = self.menu.handle_event(evento)
      if action: self._on_menu_action(action)
      self.menu.update(dt)
      self.menu.render()

    Donde _on_menu_action puede hacer:
      if action[0] == "start":
          self.modo = action[1]["mode"]  # "1P" o "2P"
          self.estado_juego = "jugando"
          self._set_music_state("ingame")
          self._start_new_rally()
      elif action[0] == "options":
          self.estado_juego = "opciones"
      elif action[0] == "quit":
          pygame.event.post(pygame.event.Event(pygame.QUIT))
    """

    def __init__(self, screen: pygame.Surface, audio=None,
                 font_title: Optional[pygame.font.Font] = None,
                 font_item: Optional[pygame.font.Font] = None,
                 font_small: Optional[pygame.font.Font] = None):
        self.screen = screen
        self.audio = audio

        # Fuentes
        self.font_title = font_title or pygame.font.Font(None, 64)
        self.font_item  = font_item  or pygame.font.Font(None, 44)
        self.font_small = font_small or pygame.font.Font(None, 28)

        # Ítems del menú (texto, acción, payload opcional)
        self.items: List[Tuple[str, str, Dict[str, Any]]] = [
            ("1 Jugador",  "start",   {"mode": "1P"}),
            ("2 Jugadores","start",   {"mode": "2P"}),
            ("Opciones",   "options", {}),
            ("Salir",      "quit",    {}),
        ]
        self.index = 0
        self._opened = False

        # Efecto visual simple
        self._sel_tick = 0.0

        # Tips / ayuda en pantalla
        self.footer_lines = [
            "↑/↓ para moverte · Enter para seleccionar · Esc para salir",
            "Atajo rápido: 1 → 1 Jugador | 2 → 2 Jugadores",
        ]

    # --------------- Ciclo de vida ---------------
    def open(self):
        self._opened = True
        self.index = 0
        self._sel_tick = 0.0

    def close(self):
        self._opened = False

    # --------------- Entrada ---------------
    def handle_event(self, event: pygame.event.Event) -> Optional[Tuple[str, Dict[str, Any]]]:
        if not self._opened:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._move(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._move(+1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._select()
            elif event.key == pygame.K_ESCAPE:
                self._play("ui_back")
                return ("quit", {})
            # Atajos
            elif event.key == pygame.K_1:
                return self._select_direct("1P")
            elif event.key == pygame.K_2:
                return self._select_direct("2P")

        return None

    def _move(self, delta: int):
        self.index = (self.index + delta) % len(self.items)
        self._play("ui_move")

    def _select(self) -> Tuple[str, Dict[str, Any]]:
        text, action, payload = self.items[self.index]
        self._play("ui_select")
        return (action, payload)

    def _select_direct(self, mode: str) -> Tuple[str, Dict[str, Any]]:
        # Devuelve directamente acción start con el modo forzado
        self._play("ui_select")
        return ("start", {"mode": mode})

    def _play(self, key: str):
        if self.audio and hasattr(self.audio, "play_sound"):
            try:
                self.audio.play_sound(key)
            except Exception:
                pass

    # --------------- Lógica ---------------
    def update(self, dt_ms: int):
        if not self._opened:
            return
        # Animación simple para el selector
        self._sel_tick = (self._sel_tick + dt_ms / 1000.0) % 1.0

    # --------------- Dibujo ---------------
    def render(self):
        if not self._opened:
            return

        cx = ANCHO // 2
        # Título
        title_surf = self.font_title.render("Tennis Isométrico", True, BLANCO)
        self.screen.blit(title_surf, title_surf.get_rect(center=(cx, 140)))

        # Items
        base_y = 260
        gap = 60
        for i, (text, _action, payload) in enumerate(self.items):
            sel = (i == self.index)
            label = f"> {text} <" if sel else f"  {text}  "
            surf = self.font_item.render(label, True, BLANCO)
            self.screen.blit(surf, surf.get_rect(center=(cx, base_y + i * gap)))

            # Subtexto del modo (para 1P/2P)
            if _action == "start" and "mode" in payload:
                mode = payload["mode"]
                subtitle = "(contra IA)" if mode == "1P" else "(dos jugadores locales)"
                sub = self.font_small.render(subtitle, True, BLANCO)
                self.screen.blit(sub, sub.get_rect(center=(cx, base_y + i * gap + 28)))

        # Footer / ayuda
        fy = base_y + gap * len(self.items) + 36
        for line in self.footer_lines:
            s = self.font_small.render(line, True, BLANCO)
            self.screen.blit(s, s.get_rect(center=(cx, fy)))
            fy += 26

        # Indicador animado (pequeño brillo debajo del item seleccionado)
        sel_y = base_y + self.index * gap + 20
        w = int(180 + 20 * (0.5 - abs(self._sel_tick - 0.5)))  # respira
        glow = pygame.Surface((w, 6), pygame.SRCALPHA)
        glow.fill((255, 255, 255, 90))
        self.screen.blit(glow, glow.get_rect(center=(cx, sel_y + 30)))


# ----------- Helper opcional -----------
def run_standalone():
    """
    Permite probar el menú de forma aislada:
      python -m engine.menu
    """
    pygame.init()
    screen = pygame.display.set_mode((ANCHO, ALTO))
    clock = pygame.time.Clock()
    menu = MenuScreen(screen, audio=None)
    menu.open()

    running = True
    while running:
        dt = clock.tick(60)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            else:
                action = menu.handle_event(e)
                if action:
                    print("[Menu action]", action)
                    if action[0] == "quit":
                        running = False

        screen.fill((20, 30, 50))
        menu.update(dt)
        menu.render()
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run_standalone()
