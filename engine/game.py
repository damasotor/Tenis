import os
import json
import pygame

from engine.player import Player
from engine.field import Field
from engine.utils.colors import AZUL_OSCURO, BLANCO
from engine.utils.screen import ANCHO, ALTO, world_to_screen
from engine.audio import AudioManager
from engine.ball import Ball

# Debug overlays (pique IN/OUT)
try:
    from engine.debug.overlays import DebugOverlays
except Exception:
    DebugOverlays = None  # type: ignore

# Overlay 3-2-1
try:
    from engine.ui.countdown import RestartCountdown
except Exception:
    RestartCountdown = None  # type: ignore

# IA simple para P2 (modo 1P)
try:
    from engine.ai.simple_ai import SimpleTennisAI
except Exception:
    SimpleTennisAI = None  # type: ignore

# Puntuación
try:
    from engine.score import ScoreManager
except Exception:
    ScoreManager = None  # type: ignore


class Game:
    def __init__(self, player1_name="P1", player2_name="P2", screen=None):
        # Ventana
        self.PANTALLA = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption('Tennis Isométrico en construcción...')

        # Mundo
        self.field = Field(6, 10)
        self.jugador1 = Player(520, 350,  field=self.field, jugador2=False, game=self)# >x = Más a la derecha, >y = Más atrás
        self.jugador2 = Player(385, ALTO / 2 - 450, field=self.field, jugador2=True, game=self)

        # Reloj
        self.reloj = pygame.time.Clock()

        # --- AUDIO ---
        self.audio = AudioManager()
        self._load_audio_assets()

        # Config persistente de audio
        self.config_path = os.path.join("assets", "audio_config.json")
        self._load_audio_config()

        # Flags de desarrollo
        self.debug_audio = os.getenv("VJ2D_DEBUG_AUDIO", "1") == "1"
        self.use_crowd_ambience = False

        # Música por estado → MENÚ (respetando mute de grupo)
        self._set_music_state("menu")

        # ---- MODO / ESTADOS ----
        self.modo = os.getenv("VJ2D_MODO", "1P")
        self.estado_juego = 'menu'  # 'menu'|'opciones'|'jugando'|'pausa'|'victoria'|'gameover'

        # Menú simple
        self.menu_items = ["Comenzar", "Opciones", "Salir"]
        self.menu_index = 0

        # Fuentes
        self.font_title = pygame.font.Font(None, 64)
        self.font_item  = pygame.font.Font(None, 44)
        self.font_small = pygame.font.Font(None, 32)
        self.font_hud   = pygame.font.Font(None, 38)

        # score puntaje en español lindo
        self.score = ScoreManager("P1", "P2", screen=self.PANTALLA) if ScoreManager else None

        # Pelotas
        self.balls = pygame.sprite.Group()
        self._ball_main = None  # referencia a la pelota "principal"
        self.current_server = "P1"
        # IA / control según modo
        self.ai_p2 = None
        if self.modo == "1P" and SimpleTennisAI is not None:
            self.jugador2.is_human = False
            self.jugador2.home_x = getattr(self.jugador2, "world_x", getattr(self.jugador2, "x", 0))
            self.jugador2.home_y = getattr(self.jugador2, "world_y", getattr(self.jugador2, "y", 0))
            self.ai_p2 = SimpleTennisAI(self.jugador2, None, side="top")  # type: ignore
        else:
            self.jugador2.is_human = True

        # Debug overlay (F1 = bounds, F3 = bounces)
        self._debug_bounds = False
        self.debug_overlays = DebugOverlays() if DebugOverlays else None
        self.show_bounce_debug = True

        # Mute música (legacy, mantenido para UI de opciones)
        self._music_muted = False
        self._music_prev_vol = self.audio.group_vol.get("music", 0.4)

        # Opciones de Audio
        self._opts_names  = ["Música", "SFX", "UI"]
        self._opts_groups = ["music",  "sfx", "ui"]
        self._opts_index  = 0
        self._opts_values = [
            self.modo,
            self.audio.group_vol["music"],
            self.audio.group_vol["sfx"],
            self.audio.group_vol["ui"],
        ]

        # Último que pegó
        self.last_hitter = None  # "P1"/"P2"/None

        # --- Cuenta regresiva de reinicio (punto 4) ---
        self._restart_cd = RestartCountdown(self._reiniciar_partida) if RestartCountdown else None
        self._restart_block_input = False  # si True, no procesamos entradas de juego durante el 3-2-1

    # ---------------------------
    # Config de juego (modo 1P/2P)
    # ---------------------------
    def _load_game_config(self):
        try:
            if os.path.exists(self.game_config_path):
                with open(self.game_config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                m = str(cfg.get("modo", "1P")).upper()
                if m in ("1P", "2P"):
                    self.modo = m
        except Exception as e:
            print(f"[GameCfg] No se pudo leer game_config.json: {e}")

    def _save_game_config(self):
        try:
            os.makedirs(os.path.dirname(self.game_config_path), exist_ok=True)
            with open(self.game_config_path, "w", encoding="utf-8") as f:
                json.dump({"modo": self.modo}, f, indent=2)
        except Exception as e:
            print(f"[GameCfg] No se pudo guardar game_config.json: {e}")

    def _apply_mode(self):
        """Aplica el modo actual (1P → IA en P2; 2P → ambos humanos)."""
        if self.modo == "1P" and SimpleTennisAI is not None:
            self.jugador2.is_human = False
            self.jugador2.home_x = getattr(self.jugador2, "world_x", getattr(self.jugador2, "x", 0))
            self.jugador2.home_y = getattr(self.jugador2, "world_y", getattr(self.jugador2, "y", 0))
            self.ai_p2 = SimpleTennisAI(self.jugador2, self._ball_main, side="top")  # type: ignore
        else:
            self.jugador2.is_human = True
            self.ai_p2 = None

    def _set_mode(self, new_mode: str):
        new_mode = (new_mode or "").upper()
        if new_mode not in ("1P", "2P"):
            return
        if new_mode == self.modo:
            return
        self.modo = new_mode
        self._apply_mode()
        self._save_game_config()
        if hasattr(self, "audio"):
            self.audio.play_sound("ui_select")

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

        # Tenis base
        self.audio.load_sound("serve",         p("serve.wav"),        0.9, group="sfx", cooldown_ms=150)
        if os.path.exists(p("serve2.wav")):
            self.audio.load_sound("serve2",    p("serve2.wav"),       0.9, group="sfx", cooldown_ms=150)
            self.audio.register_variants("serve", "serve2")

        self.audio.load_sound("hit_racket",    p("hit_racket.wav"),   0.8, group="sfx", cooldown_ms=40)
        self.audio.load_sound("bounce_court",  p("bounce_court.wav"), 0.7, group="sfx", cooldown_ms=60)

        # Compat viejo
        if os.path.exists(p("net_touch.wav")):
            self.audio.load_sound("net_touch", p("net_touch.wav"), 0.7, group="sfx", cooldown_ms=120)

        self.audio.load_sound("out_whistle",   p("out_whistle.wav"),  0.7, group="sfx", cooldown_ms=300)
        self.audio.load_sound("score_jingle",  p("score_jingle.wav"), 0.8, group="sfx", cooldown_ms=400)

        # Variantes opcionales
        variants = []
        for i in (2, 3):
            fn = f"hit_racket{i}.wav"
            if os.path.exists(p(fn)):
                self.audio.load_sound(f"hit_racket{i}", p(fn), 0.8, group="sfx", cooldown_ms=40)
                variants.append(f"hit_racket{i}")
        if variants:
            self.audio.register_variants("hit_racket", *variants)

        # Público (opcionales)
        if os.path.exists(p("crowd_ooh.wav")):
            self.audio.load_sound("crowd_ooh", p("crowd_ooh.wav"), 0.75, group="sfx", cooldown_ms=300)
        if os.path.exists(p("crowd_ahh.wav")):
            self.audio.load_sound("crowd_ahh", p("crowd_ahh.wav"), 0.75, group="sfx", cooldown_ms=300)

        # Jingles fin (opcionales)
        if os.path.exists(p("win_jingle.wav")):
            self.audio.load_sound("win_jingle",  p("win_jingle.wav"),  0.9, group="sfx", cooldown_ms=1500)
        if os.path.exists(p("lose_jingle.wav")):
            self.audio.load_sound("lose_jingle", p("lose_jingle.wav"), 0.9, group="sfx", cooldown_ms=1500)
        if os.path.exists(p("sting_match.wav")):
            self.audio.load_sound("sting_match", p("sting_match.wav"), 0.85, group="sfx", cooldown_ms=800)

        # NUEVO: sonidos de red (cinta/cuerpo)
        if hasattr(self.audio, "load_net_sfx"):
            self.audio.load_net_sfx()

    # ---------------------------
    # Persistencia de audio
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
    # Música por estado (respeta mute)
    # ---------------------------
    def _set_music_state(self, state: str):
        def ap(*parts):
            return os.path.join("assets", "audio", *parts)

        # Importante: NO forzar volume en play_music; dejar que use el del grupo
        # así si el usuario muteó música, se respeta.
        if state == "menu":
            self.audio.fadeout_music(200)
            path = ap("menu_music.wav")
            if os.path.exists(path):
                self.audio.load_music(path)
                self.audio.play_music(loops=-1, volume=None)
            return

        if state == "ingame":
            self.audio.fadeout_music(200)
            music_path = None
            if self.use_crowd_ambience and os.path.exists(ap("crowd_loop.wav")):
                music_path = ap("crowd_loop.wav")
            elif os.path.exists(ap("ingame_music.wav")):
                music_path = ap("ingame_music.wav")
            if music_path:
                self.audio.load_music(music_path)
                self.audio.play_music(loops=-1, volume=None)

    # ---------------------------
    # Bucle principal
    # ---------------------------
    def game_loop(self):
        ejecutando = True
        while ejecutando:
            dt = self.reloj.tick(15)

            # Overlays (lifetime)
            if self.debug_overlays:
                self.debug_overlays.update(dt)
            if self._restart_cd and self._restart_cd.active:
                self._restart_cd.update(dt)

            # INPUT
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False

                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_F1:
                        self._debug_bounds = not self._debug_bounds
                        if hasattr(self.field, "debug"):
                            self.field.debug = self._debug_bounds

                    if evento.key == pygame.K_F3 and self.debug_overlays:
                        self.show_bounce_debug = not self.show_bounce_debug
                    # 🎾 Saque jugador 1 y jugador 2
                    # --- Jugador 1 ---
                    if evento.key == pygame.K_SPACE:
                        # Asegurarse de que haya una pelota principal
                        ball = self._ball_main
                        if ball is not None:
                            # Si la pelota está lista para sacar → lanzar hacia arriba
                            if getattr(ball, "serve_stage", "ready") == "ready":
                                # Posición inicial del jugador 1 (desde world_x, world_y)
                                start_x, start_y = world_to_screen(self.jugador1.world_x, self.jugador1.world_y)
                                ball.start_toss("P1", start_x - 20, start_y - 60)
                                self.jugador1.iniciar_saque()  # animación del lanzamiento
                            # Si la pelota ya fue lanzada → intentar golpear
                            elif getattr(ball, "serve_stage", None) in ("toss", "falling"):
                                if self.jugador1:
                                    self.jugador1.realizar_saque()
                                    ball.hit_by_player((self.jugador1.world_x, self.jugador1.world_y), zone=self.jugador1.pending_direction, is_player2=self.jugador1.is_player2)
                                else:
                                    self.jugador2.realizar_saque()
                                    ball.hit_by_player((self.jugador2.world_x, self.jugador2.world_y), zone=self.jugador2.pending_direction, is_player2=self.jugador2.is_player2)
                        else:
                            print("[WARN] No hay pelota principal activa para el saque.")

                    # --- Jugador 2 ---
                    if evento.key == pygame.K_f:
                        # Asegurarse de que haya una pelota principal
                        ball = self._ball_main
                        if ball is not None:
                            # Si la pelota está lista para sacar → lanzar hacia arriba
                            if getattr(ball, "serve_stage", "ready") == "ready":
                                start_x = self.jugador2.world_x
                                start_y = self.jugador2.world_y
                                ball.start_toss("P2", start_x, start_y)
                                self.jugador2.iniciar_saque()  # animación del lanzamiento
                            # Si la pelota ya fue lanzada → intentar golpear
                            elif getattr(ball, "serve_stage", None) in ("toss", "falling"):
                                self.jugador2.golpear_saque()
                                ball.hit_by_player()
                        else:
                            print("[WARN] No hay pelota principal activa para el saque.")

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

                    # Mute global (respeta al reiniciar)
                    if evento.key == pygame.K_m:
                        self.audio.toggle_mute_all()

                    # ---- ESTADOS ----
                    if self.estado_juego == 'menu':
                        # Atajos de modo en MENÚ: 1 → 1P, 2 → 2P
                        if evento.key == pygame.K_1:
                            self._set_mode("1P")
                        elif evento.key == pygame.K_2:
                            self._set_mode("2P")
                        elif evento.key in (pygame.K_UP, pygame.K_w):
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
                        # No aceptar entradas de gameplay durante el 3-2-1
                        if self._restart_block_input:
                            # pero sí permitir Esc para pausar/salir
                            if evento.key == pygame.K_ESCAPE:
                                if "ui_whoosh" in self.audio.sounds:
                                    self.audio.play_sound("ui_whoosh")
                                self.audio.play_sound("ui_back")
                                self.estado_juego = 'pausa'
                                self.audio.duck_music(0.08)
                            continue

                        if evento.key == pygame.K_ESCAPE:
                            if "ui_whoosh" in self.audio.sounds:
                                self.audio.play_sound("ui_whoosh")
                            self.audio.play_sound("ui_back")
                            self.estado_juego = 'pausa'
                            self.audio.duck_music(0.08)

                        # Debug SFX y AUTOGANAR → ahora “reinicio 3-2-1”
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
                                if "net_tape" in self.audio.sounds:
                                    self.audio.play_sound("net_tape")
                                if "net_body" in self.audio.sounds:
                                    self.audio.play_sound("net_body")
                                elif "net_touch" in self.audio.sounds:
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
                            if evento.key == pygame.K_c and "crowd_ooh" in self.audio.sounds:
                                self.audio.play_sound("crowd_ooh")
                            if evento.key == pygame.K_f and "crowd_ahh" in self.audio.sounds:
                                self.audio.play_sound("crowd_ahh")
                            if evento.key == pygame.K_k and "sting_match" in self.audio.sounds:
                                self.audio.duck_music(0.10)
                                self.audio.play_sound("sting_match")
                                self.audio.unduck_music()

                            # <<<< Punto 4: antes hacía _enter_victoria(); ahora 3-2-1 sin cartel >>>>
                            if evento.key == pygame.K_g:
                                self._start_debug_restart_countdown()

                    elif self.estado_juego == 'pausa':
                        if evento.key in (pygame.K_ESCAPE, pygame.K_p):
                            if "ui_whoosh" in self.audio.sounds:
                                self.audio.play_sound("ui_whoosh")
                            self.audio.play_sound("ui_back")
                            self.estado_juego = 'jugando'
                            self.audio.unduck_music()

                    elif self.estado_juego in ('victoria', 'gameover'):
                        if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self._reiniciar_partida()
                        elif evento.key == pygame.K_ESCAPE:
                            self._volver_al_menu()

            # LÓGICA
            if self.estado_juego == 'jugando':
                teclas = pygame.key.get_pressed()

                # Bloqueo de entradas/movimientos durante el 3-2-1
                if not self._restart_block_input:
                    # P1 (humano)
                    self.jugador1.mover(teclas)

                    # P2: IA en 1P, humano en 2P
                    if self.modo == "1P" and self.ai_p2 is not None and self._ball_main is not None:
                        # asegurar referencia a la pelota por si cambió en el rally
                        if getattr(self.ai_p2, "ball", None) is not self._ball_main:
                            self.ai_p2.ball = self._ball_main  # type: ignore
                        # obtener las teclas simuladas desde la IA
                        simulated_keys = self.ai_p2.get_simulated_keys()

                        # mover jugador 2 usando las teclas simuladas
                        self.jugador2.mover(simulated_keys)
                    else:
                        self.jugador2.mover(teclas)

                # Actualización de animaciones/estado visual
                self.jugador1.update()
                self.jugador2.update()

                # Pelota (no se mueve durante el 3-2-1)
                if not self._restart_block_input:
                    self.balls.update()

                # Colisiones jugador-pelota (no durante el 3-2-1)
                if not self._restart_block_input:
                    for ball in self.balls:
                        if self.jugador1.check_ball_collision(ball):
                            self.last_hitter = "P1"
                        if self.jugador2.check_ball_collision(ball):
                            self.last_hitter = "P2"


            # RENDER
            self.PANTALLA.fill(AZUL_OSCURO)

            if self.estado_juego == 'menu':
                self._draw_menu()
            elif self.estado_juego == 'opciones':
                self._draw_options()
            elif self.estado_juego == 'jugando':
                self._render_ingame()
            elif self.estado_juego == 'pausa':
                self._render_ingame()
                self._draw_center_text("PAUSA (Esc/P para volver)")
            elif self.estado_juego == 'victoria':
                self._render_victoria()
            elif self.estado_juego == 'gameover':
                self._render_gameover()

            # Overlays
            if self.debug_overlays and self.show_bounce_debug:
                self.debug_overlays.draw(self.PANTALLA)
            if self._restart_cd and self._restart_cd.active:
                self._restart_cd.draw(self.PANTALLA, "Reiniciando partida")

            pygame.display.flip()

        # Guardar mezcla al salir
        self._save_audio_config()
        pygame.quit()

    # ---------------------------
    # MENÚ
    # ---------------------------
    def _menu_select(self):
        item = self.menu_items[self.menu_index]
        if item == "Comenzar":
            self._set_music_state("ingame")
            self.estado_juego = 'jugando'
            self._start_new_rally()
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
        modo_txt = f"Modo: {self.modo}  (env VJ2D_MODO=1P/2P)"
        hint = self.font_small.render(modo_txt, True, BLANCO)
        self.PANTALLA.blit(hint, hint.get_rect(center=(ANCHO // 2, 260 + len(self.menu_items)*60 + 30)))

    def _draw_center_text(self, msg):
        surf = self.font_item.render(msg, True, BLANCO)
        self.PANTALLA.blit(surf, surf.get_rect(center=(ANCHO // 2, ALTO // 2)))

    # ---------------------------
    # Opciones (ahora incluye Modo)
    # ---------------------------
    def _enter_options(self):
        if "ui_whoosh" in self.audio.sounds:
            self.audio.play_sound("ui_whoosh")
        self.audio.play_sound("ui_select")
        self.estado_juego = 'opciones'
        self._opts_values = [
            self.modo,                              # índice 0: "1P"/"2P"
            self.audio.group_vol["music"],          # 1
            self.audio.group_vol["sfx"],            # 2
            self.audio.group_vol["ui"],             # 3
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
            # Aplicar volúmenes
            for i, g in enumerate(self._opts_groups):
                if g:  # sólo grupos de audio (índice 0 es None)
                    self.audio.set_group_volume(g, self._opts_values[i])
            self._save_audio_config()
            # Guardar modo
            self._save_game_config()
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
        if idx == 0:
            # Toggle de "Modo de juego"
            if key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                self._set_mode("2P" if self.modo == "1P" else "1P")
                self._opts_values[0] = self.modo
                return True
        else:
            # Sliders de audio
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
        title = self.font_title.render("Opciones", True, BLANCO)
        self.PANTALLA.blit(title, title.get_rect(center=(ANCHO // 2, 120)))
        y0 = 220
        for i, name in enumerate(self._opts_names):
            sel = (i == self._opts_index)
            label = f"> {name} <" if sel else f"  {name}  "
            if i == 0:
                line = f"{label} : {self.modo}  (←/→)"
            else:
                val = int(self._opts_values[i] * 100)
                line = f"{label} : {val}%"
            surf = self.font_item.render(line, True, BLANCO)
            self.PANTALLA.blit(surf, surf.get_rect(center=(ANCHO // 2, y0 + i * 60)))
        hint = "←/→ ajustar, ↑/↓ mover, Enter guardar, Esc cancelar"
        hs = self.font_small.render(hint, True, BLANCO)
        self.PANTALLA.blit(hs, hs.get_rect(center=(ANCHO // 2, y0 + 60 * len(self._opts_names) + 40)))

    # ---------------------------
    # Jingles / ESTADOS FINALES
    # ---------------------------
    def _enter_victoria(self):
        self.estado_juego = 'victoria'
        self.audio.fadeout_music(200)
        if "win_jingle" in self.audio.sounds:
            self.audio.play_sound("win_jingle")
        else:
            self._set_music_state("menu")

    def _enter_gameover(self):
        self.estado_juego = 'gameover'
        self.audio.fadeout_music(200)
        if "lose_jingle" in self.audio.sounds:
            self.audio.play_sound("lose_jingle")
        else:
            self._set_music_state("menu")

    # ---------------------------
    # RENDER helpers
    # ---------------------------
    def _render_ingame(self):
        self.field.draw(self.PANTALLA)

        if self._debug_bounds:
            self.field.draw_debug_bounds(self.PANTALLA)
            self.field.net.draw_debug(self.PANTALLA)

        for b in self.balls:
            b.draw(self.PANTALLA)

        self.jugador2.draw(self.PANTALLA)
        self.jugador1.draw(self.PANTALLA)

        if self._debug_bounds:
            self._draw_player_hitboxes(self.jugador1, self.PANTALLA)
            self._draw_player_hitboxes(self.jugador2, self.PANTALLA)

        if self.score:
            self.score.draw_hud(self.PANTALLA, self.font_hud)

    def _render_victoria(self):
        # Fondo tenue del ingame + cartel
        self._render_ingame()
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((10, 40, 10, 180))
        self.PANTALLA.blit(overlay, (0, 0))
        t1 = self.font_title.render("¡VICTORIA!", True, BLANCO)
        t2 = self.font_small.render("Enter: Reintentar   |   Esc: Volver al menú", True, BLANCO)
        self.PANTALLA.blit(t1, t1.get_rect(center=(ANCHO // 2, ALTO // 2 - 20)))
        self.PANTALLA.blit(t2, t2.get_rect(center=(ANCHO // 2, ALTO // 2 + 40)))

    def _render_gameover(self):
        self._render_ingame()
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((40, 10, 10, 180))
        self.PANTALLA.blit(overlay, (0, 0))
        t1 = self.font_title.render("GAME OVER", True, BLANCO)
        t2 = self.font_small.render("Enter: Reintentar   |   Esc: Volver al menú", True, BLANCO)
        self.PANTALLA.blit(t1, t1.get_rect(center=(ANCHO // 2, ALTO // 2 - 20)))
        self.PANTALLA.blit(t2, t2.get_rect(center=(ANCHO // 2, ALTO // 2 + 40)))

    def set_starting_player(self, player: str):
        """Permite elegir el jugador que saca ('P1' o 'P2')."""
        p = (player or "").upper()
        if p in ("P1", "P2"):
            self.current_server = p
        else:
            # Fallback por si la entrada es inválida
            print(f"[ERROR] Jugador inicial inválido: {player}. Usando '{self.current_server}'.")

    # ---------------------------
    # Rally / PUNTUACIÓN donde empieza la pelota
    # ---------------------------
    def _start_new_rally(self):
        cx, cy = self.jugador1.x, self.jugador1.y
        wx, wy = world_to_screen(cx, cy)
        self.balls.empty()
        ball = Ball(wx - 20, wy - 60, game=self, vx=0, vy=0)
        ball.z = 50
        ball.serve_stage = "ready"
        self.balls.add(ball)
        self._ball_main = ball
        ball.start_rally()
        ball.launch_toward_random_zone()
        self.last_hitter = None

        if self.ai_p2 is not None:
            self.ai_p2.ball = ball  # type: ignore

        if self.score and self.score.game_winner:
            self.score.reset_game()

    def point_for(self, who: str):
        if not self.score:
            self._start_new_rally()
            return

        self.score.point_for(who)

        gw = getattr(self.score, "game_winner", None)
        if gw is not None:
            if gw == 1:
                self._enter_victoria()
            else:
                self._enter_gameover()
            return

        self._start_new_rally()

    # ---------------------------
    # REINTENTAR / VOLVER
    # ---------------------------
    def _reiniciar_partida(self):
        # Música de juego (respetando mute)
        self._set_music_state("ingame")

        if self.score:
            if hasattr(self.score, "reset_match"):
                self.score.reset_match()
            else:
                self.score.reset_game()

        if hasattr(self.jugador1, "reset_position"):
            self.jugador1.reset_position()
        if hasattr(self.jugador2, "reset_position"):
            self.jugador2.reset_position()

        self._start_new_rally()
        self.estado_juego = 'jugando'
        self._restart_block_input = False  # liberar inputs

    def _volver_al_menu(self):
        self._set_music_state("menu")
        self.estado_juego = 'menu'

    # ---------------------------
    # Punto 4: Autowin de debug → “321 reiniciando partida”
    # ---------------------------
    def _start_debug_restart_countdown(self, ms=3000):
        if not self._restart_cd:
            # Fallback sin módulo: reinicio directo
            self._reiniciar_partida()
            return
        # Sin jingle ni cartel de victoria. Opcionalmente un whoosh suave.
        if "ui_whoosh" in self.audio.sounds:
            self.audio.play_sound("ui_whoosh")
        self._restart_block_input = True
        self._restart_cd.start(ms)

    # ---------------------------
    # Debug overlay: cajas de colisión de jugadores
    # ---------------------------
    def _draw_player_hitboxes(self, player, surface):
        try:
            from engine.config.collisions import COLOR_BODY, COLOR_RACKET
        except Exception:
            COLOR_BODY, COLOR_RACKET = (50, 220, 60), (240, 200, 40)

        if hasattr(player, "body_rect"):
            pygame.draw.rect(surface, COLOR_BODY, player.body_rect, width=2)
        if hasattr(player, "racket_rect"):
            pygame.draw.rect(surface, COLOR_RACKET, player.racket_rect, width=2)
