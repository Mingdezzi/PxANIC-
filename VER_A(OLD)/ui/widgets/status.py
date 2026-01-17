import pygame
from ui.widgets.base import UIWidget
from colors import COLORS

class PlayerStatusWidget(UIWidget):
    def __init__(self, game):
        super().__init__(game)
        self.width = 360
        self.height = 110
        self.panel_bg = self.create_panel_bg(self.width, self.height)

    def draw(self, screen):
        p = self.game.player
        x, y = 20, 20
        
        # 배경 그리기
        screen.blit(self.panel_bg, (x, y))

        role_cols = {
            'CITIZEN': (100, 200, 100), 
            'POLICE': (50, 50, 255), 
            'MAFIA': (200, 50, 50), 
            'DOCTOR': (200, 200, 255), 
            'SPECTATOR':(100,100,100)
        }
        c = role_cols.get(p.role, (200, 200, 200))
        
        # 아바타 영역
        avatar_rect = pygame.Rect(x + 15, y + 15, 60, 60)
        pygame.draw.rect(screen, (40, 40, 40), avatar_rect, border_radius=8)
        pygame.draw.rect(screen, c, avatar_rect, 3, border_radius=8)
        
        # 역할 이니셜
        role_char = p.role[0] 
        txt = self.font_big.render(role_char, True, c)
        screen.blit(txt, (avatar_rect.centerx - txt.get_width()//2, avatar_rect.centery - txt.get_height()//2))
        
        # 역할 이름 (아바타 하단)
        role_name = self.font_small.render(p.role, True, (200, 200, 200))
        screen.blit(role_name, (avatar_rect.centerx - role_name.get_width()//2, avatar_rect.bottom + 8))

        # 상태바
        bar_x = x + 130  
        bar_w = 200

        hp_ratio = max(0, p.hp / p.max_hp)
        self._draw_bar(screen, bar_x, y + 25, bar_w, 12, hp_ratio, (220, 60, 60), "HP")
        
        ap_ratio = max(0, p.ap / p.max_ap)
        self._draw_bar(screen, bar_x, y + 50, bar_w, 12, ap_ratio, (60, 150, 220), "AP")
        
        # 소지금 표시
        coin_txt = self.font_digit.render(f"{p.coins:03d} $", True, (255, 215, 0))
        screen.blit(coin_txt, (bar_x, y + 75))

    def _draw_bar(self, screen, x, y, w, h, ratio, color, label):
        pygame.draw.rect(screen, (40, 40, 40), (x, y, w, h), border_radius=4)
        fill_w = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=4)
        for i in range(x, x+w, 10):
            pygame.draw.line(screen, (0,0,0,50), (i, y), (i+5, y+h), 1)
        l_surf = self.font_small.render(label, True, (200, 200, 200))
        screen.blit(l_surf, (x - 25, y - 2))
