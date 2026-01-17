from dataclasses import dataclass, field
from typing import Dict

@dataclass
class Stats:
    hp: int = 100
    max_hp: int = 100
    ap: int = 100
    max_ap: int = 100
    alive: bool = True
    coins: int = 0

@dataclass
class StatusEffects:
    # 감정 상태 (0~5 단계)
    emotions: Dict[str, int] = field(default_factory=dict)
    # 버프/디버프 상태 (True/False)
    buffs: Dict[str, bool] = field(default_factory=lambda: {
        'INFINITE_STAMINA': False,
        'SILENT': False,
        'FAST_WORK': False,
        'NO_PAIN': False
    })
    # 사운드 쿨타임 (System용)
    sound_timers: Dict[str, int] = field(default_factory=lambda: {
        'HEARTBEAT': 0, 
        'COUGH': 0, 
        'SCREAM': 0, 
        'FOOTSTEP': 0
    })
    # 기타 상태
    stun_timer: int = 0
    is_hiding: bool = False
    hiding_type: int = 0 # 1: Passive, 2: Active
    hidden_in_solid: bool = False
    
    # 신체 상태
    shiver_timer: int = 0
    blink_timer: int = 0
    breath_gauge: float = 100.0
    narcolepsy_timer: int = 0
    is_eyes_closed: bool = False
