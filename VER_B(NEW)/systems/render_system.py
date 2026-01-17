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
    # [CharacterRenderer Constants]
    RECT_BODY = pygame.Rect(4, 4, 24, 24)
    RECT_CLOTH = pygame.Rect(4, 14, 24, 14)
    RECT_ARM_L = pygame.Rect(8, 14, 4, 14)
    RECT_ARM_R = pygame.Rect(20, 14, 4, 14)
    RECT_HAT_TOP = pygame.Rect(2, 2, 28, 5)
    RECT_HAT_RIM = pygame.Rect(6, 0, 20, 7)

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
        
        # Sprite & Text Cache
        self._sprite_cache = {}
        self._name_surface_cache = {}
        self.font_name = pygame.font.SysFont("arial", 11, bold=True)
        self.font_popup = pygame.font.SysFont("arial", 12, bold=True)
        
        # Current Lighting State
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
        pass

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
        
        # Calculate Vibration Offset (Shiver)
        now = pygame.time.get_ticks()
        vib_x, vib_y = 0, 0
        if status.shiver_timer > now:
            # Simple random shake if timer active
            import random
            intensity = 2
            vib_x = random.randint(-intensity, intensity)
            vib_y = random.randint(-intensity, intensity)

        # Culling
        dx = trans.x - self.camera.x + vib_x
        dy = trans.y - self.camera.y + vib_y
        if not (-50 < dx < self.last_size[0] + 50 and -50 < dy < self.last_size[1] + 50): return
        
        # Visibility Check (Hiding)
        alpha = 255
        is_highlighted = (viewer_role == "MAFIA" and device_on)
        
        if status.is_hiding and not is_highlighted:
            if ident.is_player or viewer_role == "SPECTATOR": alpha = 120
            else: return
            
        cache_key = (
            ident.role, ident.sub_role, 
            sprite.custom_data['skin'], sprite.custom_data['clothes'], sprite.custom_data['hat'],
            anim.facing_dir, is_highlighted, phase
        )
        
        if cache_key in self._sprite_cache:
            base_surf = self._sprite_cache[cache_key]
        else:
            base_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            
            skin_idx = sprite.custom_data['skin']
            cloth_idx = sprite.custom_data['clothes']
            body_col = CUSTOM_COLORS['SKIN'][skin_idx % len(CUSTOM_COLORS['SKIN'])]
            cloth_col = CUSTOM_COLORS['CLOTHES'][cloth_idx % len(CUSTOM_COLORS['CLOTHES'])]
            
            if is_highlighted: body_col, cloth_col = (255, 50, 50), (150, 0, 0)
            
            # Shadow
            pygame.draw.ellipse(base_surf, (0, 0, 0, 80), (4, TILE_SIZE - 8, TILE_SIZE - 8, 6))
            # Body
            pygame.draw.rect(base_surf, body_col, self.RECT_BODY, border_radius=6)
            
            # Role Specific Clothing
            if ident.role == "MAFIA":
                if phase == "NIGHT":
                    pygame.draw.rect(base_surf, (30, 30, 35), self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                    pygame.draw.polygon(base_surf, (180, 0, 0), [(16, 14), (13, 22), (19, 22)]) # Tie
                else:
                    fake_col = cloth_col
                    if ident.sub_role == "POLICE": fake_col = (20, 40, 120)
                    elif ident.sub_role == "DOCTOR": fake_col = (240, 240, 250)
                    
                    pygame.draw.rect(base_surf, fake_col, self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                    if ident.sub_role == "FARMER":
                        pygame.draw.rect(base_surf, (120, 80, 40), self.RECT_ARM_L)
                        pygame.draw.rect(base_surf, (120, 80, 40), self.RECT_ARM_R)
                        
            elif ident.role == "DOCTOR":
                pygame.draw.rect(base_surf, (240, 240, 250), self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                pygame.draw.rect(base_surf, (255, 50, 50), (14, 16, 4, 10)) # Cross V
                pygame.draw.rect(base_surf, (255, 50, 50), (11, 19, 10, 4)) # Cross H
                
            elif ident.role == "POLICE":
                pygame.draw.rect(base_surf, (20, 40, 120), self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                pygame.draw.circle(base_surf, (255, 215, 0), (10, 18), 3) # Badge
                
            else: # CITIZEN
                pygame.draw.rect(base_surf, cloth_col, self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                if ident.sub_role == "FARMER":
                    pygame.draw.rect(base_surf, (120, 80, 40), self.RECT_ARM_L)
                    pygame.draw.rect(base_surf, (120, 80, 40), self.RECT_ARM_R)

            # Eyes
            fx, fy = anim.facing_dir
            ox, oy = fx * 3, fy * 2
            pygame.draw.circle(base_surf, (255, 255, 255), (11 + ox, 12 + oy), 4)
            pygame.draw.circle(base_surf, (255, 255, 255), (21 + ox, 12 + oy), 4)
            pygame.draw.circle(base_surf, (0, 0, 0), (11 + ox + fx, 12 + oy + fy), 2)
            pygame.draw.circle(base_surf, (0, 0, 0), (21 + ox + fx, 12 + oy + fy), 2)
            
            # Hat
            hat_idx = sprite.custom_data.get('hat', 0) % len(CUSTOM_COLORS['HAT'])
            if hat_idx > 0:
                hat_col = CUSTOM_COLORS['HAT'][hat_idx]
                pygame.draw.rect(base_surf, hat_col, self.RECT_HAT_TOP)
                pygame.draw.rect(base_surf, hat_col, self.RECT_HAT_RIM)
            
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
        
        name_surf = self.font_name.render(ident.name, True, name_col)
        self.canvas.blit(name_surf, (dx + 16 - name_surf.get_width()//2, dy - 15))
        
        # Popups
        if hasattr(entity, 'popups'): # Duck typing for now, ideally component
            # But popups are not in ECS components list yet? 
            # Wait, EntityFactory didn't add a 'Popup' component.
            # Popups are transient. Let's check where they are stored.
            # In OLD, they were in entity.popups list.
            # In NEW, we should probably add a visual component or handle it here via a temporary list in RenderSystem?
            # Or better, we can read them from a transient list in 'StatusEffects' or 'InteractionState'?
            # Actually, InteractionSystem sends 'SHOW_POPUP' event to UI.
            # But overhead text (damage, etc) should be here.
            # Let's check where OLD stored popups. Entity.popups list.
            # NEW doesn't have it on Entity. 
            pass

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
