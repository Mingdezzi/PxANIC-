from dataclasses import dataclass, field
from typing import List, Tuple, Any

@dataclass
class Graphics:
    # 시각적 상태
    is_hiding: bool = False
    hiding_type: int = 0  # 0: None, 1: Passive(Dark), 2: Active(Object/Bed)
    
    # 장비 상태 (외형에 영향)
    flashlight_on: bool = False
    device_on: bool = False
    device_battery: float = 100.0
    
    # 애니메이션/렌더링 보정
    color: Tuple[int, int, int] = (255, 255, 255)
    scale: float = 1.0
    visible: bool = True
