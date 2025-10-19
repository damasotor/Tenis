"""
Parámetros de colisiones (tunables sin tocar el código de Player).
Valores pensados para sprites humanoides ~48–64 px de alto.
Ajustá a gusto si tus sprites cambian.
"""

# Escalado de la caja de CUERPO (porcentaje del frame actual)
BODY_W_SCALE = 0.55     # ancho ~55% del frame
BODY_H_SCALE = 0.80     # alto  ~80% del frame

# Offset relativo de la caja de CUERPO (en px respecto al rect del frame)
BODY_Y_OFFSET = 4       # empuja la caja un poco hacia abajo

# Escalado de la caja de RAQUETA
RACKET_W_SCALE = 0.40   # bastante angosta para ser “canto” de raqueta
RACKET_H_SCALE = 0.28   # poco alta (zona de contacto)
# Offset en px relativo al rect del frame
RACKET_Y_OFFSET = -6    # arriba del cuerpo (negativo = hacia arriba)

# Debug color (solo si el juego activa _debug_bounds)
COLOR_BODY   = (50, 220, 60)    # verde
COLOR_RACKET = (240, 200, 40)   # amarillo
