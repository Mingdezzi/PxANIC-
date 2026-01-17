import pygame
from settings import *
from colors import *
from world.tiles import get_texture, get_tile_category

class CharacterRenderer:
    _sprite_cache = {}
    
    pygame.font.init()
    NAME_FONT = pygame.font.SysFont("arial", 11, bold=True)
    POPUP_FONT = pygame.font.SysFont("arial", 12, bold=True)

    RECT_BODY = pygame.Rect(4, 4, 24, 24)
    RECT_CLOTH = pygame.Rect(4, 14, 24, 14)
    RECT_ARM_L = pygame.Rect(8, 14, 4, 14)
    RECT_ARM_R = pygame.Rect(20, 14, 4, 14)
    RECT_HAT_TOP = pygame.Rect(2, 2, 28, 5)
    RECT_HAT_RIM = pygame.Rect(6, 0, 20, 7)

    _name_surface_cache = {}

    @classmethod
    def clear_cache(cls):
        cls._sprite_cache.clear()
        cls._name_surface_cache.clear()

    @classmethod
    def _get_cache_key(cls, entity, is_highlighted):
        skin_idx = entity.custom.get('skin', 0)
        cloth_idx = entity.custom.get('clothes', 0)
        hat_idx = entity.custom.get('hat', 0)
        facing = getattr(entity, 'facing_dir', (0, 1))
        return (skin_idx, cloth_idx, hat_idx, entity.role, entity.sub_role, facing, is_highlighted)

    @staticmethod
    def draw_entity(screen, entity, camera_x, camera_y, viewer_role="PLAYER", current_phase="DAY", viewer_device_on=False):
        if not entity.alive: return
        draw_x = entity.rect.x - camera_x
        draw_y = entity.rect.y - camera_y
        screen_w, screen_h = screen.get_width(), screen.get_height()
        if not (-50 < draw_x < screen_w + 50 and -50 < draw_y < screen_h + 50): return

        alpha = 255
        is_highlighted = False
        if viewer_role == "MAFIA" and viewer_device_on:
            is_highlighted = True; alpha = 255 

        if entity.is_hiding and not is_highlighted:
            is_visible = False
            if getattr(entity, 'is_player', False) or entity.name == "Player 1": is_visible, alpha = True, 120
            elif viewer_role == "SPECTATOR": is_visible, alpha = True, 120
            if not is_visible: return

        cache_key = CharacterRenderer._get_cache_key(entity, is_highlighted)
        if cache_key in CharacterRenderer._sprite_cache:
            base_surf = CharacterRenderer._sprite_cache[cache_key]
        else:
            base_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            skin_idx = entity.custom.get('skin', 0) % len(CUSTOM_COLORS['SKIN'])
            cloth_idx = entity.custom.get('clothes', 0) % len(CUSTOM_COLORS['CLOTHES'])
            body_color = CUSTOM_COLORS['SKIN'][skin_idx]
            clothes_color = CUSTOM_COLORS['CLOTHES'][cloth_idx]
            if is_highlighted: body_color = (255, 50, 50); clothes_color = (150, 0, 0)
            pygame.draw.ellipse(base_surf, (0, 0, 0, 80), (4, TILE_SIZE - 8, TILE_SIZE - 8, 6))
            pygame.draw.rect(base_surf, body_color, CharacterRenderer.RECT_BODY, border_radius=6)
            if entity.role == "MAFIA":
                if current_phase == "NIGHT":
                    pygame.draw.rect(base_surf, (30, 30, 35), CharacterRenderer.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                    pygame.draw.polygon(base_surf, (180, 0, 0), [(16, 14), (13, 22), (19, 22)])
                else:
                    fake_color = clothes_color
                    if entity.sub_role == "POLICE": fake_color = (20, 40, 120)
                    elif entity.sub_role == "DOCTOR": fake_color = (240, 240, 250)
                    pygame.draw.rect(base_surf, fake_color, CharacterRenderer.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
            elif entity.role == "DOCTOR":
                pygame.draw.rect(base_surf, (240, 240, 250), CharacterRenderer.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
            elif entity.role == "POLICE":
                pygame.draw.rect(base_surf, (20, 40, 120), CharacterRenderer.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
            else:
                pygame.draw.rect(base_surf, clothes_color, CharacterRenderer.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)

            f_dir = getattr(entity, 'facing_dir', (0, 1))
            ox, oy = f_dir[0] * 3, f_dir[1] * 2
            pygame.draw.circle(base_surf, (255, 255, 255), (16 - 5 + ox, 12 + oy), 3)
            pygame.draw.circle(base_surf, (0, 0, 0), (16 - 5 + ox + f_dir[0], 12 + oy + f_dir[1]), 1)
            pygame.draw.circle(base_surf, (255, 255, 255), (16 + 5 + ox, 12 + oy), 3)
            pygame.draw.circle(base_surf, (0, 0, 0), (16 + 5 + ox + f_dir[0], 12 + oy + f_dir[1]), 1)
            CharacterRenderer._sprite_cache[cache_key] = base_surf

        final_surf = base_surf
        if alpha < 255: final_surf = base_surf.copy(); final_surf.set_alpha(alpha)
        screen.blit(final_surf, (draw_x, draw_y))

        name_color = (230, 230, 230)
        if entity.role == "POLICE" and viewer_role in ["POLICE", "SPECTATOR"]: name_color = (100, 180, 255)
        elif entity.role == "MAFIA" and viewer_role in ["MAFIA", "SPECTATOR"]: name_color = (255, 100, 100)
        text_cache_key = (id(entity), entity.name, name_color)
        if text_cache_key in CharacterRenderer._name_surface_cache: name_surf = CharacterRenderer._name_surface_cache[text_cache_key]
        else: name_surf = CharacterRenderer.NAME_FONT.render(entity.name, True, name_color); CharacterRenderer._name_surface_cache[text_cache_key] = name_surf
        screen.blit(name_surf, (draw_x + (TILE_SIZE // 2) - (name_surf.get_width() // 2), draw_y - 14))

class MapRenderer:
    def __init__(self, map_manager):
        self.map_manager = map_manager

    def draw(self, screen, camera, dt, visible_tiles=None, tile_alphas=None):
        if tile_alphas is None: tile_alphas = {}
        vw, vh = camera.width / camera.zoom_level, camera.height / camera.zoom_level
        
        start_col = int(max(0, camera.x // TILE_SIZE))
        start_row = int(max(0, camera.y // TILE_SIZE))
        end_col = int(min(self.map_manager.width, (camera.x + vw) // TILE_SIZE + 2))
        end_row = int(min(self.map_manager.height, (camera.y + vh) // TILE_SIZE + 2))

        cam_x, cam_y = camera.x, camera.y
        floors = self.map_manager.map_data['floor']
        walls = self.map_manager.map_data['wall']
        objects = self.map_manager.map_data['object']
        zones = self.map_manager.zone_map

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                draw_x = c * TILE_SIZE - cam_x
                draw_y = r * TILE_SIZE - cam_y
                is_indoor = (zones[r][c] in INDOOR_ZONES)
                
                # Smooth Alpha Logic
                draw_alpha = 255
                if is_indoor and visible_tiles is not None:
                    draw_alpha = tile_alphas.get((c, r), 0)

                # (1) 바닥 (Floor)
                if not (is_indoor and draw_alpha <= 0):
                    tile_data = floors[r][c]
                    tid = tile_data[0] if isinstance(tile_data, (tuple, list)) else tile_data
                    rot = tile_data[1] if isinstance(tile_data, (tuple, list)) else 0
                    if tid != 0:
                        img = get_texture(tid, rot)
                        if draw_alpha < 255:
                            img = img.copy(); img.set_alpha(draw_alpha)
                        screen.blit(img, (draw_x, draw_y))

                # (2) 벽 (Wall) - Always visible silhouette
                tile_data = walls[r][c]
                tid = tile_data[0] if isinstance(tile_data, (tuple, list)) else tile_data
                rot = tile_data[1] if isinstance(tile_data, (tuple, list)) else 0
                if tid != 0:
                    img = get_texture(tid, rot); screen.blit(img, (draw_x, draw_y))

                # (3) 오브젝트 (Object)
                tile_data = objects[r][c]
                tid = tile_data[0] if isinstance(tile_data, (tuple, list)) else tile_data
                rot = tile_data[1] if isinstance(tile_data, (tuple, list)) else 0
                if tid != 0:
                    is_door = (get_tile_category(tid) == 5)
                    if not (is_indoor and not is_door and draw_alpha <= 0):
                        img = get_texture(tid, rot)
                        if is_indoor and not is_door and draw_alpha < 255:
                            img = img.copy(); img.set_alpha(draw_alpha)
                        screen.blit(img, (draw_x, draw_y))
