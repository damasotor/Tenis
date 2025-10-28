# 🎾 Proyecto: Videojuego 2D – *Tennis Isométrico*

## 🧩 Descripción general
Juego 2D en desarrollo construido con **Pygame**, que simula un partido de tenis en vista isométrica.  
Incluye sistema de audio avanzado (música, efectos, crowd), detección de colisiones, IA del jugador 2, control de dos jugadores y menú de opciones interactivo.  
La versión actual implementa mejoras en física, detección de red, conteo de puntos, reinicio 3–2–1 y fallbacks gráficos seguros.

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
| Mover Jugador 2 | W / A / S / D (modo 2P) |
| Pausa / Reanudar | `Esc` o `P` |
| Volumen Música | `1` (−) / `2` (+) |
| Volumen SFX | `3` (−) / `4` (+) |
| Mute Global | `M` |
| Mostrar límites de debug | `F1` |
| Mostrar rebotes IN/OUT | `F3` |
| Reinicio rápido (debug) | `G` → cuenta regresiva 3–2–1 |

---

## 🧪 Hotkeys de test (solo con `debug_audio=True`)

| Hotkey | Acción |
|--------|--------|
| `V` | Sonido de saque |
| `H` | Simula golpe de raqueta |
| `B` | Rebote en cancha |
| `N` | Toque de red (tape/body) + crowd *“ooh”* |
| `O` | Simula pelota fuera (out) |
| `P` | Simula punto anotado |
| `C` | Crowd *“ooh”* |
| `F` | Crowd *“ahh”* |
| `K` | Sting de match point |
| `G` | Reinicio 3–2–1 (debug) |
| `L` | Jingle de derrota |

---

## 🎮 IA del Jugador 2 (modo 1P)
- La IA de P2 se activa automáticamente en modo 1P (`VJ2D_MODO=1P`).
- Persigue la pelota con latencia y leve error de puntería (no perfecta).
- En modo 2P (`VJ2D_MODO=2P`), ambos jugadores son humanos.

---

## 🕸️ Red y colisiones
- La red se divide en dos zonas: **cinta superior** (permite paso con pérdida de energía y sonido `net_tape`) y **cuerpo** (rebota hacia atrás con `net_body`).  
- La consola ya no muestra spam de logs (`Rect red lógica...`).  
- Colisiones precisas basadas en `circle_rect_collision` y `circle_rect_mtv`.

---

## 🏐 Piques, OUT y “ground_y”
- El suelo ahora se sincroniza con `field.get_court_rect().bottom`, garantizando rebotes precisos sobre la cancha visible.  
- Si la pelota pica fuera del rect del court, se marca **OUT** y se asigna punto al rival del último golpeador.  
- El sistema de debug (`F3`) muestra un overlay visual de piques IN/OUT.

---

## 💥 Golpe al cuerpo (Body Hit)
- Si la pelota impacta directamente en el cuerpo de un jugador, se reproduce un efecto corto (`bounce_court`) y se adjudica **punto automático al rival**.  
- El score HUD se actualiza correctamente.  

---

## 🔊 Audio
- Sistema de audio centralizado (grupos: `music`, `sfx`, `ui`, `amb`).  
- Persistencia automática en `assets/audio_config.json`.  
- Volúmenes ajustables con teclas 1–4 y mute global con `M`.  
- Nueva carga de SFX de red: `net_tape.wav` y `net_body.wav`.  
- Se conserva el estado de mute/volumen al reiniciar el juego.

---

## 🎵 Archivos de audio esperados (`assets/audio/`)

| Archivo | Uso |
|----------|-----|
| `menu_music.wav` | Música del menú principal |
| `crowd_loop.wav` | Ambiente de público continuo |
| `ingame_music.wav` | Música del partido |
| `serve.wav` / `serve2.wav` | Saque |
| `hit_racket*.wav` | Golpes de raqueta |
| `net_tape.wav` / `net_body.wav` | Colisiones con red |
| `out_whistle.wav` | Pelota fuera |
| `score_jingle.wav` | Jingle de punto |
| `crowd_ooh.wav` / `crowd_ahh.wav` | Reacciones del público |
| `win_jingle.wav` / `lose_jingle.wav` | Fin del partido |
| `sting_match.wav` | Punto decisivo |

---

## 🧩 Texturas opcionales (`assets/texturas/`)

| Archivo | Uso |
|----------|-----|
| `Cancha.png` | Fondo del campo principal |
| `red.png` | Textura de la red central |

> 🔧 Si no existen, se usan **fallbacks sólidos** (colores planos).  
> No son requeridos para jugar, pero mejoran la presentación visual.

---

## 💾 Persistencia
El volumen y configuración de sonido se guardan automáticamente en `assets/audio_config.json`.  
Ejemplo de configuración actual por defecto:
```json
{
  "music": 0.40,
  "sfx": 0.85,
  "ui": 0.70
}
```

---

## ⚙️ Debug y herramientas
- `F1` muestra hitboxes de jugadores y red.  
- `F3` activa overlay de piques IN/OUT.  
- `G` activa cuenta regresiva 3–2–1 para reinicio rápido (debug).  
- `M` mutea/desmutea todos los sonidos.

---

## 🧠 Notas técnicas
- `Ball.ground_y` se sincroniza con el rect real del campo (`court_rect.bottom`).  
- `Ball.on_body_hit()` asigna punto automáticamente según `last_hitter`.  
- `Player.update_racket()` ajusta offset de raqueta (1.6x).  
- `SimpleTennisAI.update()` reemplaza controles humanos en modo 1P.  
- `Net.update()` limpia logs por frame.  
- Persistencia de audio en `assets/audio_config.json`.
- Documentación adicional en `docs/ASSETS.md`.

---

## 👥 Equipo y mantenimiento
Proyecto académico desarrollado en el marco del curso de *Videojuegos 2D*.  
**Colaboradores:** equipo de desarrollo VJ2D (2025).  
