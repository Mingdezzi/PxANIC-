import pygame
import math
import random
from .base_system import BaseSystem
from settings import TILE_SIZE

class StatsSystem(BaseSystem):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.last_stats = {} # {entity_id: {'hp': val, 'coins': val}}
        self.siren_event_queue = []
        
        self.event_bus.subscribe("TRIGGER_SIREN", self._on_trigger_siren)
        self.event_bus.subscribe("NEW_DAY", self._on_new_day)

    def update(self, dt, entities, player, is_blackout, phase):
        if getattr(self, 'pending_morning_process', False):
            self._process_morning_routine(entities)
            self.pending_morning_process = False

        # 사이렌 이벤트 처리
        self._process_siren_queue(entities)

        # 플레이어 감정 계산
        self._calculate_player_emotions(player, entities, is_blackout, phase)
        
        # 모든 엔티티 상태 업데이트
        for entity in entities:
            if not hasattr(entity, 'stats'): continue
            self._update_entity_stats(dt, entity)
            self._check_stat_changes(entity)

    def _on_new_day(self, data):
        # 아침 정산 (Morning Process)
        # PlayState에서 entities 목록을 직접 접근하기 어려우므로, 
        # 다음 update 루프에서 처리하도록 플래그를 세우거나,
        # PlayState가 이 로직을 호출하도록 하는 것이 좋음.
        # 하지만 여기서는 update 메서드로 entities가 들어오므로,
        # pending_morning_process 플래그를 사용.
        self.pending_morning_process = True

    def _process_morning_routine(self, entities):
        # 실제 로직 실행
        for entity in entities:
            if not hasattr(entity, 'stats') or not entity.stats.alive: continue
            
            # 1. 회복 (집에서 잤는지 체크는 복잡하므로 약식 구현)
            # 은신 중이거나 침대에 있으면 보너스
            is_resting = entity.graphics.is_hiding and entity.graphics.hiding_type == 2
            
            if is_resting:
                entity.stats.hp = min(entity.stats.max_hp, entity.stats.hp + 20)
                entity.stats.ap = min(entity.stats.max_ap, entity.stats.ap + 20)
            else:
                # 노숙 페널티
                entity.stats.hp = max(1, entity.stats.hp - 10)
                entity.stats.ap = max(0, entity.stats.ap - 10)
                
            # 2. 업무 정산 (시민 직업군만)
            role = entity.role.main_role
            if role in ["CITIZEN", "DOCTOR"]:
                if entity.role.daily_work_count < 5:
                    entity.stats.hp -= 10
                    if entity.name == "Player": # 플레이어만 알림
                        self.event_bus.publish("SHOW_ALERT", {'text': "Work Quota Failed! HP -10", 'color': (255, 50, 50)})
            
            # 리셋
            entity.role.daily_work_count = 0
            entity.role.bullets_fired_today = 0 # 경찰
            entity.graphics.is_hiding = False
            entity.graphics.hiding_type = 0
            
            # 상태이상 해제
            entity.stats.status_effects = {k: False for k in entity.stats.status_effects}

    # ... (나머지 메서드 유지)

    def _on_trigger_siren(self, data):
        self.siren_event_queue.append(data)

    def _process_siren_queue(self, entities):
        while self.siren_event_queue:
            data = self.siren_event_queue.pop(0)
            sx, sy, r = data['x'], data['y'], data['radius']
            r_sq = r * r
            
            for e in entities:
                # 경찰 자신은 제외 (역할 체크 필요하지만 생략)
                dist_sq = (e.transform.x - sx)**2 + (e.transform.y - sy)**2
                if dist_sq <= r_sq:
                    e.stats.status_effects['STUNNED'] = True
                    e.stats.stun_end_time = pygame.time.get_ticks() + 3000

    def _update_entity_stats(self, dt, entity):
        stats = entity.stats
        
        # 스턴 해제 체크
        if getattr(stats, 'stun_end_time', 0) > 0:
            if pygame.time.get_ticks() > stats.stun_end_time:
                stats.status_effects['STUNNED'] = False
                stats.stun_end_time = 0
        
        physics = entity.physics
        
        # 스태미나 (Breath Gauge) 회복/소모
        infinite = stats.status_effects.get('INFINITE_STAMINA', False) or \
                   (entity.role.main_role == "POLICE" and 'RAGE' in stats.emotions)
                   
        if physics.move_state == "RUN" and physics.is_moving and not infinite:
            stats.breath_gauge = max(0, stats.breath_gauge - (0.5 * dt / 16.0))
            if stats.breath_gauge <= 0:
                physics.move_state = "WALK"
        elif physics.move_state != "RUN":
            stats.breath_gauge = min(100, stats.breath_gauge + (0.5 * dt / 16.0))

        # 기면증 (Fatigue Lv.5)
        if stats.emotions.get('FATIGUE', 0) >= 5:
            now = pygame.time.get_ticks()
            if (now // 4000) % 2 == 1:
                stats.is_eyes_closed = True
            else:
                stats.is_eyes_closed = False
        else:
            stats.is_eyes_closed = False

    def _check_stat_changes(self, entity):
        eid = entity.uid
        current_hp = entity.stats.hp
        current_coins = entity.inventory.coins if hasattr(entity, 'inventory') else 0
        
        if eid not in self.last_stats:
            self.last_stats[eid] = {'hp': current_hp, 'coins': current_coins}
            return

        last = self.last_stats[eid]
        
        # HP Change
        if current_hp != last['hp']:
            diff = int(current_hp - last['hp'])
            if diff != 0:
                color = (50, 255, 50) if diff > 0 else (255, 50, 50)
                text = f"{'+' if diff > 0 else ''}{diff} HP"
                if hasattr(entity, 'popups'):
                    entity.popups.append({'text': text, 'color': color, 'timer': pygame.time.get_ticks() + 1500})
            last['hp'] = current_hp

        # Coin Change
        if current_coins != last['coins']:
            diff = current_coins - last['coins']
            if diff != 0:
                color = (255, 215, 0)
                text = f"{'+' if diff > 0 else ''}{diff} G"
                if hasattr(entity, 'popups'):
                    entity.popups.append({'text': text, 'color': color, 'timer': pygame.time.get_ticks() + 1500})
            last['coins'] = current_coins

    def _calculate_player_emotions(self, player, entities, is_blackout, phase):
        stats = player.stats
        role = player.role.main_role
        
        stats.emotions = {}
        
        if role == "SPECTATOR" or not stats.alive: return

        if stats.hp >= 80 and stats.ap >= 80: stats.emotions['HAPPINESS'] = 1

        if stats.hp <= 50:
            if stats.hp <= 10: level = 5
            elif stats.hp <= 20: level = 4
            elif stats.hp <= 30: level = 3
            elif stats.hp <= 40: level = 2
            else: level = 1
            stats.emotions['PAIN'] = level

        if stats.ap <= 50:
            if stats.ap <= 10: level = 5
            elif stats.ap <= 20: level = 4
            elif stats.ap <= 30: level = 3
            elif stats.ap <= 40: level = 2
            else: level = 1
            stats.emotions['FATIGUE'] = level

        if is_blackout: stats.emotions['FEAR'] = 1

        target_roles = []
        my_emotion = None
        
        if role == "MAFIA" and phase in ["NIGHT", "DAWN"]:
            target_roles = ["CITIZEN", "DOCTOR", "POLICE"]
            my_emotion = 'DOPAMINE'
        elif role == "POLICE" and phase in ["NIGHT", "DAWN"]:
            target_roles = ["MAFIA"]
            my_emotion = 'RAGE'
        elif phase in ["EVENING", "NIGHT", "DAWN"]:
            target_roles = ["MAFIA"]
            my_emotion = 'ANXIETY'

        if my_emotion and target_roles:
            min_dist_tile = 999
            for e in entities:
                if e == player: continue
                if not e.stats.alive: continue
                
                if e.role.main_role in target_roles:
                    dx = player.transform.x - e.transform.x
                    dy = player.transform.y - e.transform.y
                    d_tile = math.sqrt(dx*dx + dy*dy) / TILE_SIZE
                    if d_tile < min_dist_tile:
                        min_dist_tile = d_tile
            
            level = 0
            if min_dist_tile <= 5: level = 5
            elif min_dist_tile <= 10: level = 4
            elif min_dist_tile <= 20: level = 3
            elif min_dist_tile <= 25: level = 2
            elif min_dist_tile <= 30: level = 1
            
            if level > 0: stats.emotions[my_emotion] = level

        if not stats.emotions: stats.emotions['CALM'] = 1