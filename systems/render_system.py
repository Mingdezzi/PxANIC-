import pygame
import math
from settings import TILE_SIZE, WORK_SEQ
from world.tiles import get_texture
from colors import CUSTOM_COLORS
from core.resource_manager import ResourceManager
from .fov import FOV 

class RenderSystem:
    _sprite_cache = {}
    _name_surface_cache = {}
    
    RECT_BODY = pygame.Rect(4, 4, 24, 24)
    RECT_CLOTH = pygame.Rect(4, 14, 24, 14)
    RECT_ARM_L = pygame.Rect(8, 14, 4, 14)
    RECT_ARM_R = pygame.Rect(20, 14, 4, 14)
    RECT_HAT_TOP = pygame.Rect(2, 2, 28, 5)
    RECT_HAT_RIM = pygame.Rect(6, 0, 20, 7)

    def __init__(self, map_manager):
        self.resource_manager = ResourceManager.get_instance()
        self.map_manager = map_manager
        self.fov = FOV(map_manager.width, map_manager.height, map_manager)
        self.font_name = self.resource_manager.get_font('arial', 11)
        self.gradient_halo = self._create_smooth_gradient(500)
        self.tile_alphas = {} 

    def _create_smooth_gradient(self, radius):
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            ratio = r / radius
            alpha = int(255 * (1 - ratio * ratio))
            pygame.draw.circle(surf, (255, 255, 255, alpha), (radius, radius), r)
        return surf

    def draw(self, screen, camera, entities, map_manager, current_phase, viewer_entity=None):
        self._draw_map(screen, camera, map_manager)
        
        visible_entities = []
        screen_rect = pygame.Rect(camera.x - 50, camera.y - 50, camera.width + 100, camera.height + 100)
        
        viewer_role = viewer_entity.role.main_role if viewer_entity else "SPECTATOR"
        viewer_device = viewer_entity.graphics.device_on if viewer_entity else False

        visible_tiles = set()
        vision_radius = 0
        
        if viewer_entity and viewer_role != "SPECTATOR":
            vision_radius = self._get_vision_radius(viewer_entity, current_phase)
            direction = viewer_entity.transform.facing if viewer_role == "POLICE" and viewer_entity.graphics.flashlight_on else None
            visible_tiles = self.fov.cast_rays(viewer_entity.transform.x + 16, viewer_entity.transform.y + 16, vision_radius, direction)
            
            fade_speed = 15
            for tile in visible_tiles:
                curr = self.tile_alphas.get(tile, 0)
                if curr < 255: self.tile_alphas[tile] = min(255, curr + fade_speed)
            
            for tile in list(self.tile_alphas.keys()):
                if tile not in visible_tiles:
                    self.tile_alphas[tile] -= fade_speed
                    if self.tile_alphas[tile] <= 0:
                        del self.tile_alphas[tile]

        for entity in entities:
            if not hasattr(entity, 'transform') or not hasattr(entity, 'graphics'): continue
            if not entity.transform.rect.colliderect(screen_rect): continue
            
            if viewer_role != "SPECTATOR":
                gx, gy = int(entity.transform.x // TILE_SIZE), int(entity.transform.y // TILE_SIZE)
                if (gx, gy) not in visible_tiles and entity != viewer_entity: continue

            visible_entities.append(entity)
        
        visible_entities.sort(key=lambda e: e.transform.y)
        
        for entity in visible_entities:
            # [수정] 떨림 효과 반영
            offset_x, offset_y = entity.graphics.vibration_offset
            draw_x = entity.transform.x + offset_x
            draw_y = entity.transform.y + offset_y
            
            self._draw_entity_at(screen, entity, draw_x, draw_y, camera.x, camera.y, viewer_role, current_phase, viewer_device)

        if viewer_entity and viewer_role != "SPECTATOR":
            self._draw_lighting(screen, camera, current_phase, viewer_entity, vision_radius)
            
            if viewer_entity.graphics.is_eyes_closed:
                black_surf = pygame.Surface((camera.width, camera.height))
                black_surf.fill((0, 0, 0))
                screen.blit(black_surf, (0, 0))

        if viewer_entity:
            self._draw_offscreen_pins(screen, camera, viewer_entity)

    def _draw_entity_at(self, screen, entity, x, y, cx, cy, viewer_role, current_phase, viewer_device_on):
        if hasattr(entity, 'stats') and not entity.stats.alive:
            draw_rect = pygame.Rect(x - cx, y - cy, 24, 24)
            pygame.draw.rect(screen, (50, 50, 50), draw_rect)
            return

        alpha = 255
        is_highlighted = (viewer_role == "MAFIA" and viewer_device_on)
        
        if entity.graphics.is_hiding and not is_highlighted:
            is_visible = False
            if viewer_role == "SPECTATOR": is_visible, alpha = True, 120
            elif getattr(entity, 'name', '') == "Player": is_visible, alpha = True, 120 # 본인은 보임
            
            if not is_visible: return

        skin = entity.role.skin_idx; cloth = entity.role.clothes_idx; hat = entity.role.hat_idx
        role = entity.role.main_role; sub_role = entity.role.sub_role; facing = entity.transform.facing
        cache_key = (skin, cloth, hat, role, sub_role, facing, is_highlighted, current_phase)
        
        if cache_key in self._sprite_cache: 
            base_surf = self._sprite_cache[cache_key]
        else: 
            base_surf = self._create_entity_surface(entity, is_highlighted, current_phase)
            self._sprite_cache[cache_key] = base_surf
            
        final_surf = base_surf
        if alpha < 255: 
            final_surf = base_surf.copy()
            final_surf.set_alpha(alpha)
            
        screen.blit(final_surf, (x - cx, y - cy))
        self._draw_name(screen, entity, x - cx, y - cy, viewer_role)

    def _create_entity_surface(self, entity, is_highlighted, current_phase):
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        skin_idx = entity.role.skin_idx % len(CUSTOM_COLORS['SKIN'])
        cloth_idx = entity.role.clothes_idx % len(CUSTOM_COLORS['CLOTHES'])
        body_color = CUSTOM_COLORS['SKIN'][skin_idx]
        clothes_color = CUSTOM_COLORS['CLOTHES'][cloth_idx]
        
        if is_highlighted: 
            body_color = (255, 50, 50)
            clothes_color = (150, 0, 0)
            
        pygame.draw.ellipse(surf, (0, 0, 0, 80), (4, TILE_SIZE - 8, TILE_SIZE - 8, 6))
        pygame.draw.rect(surf, body_color, self.RECT_BODY, border_radius=6)
        
        role = entity.role.main_role
        sub_role = entity.role.sub_role
        
        if role == "MAFIA":
            if current_phase == "NIGHT":
                 pygame.draw.rect(surf, (30, 30, 35), self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                 pygame.draw.polygon(surf, (180, 0, 0), [(16, 14), (13, 22), (19, 22)])
            else:
                fake_color = clothes_color
                if sub_role == "POLICE": fake_color = (20, 40, 120)
                elif sub_role == "DOCTOR": fake_color = (240, 240, 250)
                pygame.draw.rect(surf, fake_color, self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                if sub_role == "FARMER": 
                    pygame.draw.rect(surf, (120, 80, 40), self.RECT_ARM_L)
                    pygame.draw.rect(surf, (120, 80, 40), self.RECT_ARM_R)
        elif role == "DOCTOR":
            pygame.draw.rect(surf, (240, 240, 250), self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
            pygame.draw.rect(surf, (255, 50, 50), (14, 16, 4, 10))
            pygame.draw.rect(surf, (255, 50, 50), (11, 19, 10, 4))
        elif role == "POLICE":
            pygame.draw.rect(surf, (20, 40, 120), self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
            pygame.draw.circle(surf, (255, 215, 0), (10, 18), 3)
        else:
            pygame.draw.rect(surf, clothes_color, self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
            if sub_role == "FARMER": 
                pygame.draw.rect(surf, (120, 80, 40), self.RECT_ARM_L)
                pygame.draw.rect(surf, (120, 80, 40), self.RECT_ARM_R)

        f_dir = entity.transform.facing
        ox, oy = f_dir[0] * 3, f_dir[1] * 2
        pygame.draw.circle(surf, (255, 255, 255), (16 - 5 + ox, 12 + oy), 3)
        pygame.draw.circle(surf, (0, 0, 0), (16 - 5 + ox + f_dir[0], 12 + oy + f_dir[1]), 1)
        pygame.draw.circle(surf, (255, 255, 255), (16 + 5 + ox, 12 + oy), 3)
        pygame.draw.circle(surf, (0, 0, 0), (16 + 5 + ox + f_dir[0], 12 + oy + f_dir[1]), 1)
        
        hat_idx = entity.role.hat_idx % len(CUSTOM_COLORS['HAT'])
        if hat_idx > 0:
            hat_color = CUSTOM_COLORS['HAT'][hat_idx]
            pygame.draw.rect(surf, hat_color, self.RECT_HAT_TOP)
            pygame.draw.rect(surf, hat_color, self.RECT_HAT_RIM)
            
        return surf

    def _draw_name(self, screen, entity, dx, dy, viewer_role):
        name = getattr(entity, 'name', 'Unknown')
        name_color = (230, 230, 230)
        
        if entity.role.main_role == "POLICE" and viewer_role in ["POLICE", "SPECTATOR"]:
            name_color = (100, 180, 255)
        elif entity.role.main_role == "MAFIA" and viewer_role in ["MAFIA", "SPECTATOR"]:
            name_color = (255, 100, 100)
            
        key = (id(entity), name, name_color)
        if key in self._name_surface_cache:
            name_surf = self._name_surface_cache[key]
        else:
            name_surf = self.font_name.render(name, True, name_color)
            self._name_surface_cache[key] = name_surf
            
        text_x = dx + (TILE_SIZE // 2) - (name_surf.get_width() // 2)
        screen.blit(name_surf, (text_x, dy - 14))

    def _get_vision_radius(self, entity, phase):
        base = 8 
        if phase in ['MORNING', 'DAY', 'NOON', 'AFTERNOON']: base = 14
        else:
            if entity.role.main_role == "MAFIA": base = 10
            elif entity.role.main_role == "POLICE" and entity.graphics.flashlight_on: base = 12
            else: base = 6
            if phase == 'DAWN' and entity.role.main_role != "MAFIA": base = 0
        
        if 'FATIGUE' in entity.stats.emotions:
            base = max(1.0, base - entity.stats.emotions['FATIGUE'] * 0.5)
        return base

    def _draw_lighting(self, screen, camera, phase, player, radius_tiles):
        ambient_alpha = 0
        if phase == 'EVENING': ambient_alpha = 100
        elif phase in ['NIGHT', 'DAWN']: ambient_alpha = 230
        
        if ambient_alpha <= 0: return

        dark_surface = pygame.Surface((camera.width, camera.height), pygame.SRCALPHA)
        dark_surface.fill((5, 5, 10, ambient_alpha))
        
        light_mask = pygame.Surface((camera.width, camera.height), pygame.SRCALPHA)
        light_mask.fill((0, 0, 0, 0))

        direction = None
        if player.role.main_role == "POLICE" and player.graphics.flashlight_on:
            direction = player.transform.facing

        poly_points = self.fov.get_poly_points(player.transform.x+16, player.transform.y+16, radius_tiles, direction, 60)
        rel_points = [(p[0]-camera.x, p[1]-camera.y) for p in poly_points]
        
        if len(rel_points) > 2:
            pygame.draw.polygon(light_mask, (255, 255, 255, 255), rel_points)
            radius_px = int(radius_tiles * TILE_SIZE * 1.2)
            halo = pygame.transform.scale(self.gradient_halo, (radius_px * 2, radius_px * 2))
            light_mask.blit(halo, ((player.transform.x+16)-camera.x-radius_px, (player.transform.y+16)-camera.y-radius_px), special_flags=pygame.BLEND_RGBA_MULT)

        dark_surface.blit(light_mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(dark_surface, (0, 0))

    def _draw_map(self, screen, camera, map_manager):
        vw, vh = camera.width, camera.height
        cam_x, cam_y = camera.x, camera.y
        start_col = int(max(0, cam_x // TILE_SIZE)); start_row = int(max(0, cam_y // TILE_SIZE))
        end_col = int(min(map_manager.width, (cam_x + vw) // TILE_SIZE + 2)); end_row = int(min(map_manager.height, (cam_y + vh) // TILE_SIZE + 2))
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                draw_x = c * TILE_SIZE - cam_x; draw_y = r * TILE_SIZE - cam_y
                for layer in [map_manager.map_data['floor'], map_manager.map_data['wall'], map_manager.map_data['object']]:
                    tile_data = layer[r][c]; tid = tile_data[0]; rot = tile_data[1] if len(tile_data) > 1 else 0
                    if tid != 0:
                        img = get_texture(tid, rot)
                        if img: screen.blit(img, (draw_x, draw_y))

    def _draw_offscreen_pins(self, screen, camera, player):
        job = player.role.sub_role if player.role.sub_role else player.role.main_role
        if job not in WORK_SEQ: return
        step = player.role.work_step % 3
        target_tid = WORK_SEQ[job][step]
        target_pixels = self.map_manager.tile_cache.get(target_tid, [])
        if not target_pixels: return
        screen_rect = pygame.Rect(camera.x, camera.y, camera.width, camera.height)
        for (tx, ty) in target_pixels:
            if screen_rect.collidepoint(tx, ty):
                pygame.draw.rect(screen, (255, 255, 0), (tx - camera.x, ty - camera.y, TILE_SIZE, TILE_SIZE), 2); return 
        target_x, target_y = target_pixels[0]
        center_x, center_y = camera.x + camera.width / 2, camera.y + camera.height / 2
        dx = target_x - center_x; dy = target_y - center_y
        if dx == 0 and dy == 0: return
        margin = 30; half_w = camera.width / 2 - margin; half_h = camera.height / 2 - margin
        scale = min(abs(half_w / dx) if dx != 0 else float('inf'), abs(half_h / dy) if dy != 0 else float('inf'))
        pin_x = camera.width / 2 + dx * scale; pin_y = camera.height / 2 + dy * scale
        pygame.draw.circle(screen, (255, 215, 0), (int(pin_x), int(pin_y)), 8)
        pygame.draw.circle(screen, (255, 255, 255), (int(pin_x), int(pin_y)), 10, 2)