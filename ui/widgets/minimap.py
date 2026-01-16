import pygame
from settings import TILE_SIZE

MINIMAP_COLORS = {
    1110000: (100, 80, 50),    # Dirt
    1110001: (34, 139, 34),    # Grass
    1110002: (100, 100, 100),  # Stone
    3220000: (50, 50, 50),     # Wall
    5310000: (0, 0, 255),      # Water/Object
    8321006: (255, 0, 0),      # Vending Machine
}

DEFAULT_COLORS = {
    'floor': (40, 40, 40),
    'wall': (100, 100, 100),
    'object': (200, 200, 100)
}

class MinimapWidget:
    def __init__(self, map_manager):
        self.map_manager = map_manager
        self.minimap_surface = None
        self.cached_scaled = None
        self.last_update_time = 0

    def generate_surface(self):
        w = self.map_manager.width
        h = self.map_manager.height
        surf = pygame.Surface((w, h))
        surf.fill((20, 20, 25))

        floors = self.map_manager.map_data['floor']
        walls = self.map_manager.map_data['wall']
        objects = self.map_manager.map_data['object']
        
        pixels = pygame.PixelArray(surf)

        for y in range(h):
            for x in range(w):
                # Floor
                f_val = floors[y][x]
                f_tid = f_val[0] if isinstance(f_val, (tuple, list)) else f_val
                if f_tid != 0:
                    pixels[x, y] = MINIMAP_COLORS.get(f_tid, DEFAULT_COLORS['floor'])
                
                # Wall
                w_val = walls[y][x]
                w_tid = w_val[0] if isinstance(w_val, (tuple, list)) else w_val
                if w_tid != 0:
                    pixels[x, y] = MINIMAP_COLORS.get(w_tid, DEFAULT_COLORS['wall'])
                
                # Object
                o_val = objects[y][x]
                o_tid = o_val[0] if isinstance(o_val, (tuple, list)) else o_val
                if o_tid != 0:
                    pixels[x, y] = MINIMAP_COLORS.get(o_tid, DEFAULT_COLORS['object'])
        
        pixels.close()
        self.cached_scaled = None
        return surf

    def draw(self, screen, w, h, player, npcs):
        mm_w, mm_h = 200, 150
        x = w - mm_w - 20
        y = h - 140 - 20 - mm_h - 10
        
        rect = pygame.Rect(x, y, mm_w, mm_h)
        
        # 배경
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        screen.blit(s, rect.topleft)
        pygame.draw.rect(screen, (100, 100, 120), rect, 2)
        
        if self.minimap_surface is None:
            self.minimap_surface = self.generate_surface()
            
        if self.cached_scaled is None:
            self.cached_scaled = pygame.transform.scale(self.minimap_surface, (mm_w - 4, mm_h - 4))
            
        screen.blit(self.cached_scaled, (rect.x + 2, rect.y + 2))
        
        # 플레이어 위치
        map_w_px = self.map_manager.width * TILE_SIZE
        map_h_px = self.map_manager.height * TILE_SIZE
        
        if map_w_px > 0:
            px = (player.transform.x + player.transform.width/2) / map_w_px
            py = (player.transform.y + player.transform.height/2) / map_h_px
            
            dot_x = rect.x + 2 + px * (mm_w - 4)
            dot_y = rect.y + 2 + py * (mm_h - 4)
            pygame.draw.circle(screen, (0, 255, 0), (int(dot_x), int(dot_y)), 3)
            
            # 동체 탐지기 등 레이더 표시 (간략화)
            if player.graphics.device_on:
                for n in npcs:
                    if not n.stats.alive: continue
                    nx = (n.transform.x + n.transform.width/2) / map_w_px
                    ny = (n.transform.y + n.transform.height/2) / map_h_px
                    
                    dot_nx = rect.x + 2 + nx * (mm_w - 4)
                    dot_ny = rect.y + 2 + ny * (mm_h - 4)
                    pygame.draw.circle(screen, (0, 200, 0), (int(dot_nx), int(dot_ny)), 2)
