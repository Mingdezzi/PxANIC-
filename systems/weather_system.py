import pygame
import random
import math
from settings import SCREEN_WIDTH, SCREEN_HEIGHT

class WeatherSystem:
    def __init__(self):
        self.current_weather = 'CLEAR'
        self.particles = [] # [x, y, speed, type]
        
        # 미리 파티클 생성
        for _ in range(100):
            self.particles.append([
                random.randint(0, SCREEN_WIDTH),
                random.randint(0, SCREEN_HEIGHT),
                random.randint(5, 10), # speed
                random.choice([0, 1])  # 0: rain, 1: snow
            ])

    def update(self, dt, weather_type):
        self.current_weather = weather_type
        if weather_type in ['CLEAR', 'FOG']: return

        # [복구] 파티클 움직임 (PlayState update 로직 이식)
        current_w, current_h = pygame.display.get_surface().get_size()
        
        for p in self.particles:
            p[1] += p[2] # y축 이동
            if weather_type == 'RAIN': 
                p[0] -= 1 # 빗물 사선 효과
            
            # 화면 밖으로 나가면 재배치
            if p[1] > current_h:
                p[1] = -10
                p[0] = random.randint(0, current_w)

    def draw(self, screen):
        if self.current_weather == 'CLEAR': return

        # [복구] 날씨 그리기 (PlayState draw 로직 이식)
        if self.current_weather == 'RAIN':
            for p in self.particles:
                start_pos = (p[0], p[1])
                end_pos = (p[0] - 2, p[1] + 10)
                pygame.draw.line(screen, (150, 150, 255, 150), start_pos, end_pos, 1)
                
        elif self.current_weather == 'SNOW':
            for p in self.particles:
                pygame.draw.circle(screen, (255, 255, 255, 200), (int(p[0]), int(p[1])), 2)
                
        elif self.current_weather == 'FOG':
            # 안개 효과 (전체 화면 덮기)
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            alpha = 100 + int(math.sin(pygame.time.get_ticks() * 0.002) * 20)
            overlay.fill((200, 200, 220, alpha))
            screen.blit(overlay, (0, 0))