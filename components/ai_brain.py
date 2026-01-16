from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any

# BT 노드 클래스 정의 (데이터로서의 구조)
class BTNode:
    def tick(self, entity, blackboard): return "FAILURE"

@dataclass
class AIBrain:
    tree: Optional[Any] = None  # Behavior Tree Root Node
    current_state: str = "IDLE"
    
    target_entity: Optional[Any] = None
    last_known_pos: Optional[Tuple[int, int]] = None
    
    path: List[Tuple[int, int]] = field(default_factory=list)
    pending_path: Optional[List[Tuple[int, int]]] = None
    is_pathfinding: bool = False
    path_cooldown: int = 0
    
    # AI 기억/감정 데이터
    suspicion_meter: Dict[str, float] = field(default_factory=dict)
    failed_targets: Dict[str, int] = field(default_factory=dict)
    investigate_pos: Optional[Tuple[int, int]] = None
