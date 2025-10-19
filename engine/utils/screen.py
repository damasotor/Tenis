ANCHO, ALTO = 800, 600
SCALE = 50

# Intentamos reutilizar la proyección centralizada del motor.
# Si todavía no existe engine/utils/iso.py o falla el import por paths,
# usamos las funciones locales (no se rompe nada).
try:
    from engine.utils.iso import world_to_screen, screen_to_world  # reexport
except Exception:
    def world_to_screen(x, y):
        iso_x = x - y
        iso_y = (x + y) / 2
        return iso_x, iso_y

    # Ya que estamos, dejamos también la inversa como util local.
    def screen_to_world(iso_x, iso_y):
        # iso_x = x - y
        # iso_y = (x + y) / 2  => x + y = 2*iso_y
        # sumando: 2x = iso_x + 2*iso_y
        x = (iso_x + 2 * iso_y) / 2
        y = x - iso_x
        return x, y
