from dataclasses import dataclass, field
from typing import Dict, Any, Tuple

@dataclass
class Stats:
    hp: float = 100.0
    max_hp: float = 100.0
    ap: float = 100.0
    max_ap: float = 100.0
    alive: bool = True
    
    # 감정 상태 (예: {'FEAR': 1, 'HAPPINESS': 1})
    emotions: Dict[str, int] = field(default_factory=dict)
    
    # 상태 이상 및 버프 (예: {'STUNNED': True, 'INFINITE_STAMINA': False})
    # 기존 buffs 딕셔너리와 status_effects를 통합 관리
    status_effects: Dict[str, Any] = field(default_factory=lambda: {
        'STUNNED': False,
        'SILENT': False,
        'NO_PAIN': False,
        'INFINITE_STAMINA': False,
        'FAST_WORK': False,
        'DOPAMINE': False  # 마피아 추격 시
    })
    
    # 신체 상태
    breath_gauge: float = 100.0
    is_eyes_closed: bool = False  # 기면증 등으로 눈 감김
    vibration_offset: Tuple[int, int] = (0, 0) # 공포로 인한 떨림
