import pygame
import math
import random
from core.ecs_manager import ECSManager
from core.event_bus import EventBus
from core.game_state_manager import GameStateManager
from core.resource_manager import ResourceManager
from components.identity import Identity
from components.common import Transform
from settings import SOUND_INFO, TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT

class VisualSoundEffect:
    def __init__(self, x, y, text, color, size_scale=1.0, duration=1500, shake=False, blink=False):
        self.x = x
        self.y = y
        self.text = str(text)
        self.color = color
        self.duration = duration
        self.start_time = pygame.time.get_ticks()
        self.alive = True
        self.shake = shake
        self.blink = blink
        
        angle_deg = random.uniform(240, 300)
        self.angle_rad = math.radians(angle_deg)
        self.speed = 1.2 * size_scale
        
        self.resource_manager = ResourceManager.get_instance()
        # 폰트 로드 (크기 비례)
        font_size = int(max(16, (52 * size_scale) * 0.5))
        self.font = pygame.font.SysFont("arial black", font_size, bold=True)
        
        self.normal_image = self._render_text(self.text, self.color)
        self.blink_image = self._render_text(self.text, (255, 255, 255)) if blink else None
        self.image = self.normal_image
        
        self.offset_x, self.offset_y = 0, 0
        self.alpha = 255

    def _render_text(self, text, color):
        txt = self.font.render(text, True, color)
        outline = self.font.render(text, True, (0, 0, 0))
        w, h = txt.get_size()
        s = pygame.Surface((w+4, h+4), pygame.SRCALPHA)
        for dx, dy in [(-2,0), (2,0), (0,-2), (0,2)]: s.blit(outline, (dx+2, dy+2))
        s.blit(txt, (2, 2))
        return s

    def update(self):
        now = pygame.time.get_ticks()
        elapsed = now - self.start_time
        if elapsed > self.duration: self.alive = False; return
        
        progress = elapsed / self.duration
        dist = self.speed * (elapsed / 12)
        self.offset_x = math.cos(self.angle_rad) * dist
        self.offset_y = math.sin(self.angle_rad) * dist + (progress**2 * 30)
        
        if self.shake:
            intensity = 3 * (1 - progress)
            self.offset_x += random.uniform(-intensity, intensity)
            self.offset_y += random.uniform(-intensity, intensity)
            
        if self.blink and self.blink_image:
            self.image = self.blink_image if (now // 200) % 2 == 0 else self.normal_image
            
        if progress > 0.6: self.alpha = int(255 * (1 - (progress - 0.6) / 0.4))
        else: self.alpha = 255

class SoundSystem:
    def __init__(self, ecs: ECSManager, event_bus: EventBus):
        self.ecs = ecs
        self.event_bus = event_bus
        self.visual_effects = []
        self.event_bus.subscribe("PLAY_SOUND", self.handle_sound_event)

    def update(self, dt):
        for fx in self.visual_effects[:]:
            fx.update()
            if not fx.alive: self.visual_effects.remove(fx)

    def handle_sound_event(self, data):
        # data format: (s_type, x, y, radius, source_role)
        if len(data) == 5: s_type, x, y, radius, source_role = data
        else: s_type, x, y, radius = data; source_role = "UNKNOWN"
        
        # Local Player 찾기 (청자)
        players = [e for e in self.ecs.get_entities_with(Identity) if self.ecs.get_component(e, Identity).is_player]
        if not players: return
        player_id = players[0]
        player_transform = self.ecs.get_component(player_id, Transform)
        player_identity = self.ecs.get_component(player_id, Identity)
        
        dist = math.sqrt((player_transform.x - x)**2 + (player_transform.y - y)**2)
        if dist > radius * 1.5: return # 안 들림
        
        # 주관적 시각화 로직 (Legacy Logic Preservation)
        info = SOUND_INFO.get(s_type, {'base_rad': 5, 'color': (200, 200, 200)})
        base_color = info['color']
        my_role = player_identity.role
        
        importance = 1.0
        final_color = base_color
        shake = False
        blink = False
        
        if my_role in ["CITIZEN", "DOCTOR"]:
            if source_role == "MAFIA":
                importance, final_color, shake = 2.0, (255, 50, 50), True
                if s_type in ["BANG!", "SLASH", "SCREAM"]: importance = 2.5
            elif source_role == "POLICE":
                importance, final_color = 1.5, (50, 150, 255)
        elif my_role == "MAFIA":
            if source_role == "POLICE":
                importance, final_color, blink = 2.5, (200, 50, 255), True
            elif source_role in ["CITIZEN", "DOCTOR"]:
                importance, final_color = 1.5, (255, 255, 100)
        elif my_role == "POLICE":
            if source_role == "MAFIA":
                importance, final_color = 2.0, (255, 150, 0)
        
        if s_type in ["SIREN", "BOOM"]: importance, blink = 2.5, True
        
        dist_factor = max(0.2, 1.0 - (dist / (radius * 1.5)))
        base_scale = radius / (6 * TILE_SIZE)
        final_scale = max(0.5, min(2.5, base_scale * importance * dist_factor))
        
        self.visual_effects.append(VisualSoundEffect(x, y, s_type, final_color, final_scale, shake=shake, blink=blink))

    def draw(self, screen, camera):
        for fx in self.visual_effects:
            dx = fx.x - camera.x - (fx.image.get_width() // 2) + fx.offset_x
            dy = fx.y - camera.y - (fx.image.get_height() // 2) + fx.offset_y
            
            # Alpha 적용
            if fx.alpha < 255:
                temp = fx.image.copy()
                temp.set_alpha(fx.alpha)
                screen.blit(temp, (dx, dy))
            else:
                screen.blit(fx.image, (dx, dy))
