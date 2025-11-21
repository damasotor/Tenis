import os
import pygame
from engine.game_object import GameObject

class Background(GameObject):
    def __init__(self, game):
        self.game = game
        json_path = os.path.join('assets', 'sprites', 'background_animation', 'background.json')
        super().__init__(0, 0, json_path=json_path)
        self.current_animation = "idle" if "idle" in self.animations else list(self.animations.keys())[0]
        self.frame_index = 0
        self.anim_timer = 0
        self.aplaudiendo = False
        self.animation_speed = 120
        self.rect = self.sprite_sheet.get_rect(topleft=(0, 0))

    def aplaudir(self):
        """Activa animación + sonido de aplauso."""
        if "clap" in self.animations:
            self.current_animation = "clap"
            self.frame_index = 0
            self.aplaudiendo = True
            self.anim_timer = 0

        # 🔊 SONIDO DE PÚBLICO
        if "crowd_ooh" in self.game.audio.sounds:
            self.game.audio.play_sound("crowd_ooh")

    def update(self, dt):
        if not self.animations:
            return

        self.anim_timer += dt
        if self.anim_timer >= self.animation_speed:
            self.anim_timer = 0
            self.frame_index += 1

            if self.aplaudiendo and self.current_animation == "clap":
                if self.frame_index >= len(self.animations["clap"]):
                    self.current_animation = "idle"
                    self.frame_index = 0
                    self.aplaudiendo = False
            else:
                if self.frame_index >= len(self.animations[self.current_animation]):
                    self.frame_index = 0

    def draw(self, surface):
        if not self.sprite_sheet or not self.animations:
            return

        frames = self.animations.get(self.current_animation, [])
        if not frames:
            return

        self.frame_index %= len(frames)
        fx, fy, fw, fh = frames[self.frame_index]
        frame_surf = self.sprite_sheet.subsurface(pygame.Rect(fx, fy, fw, fh))
        surface.blit(frame_surf, (0, 0))
