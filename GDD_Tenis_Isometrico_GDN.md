# Tenis Isométrico GDN - Documento de Diseño de Juego (GDD)

**Integrantes:** Gonzalo Canepa, Damaso Tor, Nicolás Bentancor  
**Correos de los integrantes:** <gcanepa28@gmail.com>, <damasomail@gmail.com> y <bentanico@gmail.com>

**Versión:** 1.0.1  
**Fecha:** 2025-11-21

---

## 1. Resumen Ejecutivo

* **Título del Juego:** Tenis Isométrico GDN
* **Género:** Deportes / Arcade Isométrico  
* **Plataforma(s) Objetivo:** PC (Windows, macOVS, Linux)  
* **Público Objetivo:** Jugadores casuales y jugadores competitivos que disfrutan precisión y reflejos  
* **Propuesta Única de Venta (USP):**  
  *“Un juego de tenis isométrico dinámico, con física realista, controles accesibles y efectos visuales estilo arcade.”*

---

## 2. Concepto del Juego

### 2.1. Visión General

El jugador vive la fantasía de competir en partidos de tenis rápidos y dinámicos, vistos desde una cámara isométrica. El foco está en reflejos, precisión en el posicionamiento y la satisfacción del impacto de la pelota, acompañado de una ambientación liviana y accesible.

### 2.2. Pilares de Diseño

* **Pilar 1:** Jugabilidad rápida y responsiva  
* **Pilar 2:** Física simple pero coherente  
* **Pilar 3:** Claridad visual (isométrico legible)  
* **Pilar 4:** Accesibilidad (controles simples, 1P y 2P)

### 2.3. Inspiraciones y Referencias

* Final Match Tennis  
* Virtua Tennis  
* Juegos retro isométricos (Sensible Soccer para estilo de lectura visual)  

---

## 3. Mecánicas de Juego (Gameplay)

### 3.1. Bucle Principal

1. El jugador se posiciona en la cancha.  
2. Golpea la pelota o prepara el saque.  
3. Se desarrolla el rally con rebotes, red y puntos.  
4. Se reinicia la jugada y el ciclo continúa.

**Recompensa:** puntos, ventaja y progreso en el partido.

### 3.2. Mecánicas Detalladas

* **Movimiento del Jugador:** isométrico, con diagonales naturales por perspectiva.  
* **Saque:** secuencia de toss → hit con espacio (P1) o F (P2).  
* **Golpe:** el juego elige dirección según zona objetivo.  
* **Física:** bote, rebote, colisión con red, velocidad vertical.  
* **Sistema de Puntuación:** 15 → 30 → 40 → ventaja → game.  
* **Mecánicas Únicas:**  
  * Paneo de audio dinámico  
  * Red con detección de altura real  
  * IA básica para jugadores CPU  

### 3.3. Controles

| Acción | Jugador 1 (Teclado) | Jugador 2 (Teclado) | Gamepad | Mobile |
| :--- | :--- | :--- | :--- | :--- |
| Moverse | WASD | Flechas | Stick Izq | N/A |
| Saque | Espacio | F | Botón A | N/A |
| Golpe | Espacio (tiempo contextual) | F | Botón X | N/A |
| Pausa | Esc/P | Esc/P | Start | N/A |

---

## 4. Mundo y Narrativa

### 4.1. Historia

No existe narrativa lineal. La fantasía es competir en un torneo de tenis arcade isométrico.

### 4.2. Personajes

* **Jugador 1 / Jugador 2**  
  * Rol: competidores  
  * Estilo visual retro-isométrico  
  * Habilidades: movilidad rápida y golpes precisos  

### 4.3. Entorno y Niveles

* **Cancha Estándar:**  
  * Estética retro / clay court  
  * Público animado  
  * Objetivo: ganar el partido  
  * Desafíos: velocidad, reacción, precisión  

---

## 5. Arte y Sonido

### 5.1. Dirección de Arte

* **Estilo:** Pixel-art isométrico híbrido  
* **Paleta:** tonos cálidos (arcilla), público colorido  
* **Inspiración Visual:** juegos deportivos retro + estilo arcade moderno

### 5.2. Sonido y Música

* **Música:** ambiental ligera para menú y partido  
* **SFX:**  
  * Golpe de pelota  
  * Pique  
  * Red (tape/body)  
  * Público  
  * Puntos y out  

---

## 6. UI / UX

### 6.1. Flujo de Pantallas

Pantalla de Título → Menú Principal → (Jugar / Opciones / Salir)  
→ Partida → Pausa → (Continuar / Volver al menú)

### 6.2. HUD

* Marcador de puntos  
* Indicadores de saque  
* Posición del jugador (visual)

### 6.3. Menús

* Menú principal  
* Opciones (música, SFX, UI volumen, modo 1P/2P)  
* Pausa

---

## 7. Producción y Monetización

### 7.1. Roadmap

* **Prototipo:** — Física, pelota, red  
* **Vertical Slice:** — Saque, rally, UI básica  
* **Alfa:** — IA, audio completo, menú  
* **Beta:** — Pulido visual, corrección de bugs  
* **Lanzamiento:** — Versión jugable completa

### 7.2. Monetización

Juego gratuito educativo / práctica — sin monetización.

---

## 8. Fuentes de los Assets

| ID | Descripción | Tipo | Fuente | Licencia | Costo | Notas |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| MUS-001 | Música de menú | Audio | freesound.org | CC0 | Gratis | — |
| SFX-001 | Golpe de pelota | Audio | freesound.org | CC0 | Gratis | — |
| SFX-002 | Pique | Audio | freesound.org | CC0 | Gratis | — |
| SFX-003 | Red | Audio | freesound.org | CC0 | Gratis | — |
| TEX-001 | Cancha | Gráfico | Interno | Propia | N/A | — |
| TEX-002 | Jugadores | Gráfico | Interno | Propia | N/A | — |

---

## 9. Control de Cambios

| Versión | Fecha | Autor | Cambio | Razón |
| :--- | :--- | :--- | :--- | :--- |
| 1.0.0 | 2025-11-12 | Equipo | Documentación y basecode | Entrega del proyecto |
| 1.0.1 | 2025-11-21 | Equipo | Documentación y basecode | Mejora del proyecto |
