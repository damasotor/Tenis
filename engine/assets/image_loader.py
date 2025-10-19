import os
import pygame

def load_image(path: str, convert_alpha: bool = True):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Asset no encontrado: {path}")
    img = pygame.image.load(path)
    return img.convert_alpha() if convert_alpha else img.convert()
