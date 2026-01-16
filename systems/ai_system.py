import random
import math
from .base_system import BaseSystem
from settings import TILE_SIZE, VISION_RADIUS, WORK_SEQ
from world.pathfinder import Pathfinder
from components.ai_brain import BTNode

# --- Behavior Tree Classes ---
class BTState:
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"

class Composite(BTNode):
    def __init__(self, children=None): self.children = children or []

class Selector(Composite):
    def tick(self, entity, blackboard):
        for child in self.children:
            status = child.tick(entity, blackboard)
            if status != BTState.FAILURE: return status
        return BTState.FAILURE

class Sequence(Composite):
    def tick(self, entity, blackboard):
        for child in self.children:
            status = child.tick(entity, blackboard)
            if status == BTState.FAILURE: return BTState.FAILURE
            if status == BTState.RUNNING: return BTState.RUNNING
        return BTState.SUCCESS

class Action(BTNode):
    def __init__(self, action_func): self.action_func = action_func
    def tick(self, entity, blackboard): return self.action_func(entity, blackboard)

class Condition(BTNode):
    def __init__(self, condition_func): self.condition_func = condition_func
    def tick(self, entity, blackboard): return BTState.SUCCESS if self.condition_func(entity, blackboard) else BTState.FAILURE

# --- AI System ---
class AISystem(BaseSystem):
    def __init__(self, map_manager):
        self.map_manager = map_manager
        self.pathfinder = Pathfinder(map_manager)

    def update(self, dt, entities, player, blackboard_data):
        # Blackboard 생성 (AI가 공유하는 정보)
        # blackboard_data는 PlayState에서 넘겨준 시간 정보 등
        blackboard = {
            'phase': blackboard_data.get('phase', 'DAY'),
            'day_count': blackboard_data.get('day_count', 1),
            'player': player,
            'npcs': [e for e in entities if e != player],
            'map_manager': self.map_manager,
            'pathfinder': self.pathfinder,
            'entities': entities # 전체 엔티티 참조용
        }

        for entity in entities:
            if not hasattr(entity, 'ai_brain'): continue
            if not entity.stats.alive: continue
            
            # [New] 시각 정보 업데이트 및 범죄 목격
            self._update_vision_and_memory(entity, blackboard)

            # 트리 빌드
            if not entity.ai_brain.tree:
                entity.ai_brain.tree = self._build_tree(entity)

            # BT 실행
            entity.ai_brain.tree.tick(entity, blackboard)
            
            # 경로 이동 처리
            self._process_path_movement(entity)

    def _update_vision_and_memory(self, entity, bb):
        # 시야 내의 엔티티 감지
        vision_range = VISION_RADIUS['DAY'] * TILE_SIZE # 단순화
        brain = entity.ai_brain
        
        for target in bb['entities']:
            if target == entity: continue
            if not target.stats.alive: 
                # 시체 목격
                dist = math.sqrt((entity.transform.x - target.transform.x)**2 + (entity.transform.y - target.transform.y)**2)
                if dist < vision_range:
                    # 시체 발견! -> 신고 로직 (추후 구현)
                    pass
                continue

            # 살아있는 대상
            dist = math.sqrt((entity.transform.x - target.transform.x)**2 + (entity.transform.y - target.transform.y)**2)
            if dist < vision_range:
                # 마피아(빌런) 목격 (Role check 대신 is_visible_villain 등 사용 권장하지만 여기선 Role 직접 확인)
                # 실제로는 target.role.is_revealed 등을 체크해야 함
                if target.role.main_role == "MAFIA" and bb['phase'] == 'NIGHT':
                    # 밤에 마피아를 봄 -> 의심도 급증
                    brain.suspicion_meter[target.name] = 100
                    brain.current_state = "FLEE" # 상태 전환 (BT에서 처리)

    def _build_tree(self, entity):
        role = entity.role.main_role
        
        # 공통 생존/생활 패턴
        common_behavior = Selector([
            Sequence([Condition(self.check_needs_shopping), Action(self.do_shopping)]),
            Sequence([Condition(self.is_night_time), Action(self.do_go_home)]),
            Sequence([Condition(self.is_work_time), Action(self.do_work)]),
            Action(self.do_wander)
        ])

        if role == "POLICE":
            return Selector([
                # 추격 로직 (구현 필요 시 추가)
                Action(self.do_wander) 
            ])
        elif role == "MAFIA":
            return Selector([
                Sequence([Condition(self.can_kill), Action(self.do_mafia_kill)]),
                common_behavior
            ])
        else:
            return common_behavior

    # --- Conditions ---
    def check_needs_shopping(self, entity, bb):
        # HP/AP가 낮고 돈이 있으면 쇼핑
        return (entity.stats.hp < 50 or entity.stats.ap < 40) and entity.inventory.coins >= 3

    def can_kill(self, entity, bb):
        # 밤이고, 쿨타임이 찼고, 주변에 시민이 있으면 살인 시도
        if bb['phase'] != 'NIGHT': return False
        # 쿨타임 체크 (임시)
        if getattr(entity, 'kill_cooldown', 0) > pygame.time.get_ticks(): return False
        
        # 주변 타겟 탐색 (플레이어 포함)
        targets = bb['npcs'] + [bb['player']]
        for t in targets:
            if t == entity or not t.stats.alive: continue
            if t.role.main_role == "MAFIA": continue # 동료 제외
            
            dist = math.sqrt((entity.transform.x - t.transform.x)**2 + (entity.transform.y - t.transform.y)**2)
            if dist < TILE_SIZE * 5: # 사거리 내 감지
                bb['kill_target'] = t
                return True
        return False

    def is_work_time(self, entity, bb):
        phase = bb['phase']
        # 아침/낮이고 아직 할당량을 못 채웠으면 일하러 감
        return phase in ['MORNING', 'DAY'] and entity.role.daily_work_count < 5

    def is_night_time(self, entity, bb):
        return bb['phase'] in ['EVENING', 'NIGHT']

    # --- Actions ---
    def do_shopping(self, entity, bb):
        brain = entity.ai_brain
        from settings import VENDING_MACHINE_TID 
        
        if brain.path: return BTState.RUNNING
        
        # 자판기 위치 찾기 (캐시 활용)
        vending_pos = self._find_nearest_tile(entity, VENDING_MACHINE_TID)
            
        if vending_pos:
            dist = math.sqrt((entity.transform.x - vending_pos[0])**2 + (entity.transform.y - vending_pos[1])**2)
            if dist < TILE_SIZE * 1.5:
                # 구매 실행
                if entity.inventory.coins >= 3:
                    entity.inventory.coins -= 3
                    entity.stats.hp = min(entity.stats.max_hp, entity.stats.hp + 20)
                    # self.event_bus.publish("PLAY_SOUND", ...) # 필요 시 추가
                return BTState.SUCCESS
            
            # 이동 요청
            path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), vending_pos)
            if path:
                brain.path = path
                return BTState.RUNNING
        
        return BTState.FAILURE

    def do_go_home(self, entity, bb):
        # 원본 find_house_door 로직 복구
        brain = entity.ai_brain
        if entity.graphics.is_hiding: return BTState.SUCCESS
        if brain.path: return BTState.RUNNING
        
        # 집(실내 구역 입구) 찾기
        house_pos = self._find_house_door(entity)
        
        if house_pos:
            dist = math.sqrt((entity.transform.x - house_pos[0])**2 + (entity.transform.y - house_pos[1])**2)
            if dist < TILE_SIZE:
                # 도착 -> 은신(휴식)
                entity.graphics.is_hiding = True
                entity.graphics.hiding_type = 2
                return BTState.SUCCESS
            
            # 이동 요청
            path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), house_pos)
            if path:
                brain.path = path
                return BTState.RUNNING
        
        # 집을 못 찾으면 배회
        return self.do_wander(entity, bb)

    def _find_nearest_tile(self, entity, tid):
        if tid in self.map_manager.tile_cache:
            candidates = self.map_manager.tile_cache[tid]
            if candidates:
                # 거리순 정렬
                # candidates.sort(key=lambda p: (entity.transform.x-p[0])**2 + (entity.transform.y-p[1])**2)
                # 최적화를 위해 정렬 대신 그냥 랜덤 or 첫번째 반환 (봇이 많으면 정렬 부하 큼)
                return random.choice(candidates)
        return None

    def _find_house_door(self, entity):
        # 원본 로직: INDOOR_ZONES에 속하고 문(Object)인 타일 찾기
        from settings import INDOOR_ZONES
        from world.tiles import get_tile_function # or direct check
        
        # 매번 전체 맵을 뒤지는 건 비효율적이므로, 한 번 찾으면 Brain에 기억시키거나
        # MapManager가 'HouseDoors' 캐시를 가지고 있어야 함.
        # 여기서는 MapManager의 tile_cache를 뒤져서 조건에 맞는 것을 찾음.
        
        # 문(Category 5) 타일들 중 Zone이 Indoor인 것
        # 하지만 tile_cache는 TID 키로 저장되어 있음. 
        # 따라서 문에 해당하는 TID들을 모두 검사해야 함.
        # 더 효율적인 방법: 맵 로딩 시 'door_cache'를 만드는 것.
        # 현재는 임시로 랜덤 좌표 반환하지 않고, MapManager를 통해 유효한 문 좌표 탐색 시도.
        
        # MapManager에 문 좌표 캐시가 없으므로 실시간 탐색 (비효율적이지만 정확함)
        # 단, 맵 전체 탐색은 너무 느리므로, NPC 주변 일정 범위만 탐색하거나
        # 맵 로딩 시점에 캐싱해두는 게 맞음.
        
        # [Fallback] MapManager에 get_indoor_doors 메서드가 없으므로,
        # tile_cache의 모든 키를 순회하며 문(Cat 5)인지 확인하고 Zone 체크.
        # 너무 느릴 수 있으니, 그냥 랜덤한 '안전 구역(Zone 1)' 이나 침대로 이동하도록 유도.
        
        from settings import BED_TILES
        for bed_tid in BED_TILES:
            bed_pos = self._find_nearest_tile(entity, bed_tid)
            if bed_pos: return bed_pos
            
        return None

    def do_mafia_kill(self, entity, bb):
        target = bb.get('kill_target')
        if not target or not target.stats.alive: return BTState.FAILURE
        
        dist = math.sqrt((entity.transform.x - target.transform.x)**2 + (entity.transform.y - target.transform.y)**2)
        if dist < TILE_SIZE * 1.2:
            # 살인 실행!
            # CombatSystem을 호출하거나 직접 데미지 (직접 데미지가 편함)
            # 여기서는 CombatSystem 이벤트를 사용하는 것이 좋음... 하지만 AI 로직 내에서 즉시 처리
            target.stats.hp -= 70 # 치명타
            entity.kill_cooldown = pygame.time.get_ticks() + 10000 # 10초 쿨타임
            
            # 사운드 이벤트
            # ...
            return BTState.SUCCESS
        
        # 추격 이동
        path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), (target.transform.x, target.transform.y))
        if path:
            entity.ai_brain.path = path
            return BTState.RUNNING
            
        return BTState.FAILURE

    def do_work(self, entity, bb):
        # 1. 작업 위치가 없으면 찾기
        # 2. 이동
        # 3. 도착하면 작업 수행 (타이머)
        brain = entity.ai_brain
        
        # 이미 작업 중인지 체크 (Interaction 컴포넌트 활용)
        if entity.interaction.is_interacting:
            # 작업 진행 중... (InteractionSystem이나 여기서 처리)
            # 여기서는 간단히 타이머 체크만
            now = pygame.time.get_ticks()
            if now > entity.interaction.progress_timer:
                entity.interaction.is_interacting = False
                entity.role.daily_work_count += 1
                entity.inventory.coins += 1
                brain.path = [] # 이동 종료
                return BTState.SUCCESS
            return BTState.RUNNING

        # 이동 중이면 계속 이동
        if brain.path:
            return BTState.RUNNING

        # 작업 위치 찾기
        job = entity.role.sub_role if entity.role.sub_role else entity.role.main_role
        if job in WORK_SEQ:
            # 오늘의 작업 타일 ID
            day = bb.get('day_count', 1)
            target_tid = WORK_SEQ[job][(day - 1) % 3]
            
            # MapManager에서 해당 타일 위치 찾기
            candidates = self.map_manager.tile_cache.get(target_tid, [])
            if candidates:
                target_pos = random.choice(candidates)
                # 바로 옆 타일로 이동해야 함 (타일 위가 아니라)
                # Pathfinder 호출
                path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), target_pos)
                if path:
                    brain.path = path
                    # 도착 후 작업을 위해 임시 상태 설정 (도착 판정은 _process_path_movement에서 함)
                    # 여기서는 도착했다고 가정하고 바로 작업 시작 (간소화)
                    entity.interaction.is_interacting = True
                    entity.interaction.progress_timer = pygame.time.get_ticks() + 3000 # 3초 작업
                    return BTState.RUNNING
        
        return BTState.FAILURE

    def do_go_home(self, entity, bb):
        # 집(실내)으로 이동
        brain = entity.ai_brain
        if entity.graphics.is_hiding: return BTState.SUCCESS
        
        if brain.path: return BTState.RUNNING
        
        # 실내 구역 찾기 (Zone ID 2 이상인 곳)
        # 임시로 랜덤한 실내 좌표
        # 실제로는 MapManager에 get_indoor_tiles 같은 메서드 필요
        # 여기서는 랜덤 이동으로 대체하거나 집 좌표를 미리 캐싱해야 함
        return self.do_wander(entity, bb) # 임시

    def do_wander(self, entity, bb):
        brain = entity.ai_brain
        
        # 이미 이동 중이면 RUNNING
        if brain.is_pathfinding or brain.path:
            return BTState.RUNNING
        
        # 랜덤 목적지 설정 (확률 대폭 상향 20%)
        if random.random() < 0.2: 
            # [Fix] 맵 매니저에게 유효한 바닥 타일 요청
            target_pos = self.map_manager.get_random_floor_tile()
            
            if target_pos:
                # 너무 멀면 포기 (선택적)
                dist_sq = (entity.transform.x - target_pos[0])**2 + (entity.transform.y - target_pos[1])**2
                if dist_sq > (TILE_SIZE * 20)**2: # 20칸 이상이면 다시
                    return BTState.RUNNING

                path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), target_pos)
                
                if path:
                    brain.path = path
                    return BTState.SUCCESS
            
            # [Fallback] 여전히 실패하면 직선 이동 시도
            brain.path = []
            angle = random.uniform(0, math.pi * 2)
            dist = TILE_SIZE * 3
            fx = entity.transform.x + math.cos(angle) * dist
            fy = entity.transform.y + math.sin(angle) * dist
            
            if 0 <= fx < self.map_manager.width * TILE_SIZE and 0 <= fy < self.map_manager.height * TILE_SIZE:
                 brain.path.append((fx, fy))
                 return BTState.SUCCESS
                
        return BTState.RUNNING

    def _process_path_movement(self, entity):
        brain = entity.ai_brain
        if not brain.path:
            entity.physics.velocity = (0, 0)
            return

        target_pos = brain.path[0] # (x, y) 튜플
        current_x, current_y = entity.transform.x + 16, entity.transform.y + 16 # 중심점
        
        dx = target_pos[0] - current_x
        dy = target_pos[1] - current_y
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist < 5: # 도착
            brain.path.pop(0)
            if not brain.path:
                entity.physics.velocity = (0, 0)
        else:
            # 정규화 및 속도 적용
            speed = 1.0 # 기본 1.0, PhysicsSystem에서 실제 속도 곱해짐
            entity.physics.velocity = (dx/dist * speed, dy/dist * speed)
            
            # Facing 설정
            if abs(dx) > abs(dy):
                entity.transform.facing = (1 if dx > 0 else -1, 0)
            else:
                entity.transform.facing = (0, 1 if dy > 0 else -1)
