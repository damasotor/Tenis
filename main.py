import os
import sys
import pygame
from engine.game import Game

if __name__ == "__main__":
    # Fijar el directorio de trabajo al del archivo (rutas relativas estables)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Inicializar Pygame (audio y video)
    pygame.init()
    
    try:
        game = Game()
        game.game_loop()
    except Exception as e:
        # Log simple a stderr para depurar si algo truena
        print(f"[ERROR] {e}", file=sys.stderr)
        raise
    finally:
        pygame.quit()
