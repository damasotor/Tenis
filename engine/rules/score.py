import pygame

POINT_ORDER = ["0", "15", "30", "40", "AD"]

class ScoreManager:
    """
    Lleva la puntuación del game actual (sin sets para simplificar).
    Maneja deuce/ventaja. Expone helpers para dibujar HUD.
    """
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        self.p1 = 0  # cuenta interna en pasos: 0,1,2,3 -> 0,15,30,40 ; 4 = AD
        self.p2 = 0
        self.game_winner = None  # "P1" / "P2" / None

    def _as_str(self, pts: int) -> str:
        idx = min(pts, len(POINT_ORDER)-1)
        return POINT_ORDER[idx]

    def point_for(self, who: str) -> str:
        """
        Suma punto a 'P1' o 'P2'. Devuelve un texto de estado para logs/debug.
        """
        if self.game_winner:
            return "game already ended"

        if who == "P1":
            self._add_p1()
        else:
            self._add_p2()

        return self._state_str()

    def _deuce(self) -> bool:
        return self.p1 >= 3 and self.p2 >= 3 and self.p1 == self.p2

    def _state_str(self) -> str:
        if self.game_winner:
            return f"Game {self.game_winner}"
        if self._deuce():
            return "Deuce"
        if self.p1 >= 4 and self.p2 == 3:
            return "Adv P1"
        if self.p2 >= 4 and self.p1 == 3:
            return "Adv P2"
        return f"{self._as_str(self.p1)} - {self._as_str(self.p2)}"

    def _add_p1(self):
        # deuce/adv reglas
        if self.p2 >= 4 and self.p1 == 3:   # P2 tenía ventaja → vuelve a deuce
            self.p2 = 3
            return
        if self.p1 >= 3 and self.p2 >= 3:
            if self.p1 == 3:   # P1 gana ventaja
                self.p1 = 4
                return
            if self.p1 == 4:   # P1 gana game
                self.game_winner = "P1"
                return
        # progreso normal
        if self.p1 < 3:
            self.p1 += 1
        else:
            # P1 en 40 y P2 < 40 → game
            if self.p2 < 3:
                self.game_winner = "P1"
            else:
                # caso deuce ya cubierto arriba
                pass

    def _add_p2(self):
        if self.p1 >= 4 and self.p2 == 3:   # P1 tenía ventaja → vuelve a deuce
            self.p1 = 3
            return
        if self.p1 >= 3 and self.p2 >= 3:
            if self.p2 == 3:   # P2 gana ventaja
                self.p2 = 4
                return
            if self.p2 == 4:   # P2 gana game
                self.game_winner = "P2"
                return
        if self.p2 < 3:
            self.p2 += 1
        else:
            if self.p1 < 3:
                self.game_winner = "P2"

    # ------------- HUD -------------
    def draw_hud(self, surface: pygame.Surface, font: pygame.font.Font):
        """
        Dibuja un HUD simple centered arriba.
        """
        if self.game_winner:
            text = f"Game {self.game_winner}"
        else:
            if self._deuce():
                text = "DEUCE"
            elif self.p1 >= 4 and self.p2 == 3:
                text = "Adv P1"
            elif self.p2 >= 4 and self.p1 == 3:
                text = "Adv P2"
            else:
                text = f"P1 {self._as_str(self.p1)}  -  P2 {self._as_str(self.p2)}"

        surf = font.render(text, True, (255, 255, 255))
        rect = surf.get_rect(midtop=(surface.get_width() // 2, 12))
        surface.blit(surf, rect)
