# Coloca esta clase en un archivo 'engine/score.py' y asegúrate de importarla
# O, si no tienes un archivo separado, colócala en 'engine/game.py'
class ScoreManager:
    """Gestiona la puntuación de un juego de tenis (0, 15, 30, 40, Deuce, Adv, Game)."""

    # La puntuación de tenis se mapea internamente a 0, 1, 2, 3 puntos.
    SCORES = {0: "0", 1: "15", 2: "30", 3: "40"}
    
    def __init__(self, player1_name="P1", player2_name="P2"):
        self.player1_name = player1_name
        self.player2_name = player2_name
        self.reset_game()
        
    def reset_game(self):
        """Reinicia la puntuación de un juego."""
        self.p1_points = 0  # 0, 1, 2, 3...
        self.p2_points = 0
        self.game_winner = None # 'P1', 'P2', o None
        
    def point_for(self, winner: str):
        """Suma un punto al jugador ganador y verifica si se termina el juego."""
        if self.game_winner:
            return 

        if winner == self.player1_name:
            self.p1_points += 1
        elif winner == self.player2_name:
            self.p2_points += 1
        else:
            return

        self._check_game_end()
        
    def _check_game_end(self):
        p1 = self.p1_points
        p2 = self.p2_points
        
        # Lógica de Deuce/Ventaja
        if p1 >= 3 and p2 >= 3:
            diff = abs(p1 - p2)
            
            # Ganar el juego (2 puntos de ventaja después del 40-40)
            if diff >= 2:
                self.game_winner = self.player1_name if p1 > p2 else self.player2_name
            
        # Ganar el juego sin Deuce (ej: 40-0, 40-30)
        elif p1 >= 4:
            self.game_winner = self.player1_name
        elif p2 >= 4:
            self.game_winner = self.player2_name

    def get_score_str(self) -> str:
        """Devuelve la puntuación actual en formato de texto (ej: "15-30" o "Advantage P1")."""
        if self.game_winner:
            return f"Game {self.game_winner}"

        p1 = self.p1_points
        p2 = self.p2_points
        
        # Caso Deuce / Ventaja
        if p1 >= 3 and p2 >= 3:
            if p1 == p2:
                return "Deuce"
            elif p1 > p2:
                return "Advantage P1"
            else:
                return "Advantage P2"
                
        # Puntuación normal (0, 15, 30, 40)
        score1 = self.SCORES.get(p1, "40+")
        score2 = self.SCORES.get(p2, "40+")
        
        return f"{score1}-{score2}"
