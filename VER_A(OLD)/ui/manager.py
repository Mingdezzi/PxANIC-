import pygame
from ui.hud import HUD
from ui.menus import PopupManager
from ui.widgets.base import UIWidget
from settings import DEFAULT_PHASE_DURATIONS, SCREEN_WIDTH, SCREEN_HEIGHT, ITEMS

class UIManager:
    def __init__(self, game):
        self.game = game
        
        # [Component Managers]
        self.hud = HUD(game)
        self.menus = PopupManager(game)
        
        # [State Variables]
        self.show_vending = False
        self.show_inventory = False
        self.show_voting = False
        self.show_news = False
        self.sel_idx = 0
        self.news_text = []
        
        self.alert_text = ""
        self.alert_timer = 0
        self.alert_color = (255, 255, 255)
        
        # [Spectator System]
        self.spectator_follow_target = None
        self.spectator_scroll_y = 0
        self.entity_rects = []
        
        # [Safety Fix] 초기값을 None이 아닌 빈 Rect로 설정하여 AttributeError 방지
        self.skip_btn_rect = pygame.Rect(0, 0, 0, 0)

        # Compatibility
        self.custom_durations = DEFAULT_PHASE_DURATIONS.copy()
        
        # Shared Resources (폰트 로딩용 더미 위젯)
        self._base = UIWidget(game) 

    @property
    def minimap_rect(self):
        return self.hud.get_minimap_rect()

    def show_alert(self, text, color=(255, 255, 255)):
        self.alert_text = text
        self.alert_color = color
        self.alert_timer = pygame.time.get_ticks() + 3000

    def toggle_vending_machine(self):
        self.show_vending = not self.show_vending
        if self.show_vending: self.show_inventory = False; self.show_voting = False; self.sel_idx = 0

    def toggle_inventory(self):
        self.show_inventory = not self.show_inventory
        if self.show_inventory: self.show_vending = False; self.show_voting = False; self.sel_idx = 0

    def show_daily_news(self, news_log):
        self.show_news = True
        self.news_text = news_log if news_log else ["No special news today."]

    def draw(self, screen):
        w, h = screen.get_size()
        
        # 1. HUD 그리기 (게임 화면 위)
        self.hud.draw(screen)
        
        # 2. 팝업 메뉴 그리기
        self.menus.draw_vote_ui(screen, w, h)
        
        if self.show_inventory:
            self.menus.draw_inventory(screen, w, h, self.sel_idx)
        if self.show_vending:
            self.menus.draw_vending_machine(screen, w, h, self.sel_idx)
            
        if self.game.player.role == "SPECTATOR":
            # PlayState에서 변경된 스크롤 값을 PopupManager에 전달
            self.menus.spectator_scroll_y = self.spectator_scroll_y
            self.menus.draw_spectator_ui(screen, w, h)
            
            # 그려진 후의 버튼 위치와 엔티티 목록을 다시 가져와 PlayState가 참조할 수 있게 함
            self.entity_rects = self.menus.entity_rects
            self.skip_btn_rect = self.menus.skip_btn_rect
            
        if self.show_news:
            self.menus.draw_daily_news(screen, w, h, self.news_text)

        # 3. 알림 메시지 (최상단)
        if pygame.time.get_ticks() < self.alert_timer:
            font = self._base.font_big
            txt_surf = font.render(self.alert_text, True, self.alert_color)
            bg_rect = txt_surf.get_rect(center=(w // 2, 150))
            bg_rect.inflate_ip(40, 20)
            
            s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            screen.blit(s, bg_rect.topleft)
            screen.blit(txt_surf, txt_surf.get_rect(center=bg_rect.center))

    # PlayState에서 호출하는 투표 팝업 프록시
    def draw_vote_popup(self, screen, sw, sh, npcs, player, current_target):
        if self.show_voting:
            return self.menus.draw_vote_popup(screen, sw, sh, npcs, player, current_target)
        return []

    def handle_keyboard(self, key, npcs=None):
        if self.show_news:
            if key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE]: self.show_news = False
            return True
            
        items_list = list(ITEMS.keys())
        if self.show_vending:
            if key == pygame.K_UP: self.sel_idx = (self.sel_idx - 1) % len(items_list)
            elif key == pygame.K_DOWN: self.sel_idx = (self.sel_idx + 1) % len(items_list)
            elif key == pygame.K_RETURN: return self.game.player.buy_item(items_list[self.sel_idx])
            elif key in [pygame.K_ESCAPE, pygame.K_e]: self.show_vending = False
            return True
            
        if self.show_inventory:
            if key == pygame.K_UP: self.sel_idx = (self.sel_idx - 1) % len(items_list)
            elif key == pygame.K_DOWN: self.sel_idx = (self.sel_idx + 1) % len(items_list)
            elif key == pygame.K_RETURN: return self.game.player.use_item(items_list[self.sel_idx])
            elif key in [pygame.K_ESCAPE, pygame.K_i]: self.show_inventory = False
            return True
            
        if self.show_voting:
            targets = [n for n in npcs if n.alive] + ([self.game.player] if self.game.player.alive else [])
            if not targets: return False
            if key == pygame.K_UP: self.sel_idx = (self.sel_idx - 1) % len(targets)
            elif key == pygame.K_DOWN: self.sel_idx = (self.sel_idx + 1) % len(targets)
            elif key == pygame.K_RETURN: targets[self.sel_idx].vote_count += 1; self.show_voting = False; return "VOTED"
            return True
            
        if key == pygame.K_ESCAPE:
            self.show_vending = False
            self.show_inventory = False
            self.show_voting = False
            self.show_news = False
            return True
        return False