import pygame
import random
from .base_system import BaseSystem
from settings import SCREEN_WIDTH, SCREEN_HEIGHT

class WeatherSystem(BaseSystem):
    def __init__(self):
        self.particles = []
        self.current_weather = 'CLEAR'
        self.spawn_timer = 0

    def update(self, dt, current_weather):
        self.current_weather = current_weather
        
        if self.current_weather == 'RAIN':
            self._spawn_rain(dt)
        elif self.current_weather == 'SNOW':
            self._spawn_snow(dt)
            
        self._update_particles(dt)

    def draw(self, screen):
        for p in self.particles:
            if self.current_weather == 'RAIN':
                # 비: 선으로 그리기
                start = (p['x'], p['y'])
                end = (p['x'] + p['vx']*0.1, p['y'] + p['vy']*0.1)
                pygame.draw.line(screen, (150, 150, 255, 150), start, end, 1)
            elif self.current_weather == 'SNOW':
                # 눈: 원으로 그리기
                pygame.draw.circle(screen, (255, 255, 255, 200), (int(p['x']), int(p['y'])), int(p['size']))

    def _spawn_rain(self, dt):
        self.spawn_timer += dt
        if self.spawn_timer > 10: # 빈도
            self.spawn_timer = 0
            for _ in range(5):
                self.particles.append({
                    'x': random.randint(-100, SCREEN_WIDTH + 100),
                    'y': -10,
                    'vx': random.randint(-2, 2) * 10,
                    'vy': random.randint(15, 25) * 20,
                    'life': 100
                })

    def _spawn_snow(self, dt):
        self.spawn_timer += dt
        if self.spawn_timer > 50:
            self.spawn_timer = 0
            self.particles.append({
                'x': random.randint(-100, SCREEN_WIDTH + 100),
                'y': -10,
                'vx': random.randint(-20, 20),
                'vy': random.randint(2, 5) * 10,
                'size': random.randint(2, 4),
                'life': 200
            })

    def _update_particles(self, dt):
        dt_sec = dt / 1000.0
        for p in self.particles[:]:
            p['x'] += p['vx'] * dt_sec
            p['y'] += p['vy'] * dt_sec
            
            # 화면 밖 제거
            if p['y'] > SCREEN_HEIGHT + 10:
                self.particles.remove(p)
