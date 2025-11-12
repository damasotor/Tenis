# README — Tennis Isométrico (Pygame)

Guía para levantar el proyecto en **Windows, macOS o Linux**.

## 1) Requisitos

- **Python 3.10+**
- **pip** (incluido con Python)
- **Virtualenv** (opcional pero recomendado)
- **SDL / audio**:
  - Windows/macOS: ya viene con Pygame.
  - Linux: instalar librerías de audio si hace falta (`sudo apt install libsdl2-mixer-2.0-0 libasound2`).

## 2) Clonar y entrar

```bash
git clone <tu-repo>
cd <tu-repo>
```

> Si no tenés las fuentes DejaVu, el juego hace *fallback* a una fuente del sistema.

## 3) Instalación y ejecución rápida

### Desde la raíz del proyecto, ejecutá

```bash
# Crear entorno limpio
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
python3 -m pip install pygame pillow

# Ejecutar el juego
python3 main.py
```

> 🧩 Alternativamente, podés usar pip install -r requirements.txt ya que el archivo ya incluye pygame y pillow.

## 4) Variables de entorno útiles

- `VJ2D_MODO` para arrancar en 1P o 2P.
  - Valores: `1P` o `2P`
- `VJ2D_DEBUG_AUDIO` para habilitar teclas de prueba de sonidos.
  - Valores: `1` habilita, `0` deshabilita

Ejemplos:

```bash
# macOS/Linux
export VJ2D_MODO=1P
export VJ2D_DEBUG_AUDIO=1
# Windows PowerShell
$env:VJ2D_MODO="1P"
$env:VJ2D_DEBUG_AUDIO="1"
```

## 5) Ejecutar

```bash
python main.py
```

Al primer arranque se crean o leen:

- `assets/audio_config.json` para volúmenes.
- `assets/game_config.json` para el modo 1P/2P.

## 6) Controles

### Menú principal

- `↑/↓` mover
- `Enter` seleccionar
- `Esc` salir

### Opciones

- Fila seleccionada queda **resaltada** con una banda clara que cubre **etiqueta + slider + porcentaje**.
- `↑/↓` cambiar de fila
- `←/→` ajustar valor
- Botones inferiores:
  - **APLICAR** guarda cambios y vuelve al menú
  - **VOLVER** descarta cambios y vuelve al menú

### Partida

- `WASD` o flechas para mover jugadores humanos
- `Espacio` secuencia de saque P1
- `F` secuencia de saque P2 (debug o 2P)
- `Esc` o `P` pausa
  - En pausa: `Esc/P` continuar, `Enter` volver al menú

### Atajos y debug

- `F1` mostrar límites y debug de cancha
- `F3` alternar overlay de botes si está disponible
- `M` mute global
- Mezcla rápida:
  - `1` baja música
  - `2` sube música
  - `3` baja SFX
  - `4` sube SFX

> Si `VJ2D_DEBUG_AUDIO=1`, también:  
`V` sirve, `H` golpe, `B` pique, `N` red, `O` out, `P` punto, `K` sting, `G` cuenta 3-2-1 de reinicio.

## 7) Cómo funciona el menú de Opciones

- Hay 4 filas: **Modo**, **Música**, **SFX**, **UI**.
- **Modo** conmuta `1P` ↔ `2P` con `←/→`.
- Las 3 barras de audio ajustan valores locales.  
  No se escriben en disco ni se aplican al mixer hasta **APLICAR**.
- **APLICAR**:
  - persiste `assets/audio_config.json`
  - persiste `assets/game_config.json` con el modo
  - aplica los volúmenes al mixer
- **VOLVER**:
  - descarta todo y restaura el *snapshot* previo

## 8) Solución de problemas

- **No suena el audio en Linux**  
  Instalar dependencias de SDL y ALSA:

  ```bash
  sudo apt update
  sudo apt install libsdl2-mixer-2.0-0 libasound2
  ```

- **Pygame no encuentra la música**  
  Verificá rutas dentro de `assets/audio/` y nombres de archivo.
- **Fuentes no encontradas**  
  Asegurate de tener `assets/fonts/DejaVuSans.ttf` y `DejaVuSans-Bold.ttf`.  
  Si no, se usa una fuente del sistema. Podés cambiar las rutas en la sección de fuentes.

---
