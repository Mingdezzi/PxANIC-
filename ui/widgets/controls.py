import pygame
from core.resource_manager import ResourceManager

class ControlsWidget:
    def __init__(self):
        self.rm = ResourceManager.get_instance()
        self.font_main = self.rm.get_font("malgungothic", 20)
        self.font_small = self.rm.get_font("malgungothic", 14)

    def draw(self, screen, w, h, player_role):
        icon_size = 50
        gap = 10
        start_x = 20
        start_y = h - (icon_size * 2 + gap) - 20 
        
        def get_pos(col, row):
            return start_x + col * (icon_size + gap), start_y + row * (icon_size + gap)

        self.draw_key_icon(screen, *get_pos(0, 0), "I", "인벤토리")
        self.draw_key_icon(screen, *get_pos(1, 0), "Z", "투표")
        self.draw_key_icon(screen, *get_pos(2, 0), "E", "상호작용")
        
        if player_role in ["CITIZEN", "DOCTOR"]:
            q_label = "동체탐지"
        elif player_role == "POLICE":
            q_label = "사이렌"
        else:
            q_label = "특수스킬"
        
        self.draw_key_icon(screen, *get_pos(0, 1), "Q", q_label)
        self.draw_key_icon(screen, *get_pos(1, 1), "R", "재장전")
        self.draw_key_icon(screen, *get_pos(2, 1), "V", "행동")

    def draw_key_icon(self, screen, x, y, key, label):
        rect = pygame.Rect(x, y, 50, 50)
        pygame.draw.rect(screen, (40, 40, 50), rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 120), rect, 2, border_radius=8)
        
        text_surf = self.font_main.render(key, True, (255, 255, 255))
        screen.blit(text_surf, (x + 25 - text_surf.get_width()//2, y + 4))
        
        lbl_surf = self.font_small.render(label, True, (200, 200, 200))
        if lbl_surf.get_width() > 46:
            lbl_surf = pygame.transform.smoothscale(lbl_surf, (44, int(lbl_surf.get_height() * (44/lbl_surf.get_width()))))
        screen.blit(lbl_surf, (x + 25 - lbl_surf.get_width()//2, y + 28))
