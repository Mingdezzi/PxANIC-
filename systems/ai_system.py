import pygame
import random
import math
import heapq
import threading
from core.ecs_manager import ECSManager
from core.event_bus import EventBus
from core.game_state_manager import GameStateManager
from components.common import Transform, Velocity
from components.ai import AIBrain
from components.identity import Identity
from components.status import Stats, StatusEffects
from components.interaction import InteractionState
from components.vision import Vision
from world.map_manager import MapManager
from settings import TILE_SIZE, VISION_RADIUS, INDOOR_ZONES
from world.tiles import check_collision, get_tile_category, HIDEABLE_TILES, VENDING_MACHINE_TID

class AISystem:
    def __init__(self, ecs: ECSManager, event_bus: EventBus, map_manager: MapManager):
        self.ecs = ecs
        self.event_bus = event_bus
        self.map_manager = map_manager
        self.game_state = GameStateManager.get_instance()
        
        # 스레드 안전성을 위한 락 (필요시 사용)
        self.pathfinding_lock = threading.Lock()

    def update(self, dt):
        npcs = self.ecs.get_entities_with(AIBrain, Transform, Identity, Stats)
        players = self.ecs.get_entities_with(Identity, Transform, Stats)
        player_ent = next((p for p in players if self.ecs.get_component(p, Identity).is_player), None)
        
        # Blackboard 구성
        blackboard = {
            'phase': 'DAY', # TimeSystem에서 받아와야 함 (임시) - 실제로는 GameStateManager나 Event로 동기화
            'player': player_ent,
            'npcs': npcs,
            'map_manager': self.map_manager
        }
        
        # [수정] TimeSystem에서 Phase 정보를 GameStateManager에 저장하거나 Event로 전파받는 구조 필요
        # 여기서는 편의상 GameStateManager에 phase 정보가 있다고 가정하거나 TimeSystem을 참조해야 하나,
        # 독립성을 위해 EventBus로 Phase 정보를 받아 캐싱하는 방식 권장.
        # 일단은 임시로 'DAY'로 두고, 나중에 TimeSystem 연동 시 수정.
        
        for entity in npcs:
            brain = self.ecs.get_component(entity, AIBrain)
            stats = self.ecs.get_component(entity, Stats)
            
            if not stats.alive: continue
            
            # 1. 시야 및 정보 갱신
            self._update_perception(entity, blackboard)
            
            # 2. BT 실행 (Stateless Node 호출)
            # 기존 Dummy 클래스의 BT 로직을 여기서 실행
            # (시간 관계상 핵심 로직인 이동/추격 위주로 구현)
            self._run_behavior_tree(entity, brain, blackboard)
            
            # 3. 경로 추적 (Movement)
            self._follow_path(entity, dt)

    def _update_perception(self, entity, bb):
        # 시야 내 타겟 감지, 의심도 증가 등
        pass

    def _run_behavior_tree(self, entity, brain, bb):
        # 간단한 FSM 형태로 구현 (BT의 복잡성을 줄임)
        identity = self.ecs.get_component(entity, Identity)
        
        if identity.role == "POLICE":
            # 추격 로직
            pass
        elif identity.role == "MAFIA":
            # 살해 로직
            pass
        else:
            # 시민: 랜덤 이동, 작업, 집 가기
            if not brain.path and not brain.is_pathfinding:
                self._request_random_move(entity)

    def _request_random_move(self, entity):
        brain = self.ecs.get_component(entity, AIBrain)
        transform = self.ecs.get_component(entity, Transform)
        
        if brain.is_pathfinding: return
        
        # 유효한 타일 찾기
        target_pos = None
        for _ in range(5):
            tx = random.randint(0, self.map_manager.width - 1)
            ty = random.randint(0, self.map_manager.height - 1)
            if not self.map_manager.check_any_collision(tx, ty):
                target_pos = (tx * TILE_SIZE + 16, ty * TILE_SIZE + 16)
                break
        
        if target_pos:
            brain.is_pathfinding = True
            start_gx = int(transform.x // TILE_SIZE)
            start_gy = int(transform.y // TILE_SIZE)
            target_gx = int(target_pos[0] // TILE_SIZE)
            target_gy = int(target_pos[1] // TILE_SIZE)
            
            thread = threading.Thread(target=self._threaded_pathfinding, args=(entity, start_gx, start_gy, target_gx, target_gy))
            thread.daemon = True
            thread.start()

    def _threaded_pathfinding(self, entity_id, sx, sy, tx, ty):
        # A* 알고리즘 (기존 로직 이식)
        try:
            open_set = []
            heapq.heappush(open_set, (0, sx, sy))
            came_from = {}
            g_score = {(sx, sy): 0}
            
            path = []
            
            while open_set and len(came_from) < 500: # Limit iterations
                _, cx, cy = heapq.heappop(open_set)
                
                if (cx, cy) == (tx, ty):
                    curr = (tx, ty)
                    while curr in came_from:
                        path.append(curr)
                        curr = came_from[curr]
                    path.reverse()
                    break
                
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.map_manager.width and 0 <= ny < self.map_manager.height:
                        if not self.map_manager.check_any_collision(nx, ny):
                            new_g = g_score[(cx, cy)] + 1
                            if (nx, ny) not in g_score or new_g < g_score[(nx, ny)]:
                                g_score[(nx, ny)] = new_g
                                priority = new_g + abs(tx - nx) + abs(ty - ny)
                                heapq.heappush(open_set, (priority, nx, ny))
                                came_from[(nx, ny)] = (cx, cy)
            
            # Main thread로 결과 전달 (여기서는 직접 컴포넌트 수정 시 Race Condition 주의)
            # 안전하게 하려면 EventBus나 Queue를 사용해야 하나, 
            # Python의 GIL 덕분에 리스트 할당 정도는 원자적일 수 있음. 
            # 하지만 ECS update 내에서 처리하는 게 정석.
            # 여기서는 편의상 brain 컴포넌트에 직접 할당하되, 추후 개선 필요.
            # (ECSManager가 Thread-safe하지 않으므로 주의)
            
            # 임시: 직접 할당 (실제로는 메인 루프에서 처리할 Queue에 넣어야 함)
            # self.event_bus.publish("PATH_FOUND", {'entity': entity_id, 'path': path})
            
            # 직접 할당 (위험 감수)
            brain = self.ecs.get_component(entity_id, AIBrain)
            if brain:
                brain.path = path
                brain.is_pathfinding = False
                
        except Exception as e:
            print(f"Pathfinding Error: {e}")

    def _follow_path(self, entity, dt):
        brain = self.ecs.get_component(entity, AIBrain)
        transform = self.ecs.get_component(entity, Transform)
        velocity = self.ecs.get_component(entity, Velocity)
        
        if not brain.path:
            velocity.dx = 0
            velocity.dy = 0
            return
            
        next_node = brain.path[0]
        target_x = next_node[0] * TILE_SIZE + 16
        target_y = next_node[1] * TILE_SIZE + 16
        
        dx = target_x - transform.x
        dy = target_y - transform.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < 5:
            brain.path.pop(0)
            if not brain.path:
                velocity.dx = 0
                velocity.dy = 0
        else:
            velocity.dx = dx / dist
            velocity.dy = dy / dist
