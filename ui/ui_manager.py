import pygame
from core.event_bus import EventBus
from core.resource_manager import ResourceManager
from .widgets.hud import HUD
from .widgets.minimap import MinimapWidget
from .widgets.controls import ControlsWidget
from .widgets.popup import PopupWidget
from .windows.inventory_window import InventoryWindow
from .windows.shop_window import ShopWindow
from .windows.vote_window import VoteWindow

class UIManager:
    def __init__(self, event_bus: EventBus, player, map_manager):
        self.event_bus = event_bus
        self.player = player
        self.map_manager = map_manager
        
        # Widgets
        self.hud = HUD(self)
        self.minimap = MinimapWidget(map_manager)
        self.controls = ControlsWidget()
        self.popup = PopupWidget()
        
        # Windows
        self.inventory_window = InventoryWindow(player)
        self.shop_window = ShopWindow(player)
        self.vote_window = VoteWindow()
        
        # Event Subscription
        self.event_bus.subscribe("SHOW_ALERT", self._on_show_alert)
        self.event_bus.subscribe("SHOW_NEWS", self._on_show_news)
        self.event_bus.subscribe("TOGGLE_INVENTORY", lambda d: self.inventory_window.toggle())
        self.event_bus.subscribe("TOGGLE_SHOP", lambda d: self.shop_window.toggle())
        self.event_bus.subscribe("TOGGLE_VOTE", lambda d: self.vote_window.toggle())

    def update(self, dt):
        pass

    def draw(self, screen, game_state):
        w, h = screen.get_size()
        
        # 1. Base HUD
        self.hud.draw(screen, self.player, game_state)
        self.controls.draw(screen, w, h, self.player.role.main_role)
        
        # 2. Minimap (우측 하단)
        npcs = game_state.get('npcs', [])
        self.minimap.draw(screen, w, h, self.player, npcs)
        
        # 3. Windows (Layered)
        if self.vote_window.visible:
            self.vote_window.draw(screen, w, h, self.player, npcs)
            
        if self.inventory_window.visible:
            self.inventory_window.draw(screen, w, h)
            
        if self.shop_window.visible:
            self.shop_window.draw(screen, w, h)
            
        # 4. Popups (Top Layer)
        self.popup.draw(screen, w, h)
        
        # 5. Spectator UI
        if self.player.role.main_role == "SPECTATOR":
            self._draw_spectator_ui(screen, w, h, npcs)

    def handle_event(self, event, game_state):
        # 윈도우 이벤트 우선 처리 (입력 가로채기)
        if self.popup.show_news:
            if self.popup.handle_event(event): return True
            
        if self.shop_window.visible:
            res = self.shop_window.handle_event(event)
            if res:
                if isinstance(res, tuple) and res[0] == "BUY_ITEM":
                    self.event_bus.publish("BUY_ITEM_REQUEST", {'item_key': res[1]})
                return True
                
        if self.inventory_window.visible:
            res = self.inventory_window.handle_event(event)
            if res:
                if isinstance(res, tuple) and res[0] == "USE_ITEM":
                    self.event_bus.publish("USE_ITEM_REQUEST", {'item_key': res[1]})
                return True
                
        if self.vote_window.visible:
            npcs = game_state.get('npcs', [])
            res = self.vote_window.handle_event(event, self.player, npcs)
            if res:
                if isinstance(res, tuple) and res[0] == "VOTE_CAST":
                    self.event_bus.publish("VOTE_CAST", {'target': res[1]})
                return True
        
        # Global Keys
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i: self.inventory_window.toggle()
            elif event.key == pygame.K_z: self.vote_window.toggle()
            # E키(상호작용)와 ESC는 상황에 따라 다름
            
        return False

    def _on_show_alert(self, data):
        self.popup.show_alert(data.get('text', ''), data.get('color', (255, 255, 255)))

    def _on_show_news(self, data):
        self.popup.show_daily_news(data.get('news_log', []))

    def _draw_spectator_ui(self, screen, w, h, npcs):
        # 관전자 전용 UI (간단 구현)
        btn_rect = pygame.Rect(w - 300, 20, 100, 40)
        pygame.draw.rect(screen, (150, 50, 50), btn_rect, border_radius=8)
        
        rm = ResourceManager.get_instance()
        font = rm.get_font("malgungothic", 14)
        txt = font.render("SKIP PHASE", True, (255, 255, 255))
        screen.blit(txt, (btn_rect.centerx - txt.get_width()//2, btn_rect.centery - txt.get_height()//2))
        
        # 생존자 목록 표시 생략 (HUD나 미니맵으로 충분할 수 있음)
