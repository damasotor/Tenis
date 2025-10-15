import os
import json
import pygame

from engine.player import Player
from engine.field import Field
from engine.utils.colors import AZUL_OSCURO, BLANCO
from engine.utils.screen import ANCHO, ALTO
from engine.audio import AudioManager  # audio central
from engine.ball import Ball           # pelota


class Game:
    def __init__(self):
        # Ventana
        self.PANTALLA = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption('Tennis Isométrico en construcción...')

        # Mundo
        self.field = Field(6, 10)
        self.jugador1 = Player(ANCHO / 3 + 185, ALTO / 2 - 25, field=self.field, jugador2=False)
        self.jugador2 = Player(ANCHO / 3 + 185, ALTO / 2 - 450, field=self.field, jugador2=True)

        # Reloj
        self.reloj = pygame.time.Clock()

        # --- AUDIO ---
        self.audio = AudioManager()
        self._load_audio_assets()

        # Config persistente de audio
        self.config_path = os.path.join("assets", "audio_config.json")
        self._load_audio_config()

        # Flags de desarrollo / ambiente
        # self.debug_audio → activa hotkeys de test (v, b, n, f, etc.)
        # self.use_crowd_ambience → True = crowd_loop.wav | False = ingame_music.wav (si existe)
        self.debug_audio = os.getenv("VJ2D_DEBUG_AUDIO", "1") == "1"
        self.use_crowd_ambience = False # cambiar a True para probar con crowd_loop.wav

        # Música por estado → arrancamos en MENÚ
        self._set_music_state("menu")

        # Estados
        self.estado_juego = 'menu'  # 'menu' | 'opciones' | 'jugando' | 'pausa' | 'game_over' | 'victoria'
        self.menu_items = ["Comenzar", "Opciones", "Salir"]
        self.menu_index = 0

        # Fuente UI
        self.font_title = pygame.font.Font(None, 64)
        self.font_item = pygame.font.Font(None, 44)
        self.font_small = pygame.font.Font(None, 32)

        # --- Pelotas ---
        self.balls = pygame.sprite.Group()

        # --- Debug overlay (F1) ---
        self._debug_bounds = False

        # --- Mute música (M) ---
        self._music_muted = False
        self._music_prev_vol = self.audio.group_vol.get("music", 0.4)

        # --- Opciones de Audio (estado temporal para sliders) ---
        self._opts_names = ["Música", "SFX", "UI"]
        self._opts_groups = ["music", "sfx", "ui"]
        self._opts_index = 0
        self._opts_values = [
            self.audio.group_vol["music"],
            self.audio.group_vol["sfx"],
            self.audio.group_vol["ui"],
        ]

    # ---------------------------
    # Carga de sonidos
    # ---------------------------
    def _load_audio_assets(self):
        ap = os.path.join("assets", "audio")
        def p(n): return os.path.join(ap, n)

        # UI
        self.audio.load_sound("ui_move",    p("ui_move.wav"),    0.6, group="ui",  cooldown_ms=90)
        self.audio.load_sound("ui_select",  p("ui_select.wav"),  0.8, group="ui",  cooldown_ms=120)
        self.audio.load_sound("ui_back",    p("ui_back.wav"),    0.6, group="ui",  cooldown_ms=120)
        if os.path.exists(p("ui_whoosh.wav")):
            self.audio.load_sound("ui_whoosh", p("ui_whoosh.wav"), 0.7, group="ui", cooldown_ms=300)

        # Tenis (con cooldowns para evitar “metralleta”)
        self.audio.load_sound("serve",         p("serve.wav"),        0.9, group="sfx", cooldown_ms=150)
        if os.path.exists(p("serve2.wav")):
            self.audio.load_sound("serve2",    p("serve2.wav"),       0.9, group="sfx", cooldown_ms=150)
            self.audio.register_variants("serve", "serve2")

        self.audio.load_sound("hit_racket",    p("hit_racket.wav"),   0.8, group="sfx", cooldown_ms=40)
        self.audio.load_sound("bounce_court",  p("bounce_court.wav"), 0.7, group="sfx", cooldown_ms=60)
        self.audio.load_sound("net_touch",     p("net_touch.wav"),    0.7, group="sfx", cooldown_ms=120)
        self.audio.load_sound("out_whistle",   p("out_whistle.wav"),  0.7, group="sfx", cooldown_ms=300)
        self.audio.load_sound("score_jingle",  p("score_jingle.wav"), 0.8, group="sfx", cooldown_ms=400)

        # Variantes opcionales de golpe (se cargarán si existen en disco)
        variants = []
        for i in (2, 3):
            fname = f"hit_racket{i}.wav"
            path = p(fname)
            if os.path.exists(path):
                self.audio.load_sound(f"hit_racket{i}", path, 0.8, group="sfx", cooldown_ms=40)
                variants.append(f"hit_racket{i}")
        if variants:
            self.audio.register_variants("hit_racket", *variants)

        # Reacciones del público (opcionales)
        if os.path.exists(p("crowd_ooh.wav")):
            self.audio.load_sound("crowd_ooh", p("crowd_ooh.wav"), 0.75, group="sfx", cooldown_ms=300)
        if os.path.exists(p("crowd_ahh.wav")):
            self.audio.load_sound("crowd_ahh", p("crowd_ahh.wav"), 0.75, group="sfx", cooldown_ms=300)

        # Jingles de fin (opcionales)
        if os.path.exists(p("win_jingle.wav")):
            self.audio.load_sound("win_jingle",  p("win_jingle.wav"),  0.9, group="sfx", cooldown_ms=1500)
        if os.path.exists(p("lose_jingle.wav")):
            self.audio.load_sound("lose_jingle", p("lose_jingle.wav"), 0.9, group="sfx", cooldown_ms=1500)

        # (Opcional) Sting para match point / set point si existe el archivo
        if os.path.exists(p("sting_match.wav")):
            self.audio.load_sound("sting_match", p("sting_match.wav"), 0.85, group="sfx", cooldown_ms=800)

    # ---------------------------
    # Persistencia de audio (volúmenes)
    # ---------------------------
    def _load_audio_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for g in ("music", "sfx", "ui"):
                if g in cfg and isinstance(cfg[g], (int, float)):
                    self.audio.set_group_volume(g, float(cfg[g]))
        except Exception:
            pass

    def _save_audio_config(self):
        cfg = {
            "music": self.audio.group_vol["music"],
            "sfx":   self.audio.group_vol["sfx"],
            "ui":    self.audio.group_vol["ui"],
        }
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            print(f"[Audio] No se pudo guardar config: {e}")

    # ---------------------------
    # Música por estado (con switch de ambiente)
    # ---------------------------
    def _set_music_state(self, state: str):
        def ap(*parts):
            return os.path.join("assets", "audio", *parts)

        if state == "menu":
            self.audio.fadeout_music(200)
            path = ap("menu_music.wav")
            if os.path.exists(path):
                self.audio.load_music(path)
                self.audio.play_music(loops=-1, volume=0.40)
            return

        if state == "ingame":
            self.audio.fadeout_music(200)
            # crowd vs instrumental
            if self.use_crowd_ambience and os.path.exists(ap("crowd_loop.wav")):
                music_path = ap("crowd_loop.wav")
                vol = 0.20
            elif os.path.exists(ap("ingame_music.wav")):
                music_path = ap("ingame_music.wav")
                vol = 0.35
            else:
                # Última red de seguridad: silencio si no hay assets
                return

            self.audio.load_music(music_path)
            self.audio.play_music(loops=-1, volume=vol)

    # ---------------------------
    # Bucle principal
    # ---------------------------
    def game_loop(self):
        ejecutando = True
        while ejecutando:
            dt = self.reloj.tick(60)

            # --- INPUT ---
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False

                elif evento.type == pygame.KEYDOWN:
                    # Toggle del overlay de límites con F1
                    if evento.key == pygame.K_F1:
                        self._debug_bounds = not self._debug_bounds

                    # Mezcla rápida
                    if evento.key == pygame.K_1:
                        v = max(0.0, self.audio.group_vol["music"] - 0.05)
                        self.audio.set_group_volume("music", v)
                        self._music_prev_vol = v if not self._music_muted else self._music_prev_vol
                    if evento.key == pygame.K_2:
                        v = min(1.0, self.audio.group_vol["music"] + 0.05)
                        self.audio.set_group_volume("music", v)
                        self._music_prev_vol = v if not self._music_muted else self._music_prev_vol
                    if evento.key == pygame.K_3:
                        v = max(0.0, self.audio.group_vol["sfx"] - 0.05)
                        self.audio.set_group_volume("sfx", v)
                    if evento.key == pygame.K_4:
                        v = min(1.0, self.audio.group_vol["sfx"] + 0.05)
                        self.audio.set_group_volume("sfx", v)
                    if evento.key == pygame.K_m:
                        if not self._music_muted:
                            self._music_prev_vol = self.audio.group_vol["music"]
                            self.audio.set_group_volume("music", 0.0)
                            self._music_muted = True
                        else:
                            self.audio.set_group_volume("music", self._music_prev_vol or 0.4)
                            self._music_muted = False

                    # Estados
                    if self.estado_juego == 'menu':
                        if evento.key in (pygame.K_UP, pygame.K_w):
                            self.menu_index = (self.menu_index - 1) % len(self.menu_items)
                            self.audio.play_sound("ui_move")
                        elif evento.key in (pygame.K_DOWN, pygame.K_s):
                            self.menu_index = (self.menu_index + 1) % len(self.menu_items)
                            self.audio.play_sound("ui_move")
                        elif evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                            self.audio.play_sound("ui_select")
                            self._menu_select()
                        elif evento.key == pygame.K_ESCAPE:
                            self.audio.play_sound("ui_back")
                            ejecutando = False

                    elif self.estado_juego == 'opciones':
                        handled = self._handle_options_input(evento.key)
                        if not handled and evento.key == pygame.K_ESCAPE:
                            self.estado_juego = 'menu'

                    elif self.estado_juego == 'jugando':
                        if evento.key == pygame.K_ESCAPE:
                            # Pausa con whoosh y duck
                            if "ui_whoosh" in self.audio.sounds:
                                self.audio.play_sound("ui_whoosh")
                            self.audio.play_sound("ui_back")
                            self.estado_juego = 'pausa'
                            self.audio.duck_music(0.08)

                        # Hotkeys de prueba (envueltos bajo debug_audio)
                        if self.debug_audio:
                            if evento.key == pygame.K_v:
                                self.audio.play_sound("serve")
                            if evento.key == pygame.K_h:
                                for b in self.balls:
                                    b.on_racket_hit()
                                    break
                            if evento.key == pygame.K_b:
                                self.audio.play_sound("bounce_court")
                            if evento.key == pygame.K_n:
                                self.audio.play_sound("net_touch")
                                if "crowd_ooh" in self.audio.sounds:
                                    self.audio.play_sound("crowd_ooh")
                            if evento.key == pygame.K_o:
                                for b in self.balls:
                                    b.on_out()
                                    break
                            if evento.key == pygame.K_p:
                                for b in self.balls:
                                    b.on_point_scored()
                                    break
                            # Reacciones/jingles de prueba
                            if evento.key == pygame.K_c and "crowd_ooh" in self.audio.sounds:
                                self.audio.play_sound("crowd_ooh")
                            # Remapeo: 'a' → 'f' para evitar conflicto con mover P2
                            if evento.key == pygame.K_f and "crowd_ahh" in self.audio.sounds:
                                self.audio.play_sound("crowd_ahh")
                            if evento.key == pygame.K_k and "sting_match" in self.audio.sounds:
                                self.audio.duck_music(0.10)
                                self.audio.play_sound("sting_match")
                                self.audio.unduck_music()
                            if evento.key == pygame.K_g and "win_jingle" in self.audio.sounds:
                                self._on_victory()
                            if evento.key == pygame.K_l and "lose_jingle" in self.audio.sounds:
                                self._on_game_over()

                    elif self.estado_juego == 'pausa':
                        if evento.key in (pygame.K_ESCAPE, pygame.K_p):
                            # Whoosh al volver
                            if "ui_whoosh" in self.audio.sounds:
                                self.audio.play_sound("ui_whoosh")
                            self.audio.play_sound("ui_back")
                            self.estado_juego = 'jugando'
                            self.audio.unduck_music()

            # --- Lógica ---
            if self.estado_juego == 'jugando':
                teclas = pygame.key.get_pressed()
                self.jugador1.mover(teclas)
                self.jugador2.mover(teclas)
                self.balls.update()
               
                for ball in self.balls:
                    # Comprobar colisión con Jugador 1
                    self.jugador1.check_ball_collision(ball)
                    
                    # Comprobar colisión con Jugador 2
                    self.jugador2.check_ball_collision(ball)
                    
            # --- Render ---
            self.PANTALLA.fill(AZUL_OSCURO)

            if self.estado_juego == 'menu':
                self._draw_menu()
            elif self.estado_juego == 'opciones':
                self._draw_options()
            else:
                self.field.draw(self.PANTALLA)

                if self._debug_bounds:
                    self.field.draw_debug_bounds(self.PANTALLA)

                self.balls.draw(self.PANTALLA)
                self.jugador2.draw(self.PANTALLA)
                self.jugador1.draw(self.PANTALLA)

                if self.estado_juego == 'pausa':
                    self._draw_center_text("PAUSA (Esc/P para volver)")

            pygame.display.flip()

        # Guardar mezcla al salir (si ajustaste con 1/2/3/4)
        self._save_audio_config()
        pygame.quit()

    # ---------------------------
    # Menú
    # ---------------------------
    def _menu_select(self):
        item = self.menu_items[self.menu_index]
        if item == "Comenzar":
            self._set_music_state("ingame")
            self.estado_juego = 'jugando'
            cx, cy = self.PANTALLA.get_width() // 2, self.PANTALLA.get_height() // 2
            self.balls.empty()
            # Crear pelota y disparar el saque explícitamente (no en __init__)
            ball = Ball(cx, cy, game=self, vx=5, vy=-5)
            self.balls.add(ball)
            ball.start_rally()
        elif item == "Opciones":
            self._enter_options()
        elif item == "Salir":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _draw_menu(self):
        title = self.font_title.render("Tennis Isométrico", True, BLANCO)
        self.PANTALLA.blit(title, title.get_rect(center=(ANCHO // 2, 140)))
        for i, txt in enumerate(self.menu_items):
            sel = (i == self.menu_index)
            label = f"> {txt} <" if sel else f"  {txt}  "
            surf = self.font_item.render(label, True, BLANCO)
            self.PANTALLA.blit(surf, surf.get_rect(center=(ANCHO // 2, 260 + i * 60)))

    def _draw_center_text(self, msg):
        surf = self.font_item.render(msg, True, BLANCO)
        self.PANTALLA.blit(surf, surf.get_rect(center=(ANCHO // 2, ALTO // 2)))

    # ---------------------------
    # Opciones de Audio
    # ---------------------------
    def _enter_options(self):
        if "ui_whoosh" in self.audio.sounds:
            self.audio.play_sound("ui_whoosh")
        self.audio.play_sound("ui_select")
        self.estado_juego = 'opciones'
        self._opts_values = [
            self.audio.group_vol["music"],
            self.audio.group_vol["sfx"],
            self.audio.group_vol["ui"],
        ]
        self._opts_index = 0

    def _handle_options_input(self, key) -> bool:
        if key in (pygame.K_ESCAPE,):
            self.audio.play_sound("ui_back")
            if "ui_whoosh" in self.audio.sounds:
                self.audio.play_sound("ui_whoosh")
            self.estado_juego = 'menu'
            return True

        if key in (pygame.K_RETURN, pygame.K_SPACE):
            for i, g in enumerate(self._opts_groups):
                self.audio.set_group_volume(g, self._opts_values[i])
            self._save_audio_config()
            self.audio.play_sound("ui_select")
            if "ui_whoosh" in self.audio.sounds:
                self.audio.play_sound("ui_whoosh")
            self.estado_juego = 'menu'
            return True

        if key in (pygame.K_UP, pygame.K_w):
            self._opts_index = (self._opts_index - 1) % len(self._opts_names)
            self.audio.play_sound("ui_move")
            return True
        if key in (pygame.K_DOWN, pygame.K_s):
            self._opts_index = (self._opts_index + 1) % len(self._opts_names)
            self.audio.play_sound("ui_move")
            return True

        idx = self._opts_index
        if key in (pygame.K_LEFT, pygame.K_a):
            self._opts_values[idx] = max(0.0, round(self._opts_values[idx] - 0.05, 2))
            self.audio.set_group_volume(self._opts_groups[idx], self._opts_values[idx])
            return True
        if key in (pygame.K_RIGHT, pygame.K_d):
            self._opts_values[idx] = min(1.0, round(self._opts_values[idx] + 0.05, 2))
            self.audio.set_group_volume(self._opts_groups[idx], self._opts_values[idx])
            return True

        return False

    def _draw_options(self):
        title = self.font_title.render("Opciones de Audio", True, BLANCO)
        self.PANTALLA.blit(title, title.get_rect(center=(ANCHO // 2, 120)))
        y0 = 220
        for i, name in enumerate(self._opts_names):
            sel = (i == self._opts_index)
            label = f"> {name} <" if sel else f"  {name}  "
            val = int(self._opts_values[i] * 100)
            line = f"{label} : {val}%"
            surf = self.font_item.render(line, True, BLANCO)
            self.PANTALLA.blit(surf, surf.get_rect(center=(ANCHO // 2, y0 + i * 60)))
        hint = "←/→ ajustar, ↑/↓ mover, Enter guardar, Esc cancelar"
        hs = self.font_small.render(hint, True, BLANCO)
        self.PANTALLA.blit(hs, hs.get_rect(center=(ANCHO // 2, y0 + 60 * len(self._opts_names) + 40)))

    # ---------------------------
    # Jingles de fin (helpers)
    # ---------------------------
    def _on_victory(self):
        if "win_jingle" in self.audio.sounds:
            self.audio.fadeout_music(200)
            self.audio.play_sound("win_jingle")
        self._set_music_state("menu")  # volver a música de menú

    def _on_game_over(self):
        if "lose_jingle" in self.audio.sounds:
            self.audio.fadeout_music(200)
            self.audio.play_sound("lose_jingle")
        self._set_music_state("menu")
