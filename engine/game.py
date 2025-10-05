import pygame

from engine.player import Player
from engine.field import Field
from engine.utils.colors import ROJO, AZUL, AZUL_OSCURO, BLANCO
from engine.utils.screen import ANCHO, ALTO


class Game:
    def __init__(self):
        #3.Definir el tamaño de la ventana
        self.PANTALLA = pygame.display.set_mode((ANCHO, ALTO))

        #4.Ponerle un título a la ventana
        pygame.display.set_caption('Tennis Isométrico en contrucción...')

        self.field = Field(6, 10)
        self.jugador1 = Player(ANCHO / 3 + 185, ALTO / 2 - 25, field=self.field, jugador2=False)
        self.jugador2 = Player(ANCHO / 3 + 185, ALTO / 2 - 450, field=self.field, jugador2=True)
        self.reloj = pygame.time.Clock()
        self.estado_juego = 'jugando'

    def game_loop(self):
        ejecutando = True
        while ejecutando:
            # Obtener el tiempo transcurrido, aunque no lo usemos para la animación
            # es una buena práctica para mantener el bucle constante.
            dt = self.reloj.tick(15)  # Menor FPS para ver mejor el cambio de frame

            # --- INPUT: Siempre procesar eventos ---
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False

            # --- Lógica del juego ---
            if self.estado_juego == 'jugando':
                teclas = pygame.key.get_pressed()
                self.jugador1.mover(teclas)
                self.jugador2.mover(teclas)
                # No llamamos a update, ya que el movimiento se encarga de la animación

            # --- Renderizado ---
            self.PANTALLA.fill(AZUL_OSCURO)

            
            #self.jugador.draw(self.PANTALLA)
            self.field.draw(self.PANTALLA)
            self.jugador1.draw(self.PANTALLA)
            self.jugador2.draw(self.PANTALLA)
            pygame.display.flip()
