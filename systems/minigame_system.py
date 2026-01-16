import pygame
import random
import math
from core.ecs_manager import ECSManager
from core.event_bus import EventBus
from core.game_state_manager import GameStateManager
from core.resource_manager import ResourceManager
from components.interaction import InteractionState
from components.identity import Identity

class MiniGameSystem:
    def __init__(self, ecs: ECSManager, event_bus: EventBus):
        self.ecs = ecs
        self.event_bus = event_bus
        self.active = False
        self.game_type = None
        self.on_success = None
        self.on_fail = None
        self.start_time = 0
        self.duration = 10000
        
        # UI Resources
        self.resource_manager = ResourceManager.get_instance()
        self.width = 240
        self.height = 160
        
        # Game State
        self.mash_progress = 0
        self.timing_cursor = 0
        self.timing_dir = 1
        self.timing_target = (0, 0)
        
        # Event Sub
        self.event_bus.subscribe("START_MINIGAME", self.start_game)

    def start_game(self, data):
        self.active = True
        self.game_type = data['type']
        self.difficulty = data.get('difficulty', 1)
        self.on_success = data.get('on_success')
        self.on_fail = data.get('on_fail')
        self.start_time = pygame.time.get_ticks()
        
        # Init specific game
        if self.game_type == 'MASHING':
            self.mash_progress = 20
        elif self.game_type == 'TIMING':
            self.timing_cursor = 0
            self.timing_dir = 1
            w = 60 - (self.difficulty * 4)
            c = self.width // 2
            self.timing_target = (c - w//2 - 20, c + w//2 - 20)

        # 플레이어 입력 잠금 (InputSystem에서 active 체크 필요)
        # 여기서는 Event로 알릴 수도 있음

    def update(self, dt):
        if not self.active: return
        
        if pygame.time.get_ticks() - self.start_time > self.duration:
            self.fail_game()
            return
            
        if self.game_type == 'MASHING':
            self.mash_progress = max(0, self.mash_progress - 0.35)
        elif self.game_type == 'TIMING':
            self.timing_cursor += (3 + self.difficulty) * self.timing_dir
            if self.timing_cursor < 0 or self.timing_cursor > self.width - 40:
                self.timing_dir *= -1

        # Handle Input (직접 처리 or InputSystem에서 전달)
        # 여기서는 직접 처리 (ECS loop 내에서 event 전달받아야 함)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            # Simple debounce needed in real impl
            pass

    def handle_event(self, event):
        if not self.active or event.type != pygame.KEYDOWN: return
        
        if self.game_type == 'MASHING':
            if event.key == pygame.K_SPACE:
                self.mash_progress += 12
                if self.mash_progress >= 100: self.success_game()
        elif self.game_type == 'TIMING':
            if event.key == pygame.K_SPACE:
                if self.timing_target[0] <= self.timing_cursor <= self.timing_target[1]:
                    self.success_game()
                else:
                    self.fail_game()

    def success_game(self):
        self.active = False
        if self.on_success: self.on_success()
        self.event_bus.publish("MINIGAME_END", {'result': 'success'})

    def fail_game(self):
        self.active = False
        if self.on_fail: self.on_fail()
        self.event_bus.publish("MINIGAME_END", {'result': 'fail'})

    def draw(self, screen, x, y):
        if not self.active: return
        
        # Overlay Drawing
        rect = pygame.Rect(x - self.width//2, y, self.width, self.height)
        pygame.draw.rect(screen, (25, 25, 35), rect, border_radius=8)
        pygame.draw.rect(screen, (180, 180, 190), rect, 2, border_radius=8)
        
        font = self.resource_manager.get_font('bold')
        title = font.render(self.game_type, True, (255, 255, 255))
        screen.blit(title, (rect.centerx - title.get_width()//2, rect.y + 20))
        
        cx, cy = rect.centerx, rect.centery + 10
        
        if self.game_type == 'MASHING':
            pygame.draw.rect(screen, (40, 40, 40), (cx-80, cy, 160, 25))
            pygame.draw.rect(screen, (0, 255, 100), (cx-80, cy, 160*(self.mash_progress/100), 25))
        elif self.game_type == 'TIMING':
            pygame.draw.rect(screen, (40, 40, 40), (cx-100, cy, 200, 25))
            tx, tx2 = self.timing_target
            pygame.draw.rect(screen, (255, 255, 0), (cx-100 + tx, cy, tx2-tx, 25))
            pygame.draw.rect(screen, (255, 255, 255), (cx-100 + self.timing_cursor, cy-2, 3, 29))
