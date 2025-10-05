import pygame
import os
import json
import collections


class GameObject:
    def __init__(self, x, y, json_path):
        self.x = x
        self.y = y
        self.sprite_sheet = None
        self.animations = {}
        self.current_animation = 'idle'
        self.frame_index = 0
        self.rect = None
        self.load_from_json(json_path)

    def load_from_json(self, json_path):
        """
        Carga la spritesheet y los datos de animación desde un archivo JSON.
        Ahora maneja la ruta relativa de forma segura.
        """
        try:
            # os.path.dirname obtiene la carpeta del JSON
            base_dir = os.path.dirname(os.path.abspath(json_path))
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Usamos os.path.join para construir una ruta multiplataforma segura
            spritesheet_path_relative = data.get('spritesheet_path')
            # Quitamos la ruta absoluta que tenías en el JSON para hacerlo portable
            spritesheet_path = os.path.join(base_dir, os.path.basename(spritesheet_path_relative))

            # Cargar la imagen
            self.sprite_sheet = pygame.image.load(spritesheet_path).convert_alpha()

            self.animations = collections.defaultdict(list)
            for anim_name, anim_list in data.get('animations', {}).items():
                for sprite_data in anim_list:
                    # Guardamos las coordenadas de cada sprite como una tupla
                    self.animations[anim_name].append(
                        (sprite_data['x'], sprite_data['y'], sprite_data['width'], sprite_data['height'])
                    )

            if not self.animations:
                raise ValueError("No se encontraron animaciones válidas en el JSON.")

            # Establecer la animación inicial y el rectángulo de colisión
            self.current_animation = 'idle' if 'idle' in self.animations else list(self.animations.keys())[0]
            first_frame_rect_data = self.animations[self.current_animation][0]
            self.rect = pygame.Rect(self.x, self.y, first_frame_rect_data[2], first_frame_rect_data[3])

        except FileNotFoundError:
            print(f"Error: El archivo JSON o la spritesheet no fue encontrado en '{json_path}'.")
            self.sprite_sheet = None
            self.animations = {}
        except Exception as e:
            print(f"Error al cargar el JSON: {e}")
            self.sprite_sheet = None
            self.animations = {}

    def draw(self, surface):
        """
        Dibuja el fotograma actual en la pantalla.
        """
        if not self.sprite_sheet or not self.animations or not self.rect: return

        frame_rect_data = self.animations[self.current_animation][self.frame_index]
        # Usamos subsurface para extraer el sprite correcto de la hoja
        frame = self.sprite_sheet.subsurface(pygame.Rect(frame_rect_data))
        surface.blit(frame, self.rect)
