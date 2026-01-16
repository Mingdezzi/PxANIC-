from dataclasses import dataclass
from typing import Tuple, List, Optional
import pygame

@dataclass
class Transform:
    x: float
    y: float
    rotation: float = 0.0
    # Rect는 시스템에서 x, y 기반으로 갱신하거나 필요시 사용
    # 여기서는 편의를 위해 초기값만 설정, MovementSystem이 동기화 책임
    width: int = 32
    height: int = 32
    
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

@dataclass
class Velocity:
    dx: float = 0.0
    dy: float = 0.0
    speed_modifier: float = 1.0

@dataclass
class Sprite:
    visible: bool = True
    alpha: int = 255
    # 렌더링에 필요한 추가 정보 (기존 CharacterRenderer 호환)
    role: str = "CITIZEN"
    sub_role: Optional[str] = None
    custom_data: dict = None # skin, clothes, hat 등

    def __post_init__(self):
        if self.custom_data is None:
            self.custom_data = {'skin': 0, 'clothes': 0, 'hat': 0}

@dataclass
class Animation:
    current_anim: str = "IDLE"
    frame_index: int = 0
    timer: float = 0.0
    facing_dir: Tuple[int, int] = (0, 1) # (x, y)
