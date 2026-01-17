import pygame
from ui.widgets.base import UIWidget
from settings import DEFAULT_PHASE_DURATIONS

class EnvironmentWidget(UIWidget):
    def __init__(self, game):
        super().__init__(game)
        self.width = 240
        self.height = 80
        self.panel_bg = self.create_panel_bg(self.width, self.height)
        
        # [Optimization] Text Caching
        self.last_full_text = ""
        self.cached_time_surf = None
        self.last_weather_str = ""
        self.cached_weather_surf = None

    def draw(self, screen):
        w, h = screen.get_size()
        x = w - self.width - 20
        y = 20
        
        screen.blit(self.panel_bg, (x, y))

        time_str = self._calculate_game_time()
        phase_str = self.game.current_phase
        day_str = f"DAY {self.game.day_count}"
        full_text = f"{day_str} | {phase_str} | {time_str}"
        
        # Check Cache
        if full_text != self.last_full_text:
            time_col = (100, 255, 100) if self.game.current_phase in ["MORNING", "DAY", "NOON", "AFTERNOON"] else (255, 100, 100)
            self.cached_time_surf = self.font_main.render(full_text, True, time_col)
            self.last_full_text = full_text
            
        screen.blit(self.cached_time_surf, (x + self.width//2 - self.cached_time_surf.get_width()//2, y + 15))
        
        weather_str = getattr(self.game, 'weather', 'CLEAR')
        if weather_str != self.last_weather_str:
            self.cached_weather_surf = self.font_small.render(f"Weather: {weather_str}", True, (200, 200, 200))
            self.last_weather_str = weather_str
            
        screen.blit(self.cached_weather_surf, (x + self.width//2 - self.cached_weather_surf.get_width()//2, y + 50))

    def _calculate_game_time(self):
        phase = self.game.current_phase
        timer = self.game.state_timer
        
        start_times = {'DAWN': (4, 0), 'MORNING': (6, 0), 'NOON': (8, 0), 'AFTERNOON': (16, 0), 'EVENING': (17, 0), 'NIGHT': (19, 0)}
        phase_lengths = {'DAWN': 120, 'MORNING': 120, 'NOON': 480, 'AFTERNOON': 60, 'EVENING': 120, 'NIGHT': 540}
        
        durations = self.game.game.shared_data.get('custom_durations', DEFAULT_PHASE_DURATIONS)
        total_duration = durations.get(phase, 60)
        
        elapsed = max(0, total_duration - timer)
        ratio = elapsed / total_duration if total_duration > 0 else 0
        
        start_h, start_m = start_times.get(phase, (0, 0))
        add_minutes = int(phase_lengths.get(phase, 60) * ratio)
        current_minutes = start_m + add_minutes
        current_h = (start_h + current_minutes // 60) % 24
        current_m = current_minutes % 60
        return f"{current_h:02d}:{current_m:02d}"
