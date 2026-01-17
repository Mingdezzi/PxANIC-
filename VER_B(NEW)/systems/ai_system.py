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
            'phase': self.game_state.current_phase, 
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
        brain = self.ecs.get_component(entity, AIBrain)
        transform = self.ecs.get_component(entity, Transform)
        identity = self.ecs.get_component(entity, Identity)
        
        # Reset Target
        brain.target_entity_id = None
        min_dist = 9999
        
        # Phase Check
        current_phase = self.game_state.current_phase
        is_night = (current_phase == "NIGHT")
        
        # Search Targets
        for target_id in bb['npcs'] + ([bb['player']] if bb['player'] else []):
            if target_id == entity: continue
            
            t_trans = self.ecs.get_component(target_id, Transform)
            t_ident = self.ecs.get_component(target_id, Identity)
            t_stats = self.ecs.get_component(target_id, Stats)
            
            if not t_stats or not t_stats.alive: continue
            
            dist = math.sqrt((transform.x - t_trans.x)**2 + (transform.y - t_trans.y)**2)
            
            # [Fix] VISION_RADIUS is a dict, use specific key and convert to pixels
            base_vision = VISION_RADIUS['DAY']
            if is_night:
                if identity.role == "MAFIA": base_vision = VISION_RADIUS['NIGHT_MAFIA']
                elif identity.role == "POLICE": base_vision = VISION_RADIUS['NIGHT_POLICE_FLASH'] 
                else: base_vision = VISION_RADIUS['NIGHT_CITIZEN']
            
            vision_pixel = base_vision * TILE_SIZE
            
            if dist > vision_pixel: continue
            
            # Logic by Role
            if identity.role == "POLICE":
                # Police chases Mafia at Night or if suspicion is high (simplified to Night for now)
                if t_ident.role == "MAFIA" and is_night:
                    if dist < min_dist:
                        min_dist = dist
                        brain.target_entity_id = target_id
                        
            elif identity.role == "MAFIA":
                # Mafia targets Citizens/Police at Night
                if t_ident.role != "MAFIA" and is_night:
                     if dist < min_dist:
                        min_dist = dist
                        brain.target_entity_id = target_id

    def _run_behavior_tree(self, entity, brain, bb):
        identity = self.ecs.get_component(entity, Identity)
        transform = self.ecs.get_component(entity, Transform)
        
        # 1. Has Target? -> Chase
        if brain.target_entity_id is not None:
            target = brain.target_entity_id
            t_trans = self.ecs.get_component(target, Transform)
            
            # Simple Pathfinding Request (Re-calc every 1 sec or if no path)
            if not brain.path or len(brain.path) < 2:
                if not brain.is_pathfinding:
                    # Threaded Pathfinding to Target
                    start_gx, start_gy = int(transform.x // TILE_SIZE), int(transform.y // TILE_SIZE)
                    target_gx, target_gy = int(t_trans.x // TILE_SIZE), int(t_trans.y // TILE_SIZE)
                    
                    brain.is_pathfinding = True
                    thread = threading.Thread(target=self._threaded_pathfinding, 
                                            args=(entity, start_gx, start_gy, target_gx, target_gy))
                    thread.daemon = True
                    thread.start()
            
            # Attack Logic (Range Check)
            dist = math.sqrt((transform.x - t_trans.x)**2 + (transform.y - t_trans.y)**2)
            if dist < TILE_SIZE * 1.5:
                # Attack Event (Cool-down check needed)
                pass 
                
        else:
            # 2. No Target -> Wander / Work
            # 시민: 랜덤 이동
            if not brain.path and not brain.is_pathfinding:
                # 5% 확률로 이동 요청 (너무 빈번하지 않게)
                if random.random() < 0.05:
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
        status = self.ecs.get_component(entity, StatusEffects)
        identity = self.ecs.get_component(entity, Identity)
        
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
            
            # [NEW] Generate Footstep Sound for NPCs
            now = pygame.time.get_ticks()
            if now > status.sound_timers['FOOTSTEP']:
                # NPC는 기본적으로 WALK 속도/간격 적용
                status.sound_timers['FOOTSTEP'] = now + 600 
                radius = 6 * TILE_SIZE # settings.NOISE_RADIUS['WALK']
                
                # 날씨 보정 (GameStateManager 접근 필요)
                if self.game_state.current_weather == 'RAIN': radius *= 0.8
                
                self.event_bus.publish("PLAY_SOUND", ("FOOTSTEP", transform.x + 16, transform.y + 16, radius, identity.role))
