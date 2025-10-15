# main.py
import os
import pygame
from engine.game import Game

if __name__ == "__main__":
    # Fijar el directorio de trabajo al del archivo (rutas relativas estables)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Inicializar Pygame
    pygame.init()

    try:
        game = Game()
        game.game_loop()
    finally:
        pygame.quit()
