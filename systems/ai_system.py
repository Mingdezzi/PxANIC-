import random
import math
import pygame
from .base_system import BaseSystem
from settings import TILE_SIZE, WORK_SEQ, BED_TILES, VENDING_MACHINE_TID
from world.pathfinder import Pathfinder
from components.ai_brain import BTNode

# --- Behavior Tree Nodes (변경 없음) ---
class BTState: SUCCESS, FAILURE, RUNNING = "SUCCESS", "FAILURE", "RUNNING"
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

# --- AI System (수정됨) ---
class AISystem(BaseSystem):
    def __init__(self, map_manager):
        self.map_manager = map_manager
        self.pathfinder = Pathfinder(map_manager)

    def update(self, dt, entities, player, blackboard_data):
        blackboard = {
            'phase': blackboard_data.get('phase', 'DAY'),
            'day_count': blackboard_data.get('day_count', 1),
            'player': player,
            'npcs': [e for e in entities if e != player],
            'map_manager': self.map_manager,
            'pathfinder': self.pathfinder,
            'entities': entities
        }

        for entity in entities:
            if not hasattr(entity, 'ai_brain'): continue
            if not entity.stats.alive: continue
            
            # 시야 및 기억 업데이트
            self._update_vision_and_memory(entity, blackboard)

            # 트리 빌드 (없으면 생성)
            if not entity.ai_brain.tree:
                entity.ai_brain.tree = self._build_tree(entity)

            # BT 실행
            entity.ai_brain.tree.tick(entity, blackboard)
            
            # 물리 이동 처리
            self._process_path_movement(entity)

    def _update_vision_and_memory(self, entity, bb):
        # [구현] 시야 내 적 감지 (간소화)
        # 추후 FOV 시스템과 연동하여 'player'나 'mafia'를 발견하면 fleeing 상태로 전환 등 가능
        pass

    def _build_tree(self, entity):
        role = entity.role.main_role
        
        # [핵심] 생활 패턴: 쇼핑 -> 귀가(밤) -> 일(낮) -> 배회
        common_behavior = Selector([
            Sequence([Condition(self.check_needs_shopping), Action(self.do_shopping)]),
            Sequence([Condition(self.is_night_time), Action(self.do_go_home)]),
            Sequence([Condition(self.is_work_time), Action(self.do_work)]),
            Action(self.do_wander)
        ])

        if role == "MAFIA":
            # 마피아는 밤에 살인 시도 -> 실패하면 귀가 안하고 배회(정찰)
            return Selector([
                Sequence([Condition(self.can_kill), Action(self.do_mafia_kill)]),
                common_behavior
            ])
        else:
            return common_behavior

    # --- Conditions ---
    def check_needs_shopping(self, e, bb): 
        # 체력/AP 부족하고 돈 있으면 쇼핑
        return (e.stats.hp < 60 or e.stats.ap < 40) and e.inventory.coins >= 3

    def can_kill(self, e, bb): 
        return bb['phase'] == 'NIGHT'

    def is_work_time(self, e, bb): 
        # 아침/낮 & 작업량 미달 시
        return bb['phase'] in ['MORNING', 'DAY'] and e.role.daily_work_count < 3

    def is_night_time(self, e, bb): 
        return bb['phase'] in ['EVENING', 'NIGHT']

    # --- Actions (기능 복구 및 강화) ---

    def do_shopping(self, entity, bb):
        brain = entity.ai_brain
        # 자판기(Vending Machine) TID
        VENDING_TIDS = [VENDING_MACHINE_TID] # settings.py에서 가져옴
        
        if brain.path: return BTState.RUNNING
        
        target_pos = self._find_nearest_tile_by_tids(entity, VENDING_TIDS)
        if not target_pos: return BTState.FAILURE # 자판기 없으면 포기

        dist = math.sqrt((entity.transform.x - target_pos[0])**2 + (entity.transform.y - target_pos[1])**2)
        if dist < TILE_SIZE * 1.5:
            # 도착 및 구매
            entity.inventory.coins -= 3
            entity.stats.hp = min(entity.stats.max_hp, entity.stats.hp + 30)
            entity.stats.ap = min(entity.stats.max_ap, entity.stats.ap + 30)
            return BTState.SUCCESS
        
        path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), target_pos)
        if path:
            brain.path = path
            return BTState.RUNNING
        return BTState.FAILURE

    def do_go_home(self, entity, bb):
        brain = entity.ai_brain
        # 이미 숨어있으면 성공 유지
        if entity.graphics.is_hiding: return BTState.SUCCESS
        if brain.path: return BTState.RUNNING
        
        # [복구] 집(침대) 찾기 로직
        house_pos = self._find_house_door(entity)
        
        if house_pos:
            dist = math.sqrt((entity.transform.x - house_pos[0])**2 + (entity.transform.y - house_pos[1])**2)
            if dist < TILE_SIZE:
                # 도착 -> 숨기(잠자기)
                entity.graphics.is_hiding = True
                entity.graphics.hiding_type = 2 # 침대 숨기
                return BTState.SUCCESS
            
            # 이동
            path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), house_pos)
            if path: 
                brain.path = path
                return BTState.RUNNING
        
        # 집 못 찾으면 그냥 배회 (멈춰있지 않게)
        return self.do_wander(entity, bb)

    def do_work(self, entity, bb):
        brain = entity.ai_brain
        
        # 작업 중(타이머) 처리
        if hasattr(entity, 'interaction') and entity.interaction.is_interacting:
            now = pygame.time.get_ticks()
            if now > entity.interaction.progress_timer:
                # 작업 완료
                entity.interaction.is_interacting = False
                entity.role.daily_work_count += 1
                entity.inventory.coins += 2
                brain.path = [] 
                return BTState.SUCCESS
            return BTState.RUNNING

        if brain.path: return BTState.RUNNING

        # 작업 타일 찾기
        job = entity.role.sub_role if entity.role.sub_role else entity.role.main_role
        target_tid = None
        
        # 1. 오늘의 작업 타일 찾기
        if job in WORK_SEQ:
            day_idx = (bb['day_count'] - 1) % 3
            if day_idx < len(WORK_SEQ[job]):
                target_tid = WORK_SEQ[job][day_idx]
        
        if not target_tid: return BTState.FAILURE

        # 2. 맵에서 해당 타일 위치 검색
        target_pos = self._find_nearest_tile_by_tids(entity, [target_tid])
        
        if target_pos:
            dist = math.sqrt((entity.transform.x - target_pos[0])**2 + (entity.transform.y - target_pos[1])**2)
            if dist < TILE_SIZE * 1.5:
                # 도착 -> 작업 시작
                if not hasattr(entity, 'interaction'): return BTState.FAILURE
                entity.interaction.is_interacting = True
                entity.interaction.progress_timer = pygame.time.get_ticks() + 4000 # 4초간 작업
                return BTState.RUNNING
            
            # 이동
            path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), target_pos)
            if path:
                brain.path = path
                return BTState.RUNNING
        
        return BTState.FAILURE # 작업 타일 못 찾음 -> 배회

    def do_wander(self, entity, bb):
        brain = entity.ai_brain
        if brain.path: return BTState.RUNNING
        
        # [수정] 랜덤 이동 확률 상향 및 실패 시 재시도
        if random.random() < 0.2: 
            target_pos = self.map_manager.get_random_floor_tile()
            if target_pos:
                # 너무 멀지 않은 곳으로 제한 (최대 25칸)
                if (entity.transform.x - target_pos[0])**2 + (entity.transform.y - target_pos[1])**2 < (TILE_SIZE * 25)**2:
                    path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), target_pos)
                    if path:
                        brain.path = path
                        return BTState.SUCCESS
        
        # 경로 못 찾았으면 FAILURE 반환하여 트리 리셋 유도
        return BTState.FAILURE

    def do_mafia_kill(self, entity, bb):
        # 마피아 킬 로직 (단순화)
        # 주변 시민 탐색 -> 추적 -> 킬
        targets = bb['npcs'] + [bb['player']]
        target = None
        for t in targets:
            if t == entity or not t.stats.alive: continue
            if t.role.main_role == "MAFIA": continue 
            
            dist = math.sqrt((entity.transform.x - t.transform.x)**2 + (entity.transform.y - t.transform.y)**2)
            if dist < TILE_SIZE * 5: 
                target = t
                break
        
        if not target: return BTState.FAILURE
        
        dist = math.sqrt((entity.transform.x - target.transform.x)**2 + (entity.transform.y - target.transform.y)**2)
        if dist < TILE_SIZE * 1.2:
            target.stats.hp -= 70 
            entity.kill_cooldown = pygame.time.get_ticks() + 10000 
            return BTState.SUCCESS
        
        path = bb['pathfinder'].find_path((entity.transform.x, entity.transform.y), (target.transform.x, target.transform.y))
        if path:
            entity.ai_brain.path = path
            return BTState.RUNNING
            
        return BTState.FAILURE

    # --- Helpers ---
    def _find_house_door(self, entity):
        # 침대 타일 중 하나를 랜덤으로 선택 (자신의 집 개념이 없으면 공용 숙소)
        # settings.BED_TILES 활용
        return self._find_nearest_tile_by_tids(entity, BED_TILES)

    def _find_nearest_tile_by_tids(self, entity, tids):
        candidates = []
        for tid in tids:
            if tid in self.map_manager.tile_cache:
                candidates.extend(self.map_manager.tile_cache[tid])
        
        if not candidates: return None
        
        # 가장 가까운 곳 찾기 (CPU 부하 고려하여 10개만 샘플링하거나 전체 검색)
        # 여기서는 전체 검색 (NPC 수가 적다고 가정)
        best_pos = None
        min_dist = float('inf')
        ex, ey = entity.transform.x, entity.transform.y
        
        for pos in candidates:
            dist = (ex - pos[0])**2 + (ey - pos[1])**2
            if dist < min_dist:
                min_dist = dist
                best_pos = pos
        return best_pos

    def _process_path_movement(self, entity):
        brain = entity.ai_brain
        if not brain.path:
            entity.physics.velocity = (0, 0)
            return

        target_pos = brain.path[0]
        cx, cy = entity.transform.x + 16, entity.transform.y + 16
        dx = target_pos[0] - cx
        dy = target_pos[1] - cy
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist < 5:
            brain.path.pop(0)
            if not brain.path: entity.physics.velocity = (0, 0)
        else:
            speed = 1.0
            # 밤에는 좀 더 천천히 걷기
            # if 'NIGHT' in bb['phase']: speed = 0.7
            
            entity.physics.velocity = (dx/dist * speed, dy/dist * speed)
            if abs(dx) > abs(dy): entity.transform.facing = (1 if dx > 0 else -1, 0)
            else: entity.transform.facing = (0, 1 if dy > 0 else -1)