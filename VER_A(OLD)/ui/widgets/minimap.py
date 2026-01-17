import pygame
from ui.widgets.base import UIWidget
from settings import TILE_SIZE
from world.tiles import TILE_DATA

# 기본 색상 (TILE_DATA에 없는 경우 대비)
DEFAULT_COLORS = {'floor': (40, 40, 40), 'wall': (100, 100, 100), 'object': (200, 200, 100)}

class MinimapWidget(UIWidget):
    def __init__(self, game):
        super().__init__(game)
        self.minimap_surface = None
        self.cached_minimap = None
        self.radar_timer = 0
        self.radar_blips = []
        self.rect = pygame.Rect(0, 0, 0, 0) # [Added] To detect clicks

    def _generate_surface(self):
        w, h = self.game.map_manager.width, self.game.map_manager.height
        surf = pygame.Surface((w, h))
        surf.fill((20, 20, 25))
        pixels = pygame.PixelArray(surf)
        
        floors = self.game.map_manager.map_data['floor']
        walls = self.game.map_manager.map_data['wall']
        objects = self.game.map_manager.map_data['object']

        for y in range(h):
            for x in range(w):
                # 우선순위: Object > Wall > Floor
                color = None
                
                # 1. Object
                o_val = objects[y][x]
                o_tid = o_val[0] if isinstance(o_val, (tuple, list)) else o_val
                if o_tid != 0 and o_tid in TILE_DATA:
                    color = TILE_DATA[o_tid].get('color')
                
                # 2. Wall (If no object or object has no color)
                if color is None:
                    w_val = walls[y][x]
                    w_tid = w_val[0] if isinstance(w_val, (tuple, list)) else w_val
                    if w_tid != 0 and w_tid in TILE_DATA:
                        color = TILE_DATA[w_tid].get('color')
                
                # 3. Floor (If no wall/object)
                if color is None:
                    f_val = floors[y][x]
                    f_tid = f_val[0] if isinstance(f_val, (tuple, list)) else f_val
                    if f_tid != 0 and f_tid in TILE_DATA:
                        color = TILE_DATA[f_tid].get('color')
                
                # Apply Color
                if color:
                    pixels[x, y] = color
                else:
                    # Fallback for empty/unknown
                    pass 

        pixels.close()
        return surf

    def draw(self, screen):
        if self.game.player.role == "SPECTATOR": return

        w, h = screen.get_size()
        mm_w, mm_h = 200, 150
        x = w - mm_w - 20
        y = h - 140 - 20 - mm_h - 10 # Emotion panel height assumed ~140
        
        mm_rect = pygame.Rect(x, y, mm_w, mm_h)
        self.rect = mm_rect # Update for click detection
        
        s = pygame.Surface((mm_rect.width, mm_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        screen.blit(s, mm_rect.topleft)
        pygame.draw.rect(screen, (100, 100, 120), mm_rect, 2)
        
        if not self.minimap_surface:
            self.minimap_surface = self._generate_surface()
            self.cached_minimap = pygame.transform.scale(self.minimap_surface, (mm_w - 4, mm_h - 4))
            
        screen.blit(self.cached_minimap, (mm_rect.x + 2, mm_rect.y + 2))
        
        # Player Dot
        map_w_px = self.game.map_manager.width * TILE_SIZE
        map_h_px = self.game.map_manager.height * TILE_SIZE
        if map_w_px > 0:
            dot_x = mm_rect.x + 2 + (self.game.player.rect.centerx / map_w_px) * (mm_w - 4)
            dot_y = mm_rect.y + 2 + (self.game.player.rect.centery / map_h_px) * (mm_h - 4)
            pygame.draw.circle(screen, (0, 255, 0), (int(dot_x), int(dot_y)), 3)

        # Radar / Special Detection
        self._draw_radar(screen, mm_rect, map_w_px, map_h_px, mm_w, mm_h)

    def _draw_radar(self, screen, mm_rect, map_w, map_h, mm_w, mm_h):
        is_blackout = getattr(self.game, 'is_blackout', False)
        
        if self.game.player.role == "MAFIA" and is_blackout:
            now = pygame.time.get_ticks()
            if now > self.radar_timer:
                self.radar_timer = now + 2000
                self.radar_blips = []
                for n in self.game.npcs:
                    if not n.alive: continue
                    color = (0, 255, 0)
                    if n.role == "POLICE": color = (0, 100, 255)
                    elif n.role == "MAFIA": color = (255, 0, 0)
                    nx = mm_rect.x + 2 + (n.rect.centerx / map_w) * (mm_w - 4)
                    ny = mm_rect.y + 2 + (n.rect.centery / map_h) * (mm_h - 4)
                    self.radar_blips.append(((int(nx), int(ny)), color))
            for pos, col in self.radar_blips: pygame.draw.circle(screen, col, pos, 4)
        
        elif self.game.player.device_on:
            if self.game.player.role == "POLICE" and getattr(self.game, 'mafia_detected_by_cctv', False):
                for n in self.game.npcs:
                    if n.role == "MAFIA" and n.alive:
                        nx = mm_rect.x + 2 + (n.rect.centerx / map_w) * (mm_w - 4)
                        ny = mm_rect.y + 2 + (n.rect.centery / map_h) * (mm_h - 4)
                        if (pygame.time.get_ticks() // 200) % 2 == 0: pygame.draw.circle(screen, (255, 0, 0), (int(nx), int(ny)), 5)
            elif self.game.player.role in ["CITIZEN", "DOCTOR"]:
                 for n in self.game.npcs:
                    if not n.alive: continue
                    import math
                    if math.sqrt((self.game.player.rect.centerx - n.rect.centerx)**2 + (self.game.player.rect.centery - n.rect.centery)**2) < 400 and getattr(n, 'is_moving', False):
                         nx = mm_rect.x + 2 + (n.rect.centerx / map_w) * (mm_w - 4)
                         ny = mm_rect.y + 2 + (n.rect.centery / map_h) * (mm_h - 4)
                         pygame.draw.circle(screen, (0, 255, 0), (int(nx), int(ny)), 3)