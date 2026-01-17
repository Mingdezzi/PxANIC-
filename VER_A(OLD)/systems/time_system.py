import pygame
import random
from settings import DEFAULT_PHASE_DURATIONS, WEATHER_TYPES, WEATHER_PROBS

class TimeSystem:
    def __init__(self, game):
        self.game = game  # Main GameEngine reference needed for shared_data access
        self.day_count = 1
        self.phases = ["DAWN", "MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"]
        self.current_phase_idx = 0
        self.current_phase = self.phases[0]
        self.state_timer = 30
        
        # Weather
        self.weather = random.choices(WEATHER_TYPES, weights=WEATHER_PROBS, k=1)[0]
        self.weather_particles = []
        for _ in range(100):
            self.weather_particles.append([
                random.randint(0, game.screen_width),
                random.randint(0, game.screen_height),
                random.randint(5, 10),
                random.choice([0, 1])
            ])
            
        # News Log
        self.daily_news_log = []
        self.mafia_last_seen_zone = None

        # Callbacks (PlayState가 연결해줄 예정)
        self.on_phase_change = None 
        self.on_morning = None 

    def init_timer(self):
        durations = self.game.shared_data.get('custom_durations', DEFAULT_PHASE_DURATIONS)
        self.state_timer = durations.get(self.current_phase, 30)

    def update(self, dt):
        self.state_timer -= dt
        if self.state_timer <= 0:
            self._advance_phase()
            
        # Update Weather Particles
        if self.weather in ['RAIN', 'SNOW']:
            current_w, current_h = pygame.display.get_surface().get_size()
            for p in self.weather_particles:
                p[1] += p[2]
                if self.weather == 'RAIN': p[0] -= 1
                if p[1] > current_h:
                    p[1] = -10
                    p[0] = random.randint(0, current_w)

    def _advance_phase(self):
        old_phase = self.current_phase
        self.current_phase_idx = (self.current_phase_idx + 1) % len(self.phases)
        self.current_phase = self.phases[self.current_phase_idx]

        # Trigger Callbacks
        if self.on_phase_change:
            self.on_phase_change(old_phase, self.current_phase)

        if self.current_phase == "MORNING":
            self.day_count += 1
            if self.on_morning:
                self.on_morning()
            
            # Daily News Logic
            if self.mafia_last_seen_zone:
                self.daily_news_log.append(f"Suspicious activity detected near {self.mafia_last_seen_zone}.")
                self.mafia_last_seen_zone = None
            
            # 여기서 UI 호출은 PlayState나 UIManager를 통해 해야 함
            # TimeSystem은 데이터만 관리하고, 표시는 외부에서 polling하거나 콜백으로 처리

        self.init_timer()
