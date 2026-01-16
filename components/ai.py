from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any, Dict

@dataclass
class AIBrain:
    active: bool = True
    state: str = "IDLE" # IDLE, MOVE, CHASE, WORK, HIDE, etc.
    
    # Behavior Tree 관련
    tree: Any = None # BT Root Node (직렬화 불가할 수 있음, 로드 시 조립 필요)
    
    # Pathfinding
    path: List[Tuple[int, int]] = field(default_factory=list)
    current_path_target: Optional[Tuple[int, int]] = None
    is_pathfinding: bool = False
    path_cooldown: int = 0
    
    # Targets
    target_entity_id: Optional[int] = None
    chase_target_id: Optional[int] = None
    target_pos: Optional[Tuple[int, int]] = None
    
    # Memory
    suspicion_meter: Dict[str, int] = field(default_factory=dict) # Name: Value
    last_seen_pos: Optional[Tuple[int, int]] = None
    investigate_pos: Optional[Tuple[int, int]] = None
    failed_targets: Dict[Tuple[int, int], int] = field(default_factory=dict)
    
    # Stats Snapshots (For diff check)
    last_stats: Dict[str, int] = field(default_factory=lambda: {'hp': 100, 'coins': 0})
