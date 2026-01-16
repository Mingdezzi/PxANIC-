import pygame
from .base_system import BaseSystem
from managers.minigame_manager import MiniGameManager

class MiniGameSystem(BaseSystem):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.manager = MiniGameManager()
        
        # 이벤트 구독 (상호작용 시스템 등에서 미니게임 시작 요청)
        self.event_bus.subscribe("START_MINIGAME", self._on_start_minigame)

    def update(self, dt):
        if self.manager.active:
            self.manager.update()

    def handle_event(self, event):
        if self.manager.active:
            self.manager.handle_event(event)
            return True # 입력 가로채기
        return False

    def draw(self, screen, player):
        if self.manager.active:
            # 플레이어 머리 위나 화면 중앙에 표시
            # 여기서는 화면 중앙 근처에 고정
            screen_w, screen_h = screen.get_size()
            self.manager.draw(screen, screen_w // 2, screen_h // 2 - 50)

    def _on_start_minigame(self, data):
        # data: {'type': 'MASHING', 'difficulty': 1, 'callback_success': func, 'callback_fail': func}
        # EventBus로는 함수(콜백)를 전달하기 어려우므로, 
        # 성공/실패 시 다시 이벤트를 발행하는 방식으로 구조 변경 권장.
        # 하지만 여기서는 InteractionSystem과 강하게 결합되어 있으므로,
        # 임시로 콜백을 직접 받거나 ID를 받아 처리.
        
        game_type = data.get('type', 'MASHING')
        difficulty = data.get('difficulty', 1)
        # 콜백 대신 이벤트 발행을 위한 컨텍스트 저장
        self.context = data.get('context', {}) # 예: {'entity_id': ..., 'target_pos': ...}
        
        self.manager.start(game_type, difficulty, self._on_success, self._on_fail)

    def _on_success(self):
        self.event_bus.publish("MINIGAME_RESULT", {'result': 'SUCCESS', 'context': self.context})

    def _on_fail(self):
        self.event_bus.publish("MINIGAME_RESULT", {'result': 'FAILURE', 'context': self.context})
