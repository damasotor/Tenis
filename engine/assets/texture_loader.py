import os
import pygame
from typing import Dict, Tuple

# Cache simple para evitar recargar la misma textura varias veces
_TEXTURE_CACHE: Dict[Tuple[str, bool], pygame.Surface] = {}


def load_texture(path: str, *, with_alpha: bool = False) -> pygame.Surface:
    """
    Carga una textura desde disco con conversión optimizada para blits rápidos.

    Por defecto utiliza convert() (sin alpha) ideal para fondos, canchas o superficies grandes.
    Si necesitás mantener el canal alfa (transparencias parciales), pasá with_alpha=True.

    La función cachea la textura por (ruta, with_alpha) para evitar recargas repetidas.

    Args:
        path: Ruta absoluta o relativa al archivo de imagen.
        with_alpha: True para usar convert_alpha() (mantiene canal alpha).

    Returns:
        pygame.Surface lista para blitear.

    Raises:
        FileNotFoundError: si la ruta no existe.
        pygame.error: si pygame no puede cargar el archivo.
    """
    norm_path = os.path.normpath(path)

    if not os.path.exists(norm_path):
        raise FileNotFoundError(f"Textura no encontrada: {norm_path}")

    # Retorno desde cache si ya fue cargada
    cached = _TEXTURE_CACHE.get((norm_path, with_alpha))
    if cached is not None:
        return cached

    # Asegurar inicialización de display (algunos modos headless fallan)
    if not pygame.get_init():
        pygame.init()

    # Carga cruda
    surf = pygame.image.load(norm_path)

    # Convertir según necesidad de alpha
    if with_alpha:
        surf = surf.convert_alpha()
    else:
        # Para texturas grandes (fondos), convert() suele rendir mejor
        surf = surf.convert_alpha()

    # Guardar en cache
    _TEXTURE_CACHE[(norm_path, with_alpha)] = surf
    return surf
