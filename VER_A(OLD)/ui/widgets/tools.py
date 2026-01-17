import pygame
import math
from ui.widgets.base import UIWidget

class SpecialToolsWidget(UIWidget):
    def __init__(self, game):
        super().__init__(game)
        self.scan_angle = 0
        self.scan_dir = 1
        self.scan_speed = 2
        self.police_bg = self.create_panel_bg(200, 120)

    def draw(self, screen):
        p = self.game.player
        if not p.device_on: return
        
        w, h = screen.get_size()
        if p.role in ["CITIZEN", "DOCTOR"]:
            self._draw_motion_tracker(screen, w, h)
        elif p.role == "POLICE":
            self._draw_police_hud(screen, w, h)

    def _draw_motion_tracker(self, screen, w, h):
        cx, cy = 340, h - 150 
        radius = 90
        
        frame_rect = pygame.Rect(cx - 100, cy - 110, 200, 240)
        pygame.draw.rect(screen, (30, 35, 30), frame_rect, border_radius=15)
        pygame.draw.rect(screen, (60, 70, 60), frame_rect, 3, border_radius=15)
        screen_rect = pygame.Rect(cx - 85, cy - 90, 170, 170)
        pygame.draw.rect(screen, (10, 25, 15), screen_rect)
        pygame.draw.rect(screen, (40, 60, 40), screen_rect, 2)

        for r in [30, 60, 90]:
            pygame.draw.circle(screen, (30, 80, 30), (cx, cy + 60), r, 1)

        self.scan_angle += self.scan_dir * self.scan_speed
        if self.scan_angle > 45 or self.scan_angle < -45: self.scan_dir *= -1
            
        scan_rad = math.radians(self.scan_angle - 90)
        ex = cx + math.cos(scan_rad) * radius
        ey = (cy + 60) + math.sin(scan_rad) * radius
        pygame.draw.line(screen, (50, 200, 50), (cx, cy + 60), (ex, ey), 2)

        detect_range = 400
        detect_range_sq = detect_range * detect_range 
        
        targets = []
        for npc in self.game.npcs:
            if not npc.alive: continue
            dist_sq = (self.game.player.rect.centerx - npc.rect.centerx)**2 + (self.game.player.rect.centery - npc.rect.centery)**2
            if dist_sq > detect_range_sq: continue
            
            dx = (npc.rect.centerx - self.game.player.rect.centerx) / detect_range
            dy = (npc.rect.centery - self.game.player.rect.centery) / detect_range
            tx = cx + dx * radius
            ty = (cy + 60) + dy * radius
            
            if screen_rect.collidepoint(tx, ty):
                targets.append((tx, ty))

        for tx, ty in targets:
            pygame.draw.circle(screen, (150, 255, 150), (int(tx), int(ty)), 4)
            s = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(s, (50, 200, 50, 100), (10, 10), 8)
            screen.blit(s, (tx-10, ty-10))

        dist_val = f"{int(detect_range/32)}m"
        lbl = self.font_digit.render(f"RNG: {dist_val}", True, (50, 180, 50))
        screen.blit(lbl, (cx - 30, cy + 90))
        title = self.font_small.render("MOTION TRACKER", True, (150, 150, 150))
        screen.blit(title, (cx - title.get_width()//2, frame_rect.top + 10))

    def _draw_police_hud(self, screen, w, h):
        x, y = 240, h - 200
        screen.blit(self.police_bg, (x, y))
        
        t = self.font_main.render("POLICE TERMINAL", True, (100, 200, 255))
        screen.blit(t, (x + 100 - t.get_width()//2, y + 10))
        bullets = getattr(self.game.player, 'bullets_fired_today', 0)
        t2 = self.font_small.render(f"Shots Fired: {bullets}/1", True, (200, 200, 200))
        screen.blit(t2, (x + 20, y + 50))
