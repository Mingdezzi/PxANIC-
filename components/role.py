from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Role:
    main_role: str  # "CITIZEN", "MAFIA", "POLICE", "DOCTOR", "SPECTATOR"
    sub_role: Optional[str] = None  # "FARMER", "MINER", "FISHER"
    
    # 외형 커스터마이징 데이터 (기존 custom 딕셔너리 대체)
    skin_idx: int = 0
    clothes_idx: int = 0
    hat_idx: int = 0
    
    is_revealed: bool = False
    
    # 특수 능력 쿨타임 및 상태
    ability_cooldown: int = 0
    bullets_fired_today: int = 0  # 경찰 발포 제한 확인용
    daily_work_count: int = 0     # 시민 업무 횟수
    work_step: int = 0            # 업무 단계
