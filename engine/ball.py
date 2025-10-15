import random
import pygame

class Ball(pygame.sprite.Sprite):
    def __init__(self, x, y, game, vx=4, vy=-5):
        super().__init__()
        self.game = game

        # Pelota simple (círculo). Luego podés cambiar por sprite.
        r = 8
        self.image = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (250, 250, 250), (r, r), r)
        self.rect = self.image.get_rect(center=(x, y))

        self.vx = vx
        self.vy = vy

        # Control de colisión con la red y velocidad mínima/máxima
        self._net_cd_ms = 90            # cooldown para no disparar SFX cada frame
        self._last_net_hit = -10**9     # timestamp del último toque de red
        self._min_speed = 2.0           # módulo mínimo de velocidad por eje
        self._max_speed = 9.0           # módulo máximo de velocidad por eje

        # ☑️ Importante: NO disparamos sonido de saque aquí. Se hace explícito con start_rally().

    # -----------------------------
    # API para iniciar rally (saque)
    # -----------------------------
    def start_rally(self):
        """Dispara el sonido de saque con ducking suave de música."""
        self.game.audio.duck_music(0.18)
        self.game.audio.play_sound("serve")
        self.game.audio.unduck_music()

    # -----------------------------
    # Helpers de audio
    # -----------------------------
    def _calc_pan(self) -> float:
        """Convierte la X de la pelota a un paneo entre -1 (izq) y +1 (der)."""
        W = self.game.PANTALLA.get_width()
        x = self.rect.centerx
        return (x / max(1, W)) * 2.0 - 1.0

    # -----------------------------
    # Ciclo de actualización
    # -----------------------------
    def update(self):
        # Movimiento básico
        self.rect.x += self.vx
        self.rect.y += self.vy

        # Asegurar velocidad mínima y máxima (evita quedarse "muerta" o irse al infinito)
        if 0 < abs(self.vx) < self._min_speed:
            self.vx = self._min_speed * (1 if self.vx >= 0 else -1)
        if 0 < abs(self.vy) < self._min_speed:
            self.vy = self._min_speed * (1 if self.vy >= 0 else -1)
        self.vx = max(-self._max_speed, min(self._max_speed, self.vx))
        self.vy = max(-self._max_speed, min(self._max_speed, self.vy))

        # ======= LÍMITES REALES DEL COURT =======
        screen = self.game.PANTALLA
        field = self.game.field

        # Court real: si Field lo expone, lo usamos; si no, fallback a pantalla
        if hasattr(field, "get_court_rect"):
            court_rect = field.get_court_rect(screen)
        else:
            court_rect = screen.get_rect()

        # Rebotes laterales (pique)
        if self.rect.left <= court_rect.left:
            self.rect.left = court_rect.left
            self.vx *= -1
            self.game.audio.play_sound_panned("bounce_court", self._calc_pan())

        if self.rect.right >= court_rect.right:
            self.rect.right = court_rect.right
            self.vx *= -1
            self.game.audio.play_sound_panned("bounce_court", self._calc_pan())

        # Techo (rebote)
        if self.rect.top <= court_rect.top:
            self.rect.top = court_rect.top
            self.vy *= -1
            self.game.audio.play_sound_panned("bounce_court", self._calc_pan())

        # Fondo (por ahora: OUT simple del lado inferior)
        if self.rect.bottom >= court_rect.bottom:
            self.rect.bottom = court_rect.bottom
            self.on_out()
            # Respawn básico: centro de pantalla con dirección aleatoria
            cx, cy = screen.get_width() // 2, screen.get_height() // 2
            self.rect.center = (cx, cy)
            self.vx = random.choice([-5, 5])
            self.vy = -5
            return  # terminamos este frame

        # ======= RED REAL =======
        if hasattr(field, "get_net_rect"):
            net_rect = field.get_net_rect(screen)
        else:
            net_rect = self._fallback_net_rect(screen)  # por compatibilidad

        if self.rect.colliderect(net_rect):
            # Resolver penetración; contemplar vx ≈ 0 para evitar quedar atrapada
            if abs(self.vx) < 1e-6:
                if self.rect.centerx >= net_rect.centerx:
                    self.rect.left = net_rect.right + 1
                    self.vx = abs(self._min_speed)
                else:
                    self.rect.right = net_rect.left - 1
                    self.vx = -abs(self._min_speed)
            else:
                if self.vx > 0:
                    self.rect.right = net_rect.left - 1
                else:
                    self.rect.left = net_rect.right + 1
                self.vx *= -1

            # Amortiguar Y levemente para evitar vibración
            self.vy *= 0.95

            # Cooldown para SFX (evita metralleta si sigue tocando varios frames)
            now = pygame.time.get_ticks()
            if (now - self._last_net_hit) >= self._net_cd_ms:
                self.game.audio.play_sound_panned("net_touch", self._calc_pan())
                # Reacción leve del público (40% de prob., si existe el SFX)
                if "crowd_ooh" in self.game.audio.sounds and random.random() < 0.4:
                    self.game.audio.play_sound("crowd_ooh")
                self._last_net_hit = now

    # ---------- Hooks de eventos (con sonido) ----------
    def on_racket_hit(self):
        """Llamá esto desde la colisión raqueta–pelota real. Incluye frenado."""
        cands = [k for k in ("hit_racket", "hit_racket2", "hit_racket3")
                 if k in self.game.audio.sounds]
        key = random.choice(cands) if cands else "hit_racket"
        self.game.audio.play_sound_panned(key, self._calc_pan())
        
        # Rebote vertical y FRENADO (Amortiguación)
        AMORTIGUACION = 0.65  # Factor de reducción de velocidad (ej: 35% de frenado)
        
        self.vy *= -1       # Invertir dirección vertical
        self.vx *= AMORTIGUACION 
        self.vy *= AMORTIGUACION
        
        # Asegurar velocidad mínima después del golpe para que siga jugando
        MIN_VEL_AFTER_HIT = 3.0
        if abs(self.vy) < MIN_VEL_AFTER_HIT:
             self.vy = MIN_VEL_AFTER_HIT * (1 if self.vy >= 0 else -1)
        # El ciclo update() se encarga de limitar al max_speed.

    def on_body_hit(self):
        """Llamá esto desde la colisión CUERPO–pelota. Es un error y produce un rebote 'muerto'."""
        
        # 1. Reproducir un sonido de impacto suave (usamos 'bounce_court' si no hay 'body_hit' SFX)
        self.game.audio.play_sound_panned("bounce_court", self._calc_pan())
        
        # 2. Rebotar suavemente con mucha pérdida de energía (la pelota cae "muerta")
        DEAD_BOUNCE_FACTOR = 0.25 # Gran reducción de velocidad
        self.vx *= -DEAD_BOUNCE_FACTOR  # Invertir y casi detener horizontal
        self.vy *= -DEAD_BOUNCE_FACTOR  # Invertir y casi detener vertical
        
        # 3. Marcar el punto (ya que chocar con el cuerpo es un error)
        self.on_point_scored()
        
    def on_out(self):
        self.game.audio.play_sound("out_whistle")
        # Reacción del público (60% de prob., si existe)
        if "crowd_ahh" in self.game.audio.sounds and random.random() < 0.6:
            self.game.audio.play_sound("crowd_ahh")

    def on_point_scored(self):
        """Método que maneja la puntuación (jingle y ducking)."""
        # Jingle con ducking suave de música + reacción (si existe)
        self.game.audio.duck_music(0.12)
        self.game.audio.play_sound("score_jingle")
        if "crowd_ooh" in self.game.audio.sounds:
            self.game.audio.play_sound("crowd_ooh")
        self.game.audio.unduck_music()

    # ---------- Fallback de red (si Field no la provee) ----------
    def _fallback_net_rect(self, screen) -> pygame.Rect:
        W = screen.get_width()
        H = screen.get_height()
        net_w = 6
        net_h = int(H * 0.6)
        net_x = (W - net_w) // 2
        net_y = (H - net_h) // 2
        return pygame.Rect(net_x, net_y, net_w, net_h)
