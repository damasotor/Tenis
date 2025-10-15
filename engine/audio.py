import pygame
import random

class AudioManager:
    """
    Gestor de audio centralizado.
    - Grupos con volumen: ui / sfx / amb / music
    - Variantes: register_variants("hit_racket", "hit_racket2", "hit_racket3")
    - Paneo estéreo por evento: play_sound_panned("bounce_court", pan=-1..+1)
    - Ducking simple de música: duck_music(down_to=0.15) / unduck_music()
    - Cooldowns por SFX para evitar spam
    """
    def __init__(self, num_channels=16):
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(num_channels)
            self.enabled = True
        except pygame.error as e:
            print(f"[Audio] Deshabilitado: {e}")
            self.enabled = False

        # name -> (Sound, group, base_volume)
        self.sounds = {}
        # base_name -> [variant_names] (incluye el base)
        self.variants = {}
        # name -> ms (tiempo mínimo entre reproducciones del mismo name)
        self.cooldowns = {}
        # name -> last_ticks
        self.last_played = {}

        self.music_path = None
        self._duck_prev = None  # guarda el volumen previo de música durante duck

        # Volúmenes por grupo (0..1)
        self.group_vol = {
            "ui":    0.70,
            "sfx":   0.85,
            "amb":   0.25,  # si usás ambiente como música, ajustarás con play_music
            "music": 0.40,
        }

    # ---------------------------
    # Carga
    # ---------------------------
    def load_sound(self, name, path, volume=0.8, group="sfx", cooldown_ms=0):
        """
        Carga un sonido. Firma compatible con tu versión anterior:
        load_sound(name, path, volume=0.8)
        (ahora opcionalmente podés indicar group y cooldown_ms)
        """
        if not self.enabled:
            return
        try:
            s = pygame.mixer.Sound(path)
            s.set_volume(max(0.0, min(1.0, float(volume))))
            self.sounds[name] = (s, group, float(volume))
            if cooldown_ms > 0:
                self.cooldowns[name] = int(cooldown_ms)
        except pygame.error as e:
            print(f"[Audio] Error cargando '{name}' desde '{path}': {e}")

    def register_variants(self, base_name, *names):
        """
        Registra variantes para que al pedir 'base_name' elija una al azar.
        Ej: register_variants('hit_racket', 'hit_racket2', 'hit_racket3')
        """
        self.variants[base_name] = [base_name] + [n for n in names if n in self.sounds]

    def load_music(self, path):
        if not self.enabled:
            return
        self.music_path = path

    # ---------------------------
    # Música
    # ---------------------------
    def play_music(self, loops=-1, volume=None):
        """
        Reproduce música con el volumen indicado o, si volume es None,
        usa el volumen del grupo 'music'.
        """
        if not (self.enabled and self.music_path):
            return
        try:
            pygame.mixer.music.load(self.music_path)
            if volume is None:
                vol = self.group_vol["music"]
            else:
                vol = max(0.0, min(1.0, float(volume)))
            pygame.mixer.music.set_volume(vol)
            pygame.mixer.music.play(loops)
        except pygame.error as e:
            print(f"[Audio] Error al reproducir música '{self.music_path}': {e}")

    def stop_music(self):
        if not self.enabled:
            return
        pygame.mixer.music.stop()

    def fadeout_music(self, ms=600):
        if not self.enabled:
            return
        pygame.mixer.music.fadeout(int(ms))

    # Ducking: baja temporalmente la música a un valor absoluto
    def duck_music(self, down_to=0.15):
        if not self.enabled:
            return
        # guarda el volumen previo (solo la primera vez hasta unduck)
        if self._duck_prev is None:
            self._duck_prev = pygame.mixer.music.get_volume()
        pygame.mixer.music.set_volume(max(0.0, min(1.0, float(down_to))))

    def unduck_music(self):
        if not self.enabled:
            return
        # restaura el volumen previo si lo teníamos, si no usa el del grupo
        if self._duck_prev is not None:
            pygame.mixer.music.set_volume(self._duck_prev)
            self._duck_prev = None
        else:
            pygame.mixer.music.set_volume(self.group_vol.get("music", 0.4))

    def set_group_volume(self, group, volume):
        """
        Ajusta el volumen de un grupo (0..1).
        Para 'music' aplica inmediatamente.
        """
        v = max(0.0, min(1.0, float(volume)))
        self.group_vol[group] = v
        if group == "music":
            pygame.mixer.music.set_volume(v)

    # ---------------------------
    # Reproducción de SFX
    # ---------------------------
    def _pick_variant(self, name):
        vs = self.variants.get(name)
        if vs:
            # filtrar por si alguna variante se removió
            vs = [n for n in vs if n in self.sounds]
            if vs:
                return random.choice(vs)
        return name

    def _can_play(self, name):
        cd = self.cooldowns.get(name)
        if not cd:
            return True
        now = pygame.time.get_ticks()
        last = self.last_played.get(name, -10**9)
        return (now - last) >= cd

    def _mark_played(self, name):
        self.last_played[name] = pygame.time.get_ticks()

    def _effective_vol(self, group, base_volume):
        """
        Volumen efectivo = volumen base del sample * volumen del grupo.
        """
        g = self.group_vol.get(group, 1.0)
        return max(0.0, min(1.0, float(base_volume) * g))

    def play_sound(self, name, loops=0):
        """Reproduce un SFX (usa variantes y cooldown si están configurados)."""
        if not self.enabled:
            return
        key = self._pick_variant(name)
        if not self._can_play(key):
            return
        pak = self.sounds.get(key)
        if not pak:
            return
        snd, group, base_vol = pak
        ch = pygame.mixer.find_channel()
        if ch:
            ch.set_volume(self._effective_vol(group, base_vol))
            ch.play(snd, loops=loops)
            self._mark_played(key)

    def play_sound_panned(self, name, pan=0.0):
        """
        Reproduce un SFX con paneo estéreo:
        pan = -1.0 (izq) ... 0 (centro) ... +1.0 (der)
        """
        if not self.enabled:
            return
        key = self._pick_variant(name)
        if not self._can_play(key):
            return
        pak = self.sounds.get(key)
        if not pak:
            return
        snd, group, base_vol = pak
        ch = pygame.mixer.find_channel()
        if not ch:
            return

        pan = max(-1.0, min(1.0, float(pan)))
        vol = self._effective_vol(group, base_vol)
        # Distribución simple en L/R
        left = vol * (1.0 - max(0.0, pan))    # si pan > 0 reduce L
        right = vol * (1.0 - max(0.0, -pan))  # si pan < 0 reduce R
        ch.set_volume(left, right)
        ch.play(snd)
        self._mark_played(key)
