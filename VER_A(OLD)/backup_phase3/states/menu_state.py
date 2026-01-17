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

    def enter(self, params=None):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(COLORS['MENU_BG'])
        w, h = screen.get_width(), screen.get_height()


        title_surf = self.title_font.render("PIXEL NIGHT", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(w // 2, h // 3))
        screen.blit(title_surf, title_rect)


        btn_rect = pygame.Rect(w // 2 - 150, h // 2, 300, 60)
        mx, my = pygame.mouse.get_pos()

        is_hover = btn_rect.collidepoint(mx, my)
        col = COLORS['BUTTON_HOVER'] if is_hover else COLORS['BUTTON']

        pygame.draw.rect(screen, col, btn_rect)
        pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2)

        txt_surf = self.large_font.render("START MISSION", True, (255, 255, 255))
        txt_rect = txt_surf.get_rect(center=btn_rect.center)
        screen.blit(txt_surf, txt_rect)

        self.buttons['Start'] = btn_rect

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                if 'Start' in self.buttons and self.buttons['Start'].collidepoint(mx, my):

                    from states.lobby_state import LobbyState
                    self.game.state_machine.change(LobbyState(self.game))
