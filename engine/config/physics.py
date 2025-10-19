"""
Constantes físicas para spin de la pelota.
Ajustá a gusto para tu “sensación” de tenis.
"""

# Intensidad de efectos al impactar (unidad arbitraria de spin)
SPIN_TOPSPIN = +0.9   # hace caer más rápido (add a_y hacia abajo)
SPIN_SLICE   = -0.7   # cae más lento (reduce a_y, incluso puede subir un poquito al principio)
SPIN_FLAT    =  0.0   # neutro

# Cómo se traduce el spin a aceleraciones por frame
SPIN_GRAVITY_SCALE = 0.12   # cuánto aporta el spin a "gravedad" extra o menor
SPIN_DRIFT_SCALE   = 0.06   # leve deriva lateral (efecto Magnus lateral)

# Decaimiento del spin por frame (0..1): más chico = dura más
SPIN_DECAY = 0.96
