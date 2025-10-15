#El "constructor" se ejecuta UNA VEZ al crear el objeto
import pygame
import os
from engine.game_object import GameObject
from engine.utils.screen import world_to_screen

# Inicializar Pygame
pygame.init()

class Player(GameObject):
    def __init__(self, x, y, field, jugador2=False):
        #self se refiere al objeto específico que se está creando
        json_path = os.path.join('assets', 'sprites', 'player_animation', 'player.json')
        super().__init__(x, y, json_path=json_path)
        self.world_x = x
        self.world_y = y
        self.field = field
        self.is_player2 = jugador2
        #self.rect = pygame.Rect(x, y, ancho, alto)
        #self.color = color
        self.velocidad = 8
        
        # 🎾 NUEVO: Rectángulo para la raqueta (asumimos que la raqueta está en el centro/parte superior del cuerpo)
        # Esto es conceptual, ajusta las dimensiones según el sprite
        self.racket_rect = self.rect.copy()
        self.racket_rect.width = self.rect.width // 2
        self.racket_rect.height = self.rect.height // 3
        self.racket_rect.centerx = self.rect.centerx
        self.racket_rect.top = self.rect.top - 5 # Un poco por encima del jugador

        #Definir animación inicial según el jugador
        if self.is_player2:
            self.current_animation = "idle-P2"
        else:
            self.current_animation = "idle"

        #Inicializar frame correctamente
        self.frame_index = 0

    def mover(self, teclas):
        moved = False

        #Teclas diferentes para jugador2
        if self.is_player2:
            izquierda = teclas[pygame.K_a]
            derecha = teclas[pygame.K_d]
            arriba = teclas[pygame.K_w]
            abajo = teclas[pygame.K_s]
        else:
            izquierda = teclas[pygame.K_LEFT]
            derecha = teclas[pygame.K_RIGHT]
            arriba = teclas[pygame.K_UP]
            abajo = teclas[pygame.K_DOWN]

        if izquierda:
            self.world_x -= self.velocidad
            if self.is_player2:
                self.current_animation = "walk-left-P2"
            else:
                self.current_animation = "walk-left"
            moved = True

        if derecha:
            self.world_x += self.velocidad
            if self.is_player2:
                self.current_animation = "walk-right-P2"
            else:
                self.current_animation = "walk-right"
            moved = True

        if arriba:
            self.world_y -= self.velocidad
            moved = True

        if abajo:
            self.world_y += self.velocidad
            moved = True

        #Limitar la mitad de la cancha según el jugador
    
        net_y = self.field.net_y
        if self.is_player2:
            if self.world_y > net_y - 1:
                self.world_y = net_y - 1
        else:
            if self.world_y < net_y + 1:
                self.world_y = net_y + 1

        # Si el jugador se movió, actualizamos frame
        if moved:
            self.frame_index = (self.frame_index + 1) % len(self.animations[self.current_animation])
            #print("Frame actual:", self.frame_index)

        # Convertir coordenadas del mundo → pantalla
        iso_x, iso_y = world_to_screen(self.world_x, self.world_y)

        # Actualizar posición en pantalla (centrar personaje)
        self.rect.center = (iso_x, iso_y)
        
        # Actualizar la posición del rect de la raqueta junto con el cuerpo
        self.racket_rect.centerx = self.rect.centerx
        self.racket_rect.top = self.rect.top - 5

    def check_ball_collision(self, ball):
        """
        Verifica la colisión de la pelota. 
        Prioriza la raqueta sobre el cuerpo.
        """
        
        # Colisión con la raqueta
        if ball.rect.colliderect(self.racket_rect):
            # Para evitar que se quede pegada
            if ball.rect.centerx < self.racket_rect.centerx:
                ball.rect.right = self.racket_rect.left - 1
            else:
                ball.rect.left = self.racket_rect.right + 1
            
            ball.on_racket_hit()
            return True 
            
        # Colisión con el cuerpo baja prioridad
        elif ball.rect.colliderect(self.rect):
            # el choque
            if ball.rect.centerx < self.rect.centerx:
                ball.rect.right = self.rect.left - 1
            else:
                ball.rect.left = self.rect.right + 1
                
            ball.on_body_hit()
            return True

        return False # No hubo colisión
