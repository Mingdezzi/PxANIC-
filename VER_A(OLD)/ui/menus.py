import pygame
from ui.widgets.base import UIWidget
from settings import ITEMS, FPS

class PopupManager(UIWidget):
    def __init__(self, game):
        super().__init__(game)
        self.dim_surface = None
        self.spectator_scroll_y = 0
        self.skip_btn_rect = None
        self.entity_rects = []

    def draw_inventory(self, screen, w, h, sel_idx):
        iw, ih = 500, 400; rect_obj = pygame.Rect(w//2 - iw//2, h//2 - ih//2, iw, ih)
        pygame.draw.rect(screen, (30, 30, 40), rect_obj); pygame.draw.rect(screen, (255, 255, 0), rect_obj, 2)
        screen.blit(self.font_big.render("INVENTORY", True, (255, 255, 0)), (rect_obj.x + 20, rect_obj.y + 20))
        items_list = list(ITEMS.keys())
        grid_cols, slot_size, gap = 5, 60, 15; start_x, start_y = rect_obj.x + 30, rect_obj.y + 70
        for i, key in enumerate(items_list):
            row, col = i // grid_cols, i % grid_cols; x, y = start_x + col * (slot_size + gap), start_y + row * (slot_size + gap); r = pygame.Rect(x, y, slot_size, slot_size)
            count = self.game.player.inventory.get(key, 0); self._draw_item_icon(screen, key, r, sel_idx == i)
            if count > 0:
                cnt_txt = self.font_small.render(str(count), True, (255, 255, 255))
                screen.blit(cnt_txt, cnt_txt.get_rect(bottomright=(r.right-2, r.bottom-2)))
            else:
                s = pygame.Surface((slot_size, slot_size), pygame.SRCALPHA); s.fill((0, 0, 0, 150)); screen.blit(s, r)
        if 0 <= sel_idx < len(items_list):
            key = items_list[sel_idx]; data = ITEMS[key]; info_y = rect_obj.bottom - 100
            pygame.draw.line(screen, (100, 100, 100), (rect_obj.x, info_y), (rect_obj.right, info_y))
            screen.blit(self.font_main.render(data['name'], True, (255, 255, 255)), (rect_obj.x + 30, info_y + 15))
            screen.blit(self.font_small.render(f"Owned: {self.game.player.inventory.get(key,0)}", True, (200, 200, 200)), (rect_obj.x + 30, info_y + 45))
            screen.blit(self.font_small.render(data['desc'], True, (150, 150, 150)), (rect_obj.x + 30, info_y + 70))

    def draw_vending_machine(self, screen, w, h, sel_idx):
        vw, vh = 600, 500; rect_obj = pygame.Rect(w//2 - vw//2, h//2 - vh//2, vw, vh)
        pygame.draw.rect(screen, (20, 20, 30), rect_obj); pygame.draw.rect(screen, (0, 255, 255), rect_obj, 3)
        screen.blit(self.font_big.render("SHOP", True, (0, 255, 255)), (rect_obj.x + 20, rect_obj.y + 20))
        items_list = list(ITEMS.keys())
        grid_cols, slot_size, gap = 5, 60, 15; start_x, start_y = rect_obj.x + 30, rect_obj.y + 70
        for i, key in enumerate(items_list):
            row, col = i // grid_cols, i % grid_cols; x, y = start_x + col * (slot_size + gap), start_y + row * (slot_size + gap)
            self._draw_item_icon(screen, key, pygame.Rect(x, y, slot_size, slot_size), sel_idx == i)
        if 0 <= sel_idx < len(items_list):
            key = items_list[sel_idx]; data = ITEMS[key]; info_y = rect_obj.bottom - 120
            pygame.draw.line(screen, (100, 100, 100), (rect_obj.x, info_y), (rect_obj.right, info_y))
            screen.blit(self.font_main.render(data['name'], True, (255, 255, 255)), (rect_obj.x + 30, info_y + 15))
            screen.blit(self.font_small.render(f"Price: {data['price']}G", True, (255, 215, 0)), (rect_obj.x + 30, info_y + 45))
            screen.blit(self.font_small.render(data['desc'], True, (200, 200, 200)), (rect_obj.x + 30, info_y + 75))

    def _draw_item_icon(self, screen, key, rect, is_sel):
        col = (60, 60, 80) if not is_sel else (100, 100, 150)
        pygame.draw.rect(screen, col, rect, border_radius=5)
        if is_sel: pygame.draw.rect(screen, (255, 255, 0), rect, 2, border_radius=5)
        c = rect.center
        if key == 'TANGERINE': pygame.draw.circle(screen, (255, 165, 0), c, 10)
        elif key == 'CHOCOBAR': pygame.draw.rect(screen, (139, 69, 19), (c[0]-8, c[1]-12, 16, 24))
        elif key == 'MEDKIT': 
            pygame.draw.rect(screen, (255, 255, 255), (c[0]-10, c[1]-8, 20, 16))
            pygame.draw.line(screen, (255, 0, 0), (c[0], c[1]-5), (c[0], c[1]+5), 2); pygame.draw.line(screen, (255, 0, 0), (c[0]-5, c[1]), (c[0]+5, c[1]), 2)
        elif key == 'KEY': pygame.draw.line(screen, (255, 215, 0), (c[0]-5, c[1]+5), (c[0]+5, c[1]-5), 3)
        elif key == 'BATTERY': pygame.draw.rect(screen, (0, 255, 0), (c[0]-6, c[1]-10, 12, 20))
        elif key == 'TASER': pygame.draw.rect(screen, (50, 50, 200), (c[0]-10, c[1]-5, 20, 10))
        else: pygame.draw.circle(screen, (200, 200, 200), c, 5)

    def draw_vote_ui(self, screen, w, h):
        if self.game.current_phase != "VOTE": return
        center_x = w // 2
        msg = self.font_big.render("VOTING SESSION", True, (255, 50, 50))
        screen.blit(msg, (center_x - msg.get_width()//2, 100))
        desc = self.font_main.render("Press 'Z' to Vote", True, (200, 200, 200))
        screen.blit(desc, (center_x - desc.get_width()//2, 140))

    def draw_vote_popup(self, screen, sw, sh, npcs, player, current_target):
        w, h = 400, 500
        cx, cy = sw // 2, sh // 2
        panel_rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        
        if self.dim_surface is None or self.dim_surface.get_size() != (sw, sh):
             self.dim_surface = pygame.Surface((sw, sh), pygame.SRCALPHA)
             self.dim_surface.fill((0, 0, 0, 150))
        screen.blit(self.dim_surface, (0, 0))
        
        pygame.draw.rect(screen, (40, 40, 45), panel_rect, border_radius=12)
        pygame.draw.rect(screen, (100, 100, 120), panel_rect, 2, border_radius=12)
        title = self.font_big.render("VOTE TARGET", True, (255, 255, 255))
        screen.blit(title, (cx - title.get_width()//2, panel_rect.top + 20))
        candidates = [player] + [n for n in npcs if n.alive]
        candidate_rects = []
        start_y = panel_rect.top + 80
        for c in candidates:
            row_rect = pygame.Rect(panel_rect.left + 20, start_y, w - 40, 40)
            is_selected = (current_target == c)
            col = (50, 50, 150) if is_selected else (60, 60, 70)
            if row_rect.collidepoint(pygame.mouse.get_pos()):
                col = (80, 80, 100)
            pygame.draw.rect(screen, col, row_rect, border_radius=4)
            info = f"{c.name} ({c.role})"
            t = self.font_main.render(info, True, (220, 220, 220))
            screen.blit(t, (row_rect.left + 10, row_rect.centery - t.get_height()//2))
            candidate_rects.append((c, row_rect))
            start_y += 50
        return candidate_rects

    def draw_daily_news(self, screen, w, h, news_text):
        if self.dim_surface is None or self.dim_surface.get_size() != (w, h):
             self.dim_surface = pygame.Surface((w, h), pygame.SRCALPHA)
             self.dim_surface.fill((0, 0, 0, 150))
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
        for line in news_text:
            t = self.font_main.render(line, True, (20, 20, 20))
            screen.blit(t, (center_x - t.get_width()//2, paper_rect.top + y_offset))
            y_offset += 35
        close_txt = self.font_small.render("Press SPACE to Close", True, (100, 100, 100))
        screen.blit(close_txt, (center_x - close_txt.get_width()//2, paper_rect.bottom - 40))

    def draw_spectator_ui(self, screen, w, h):
        self.skip_btn_rect = pygame.Rect(w - 300, 20, 100, 40)
        pygame.draw.rect(screen, (150, 50, 50), self.skip_btn_rect, border_radius=8)
        txt = self.font_small.render("SKIP PHASE", True, (255, 255, 255))
        screen.blit(txt, (self.skip_btn_rect.centerx - txt.get_width()//2, self.skip_btn_rect.centery - txt.get_height()//2))
        
        self.entity_rects = []
        start_y = 80 - self.spectator_scroll_y
        right_panel_x = w - 180
        
        for npc in self.game.npcs:
            if not npc.alive: continue
            r = pygame.Rect(right_panel_x, start_y, 160, 30)
            if 0 < start_y < h:
                col = (100, 255, 100) if npc.role == "CITIZEN" else ((255, 100, 100) if npc.role == "MAFIA" else (200, 200, 255))
                pygame.draw.rect(screen, (50, 50, 50), r, border_radius=4)
                pygame.draw.rect(screen, col, (r.left, r.top, 5, r.height), border_top_left_radius=4, border_bottom_left_radius=4)
                name_txt = self.font_small.render(f"{npc.name} ({npc.role})", True, (200, 200, 200))
                screen.blit(name_txt, (r.left + 10, r.centery - name_txt.get_height()//2))
                self.entity_rects.append((r, npc))
            start_y += 35

    def draw(self, screen):
        pass # Placeholder
