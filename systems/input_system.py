import pygame
from .base_system import BaseSystem
from core.event_bus import EventBus

class InputSystem(BaseSystem):
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def process(self, player_entity):
        if not player_entity or not player_entity.components:
            return

        # 필수 컴포넌트 확인
        if not (hasattr(player_entity, 'transform') and 
                hasattr(player_entity, 'physics') and 
                hasattr(player_entity, 'stats')):
            return

        keys = pygame.key.get_pressed()
        physics = player_entity.physics
        stats = player_entity.stats
        transform = player_entity.transform

        # 1. 이동 입력
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]: dx = -1
        if keys[pygame.K_RIGHT]: dx = 1
        if keys[pygame.K_UP]: dy = -1
        if keys[pygame.K_DOWN]: dy = 1

        # 2. 이동 상태 결정 (RUN, CROUCH, WALK)
        infinite_stamina = stats.status_effects.get('INFINITE_STAMINA', False)
        # 경찰 분노 상태 등은 Role/Stats 체크 필요하지만 여기선 간단히 버프만 체크
        
        if keys[pygame.K_LSHIFT] and (stats.breath_gauge > 0 or infinite_stamina):
            physics.move_state = "RUN"
        elif keys[pygame.K_LCTRL]:
            physics.move_state = "CROUCH"
        else:
            physics.move_state = "WALK"

        # 3. 속도 벡터 설정 (MovementSystem에서 최종 속도 계산 시 사용될 방향)
        # 여기서는 방향만 설정하고, 실제 속도 크기는 MovementSystem이 계산
        physics.velocity = (dx, dy)
        
        # Facing 설정
        if dx != 0: transform.facing = (dx, 0)
        elif dy != 0: transform.facing = (0, dy)

        # 4. 상호작용 및 특수 키 입력 (지속적이지 않은 키는 이벤트로 처리하거나 플래그 체크)
        # F키: 손전등 토글 (이벤트 루프 처리 대신 여기서 pressed 체크로 간략화 시 
        # 매 프레임 토글되는 문제 있음. 플래그 필요)
        if keys[pygame.K_f]:
            if not getattr(self, 'f_key_pressed', False):
                self.f_key_pressed = True
                if hasattr(player_entity, 'graphics'):
                    player_entity.graphics.flashlight_on = not player_entity.graphics.flashlight_on
                    state = "ON" if player_entity.graphics.flashlight_on else "OFF"
                    self.event_bus.publish("SHOW_ALERT", {'text': f"Flashlight {state}", 'color': (255, 255, 200)})
        else:
            self.f_key_pressed = False

        # 5. 아이템 사용 단축키 등
        # ... (필요 시 추가)
