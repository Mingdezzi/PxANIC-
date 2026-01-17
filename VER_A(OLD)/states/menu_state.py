import pygame
from core.base_state import BaseState
from managers.resource_manager import ResourceManager
from colors import COLORS
from settings import SCREEN_WIDTH, SCREEN_HEIGHT

class MenuState(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.resource_manager = ResourceManager.get_instance()
        self.buttons = {}
        self.title_font = self.resource_manager.get_font('title')
        self.large_font = self.resource_manager.get_font('large')
        
        # UI Style Helper
        self.panel_bg = self._create_panel_bg(400, 300)

    def _create_panel_bg(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 20, 25, 220), (0, 0, w, h), border_radius=15)
        pygame.draw.rect(s, (80, 80, 100, 255), (0, 0, w, h), 2, border_radius=15)
        return s

    def enter(self, params=None):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        w, h = screen.get_width(), screen.get_height()
        
        # 1. Background Pattern
        screen.fill((10, 10, 15))
        self._draw_grid_bg(screen, w, h)

        # 2. Title
        title_surf = self.title_font.render("PIXEL NIGHT", True, (255, 255, 255))
        # Shadow
        shadow_surf = self.title_font.render("PIXEL NIGHT", True, (0, 0, 0))
        screen.blit(shadow_surf, (w//2 - title_surf.get_width()//2 + 4, h//4 + 4))
        screen.blit(title_surf, (w//2 - title_surf.get_width()//2, h//4))

        # 3. Menu Panel Area
        panel_rect = self.panel_bg.get_rect(center=(w//2, h//2 + 50))
        screen.blit(self.panel_bg, panel_rect)

        # 4. Buttons
        start_y = panel_rect.top + 60
        self._draw_styled_button(screen, "START MISSION", w//2, start_y, 'Start')
        self._draw_styled_button(screen, "MULTIPLAYER", w//2, start_y + 80, 'Multi')
        self._draw_styled_button(screen, "EXIT", w//2, start_y + 160, 'Exit')

    def _draw_grid_bg(self, screen, w, h):
        for x in range(0, w, 40):
            pygame.draw.line(screen, (20, 20, 30), (x, 0), (x, h))
        for y in range(0, h, 40):
            pygame.draw.line(screen, (20, 20, 30), (0, y), (w, y))

    def _draw_styled_button(self, screen, text, cx, cy, key):
        btn_w, btn_h = 280, 50
        rect = pygame.Rect(0, 0, btn_w, btn_h)
        rect.center = (cx, cy)
        
        mx, my = pygame.mouse.get_pos()
        is_hover = rect.collidepoint(mx, my)
        
        # Colors
        bg_col = (40, 40, 50) if not is_hover else (60, 60, 80)
        border_col = (100, 100, 120) if not is_hover else (100, 255, 100)
        text_col = (200, 200, 200) if not is_hover else (255, 255, 255)
        
        pygame.draw.rect(screen, bg_col, rect, border_radius=8)
        pygame.draw.rect(screen, border_col, rect, 2 if not is_hover else 3, border_radius=8)
        
        txt_surf = self.large_font.render(text, True, text_col)
        screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))
        
        self.buttons[key] = rect

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                if 'Start' in self.buttons and self.buttons['Start'].collidepoint(mx, my):
                    from states.lobby_state import LobbyState
                    self.game.state_machine.change(LobbyState(self.game))
                
                if 'Multi' in self.buttons and self.buttons['Multi'].collidepoint(mx, my):
                    print("[MENU] Multiplayer clicked (Connecting...)")
                    from states.lobby_state import LobbyState
                    self.game.state_machine.change(LobbyState(self.game))
                    
                if 'Exit' in self.buttons and self.buttons['Exit'].collidepoint(mx, my):
                    self.game.running = False