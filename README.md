# 🎾 Proyecto: Videojuego 2D – *Tennis Isométrico*

## 🧩 Descripción general
Juego 2D en desarrollo construido con **Pygame**, que simula un partido de tenis en vista isométrica.  
Incluye sistema de audio avanzado (música, efectos, crowd), detección de colisiones, control de dos jugadores y menú de opciones interactivo.

---

## ⚙️ Requisitos y ejecución

### 🔧 Dependencias principales
- Python 3.10+
- Pygame  
  ```bash
  pip install pygame
  ```
- (Opcional) Pydub si generás o modificás efectos:  
  ```bash
  pip install pydub
  ```

### ▶️ Cómo ejecutar
Desde la raíz del proyecto:
```bash
python main.py
```

---

## 🕹️ Controles principales

| Acción | Tecla(s) |
|--------|-----------|
| Mover Jugador 1 | Flechas ⬆️⬇️⬅️➡️ |
| Mover Jugador 2 | W / A / S / D |
| Pausa / Reanudar | `Esc` o `P` |
| Volumen Música | `1` (−) / `2` (+) |
| Volumen SFX | `3` (−) / `4` (+) |
| Mute Música | `M` |
| Mostrar límites de debug | `F1` |

---

## 🧪 Hotkeys de test (solo con `debug_audio=True`)

| Hotkey | Acción |
|--------|--------|
| `V` | Sonido de saque |
| `H` | Simula golpe de raqueta |
| `B` | Rebote en cancha |
| `N` | Toque de red + crowd *“ooh”* |
| `O` | Simula pelota fuera (out) |
| `P` | Simula punto anotado |
| `C` | Crowd *“ooh”* |
| `F` | Crowd *“ahh”* |
| `K` | Sting de match point |
| `G` | Jingle de victoria |
| `L` | Jingle de derrota |

---

## 🎛 Configuraciones de audio y debug (`engine/game.py`)

- `self.debug_audio`  
  Si está en `True`, habilita las hotkeys internas para probar sonidos (`v`, `b`, `n`, `f`, etc.).  
  Poner en `False` para la versión jugable o entregas finales.

- `self.use_crowd_ambience`  
  Controla la música de fondo durante el juego.  
  - `True`: usa `crowd_loop.wav` (ambiente de público).  
  - `False`: usa `ingame_music.wav` (si existe) o, como fallback, el crowd.

---

## 🎵 Archivos de audio esperados (`assets/audio/`)

| Archivo | Uso |
|----------|-----|
| `menu_music.wav` | Música del menú principal |
| `crowd_loop.wav` | Ambiente de público continuo |
| `ingame_music.wav` | Tema instrumental (nuevo, fondo del partido) |
| `serve.wav` / `serve2.wav` | Sonido de saque |
| `hit_racket*.wav` | Golpes de raqueta (variantes) |
| `net_touch.wav` | Toque de red |
| `out_whistle.wav` | Pelota fuera |
| `score_jingle.wav` | Jingle de punto |
| `crowd_ooh.wav` / `crowd_ahh.wav` | Reacciones del público |
| `win_jingle.wav` / `lose_jingle.wav` | Fin del partido |
| `sting_match.wav` | Match point o set point |

---

## 💾 Persistencia de audio
Los niveles de volumen se guardan en `assets/audio_config.json`.  
El juego los actualiza al salir o al guardar desde el menú de opciones.

---

## 🧠 Notas técnicas
- El rebote con la red tiene resolución de penetración y cooldown de sonido.  
- Las velocidades mínima y máxima de la pelota están limitadas para evitar bloqueos.  
- El sistema de audio usa **ducking** para bajar temporalmente la música cuando suenan efectos importantes.

---

## 👥 Equipo y mantenimiento
- Proyecto académico desarrollado en el marco del curso de Videojuegos 2D.  
- Colaboradores: 
