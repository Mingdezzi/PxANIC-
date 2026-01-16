from .base_system import BaseSystem
from settings import DEFAULT_PHASE_DURATIONS

class TimeSystem(BaseSystem):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.timer = 0
        self.day_count = 1
        self.phases = ['DAWN', 'MORNING', 'NOON', 'AFTERNOON', 'EVENING', 'NIGHT']
        self.current_phase_idx = 1 # Start at MORNING
        self.current_phase = self.phases[self.current_phase_idx]
        
        # 페이즈별 지속 시간 (초)
        self.durations = DEFAULT_PHASE_DURATIONS.copy()
        
        self.is_blackout = False
        self.blackout_timer = 0
        
        self.event_bus.subscribe("TRIGGER_BLACKOUT", self._on_trigger_blackout)

    def update(self, dt):
        self.timer += dt / 1000.0 # 밀리초 -> 초 변환
        
        limit = self.durations.get(self.current_phase, 60)
        
        if self.timer >= limit:
            self.timer = 0
            self._advance_phase()
            
        # 정전 타이머
        if self.is_blackout:
            self.blackout_timer -= dt
            if self.blackout_timer <= 0:
                self.is_blackout = False
                self.event_bus.publish("SHOW_ALERT", {'text': "Power Restored", 'color': (100, 255, 100)})

    def trigger_blackout(self, duration_ms=10000):
        self.is_blackout = True
        self.blackout_timer = duration_ms
        self.event_bus.publish("SHOW_ALERT", {'text': "BLACKOUT!", 'color': (50, 50, 50)})

    def _on_trigger_blackout(self, data):
        self.trigger_blackout(data.get('duration', 10000))

    def _advance_phase(self):
        prev_phase = self.current_phase
        self.current_phase_idx = (self.current_phase_idx + 1) % len(self.phases)
        self.current_phase = self.phases[self.current_phase_idx]
        
        # 아침이 되면 날짜 변경
        if self.current_phase == 'MORNING':
            self.day_count += 1
            self.event_bus.publish("NEW_DAY", {'day': self.day_count})
            
        self.event_bus.publish("PHASE_CHANGED", {
            'old_phase': prev_phase, 
            'new_phase': self.current_phase,
            'day': self.day_count
        })

    def get_state_data(self):
        return {
            'phase': self.current_phase,
            'state_timer': self.timer, # UI 표시용
            'day_count': self.day_count
        }
