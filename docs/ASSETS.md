
# 🎨 Assets del proyecto (VJ2D)

Actualmente el proyecto funciona **sin texturas obligatorias**, utilizando fallbacks sólidos para permitir ejecución inmediata incluso sin recursos externos.

---

## 🏟️ Cancha

- **Esperado:** `assets/texturas/Cancha.png`  
- **Uso:** textura principal del campo de juego (`Field`)  
- **Fallback:** `screen.fill((0, 180, 0))` si falta  

> 🔧 Si se desea compartir con el equipo o mostrar una build final, colocar los PNG
> correspondientes (tamaño aprox. 1024x768 o similar para la cancha).

---

## 🕸️ Red

- **Esperado:** `assets/texturas/red.png`  
- **Uso:** textura visual de la red (`Net`)  
- **Fallback:** `pygame.draw.rect(..., (255, 0, 0))` si falta  

> 🧩 Recomendado tamaño aproximado: 512x512 px, con transparencia alpha.

---

## 🎧 Audio

Los archivos `.wav` del subdirectorio `assets/audio/` ya están referenciados y validados por el motor de sonido (`AudioManager`).

| Archivo | Obligatorio | Descripción |
|----------|--------------|-------------|
| `serve.wav` | ✅ | Sonido de saque. |
| `hit_racket.wav` | ✅ | Golpe de raqueta principal. |
| `hit_racket2.wav`, `hit_racket3.wav` | ⭕ | Variantes opcionales de golpe. |
| `bounce_court.wav` | ✅ | Rebote de la pelota en la cancha. |
| `net_tape.wav` | ✅ | Golpe leve en la cinta de la red. |
| `net_body.wav` | ✅ | Golpe fuerte en el cuerpo de la red. |
| `out_whistle.wav` | ✅ | Sonido de bola fuera. |
| `score_jingle.wav` | ✅ | Sonido de punto anotado. |
| `crowd_ooh.wav`, `crowd_ahh.wav` | ⭕ | Reacciones del público. |
| `win_jingle.wav`, `lose_jingle.wav` | ⭕ | Jingles de fin de partido. |
| `menu_music.wav`, `ingame_music.wav` | ⭕ | Música ambiental (menú y partida). |

> Si faltan algunos audios, el juego usa fallbacks silenciosos y continúa normalmente.

---

## 🌀 Sprites

- **Carpeta:** `assets/sprites/ball/`  
- **Esperado:**  
  - `ball.json` (definición de frames y animaciones)  
  - `ball.png` (spritesheet de la pelota)  
- **Fallback:** círculo blanco renderizado por código si faltan los archivos.

---

## ⚙️ Configuración de mezcla (`audio_config.json`)

Archivo: `assets/audio_config.json`

```json
{
  "music": 0.40,
  "sfx": 0.85,
  "ui": 0.70
}
```

> Estos valores definen los volúmenes base de música, efectos y UI.  
> Si se borra el archivo, se regeneran automáticamente al iniciar el juego.

---

## 🗂️ Estructura de carpetas

```
assets/
├── audio/           ← sonidos del juego
├── texturas/        ← texturas visuales (cancha, red)
├── sprites/         ← sprites y animaciones
└── audio_config.json
```

> 💡 Las carpetas deben existir aunque estén vacías.

Para mantenerlas versionadas en Git:

```
assets/texturas/.gitkeep
assets/audio/.gitkeep
assets/sprites/.gitkeep
```

> ⚠️ No eliminar los `.gitkeep`: aseguran que las carpetas vacías se suban al repositorio.

---
