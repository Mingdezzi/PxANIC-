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
        self.last_canvas_size = (0, 0)
        
        # 설정값
        self.current_ambient_alpha = 0
        self.current_vision_factor = 1.0
        self.current_clarity = 255
        
        # 그라데이션 미리 생성
        self.gradient_halo = self._create_smooth_gradient(1000)

    def _create_smooth_gradient(self, radius):
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            ratio = r / radius
            alpha = int(255 * (1 - ratio * ratio))
            pygame.draw.circle(surf, (255, 255, 255, alpha), (radius, radius), r)
        return surf

    def update(self, dt):
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
        vw, vh = int(self.game.game.screen_width / self.game.zoom_level), int(self.game.game.screen_height / self.game.zoom_level)
        
        if self.canvas is None or self.last_canvas_size != (vw, vh):
            self.canvas = pygame.Surface((vw, vh))
            self.dark_surface = pygame.Surface((vw, vh), pygame.SRCALPHA)
            self.light_mask = pygame.Surface((vw, vh), pygame.SRCALPHA)
            self.last_canvas_size = (vw, vh)
            
        return self.canvas # 캔버스 반환 (PlayState에서 여기에 맵을 그림)

    def apply_lighting(self, camera):
        # 1. 어둠 적용
        final_alpha = 250 if getattr(self.game, 'is_blackout', False) else int(self.current_ambient_alpha)
        final_alpha = max(0, min(255, final_alpha))
        self.dark_surface.fill((5, 5, 10, final_alpha))

        # 2. 시야 처리 (새벽+비마피아 제외)
        player = self.game.player
        if not (self.game.current_phase == 'DAWN' and player.role != "MAFIA"):
            self.light_mask.fill((0, 0, 0, 0))

            radius_tiles = player.get_vision_radius(self.current_vision_factor, getattr(self.game, 'is_blackout', False), getattr(self.game, 'weather', 'CLEAR'))
            
            direction = None
            angle_width = 60
            if player.role == "POLICE" and player.flashlight_on and self.game.current_phase in ['EVENING', 'NIGHT', 'DAWN']:
                direction = player.facing_dir

            poly_points_abs = self.game.fov.get_poly_points(
                player.rect.centerx, 
                player.rect.centery, 
                radius_tiles, 
                direction, 
                angle_width
            )
            
            poly_points_rel = []
            cam_x, cam_y = camera.x, camera.y
            for px, py in poly_points_abs:
                poly_points_rel.append((px - cam_x, py - cam_y))
            
            draw_clarity = self.current_clarity
            if player.role == "POLICE" and player.flashlight_on:
                draw_clarity = 240
            elif player.role == "MAFIA" and self.game.current_phase in ['NIGHT', 'DAWN']:
                draw_clarity = max(draw_clarity, 180)

            if getattr(self.game, 'is_blackout', False) and player.role != "MAFIA":
                draw_clarity = min(draw_clarity, 50)
            
            if len(poly_points_rel) > 2:
                pygame.draw.polygon(self.light_mask, (255, 255, 255, int(draw_clarity)), poly_points_rel)

            radius_px = int(radius_tiles * TILE_SIZE * 1.2)
            halo = pygame.transform.scale(self.gradient_halo, (radius_px * 2, radius_px * 2))
            
            px = player.rect.centerx - camera.x
            py = player.rect.centery - camera.y
            
            self.light_mask.blit(halo, (px - radius_px, py - radius_px), special_flags=pygame.BLEND_RGBA_MULT)
            self.dark_surface.blit(self.light_mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

        self.canvas.blit(self.dark_surface, (0, 0))
        
        # 효과 (얼음, 정전 등)
        now = pygame.time.get_ticks()
        vw, vh = self.last_canvas_size
        
        if getattr(self.game, 'is_mafia_frozen', False): 
            cycle = (now // 200) % 2
            flash_color = (255, 0, 0, 50) if cycle == 0 else (0, 0, 255, 50)
            overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
            overlay.fill(flash_color)
            self.canvas.blit(overlay, (0, 0))

        if getattr(self.game, 'is_blackout', False):
            cycle = (now // 500) % 2
            if cycle == 0:
                overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
                pygame.draw.rect(overlay, (255, 0, 0, 100), (0, 0, vw, vh), 20)
                self.canvas.blit(overlay, (0, 0))
