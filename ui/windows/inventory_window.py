import pygame
from core.resource_manager import ResourceManager
from settings import ITEMS

class InventoryWindow:
    def __init__(self, player):
        self.player = player
        self.visible = False
        self.sel_idx = 0
        
        self.rm = ResourceManager.get_instance()
        self.font_big = self.rm.get_font("malgungothic", 30)
        self.font_main = self.rm.get_font("malgungothic", 20)
        self.font_small = self.rm.get_font("malgungothic", 14)

    def toggle(self):
        self.visible = not self.visible
        self.sel_idx = 0

    def draw(self, screen, w, h):
        if not self.visible: return
        
        iw, ih = 500, 400
        rect = pygame.Rect(w//2 - iw//2, h//2 - ih//2, iw, ih)
        
        # 배경
        pygame.draw.rect(screen, (30, 30, 40), rect)
        pygame.draw.rect(screen, (255, 255, 0), rect, 2)
        
        title = self.font_big.render("INVENTORY", True, (255, 255, 0))
        screen.blit(title, (rect.x + 20, rect.y + 20))
        
        items_list = list(ITEMS.keys())
        grid_cols, slot_size, gap = 5, 60, 15
        start_x, start_y = rect.x + 30, rect.y + 70
        
        for i, key in enumerate(items_list):
            row, col = i // grid_cols, i % grid_cols
            x, y = start_x + col * (slot_size + gap), start_y + row * (slot_size + gap)
            r = pygame.Rect(x, y, slot_size, slot_size)
            
            # 아이콘 그리기 (헬퍼 메서드 사용 추천)
            self._draw_item_icon(screen, key, r, self.sel_idx == i)
            
            count = self.player.inventory.items.get(key, 0)
            if count > 0:
                cnt_txt = self.font_small.render(str(count), True, (255, 255, 255))
                screen.blit(cnt_txt, cnt_txt.get_rect(bottomright=(r.right-2, r.bottom-2)))
            else:
                s = pygame.Surface((slot_size, slot_size), pygame.SRCALPHA)
                s.fill((0, 0, 0, 150))
                screen.blit(s, r)
        
        # 상세 정보
        if 0 <= self.sel_idx < len(items_list):
            key = items_list[self.sel_idx]
            data = ITEMS[key]
            info_y = rect.bottom - 100
            
            pygame.draw.line(screen, (100, 100, 100), (rect.x, info_y), (rect.right, info_y))
            
            screen.blit(self.font_main.render(data['name'], True, (255, 255, 255)), (rect.x + 30, info_y + 15))
            screen.blit(self.font_small.render(f"Owned: {self.player.inventory.items.get(key,0)}", True, (200, 200, 200)), (rect.x + 30, info_y + 45))
            screen.blit(self.font_small.render(data['desc'], True, (150, 150, 150)), (rect.x + 30, info_y + 70))

    def _draw_item_icon(self, screen, key, rect, is_sel):
        col = (60, 60, 80) if not is_sel else (100, 100, 150)
        pygame.draw.rect(screen, col, rect, border_radius=5)
        if is_sel: pygame.draw.rect(screen, (255, 255, 0), rect, 2, border_radius=5)
        
        c = rect.center
        if key == 'TANGERINE': pygame.draw.circle(screen, (255, 165, 0), c, 10)
        elif key == 'CHOCOBAR': pygame.draw.rect(screen, (139, 69, 19), (c[0]-8, c[1]-12, 16, 24))
        elif key == 'MEDKIT': 
            pygame.draw.rect(screen, (255, 255, 255), (c[0]-10, c[1]-8, 20, 16))
            pygame.draw.line(screen, (255, 0, 0), (c[0], c[1]-5), (c[0], c[1]+5), 2)
            pygame.draw.line(screen, (255, 0, 0), (c[0]-5, c[1]), (c[0]+5, c[1]), 2)
        elif key == 'KEY': pygame.draw.line(screen, (255, 215, 0), (c[0]-5, c[1]+5), (c[0]+5, c[1]-5), 3)
        elif key == 'BATTERY': pygame.draw.rect(screen, (0, 255, 0), (c[0]-6, c[1]-10, 12, 20))
        elif key == 'TASER': pygame.draw.rect(screen, (50, 50, 200), (c[0]-10, c[1]-5, 20, 10))
        else: pygame.draw.circle(screen, (200, 200, 200), c, 5)

    def handle_event(self, event):
        if not self.visible: return False
        
        if event.type == pygame.KEYDOWN:
            items_list = list(ITEMS.keys())
            if event.key == pygame.K_UP:
                self.sel_idx = (self.sel_idx - 1) % len(items_list)
            elif event.key == pygame.K_DOWN:
                self.sel_idx = (self.sel_idx + 1) % len(items_list)
            elif event.key == pygame.K_RETURN:
                # 아이템 사용 요청 (EventBus 사용 권장)
                # 여기서는 UI Manager가 처리하도록 True 반환하거나 콜백 실행
                # 임시로 키 반환
                return ("USE_ITEM", items_list[self.sel_idx])
            elif event.key in [pygame.K_ESCAPE, pygame.K_i]:
                self.toggle()
            return True
        return False
