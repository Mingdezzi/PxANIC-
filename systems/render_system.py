import pygame
import math
from core.ecs_manager import ECSManager
from core.resource_manager import ResourceManager
from components.common import Transform, Sprite, Velocity, Animation
from components.identity import Identity
from components.status import StatusEffects
from components.interaction import Inventory, InteractionState
from world.map_manager import MapManager
from world.tiles import get_texture, WORK_SEQ
from settings import TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, PHASE_SETTINGS
from colors import CUSTOM_COLORS
from systems.fov import FOV

class RenderSystem:
    def __init__(self, ecs: ECSManager, map_manager: MapManager, camera):
        self.ecs = ecs
        self.map_manager = map_manager
        self.camera = camera
        self.resource_manager = ResourceManager.get_instance()
        self.fov = FOV(map_manager.width, map_manager.height, map_manager)
        
        # Caching
        self.canvas = None
        self.last_size = (0, 0)
        self.dark_surface = None
        self.light_mask = None
        self.gradient_halo = self._create_smooth_gradient(1000)
        
        # Sprite Cache
        self._sprite_cache = {}
        
        # Current Lighting State (TimeSystem에서 주입받거나 GameState 참조)
        self.ambient_alpha = 0
        self.vision_factor = 1.0
        self.clarity = 255

    def _create_smooth_gradient(self, radius):
        s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            alpha = int(255 * (1 - (r/radius)**2))
            pygame.draw.circle(s, (255, 255, 255, alpha), (radius, radius), r)
        return s

    def update(self, dt):
        pass # 렌더링은 draw 호출 시 수행

    def draw(self, screen, current_phase="DAY", is_blackout=False):
        vw, vh = int(self.camera.width / self.camera.zoom_level), int(self.camera.height / self.camera.zoom_level)
        
        if self.canvas is None or self.last_size != (vw, vh):
            self.canvas = pygame.Surface((vw, vh))
            self.dark_surface = pygame.Surface((vw, vh), pygame.SRCALPHA)
            self.light_mask = pygame.Surface((vw, vh), pygame.SRCALPHA)
            self.last_size = (vw, vh)
            
        self.canvas.fill((10, 10, 12)) # BG Color
        
        # 1. Map Rendering (Culling)
        self._draw_map()
        
        # 2. Entity Rendering
        # Local Player Role/Device 상태 필요
        player_ent = [e for e in self.ecs.get_entities_with(Identity) if self.ecs.get_component(e, Identity).is_player]
        player_id = player_ent[0] if player_ent else None
        player_role = "SPECTATOR"
        device_on = False
        
        if player_id is not None:
            ident = self.ecs.get_component(player_id, Identity)
            player_role = ident.role
            inv = self.ecs.get_component(player_id, Inventory)
            if inv: device_on = inv.device_on
            
        # Draw NPCs
        npcs = self.ecs.get_entities_with(Transform, Sprite, StatusEffects)
        for ent in npcs:
            if ent == player_id: continue
            self._draw_entity(ent, player_role, current_phase, device_on)
            
        # Draw Player
        if player_id is not None:
            self._draw_entity(player_id, player_role, current_phase, device_on)
            
        # 3. Lighting & FOV
        if player_role != "SPECTATOR" and player_id is not None:
            self._draw_lighting(player_id, current_phase, is_blackout)
            
        # 4. Off-screen Pins
        if player_id is not None:
            self._draw_pins(player_id)
            
        # Final Blit
        screen.blit(pygame.transform.scale(self.canvas, (self.camera.width, self.camera.height)), (0, 0))

    def _draw_map(self):
        cam_x, cam_y = self.camera.x, self.camera.y
        vw, vh = self.last_size
        
        start_col = max(0, int(cam_x // TILE_SIZE))
        start_row = max(0, int(cam_y // TILE_SIZE))
        end_col = min(self.map_manager.width, int((cam_x + vw) // TILE_SIZE) + 2)
        end_row = min(self.map_manager.height, int((cam_y + vh) // TILE_SIZE) + 2)
        
        floors = self.map_manager.map_data['floor']
        walls = self.map_manager.map_data['wall']
        objects = self.map_manager.map_data['object']
        
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                dx = c * TILE_SIZE - cam_x
                dy = r * TILE_SIZE - cam_y
                
                # Floor
                tid = floors[r][c][0]
                if tid != 0: 
                    img = get_texture(tid)
                    self.canvas.blit(img, (dx, dy))
                # Wall
                tid = walls[r][c][0]
                if tid != 0:
                    img = get_texture(tid)
                    self.canvas.blit(img, (dx, dy))
                # Object
                tid = objects[r][c][0]
                if tid != 0:
                    img = get_texture(tid)
                    self.canvas.blit(img, (dx, dy))

    def _draw_entity(self, entity, viewer_role, phase, device_on):
        trans = self.ecs.get_component(entity, Transform)
        sprite = self.ecs.get_component(entity, Sprite)
        anim = self.ecs.get_component(entity, Animation)
        status = self.ecs.get_component(entity, StatusEffects)
        ident = self.ecs.get_component(entity, Identity)
        
        # Culling
        dx = trans.x - self.camera.x
        dy = trans.y - self.camera.y
        if not (-50 < dx < self.last_size[0] + 50 and -50 < dy < self.last_size[1] + 50): return
        
        # Visibility Check (Hiding)
        alpha = 255
        is_highlighted = (viewer_role == "MAFIA" and device_on)
        
        if status.is_hiding and not is_highlighted:
            if ident.is_player or viewer_role == "SPECTATOR": alpha = 120
            else: return
            
        # Draw Sprite (Simple Rect for now, can be replaced with cached surface)
        # 캐싱 키: (role, sub_role, skin, clothes, hat, facing, highlighted, phase)
        # Phase는 마피아 변장 때문에 필요
        cache_key = (
            ident.role, ident.sub_role, 
            sprite.custom_data['skin'], sprite.custom_data['clothes'], sprite.custom_data['hat'],
            anim.facing_dir, is_highlighted, phase
        )
        
        if cache_key in self._sprite_cache:
            base_surf = self._sprite_cache[cache_key]
        else:
            base_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            
            # Body Color
            skin_idx = sprite.custom_data['skin']
            cloth_idx = sprite.custom_data['clothes']
            body_col = CUSTOM_COLORS['SKIN'][skin_idx % len(CUSTOM_COLORS['SKIN'])]
            cloth_col = CUSTOM_COLORS['CLOTHES'][cloth_idx % len(CUSTOM_COLORS['CLOTHES'])]
            
            if is_highlighted: body_col, cloth_col = (255, 50, 50), (150, 0, 0)
            
            # Mafia Night Disguise
            if ident.role == "MAFIA" and phase == "NIGHT":
                cloth_col = (30, 30, 35) # Black suit
            
            pygame.draw.rect(base_surf, body_col, (4, 4, 24, 24), border_radius=6)
            pygame.draw.rect(base_surf, cloth_col, (4, 14, 24, 14), border_bottom_left_radius=6, border_bottom_right_radius=6)
            
            # Eyes
            fx, fy = anim.facing_dir
            ox, oy = fx * 3, fy * 2
            
            # Eye White
            pygame.draw.circle(base_surf, (255, 255, 255), (11 + ox, 12 + oy), 4)
            pygame.draw.circle(base_surf, (255, 255, 255), (21 + ox, 12 + oy), 4)
            
            # Pupil (Black)
            pygame.draw.circle(base_surf, (0, 0, 0), (11 + ox + fx, 12 + oy + fy), 2)
            pygame.draw.circle(base_surf, (0, 0, 0), (21 + ox + fx, 12 + oy + fy), 2)
            
            self._sprite_cache[cache_key] = base_surf
            
        final_surf = base_surf
        if alpha < 255:
            final_surf = base_surf.copy()
            final_surf.set_alpha(alpha)
            
        self.canvas.blit(final_surf, (dx, dy))
        
        # Name Tag
        name_col = (200, 200, 200)
        if ident.role == "MAFIA" and viewer_role in ["MAFIA", "SPECTATOR"]: name_col = (255, 100, 100)
        elif ident.role == "POLICE" and viewer_role in ["POLICE", "SPECTATOR"]: name_col = (100, 100, 255)
        
        font = self.resource_manager.get_font('small')
        name_surf = font.render(ident.name, True, name_col)
        self.canvas.blit(name_surf, (dx + 16 - name_surf.get_width()//2, dy - 15))

    def _draw_lighting(self, player_id, phase, is_blackout):
        final_alpha = 250 if is_blackout else int(self.ambient_alpha)
        self.dark_surface.fill((5, 5, 10, final_alpha))
        
        if not (phase == 'DAWN' and self.ecs.get_component(player_id, Identity).role != "MAFIA"):
            self.light_mask.fill((0, 0, 0, 0))
            
            # FOV Polygon
            trans = self.ecs.get_component(player_id, Transform)
            anim = self.ecs.get_component(player_id, Animation)
            inv = self.ecs.get_component(player_id, Inventory)
            
            radius = 12.0 * self.vision_factor # Simplified, needs Player.get_vision_radius logic
            direction = None
            if inv.flashlight_on: direction = anim.facing_dir
            
            poly_points = self.fov.get_poly_points(trans.x + 16, trans.y + 16, radius, direction)
            
            # Convert to relative
            rel_points = [(p[0] - self.camera.x, p[1] - self.camera.y) for p in poly_points]
            
            if len(rel_points) > 2:
                pygame.draw.polygon(self.light_mask, (255, 255, 255, int(self.clarity)), rel_points)
                
            # Gradient Halo
            r_px = int(radius * TILE_SIZE * 1.2)
            halo = pygame.transform.scale(self.gradient_halo, (r_px*2, r_px*2))
            self.light_mask.blit(halo, (trans.x - self.camera.x + 16 - r_px, trans.y - self.camera.y + 16 - r_px), special_flags=pygame.BLEND_RGBA_MULT)
            
            self.dark_surface.blit(self.light_mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
            
        self.canvas.blit(self.dark_surface, (0, 0))

    def _draw_pins(self, player_id):
        # 오프스크린 핀
        ident = self.ecs.get_component(player_id, Identity)
        inter = self.ecs.get_component(player_id, InteractionState)
        
        job_key = ident.role if ident.role == "DOCTOR" else ident.sub_role
        if job_key in WORK_SEQ:
            target_tid = WORK_SEQ[job_key][inter.work_step % 3]
            # MapManager tile_cache 사용해야 함 (여기서는 생략, 이전 PlayState 로직 참조)
            pass 
