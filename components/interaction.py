from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Inventory:
    items: Dict[str, int] = field(default_factory=dict) # ItemKey: Count
    equipped_item: Optional[str] = None
    
    # 장비 배터리 상태 등
    device_on: bool = False
    device_battery: float = 100.0
    flashlight_on: bool = False
    powerbank_uses: int = 0

@dataclass
class InteractionState:
    last_interaction_time: int = 0
    e_key_pressed: bool = False
    e_hold_start_time: int = 0
    
    # 현재 수행 중인 작업
    is_working: bool = False
    work_finish_timer: int = 0
    work_tile_pos: Optional[tuple] = None
    
    is_unlocking: bool = False
    unlock_finish_timer: int = 0
    
    # 스킬 사용 여부
    ability_used: bool = False
    last_attack_time: int = 0
    bullets_fired_today: int = 0
    
    # 투표
    vote_count: int = 0
    
    # 일일 작업량
    daily_work_count: int = 0
    work_step: int = 0
