import pygame
from core.resource_manager import ResourceManager

class PopupWidget:
    def __init__(self):
        self.rm = ResourceManager.get_instance()
        self.font_big = self.rm.get_font("malgungothic", 30)
        self.font_main = self.rm.get_font("malgungothic", 20)
        self.font_small = self.rm.get_font("malgungothic", 14)
        
        self.alert_text = ""
        self.alert_timer = 0
        self.alert_color = (255, 255, 255)
        
        self.show_news = False
        self.news_text = []
        self.dim_surface = None

    def show_alert(self, text, color=(255, 255, 255)):
        self.alert_text = text
        self.alert_color = color
        self.alert_timer = pygame.time.get_ticks() + 3000

    def show_daily_news(self, news_log):
        self.show_news = True
        self.news_text = news_log if news_log else ["No special news today."]

    def draw(self, screen, w, h):
        # Alert
        if pygame.time.get_ticks() < self.alert_timer:
            txt_surf = self.font_big.render(self.alert_text, True, self.alert_color)
            bg_rect = txt_surf.get_rect(center=(w // 2, 150))
            bg_rect.inflate_ip(40, 20)
            
            s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            screen.blit(s, bg_rect.topleft)
            screen.blit(txt_surf, txt_surf.get_rect(center=bg_rect.center))
            
        # News
        if self.show_news:
            if not self.dim_surface or self.dim_surface.get_size() != (w, h):
                self.dim_surface = pygame.Surface((w, h), pygame.SRCALPHA)
                self.dim_surface.fill((0, 0, 0, 180))
            screen.blit(self.dim_surface, (0, 0))
            
            center_x, center_y = w // 2, h // 2
            paper_w, paper_h = 500, 600
            paper_rect = pygame.Rect(center_x - paper_w//2, center_y - paper_h//2, paper_w, paper_h)
            
            pygame.draw.rect(screen, (240, 230, 200), paper_rect)
            pygame.draw.rect(screen, (100, 90, 80), paper_rect, 4)
            
            title = self.font_big.render("DAILY NEWS", True, (50, 40, 30))
            screen.blit(title, (center_x - title.get_width()//2, paper_rect.top + 30))
            
            line_y = paper_rect.top + 80
            pygame.draw.line(screen, (50, 40, 30), (paper_rect.left + 20, line_y), (paper_rect.right - 20, line_y), 2)
            
            y_offset = 110
            for line in self.news_text:
                t = self.font_main.render(line, True, (20, 20, 20))
                screen.blit(t, (center_x - t.get_width()//2, paper_rect.top + y_offset))
                y_offset += 35
                
            close_txt = self.font_small.render("Press SPACE to Close", True, (100, 100, 100))
            screen.blit(close_txt, (center_x - close_txt.get_width()//2, paper_rect.bottom - 40))

    def handle_event(self, event):
        if self.show_news:
            if event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE]:
                self.show_news = False
                return True
        return False
