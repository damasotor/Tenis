# main.py
import pygame
from engine.game import Game

if __name__ == '__main__':
    # Creación y ejecución del juego
    game = Game()
    game.game_loop()

    # Salir de Pygame al terminar
    pygame.quit()