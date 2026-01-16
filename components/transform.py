from dataclasses import dataclass, field
import pygame
from typing import Tuple

@dataclass
class Transform:
    x: float
    y: float
    width: int = 32
    height: int = 32
    rect: pygame.Rect = field(init=False)
    facing: Tuple[int, int] = (0, 1)  # (dx, dy)
    
    def __post_init__(self):
        self.rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)
