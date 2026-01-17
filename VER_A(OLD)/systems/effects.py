import pygame
import math
import random
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, SHARED_FONTS

class VisualSound:
    def __init__(self, x, y, text, color, size_scale=1.0, duration=1500, shake=False, blink=False):
        self.x = x
        self.y = y
        self.text = str(text)
        self.base_color = color
        self.color = color
        self.duration = duration
        self.start_time = pygame.time.get_ticks()
        self.alive = True
        
        self.shake = shake
        self.blink = blink

        angle_deg = random.uniform(240, 300)
        self.angle_rad = math.radians(angle_deg)
        self.speed = 1.2 * size_scale

        base_size = int(max(16, (52 * size_scale) * 0.5))

        font_key = (base_size, 'arial black')
        if font_key not in SHARED_FONTS:
            if not pygame.font.get_init():
                pygame.font.init()
            try:
                SHARED_FONTS[font_key] = pygame.font.SysFont("arial black", base_size, bold=True)
            except:
                SHARED_FONTS[font_key] = pygame.font.SysFont("arial", base_size, bold=True)
        
        self.font = SHARED_FONTS[font_key]

        self.normal_image = self.render_text_with_outline(self.text, self.font, color, (0, 0, 0), 2)
        self.blink_image = None
        if self.blink:
            self.blink_image = self.render_text_with_outline(self.text, self.font, (255, 255, 255), (0, 0, 0), 2)
            
        self.image = self.normal_image

        self.offset_x = 0
        self.offset_y = 0
        self.alpha = 255

    def render_text_with_outline(self, text, font, inner_color, outline_color, thickness):
        text_surf = font.render(text, True, inner_color)
        outline_surf = font.render(text, True, outline_color)
        w, h = text_surf.get_size()
        final_surf = pygame.Surface((w + thickness*2, h + thickness*2), pygame.SRCALPHA)

        for dx, dy in [(-thickness,0), (thickness,0), (0,-thickness), (0,thickness)]:
            final_surf.blit(outline_surf, (dx + thickness, dy + thickness))
        final_surf.blit(text_surf, (thickness, thickness))
        return final_surf

    def update(self):
        now = pygame.time.get_ticks()
        elapsed = now - self.start_time
        if elapsed > self.duration:
            self.alive = False
            return

        progress = elapsed / self.duration
        dist = self.speed * (elapsed / 12)
        
        self.offset_x = math.cos(self.angle_rad) * dist
        self.offset_y = math.sin(self.angle_rad) * dist + (progress**2 * 30)

        if self.shake:
            shake_intensity = 3 * (1 - progress)
            self.offset_x += random.uniform(-shake_intensity, shake_intensity)
            self.offset_y += random.uniform(-shake_intensity, shake_intensity)

        if self.blink and self.blink_image:
            if (now // 200) % 2 == 0:
                self.image = self.blink_image
            else:
                self.image = self.normal_image

        if progress > 0.6:
            self.alpha = int(255 * (1 - (progress - 0.6) / 0.4))
        else:
            self.alpha = 255

    def draw(self, screen, camera_x, camera_y):
        if not self.alive: return
        draw_x = self.x - camera_x - (self.image.get_width() // 2) + self.offset_x
        draw_y = self.y - camera_y - (self.image.get_height() // 2) + self.offset_y

        draw_surf = self.image.copy()
        draw_surf.set_alpha(self.alpha)
        screen.blit(draw_surf, (draw_x, draw_y))

class SoundDirectionIndicator:
    _SHARED_GLOW_SURF = None

    def __init__(self, source_x, source_y, duration=500):
        self.source_x = source_x
        self.source_y = source_y
        self.duration = duration
        self.start_time = pygame.time.get_ticks()
        self.alive = True
        
        if SoundDirectionIndicator._SHARED_GLOW_SURF is None:
            SoundDirectionIndicator._SHARED_GLOW_SURF = self._create_glow_surface()
            
        self.glow_img = SoundDirectionIndicator._SHARED_GLOW_SURF

    def _create_glow_surface(self):
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        for r in range(100, 0, -2):
            alpha = int(150 * (r / 100))
            pygame.draw.circle(surf, (255, 0, 0, alpha), (100, 100), r)
        return surf

    def update(self):
        if pygame.time.get_ticks() - self.start_time > self.duration:
            self.alive = False

    def draw(self, screen, player_rect, camera_x, camera_y):
        dx = self.source_x - player_rect.centerx
        dy = self.source_y - player_rect.centery
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist < 400: return 

        angle = math.atan2(dy, dx)
        
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        radius_x = SCREEN_WIDTH // 2 - 50
        radius_y = SCREEN_HEIGHT // 2 - 50
        
        edge_x = cx + math.cos(angle) * radius_x
        edge_y = cy + math.sin(angle) * radius_y
        
        elapsed = pygame.time.get_ticks() - self.start_time
        alpha = 255 - int(255 * (elapsed / self.duration))
        
        final_surf = self.glow_img.copy()
        final_surf.set_alpha(alpha)
        screen.blit(final_surf, (edge_x - 100, edge_y - 100), special_flags=pygame.BLEND_ADD)
