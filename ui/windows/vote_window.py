import pygame
from core.resource_manager import ResourceManager

class VoteWindow:
    def __init__(self):
        self.visible = False
        self.sel_idx = 0
        self.rm = ResourceManager.get_instance()
        self.font_big = self.rm.get_font("malgungothic", 30)
        self.font_main = self.rm.get_font("malgungothic", 20)
        
        self.dim_surface = None

    def toggle(self):
        self.visible = not self.visible
        self.sel_idx = 0

    def draw(self, screen, w, h, player, npcs):
        if not self.visible: return

        if not self.dim_surface or self.dim_surface.get_size() != (w, h):
             self.dim_surface = pygame.Surface((w, h), pygame.SRCALPHA)
             self.dim_surface.fill((0, 0, 0, 150))
        screen.blit(self.dim_surface, (0, 0))

        panel_w, panel_h = 400, 500
        cx, cy = w // 2, h // 2
        rect = pygame.Rect(cx - panel_w//2, cy - panel_h//2, panel_w, panel_h)
        
        pygame.draw.rect(screen, (40, 40, 45), rect, border_radius=12)
        pygame.draw.rect(screen, (100, 100, 120), rect, 2, border_radius=12)
        
        title = self.font_big.render("VOTE TARGET", True, (255, 255, 255))
        screen.blit(title, (cx - title.get_width()//2, rect.top + 20))
        
        # 투표 대상: 살아있는 NPC + 플레이어(살아있으면)
        targets = [n for n in npcs if n.stats.alive]
        if player.stats.alive:
            targets.insert(0, player)
            
        start_y = rect.top + 80
        
        for i, target in enumerate(targets):
            row_rect = pygame.Rect(rect.left + 20, start_y, panel_w - 40, 40)
            
            is_selected = (self.sel_idx == i)
            col = (50, 50, 150) if is_selected else (60, 60, 70)
            
            # 마우스 오버 처리 (선택사항)
            if row_rect.collidepoint(pygame.mouse.get_pos()):
                col = (80, 80, 100)
                
            pygame.draw.rect(screen, col, row_rect, border_radius=4)
            
            info = f"{target.name} ({target.role.main_role})"
            t = self.font_main.render(info, True, (220, 220, 220))
            screen.blit(t, (row_rect.left + 10, row_rect.centery - t.get_height()//2))
            
            start_y += 50

    def handle_event(self, event, player, npcs):
        if not self.visible: return False
        
        if event.type == pygame.KEYDOWN:
            targets = [n for n in npcs if n.stats.alive]
            if player.stats.alive: targets.insert(0, player)
            
            if not targets: return False

            if event.key == pygame.K_UP:
                self.sel_idx = (self.sel_idx - 1) % len(targets)
            elif event.key == pygame.K_DOWN:
                self.sel_idx = (self.sel_idx + 1) % len(targets)
            elif event.key == pygame.K_RETURN:
                target = targets[self.sel_idx]
                self.toggle()
                return ("VOTE_CAST", target)
            elif event.key in [pygame.K_ESCAPE, pygame.K_z]:
                self.toggle()
            return True
        return False
