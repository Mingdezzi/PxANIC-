import pygame
import math
from settings import PHASE_SETTINGS, DEFAULT_PHASE_DURATIONS, TILE_SIZE, VISION_RADIUS

class LightingManager:
    def __init__(self, game):
        self.game = game
        self.canvas = None
        self.dark_surface = None
        self.light_mask = None
        self.gradient_halo = None
        self.lamp_halo = None
        self.last_canvas_size = (0, 0)
        self.scale_factor = 0.2
        self.current_ambient_alpha = 0
        self.current_vision_factor = 1.0
        self.current_clarity = 255
        self.gradient_halo = self._create_smooth_gradient(500)
        self.lamp_halo = self._create_smooth_gradient(64, alpha_start=180) 
        self.light_sources = []
        self.sources_loaded = False

    def _create_smooth_gradient(self, radius, alpha_start=255):
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            ratio = r / radius
            alpha = int(alpha_start * (1 - ratio * ratio))
            pygame.draw.circle(surf, (255, 255, 255, alpha), (radius, radius), r)
        return surf

    def init_light_sources(self):
        target_ids = [7310010, 8310016]
        self.light_sources = []
        if self.game.world and self.game.world.map_manager:
            tile_cache = self.game.world.map_manager.tile_cache
            for tid in target_ids:
                if tid in tile_cache:
                    for px, py in tile_cache[tid]:
                        self.light_sources.append((px + TILE_SIZE//2, py + TILE_SIZE//2))
        self.sources_loaded = True

    def update(self, dt):
        if not self.sources_loaded: self.init_light_sources()
        current_phase_key = self.game.current_phase
        phases = self.game.phases
        current_idx = self.game.current_phase_idx
        next_phase_idx = (current_idx + 1) % len(phases)
        next_phase_key = phases[next_phase_idx]
        curr_cfg = PHASE_SETTINGS.get(current_phase_key, PHASE_SETTINGS['NOON'])
        next_cfg = PHASE_SETTINGS.get(next_phase_key, PHASE_SETTINGS['NOON'])
        durations = self.game.game.shared_data.get('custom_durations', DEFAULT_PHASE_DURATIONS)
        total_time = durations.get(current_phase_key, 60)
        progress = 1.0 - (self.game.state_timer / max(total_time, 1))
        progress = max(0.0, min(1.0, progress))
        self.current_ambient_alpha = curr_cfg['alpha'] + (next_cfg['alpha'] - curr_cfg['alpha']) * progress
        self.current_vision_factor = curr_cfg['vision_factor'] + (next_cfg['vision_factor'] - curr_cfg['vision_factor']) * progress
        self.current_clarity = curr_cfg.get('clarity', 255) + (next_cfg.get('clarity', 255) - curr_cfg.get('clarity', 255)) * progress

    def draw(self, screen, camera):
        vw = int(self.game.game.screen_width / self.game.zoom_level)
        vh = int(self.game.game.screen_height / self.game.zoom_level)
        low_w = max(1, int(vw * self.scale_factor)); low_h = max(1, int(vh * self.scale_factor))
        if self.canvas is None or self.last_canvas_size != (low_w, low_h):
            self.canvas = pygame.Surface((vw, vh)) 
            self.dark_surface = pygame.Surface((low_w, low_h), pygame.SRCALPHA)
            self.light_mask = pygame.Surface((low_w, low_h), pygame.SRCALPHA)
            self.last_canvas_size = (low_w, low_h)
        return self.canvas 

    def apply_lighting(self, camera):
        # [Visibility] Spectators ignore darkness and see everything
        if self.game.player.role == "SPECTATOR":
            return

        # 1. 어둠 적용 (Low Res)
        final_alpha = 250 if getattr(self.game, 'is_blackout', False) else int(self.current_ambient_alpha)
        final_alpha = max(0, min(255, final_alpha))
        self.dark_surface.fill((5, 5, 10, final_alpha))
        if final_alpha > 50:
            self.light_mask.fill((0, 0, 0, 0))
            sf = self.scale_factor; cam_x, cam_y = camera.x, camera.y
            vw, vh = self.canvas.get_size()
            lamp_r = 64; lamp_r_scaled = int(lamp_r * sf)
            scaled_lamp = pygame.transform.smoothscale(self.lamp_halo, (lamp_r_scaled * 2, lamp_r_scaled * 2))
            for lx, ly in self.light_sources:
                if cam_x - lamp_r <= lx <= cam_x + vw + lamp_r and cam_y - lamp_r <= ly <= cam_y + vh + lamp_r:
                    draw_x = (lx - cam_x) * sf - lamp_r_scaled; draw_y = (ly - cam_y) * sf - lamp_r_scaled
                    self.light_mask.blit(scaled_lamp, (draw_x, draw_y), special_flags=pygame.BLEND_RGBA_ADD)
            player = self.game.player
            if not (self.game.current_phase == 'DAWN' and player.role != "MAFIA"):
                radius_tiles = player.get_vision_radius(self.current_vision_factor, getattr(self.game, 'is_blackout', False), getattr(self.game, 'weather', 'CLEAR'))
                direction = player.facing_dir if player.role == "POLICE" and player.flashlight_on and self.game.current_phase in ['EVENING', 'NIGHT', 'DAWN'] else None
                poly_points_abs = self.game.fov.get_poly_points(player.rect.centerx, player.rect.centery, radius_tiles, direction, 60)
                poly_points_rel = [((px - camera.x) * sf, (py - camera.y) * sf) for px, py in poly_points_abs]
                draw_clarity = self.current_clarity
                if player.role == "POLICE" and player.flashlight_on: draw_clarity = 240
                elif player.role == "MAFIA" and self.game.current_phase in ['NIGHT', 'DAWN']: draw_clarity = max(draw_clarity, 180)
                if getattr(self.game, 'is_blackout', False) and player.role != "MAFIA": draw_clarity = min(draw_clarity, 50)
                temp_fov = pygame.Surface(self.light_mask.get_size(), pygame.SRCALPHA)
                if len(poly_points_rel) > 2: pygame.draw.polygon(temp_fov, (255, 255, 255, int(draw_clarity)), poly_points_rel)
                radius_px = int(radius_tiles * TILE_SIZE * 1.2 * sf)
                halo = pygame.transform.scale(self.gradient_halo, (radius_px * 2, radius_px * 2))
                px, py = (player.rect.centerx - cam_x) * sf, (player.rect.centery - cam_y) * sf
                temp_fov.blit(halo, (px - radius_px, py - radius_px), special_flags=pygame.BLEND_RGBA_MULT)
                self.light_mask.blit(temp_fov, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            self.dark_surface.blit(self.light_mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        full_w, full_h = self.canvas.get_size()
        self.canvas.blit(pygame.transform.scale(self.dark_surface, (full_w, full_h)), (0, 0))
        now = pygame.time.get_ticks()
        if getattr(self.game, 'is_mafia_frozen', False):
            overlay = pygame.Surface((full_w, full_h), pygame.SRCALPHA); overlay.fill((255, 0, 0, 50) if (now//200)%2==0 else (0, 0, 255, 50)); self.canvas.blit(overlay, (0, 0))
        if getattr(self.game, 'is_blackout', False):
            if (now // 500) % 2 == 0:
                overlay = pygame.Surface((full_w, full_h), pygame.SRCALPHA); pygame.draw.rect(overlay, (255, 0, 0, 100), (0, 0, full_w, full_h), 20); self.canvas.blit(overlay, (0, 0))
        return self.canvas
