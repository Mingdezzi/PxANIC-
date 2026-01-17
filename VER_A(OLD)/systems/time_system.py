import pygame
import random
from settings import DEFAULT_PHASE_DURATIONS, WEATHER_TYPES, WEATHER_PROBS

class TimeSystem:
    def __init__(self, game):
        self.game = game
        self.day_count = 1
        self.phases = ["DAWN", "MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"]
        self.current_phase_idx = 0
        self.current_phase = self.phases[0]
        self.state_timer = 30
        
        self.weather = random.choices(WEATHER_TYPES, weights=WEATHER_PROBS, k=1)[0]
        self.weather_particles = []
        for _ in range(100):
            self.weather_particles.append([
                random.randint(0, game.screen_width),
                random.randint(0, game.screen_height),
                random.randint(5, 10),
                random.choice([0, 1])
            ])
            
        self.daily_news_log = []
        self.mafia_last_seen_zone = None

        self.on_phase_change = None 
        self.on_morning = None 

    def init_timer(self):
        durations = self.game.shared_data.get('custom_durations', DEFAULT_PHASE_DURATIONS)
        self.state_timer = durations.get(self.current_phase, 30)

    def sync_time(self, phase_idx, timer, day):
        """Called when TIME_SYNC packet is received"""
        if self.current_phase_idx != phase_idx:
            old_phase = self.current_phase
            self.current_phase_idx = phase_idx
            self.current_phase = self.phases[phase_idx]
            if self.on_phase_change:
                self.on_phase_change(old_phase, self.current_phase)
            
            # If changed to MORNING (Client side logic needs morning trigger)
            # Actually, server changed date at DAWN. 
            # But client events like healing happen at MORNING.
            if self.current_phase == "MORNING":
                if self.on_morning: self.on_morning()

        self.state_timer = timer
        self.day_count = day

    def update(self, dt):
        # Only update locally if offline
        if not (hasattr(self.game, 'network') and self.game.network.connected):
            self.state_timer -= dt
            if self.state_timer <= 0:
                self._advance_phase()
            
        # Update Weather Particles (Always)
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

        # [Rule Change] Day increases at DAWN
        if self.current_phase == "DAWN":
            self.day_count += 1

        if self.on_phase_change:
            self.on_phase_change(old_phase, self.current_phase)

        if self.current_phase == "MORNING":
            if self.on_morning:
                self.on_morning()
            
            if self.mafia_last_seen_zone:
                self.daily_news_log.append(f"Suspicious activity detected near {self.mafia_last_seen_zone}.")
                self.mafia_last_seen_zone = None

        self.init_timer()