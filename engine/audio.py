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

    Novedades:
    - Helper load_net_sfx() para cargar:
        • assets/audio/net_tape.wav  (cinta)
        • assets/audio/net_body.wav  (cuerpo)
    - Mute global reversible:
        • mute_all() / unmute_all() / toggle_mute_all() / is_all_muted()
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
        # base_name -> [variant_names]
        self.variants = {}
        # name -> cooldown ms
        self.cooldowns = {}
        # name -> last_ticks
        self.last_played = {}

        self.music_path = None
        self._duck_prev = None

        # Volúmenes por grupo (0..1)
        self.group_vol = {
            "ui":    0.70,
            "sfx":   0.85,
            "amb":   0.25,
            "music": 0.40,
        }

        # Estado mute global
        self._muted_all = False
        self._saved_group_vols = {}

    # ---------------------------
    # Carga
    # ---------------------------
    def load_sound(self, name, path, volume=0.8, group="sfx", cooldown_ms=0):
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
        self.variants[base_name] = [base_name] + [n for n in names if n in self.sounds]

    def load_music(self, path):
        if not self.enabled:
            return
        self.music_path = path

    # ---------------------------
    # SFX propios de la red
    # ---------------------------
    def load_net_sfx(self,
                     tape_path="assets/audio/net_tape.wav",
                     body_path="assets/audio/net_body.wav"):
        self.load_sound("net_tape", tape_path, 0.80, group="sfx", cooldown_ms=70)
        self.load_sound("net_body", body_path, 0.90, group="sfx", cooldown_ms=70)

    # ---------------------------
    # Música
    # ---------------------------
    def play_music(self, loops=-1, volume=None):
        if not (self.enabled and self.music_path):
            return
        try:
            pygame.mixer.music.load(self.music_path)
            vol = self.group_vol["music"] if volume is None else max(0.0, min(1.0, float(volume)))
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

    # ---------------------------
    # Ducking
    # ---------------------------
    def duck_music(self, down_to=0.15):
        if not self.enabled:
            return
        if self._duck_prev is None:
            self._duck_prev = pygame.mixer.music.get_volume()
        pygame.mixer.music.set_volume(max(0.0, min(1.0, float(down_to))))

    def unduck_music(self):
        if not self.enabled:
            return
        if self._duck_prev is not None:
            pygame.mixer.music.set_volume(self._duck_prev)
            self._duck_prev = None
        else:
            pygame.mixer.music.set_volume(self.group_vol.get("music", 0.4))

    def set_group_volume(self, group, volume):
        v = max(0.0, min(1.0, float(volume)))
        self.group_vol[group] = v
        if group == "music":
            pygame.mixer.music.set_volume(v)

    # ---------------------------
    # Mute global
    # ---------------------------
    def mute_all(self):
        if not self.enabled or self._muted_all:
            return
        self._saved_group_vols = dict(self.group_vol)
        for g in list(self.group_vol.keys()):
            self.set_group_volume(g, 0.0)
        self._muted_all = True

    def unmute_all(self):
        if not self.enabled or not self._muted_all:
            return
        if self._saved_group_vols:
            for g, v in self._saved_group_vols.items():
                self.set_group_volume(g, v)
        self._saved_group_vols = {}
        self._muted_all = False

    def toggle_mute_all(self):
        if self._muted_all:
            self.unmute_all()
        else:
            self.mute_all()

    def is_all_muted(self) -> bool:
        return bool(self._muted_all)

    # ---------------------------
    # Reproducción de SFX
    # ---------------------------
    def _pick_variant(self, name):
        vs = self.variants.get(name)
        if vs:
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
        g = self.group_vol.get(group, 1.0)
        return max(0.0, min(1.0, float(base_volume) * g))

    def play_sound(self, name, loops=0):
        """Reproduce un SFX (usa variantes y cooldown si están configurados)."""
        if not self.enabled or self._muted_all:
            return

        key = self._pick_variant(name)
        if not self._can_play(key):
            return

        pak = self.sounds.get(key)
        if not pak:
            return

        snd, group, base_vol = pak
        vol = self._effective_vol(group, base_vol)
        if vol <= 0.0:
            return

        ch = pygame.mixer.find_channel()
        if ch:
            ch.set_volume(vol)
            ch.play(snd, loops=loops)
            self._mark_played(key)

    def play_sound_panned(self, name, pan=0.0):
        """Reproduce un SFX con paneo estéreo (-1 izq, +1 der)."""
        if not self.enabled or self._muted_all:
            return

        key = self._pick_variant(name)
        if not self._can_play(key):
            return

        pak = self.sounds.get(key)
        if not pak:
            return

        snd, group, base_vol = pak
        vol = self._effective_vol(group, base_vol)
        if vol <= 0.0:
            return

        ch = pygame.mixer.find_channel()
        if not ch:
            return

        pan = max(-1.0, min(1.0, float(pan)))
        left = vol * (1.0 - max(0.0, pan))
        right = vol * (1.0 - max(0.0, -pan))

        ch.set_volume(left, right)
        ch.play(snd)
        self._mark_played(key)
