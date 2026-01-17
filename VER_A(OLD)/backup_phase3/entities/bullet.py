import math
import pygame
from colors import COLORS

class Bullet:
    def __init__(self, x, y, angle, is_enemy=False):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 12
        self.radius = 4
        self.alive = True
        self.is_enemy = is_enemy

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

    def draw(self, screen, camera_x, camera_y):
        color = (255, 100, 100) if self.is_enemy else COLORS['BULLET']
        pygame.draw.circle(screen, color, (int(self.x - camera_x), int(self.y - camera_y)), self.radius)
