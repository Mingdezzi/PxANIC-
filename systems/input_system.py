import pygame
from core.ecs_manager import ECSManager
from components.common import Velocity
from components.interaction import InteractionState
from components.identity import Identity
from components.status import StatusEffects
from components.interaction import Inventory
from core.game_state_manager import GameStateManager
from core.event_bus import EventBus

class InputSystem:
    def __init__(self, ecs: ECSManager, event_bus: EventBus):
        self.ecs = ecs
        self.event_bus = event_bus

    def update(self, dt):
        # 플레이어 엔티티 찾기
        players = [e for e in self.ecs.get_entities_with(Identity, Velocity, InteractionState) 
                  if self.ecs.get_component(e, Identity).is_player]
        
        if not players:
            return

        player_id = players[0]
        velocity = self.ecs.get_component(player_id, Velocity)
        interaction = self.ecs.get_component(player_id, InteractionState)
        status = self.ecs.get_component(player_id, StatusEffects)
        inventory = self.ecs.get_component(player_id, Inventory)

        # 1. 이동 입력 (화살표 키)
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        
        if keys[pygame.K_LEFT]: dx = -1
        if keys[pygame.K_RIGHT]: dx = 1
        if keys[pygame.K_UP]: dy = -1
        if keys[pygame.K_DOWN]: dy = 1

        # 대각선 이동 정규화 (1.0 유지)
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
            
        velocity.dx = dx
        velocity.dy = dy

        # 2. 달리기/웅크리기 상태 설정
        # RAGE(경찰) 또는 INFINITE_STAMINA 버프 시 무제한 달리기 가능
        infinite_stamina = ('RAGE' in status.emotions) or status.buffs['INFINITE_STAMINA']
        
        if keys[pygame.K_LSHIFT]:
            if status.breath_gauge > 0 or infinite_stamina:
                velocity.speed_modifier = 1.5 # RUN (Base * 1.5)
            else:
                velocity.speed_modifier = 1.0 # WALK
        elif keys[pygame.K_LCTRL]:
            velocity.speed_modifier = 0.5 # CROUCH
        else:
            velocity.speed_modifier = 1.0 # WALK

        # 3. 상호작용 키 (E) 처리 - Long Press 감지
        now = pygame.time.get_ticks()
        if keys[pygame.K_e]:
            if not interaction.e_key_pressed:
                interaction.e_key_pressed = True
                interaction.e_hold_start_time = now
                # self.logger.debug("Input", "E Key Pressed")
        else:
            if interaction.e_key_pressed:
                hold_time = now - interaction.e_hold_start_time
                interaction.e_key_pressed = False
                
                # Intent 생성 (Short vs Long)
                mode = 'long' if hold_time >= 500 else 'short'
                self.event_bus.publish("INTERACTION_REQUEST", {
                    'entity_id': player_id,
                    'mode': mode,
                    'hold_time': hold_time
                })

        # 4. 기타 단축키 (F: 손전등)
        # 키다운 이벤트는 Pygame Event Loop에서 처리하는 것이 일반적이나, 
        # 여기서는 Polling 방식으로 상태 토글을 처리하기 위해 별도 로직 필요
        # (하지만 토글은 Event Loop가 더 적합하므로 여기서는 지속 입력만 처리하거나 상태값 참조)
        pass 
