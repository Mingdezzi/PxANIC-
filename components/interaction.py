from dataclasses import dataclass
from typing import Any

@dataclass
class Interaction:
    # 키 입력 상태
    e_key_pressed: bool = False
    interaction_hold_timer: int = 0
    
    # 현재 상호작용 중인 대상 (없으면 None)
    active_target: Any = None
    
    # 작업 진행 상태 (예: 문 따기 중...)
    is_interacting: bool = False
    progress_timer: int = 0
    interaction_type: str = "" # "UNLOCK", "WORK", "HACK"
