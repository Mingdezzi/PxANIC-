import pygame
import random
from core.ecs_manager import ECSManager
from core.game_state_manager import GameStateManager
from core.event_bus import EventBus
from components.status import Stats, StatusEffects
from components.identity import Identity
from components.common import Transform
from components.interaction import InteractionState
from world.map_manager import MapManager
from settings import DEFAULT_PHASE_DURATIONS, INDOOR_ZONES, PHASE_SETTINGS, DAILY_QUOTA

class TimeSystem:
    def __init__(self, ecs: ECSManager, event_bus: EventBus, map_manager: MapManager):
        self.ecs = ecs
        self.event_bus = event_bus
        self.map_manager = map_manager
        self.game_state = GameStateManager.get_instance()
        
        self.phases = ["DAWN", "MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"]
        self.current_phase_idx = 0
        self.current_phase = self.phases[0]
        
        # 기본값 설정, 추후 PlayState에서 custom_durations 주입 가능하도록 설계
        self.durations = DEFAULT_PHASE_DURATIONS.copy()
        self.state_timer = self.durations[self.current_phase]
        
        self.current_ambient_alpha = 0
        self.current_vision_factor = 1.0
        self.current_clarity = 255

    def update(self, dt):
        self.state_timer -= dt
        
        # 페이즈 전환
        if self.state_timer <= 0:
            self._advance_phase()
            
        # 조명 값 보간 (Interpolation)
        self._update_lighting_values()
        
        # 전역 상태(정전 등) 타이머 업데이트는 GameStateManager가 아닌 System에서 처리
        now = pygame.time.get_ticks()
        if self.game_state.is_blackout and now > self.game_state.blackout_timer:
            self.game_state.is_blackout = False
            self.event_bus.publish("BLACKOUT_END")
            
        if self.game_state.is_mafia_frozen and now > self.game_state.frozen_timer:
            self.game_state.is_mafia_frozen = False
            self.event_bus.publish("SIREN_END")

    def _update_lighting_values(self):
        curr_key = self.current_phase
        next_idx = (self.current_phase_idx + 1) % len(self.phases)
        next_key = self.phases[next_idx]
        
        curr_cfg = PHASE_SETTINGS.get(curr_key, PHASE_SETTINGS['NOON'])
        next_cfg = PHASE_SETTINGS.get(next_key, PHASE_SETTINGS['NOON'])
        
        total_time = self.durations.get(curr_key, 60)
        progress = 1.0 - (self.state_timer / max(total_time, 1))
        progress = max(0.0, min(1.0, progress))
        
        # Alpha (밝기) 보간
        self.current_ambient_alpha = curr_cfg['alpha'] + (next_cfg['alpha'] - curr_cfg['alpha']) * progress
        
        # Vision Factor (시야율) 보간
        self.current_vision_factor = curr_cfg['vision_factor'] + (next_cfg['vision_factor'] - curr_cfg['vision_factor']) * progress
        
        # Clarity (선명도) 보간
        curr_clarity = curr_cfg.get('clarity', 255)
        next_clarity = next_cfg.get('clarity', 255)
        self.current_clarity = curr_clarity + (next_clarity - curr_clarity) * progress

    def _advance_phase(self):
        # 페이즈 종료 이벤트 발행
        self.event_bus.publish("PHASE_END", self.current_phase)
        
        self.current_phase_idx = (self.current_phase_idx + 1) % len(self.phases)
        self.current_phase = self.phases[self.current_phase_idx]
        self.game_state.current_phase = self.current_phase
        self.state_timer = self.durations.get(self.current_phase, 30)
        
        # [NEW] Weather Update
        from settings import WEATHER_TYPES, WEATHER_PROBS
        # random.choices returns a list, take [0]
        self.game_state.current_weather = random.choices(WEATHER_TYPES, weights=WEATHER_PROBS, k=1)[0]
        
        self.event_bus.publish("PHASE_START", self.current_phase)
        
        if self.current_phase == "MORNING":
            self._process_morning_rules()

    def _process_morning_rules(self):
        """
        아침 생존 룰 처리 (Legacy Logic Preservation)
        """
        self.game_state.day_count += 1
        self.game_state.daily_news_log.append(f"Day {self.game_state.day_count} has started.")
        
        entities = self.ecs.get_entities_with(Stats, StatusEffects, Identity, Transform, InteractionState)
        
        for entity in entities:
            stats = self.ecs.get_component(entity, Stats)
            effects = self.ecs.get_component(entity, StatusEffects)
            identity = self.ecs.get_component(entity, Identity)
            transform = self.ecs.get_component(entity, Transform)
            interaction = self.ecs.get_component(entity, InteractionState)
            
            if not stats.alive:
                continue
                
            # 1. 수면 장소 보너스/페널티
            gx = int(transform.x // 32) # TILE_SIZE
            gy = int(transform.y // 32)
            is_indoors = False
            
            if 0 <= gx < self.map_manager.width and 0 <= gy < self.map_manager.height:
                if self.map_manager.zone_map[gy][gx] in INDOOR_ZONES:
                    is_indoors = True
            
            if is_indoors:
                stats.hp = min(stats.max_hp, stats.hp + 10)
                stats.ap = min(stats.max_ap, stats.ap + 10)
            else:
                stats.hp = max(0, stats.hp - 30)
                stats.ap = max(0, stats.ap - 30)
                
            # 2. 과로 페널티 (시민/의사)
            if identity.role in ["CITIZEN", "DOCTOR"]:
                if interaction.daily_work_count < DAILY_QUOTA:
                    stats.hp -= 10
                    # self.game_state.add_news(f"{identity.name} suffered from overwork.")
            
            # 3. 상태 초기화
            interaction.daily_work_count = 0
            interaction.work_step = (self.game_state.day_count - 1) % 3
            interaction.ability_used = False
            interaction.bullets_fired_today = 0
            
            effects.is_hiding = False
            effects.hiding_type = 0
            effects.hidden_in_solid = False
            
            # 버프 해제
            for k in effects.buffs:
                effects.buffs[k] = False
                
            # 의사 포션 획득 로직
            if identity.role == "DOCTOR" and random.random() < 0.33:
                # Inventory Component Check
                from components.interaction import Inventory
                if self.ecs.has_component(entity, Inventory):
                    inv = self.ecs.get_component(entity, Inventory)
                    inv.items['POTION'] = inv.items.get('POTION', 0) + 1
                    if identity.is_player:
                        self.event_bus.publish("SHOW_POPUP", "Created Potion", (100, 255, 100))
            
            # 사망 체크
            if identity.role != "POLICE" and stats.hp <= 0:
                stats.alive = False
                self.game_state.add_news(f"{identity.name} died from exhaustion/injuries.")
                self.event_bus.publish("ENTITY_DIED", entity)
