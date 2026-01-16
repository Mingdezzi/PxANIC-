from dataclasses import dataclass
from typing import Tuple
from settings import SPEED_WALK

@dataclass
class Physics:
    speed: float = SPEED_WALK
    velocity: Tuple[float, float] = (0.0, 0.0) # [New] 현재 프레임의 이동 벡터
    move_state: str = "WALK"  # "WALK", "RUN", "CROUCH"
    is_moving: bool = False
    
    # 물리적 충돌 무시 여부
    no_clip: bool = False