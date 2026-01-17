import pygame
from ui.widgets.base import UIWidget
from settings import FPS

class EmotionPanelWidget(UIWidget):
    def __init__(self, game):
        super().__init__(game)
        self.width = 220
        self.height = 140
        self.panel_bg = self.create_panel_bg(self.width, self.height)

    def draw(self, screen):
        if self.game.player.role == "SPECTATOR": return

        w, h = screen.get_size()
        x = w - self.width - 20
        y = h - self.height - 20
        
        screen.blit(self.panel_bg, (x, y))

        p = self.game.player
        current_speed_frame = p.get_current_speed(getattr(p, 'weather', 'CLEAR'))
        current_speed_px = current_speed_frame * FPS 
        base_speed = 192 
        ratio = (current_speed_px / base_speed) * 100
        
        speed_col = (200, 255, 200) if ratio >= 100 else (255, 100, 100)
        speed_text = self.font_main.render(f"SPEED: {int(current_speed_px)} px/s ({int(ratio)}%)", True, speed_col)
        screen.blit(speed_text, (x + 15, y + 15))

        pygame.draw.line(screen, (80, 80, 90), (x+15, y+40), (x+self.width-15, y+40), 1)

        y_offset = 50
        active_statuses = []
        
        for emo, val in p.emotions.items():
            if val:
                if emo == 'FEAR': active_statuses.append(('FEAR', 'Speed -30%', (100, 100, 255)))
                elif emo == 'RAGE': active_statuses.append(('RAGE', 'Stamina ∞', (255, 50, 50)))
                elif emo == 'PAIN': active_statuses.append(('PAIN', f'Lv.{val} Slow', (255, 100, 100)))
                elif emo == 'HAPPINESS': active_statuses.append(('HAPPY', 'Speed +10%', (255, 255, 100)))
                elif emo == 'ANXIETY': active_statuses.append(('ANXTY', 'Heartbeat', (255, 150, 50)))
            
        if p.status_effects.get('FATIGUE'): active_statuses.append(('FATIGUE', 'Speed -30%', (150, 150, 150)))
        if p.status_effects.get('DOPAMINE'): active_statuses.append(('DOPA', 'Speed +20%', (255, 0, 255)))
        
        if not active_statuses:
            text = self.font_small.render("- Normal State -", True, (150, 150, 150))
            screen.blit(text, (x + 15, y + y_offset))
        else:
            for title, desc, color in active_statuses[:4]:
                text = self.font_small.render(f"■ {title}: {desc}", True, color)
                screen.blit(text, (x + 15, y + y_offset))
                y_offset += 20
