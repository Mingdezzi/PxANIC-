import pygame
from settings import TILE_SIZE
from world.tiles import get_texture
from colors import CUSTOM_COLORS
from core.resource_manager import ResourceManager

class RenderSystem:
    _sprite_cache = {}
    _name_surface_cache = {}
    
    # 반복 사용되는 Rect 상수
    RECT_BODY = pygame.Rect(4, 4, 24, 24)
    RECT_CLOTH = pygame.Rect(4, 14, 24, 14)
    RECT_ARM_L = pygame.Rect(8, 14, 4, 14)
    RECT_ARM_R = pygame.Rect(20, 14, 4, 14)
    RECT_HAT_TOP = pygame.Rect(2, 2, 28, 5)
    RECT_HAT_RIM = pygame.Rect(6, 0, 20, 7)

    def __init__(self):
        self.resource_manager = ResourceManager.get_instance()
        self.font_name = self.resource_manager.get_font('arial', 11)
        self.font_popup = self.resource_manager.get_font('arial', 12)

    def draw(self, screen, camera, entities, map_manager, current_phase="DAY", viewer_entity=None):
        # 1. 맵 렌더링 (Culling 적용)
        self._draw_map(screen, camera, map_manager)
        
        # 2. 엔티티 렌더링 (Z-Sorting)
        visible_entities = []
        screen_rect = pygame.Rect(camera.x - 50, camera.y - 50, camera.width + 100, camera.height + 100)
        
        viewer_role = viewer_entity.role.main_role if viewer_entity and hasattr(viewer_entity, 'role') else "SPECTATOR"
        viewer_device = viewer_entity.graphics.device_on if viewer_entity and hasattr(viewer_entity, 'graphics') else False

        for entity in entities:
            if not hasattr(entity, 'transform') or not hasattr(entity, 'graphics'):
                continue
            if entity.transform.rect.colliderect(screen_rect):
                visible_entities.append(entity)
        
        visible_entities.sort(key=lambda e: e.transform.y)
        
        for entity in visible_entities:
            self._draw_entity(screen, entity, camera.x, camera.y, viewer_role, current_phase, viewer_device)

        # 3. 조명 효과 (Lighting/FOV)
        if viewer_entity and viewer_role != "SPECTATOR":
            self._draw_lighting(screen, camera, current_phase, viewer_entity)

    def _draw_lighting(self, screen, camera, phase, player):
        # 어둠의 정도 (0: 밝음 ~ 255: 완전 어둠)
        darkness_level = 0
        if phase == 'EVENING': darkness_level = 100
        elif phase == 'NIGHT': darkness_level = 230
        elif phase == 'DAWN': darkness_level = 150
        
        if darkness_level > 0:
            # 어둠 마스크 생성
            darkness = pygame.Surface((camera.width, camera.height), pygame.SRCALPHA)
            darkness.fill((0, 0, 0, darkness_level))
            
            # 플레이어 시야 (구멍 뚫기)
            # 시야 반경 계산 (기존 로직 참조)
            vision_radius = 150 # 기본값
            if player.role.main_role == "MAFIA": vision_radius = 300
            elif player.graphics.flashlight_on: vision_radius = 250
            
            # 그라데이션 라이트
            light_surf = self.resource_manager.create_gradient_surface(vision_radius, (0, 0, 0))
            
            # 마스크 모드로 블리팅 (어둠에서 빛 부분 제거)
            # Pygame의 BLEND_RGBA_SUB를 사용하여 알파값을 뺌
            cx = player.transform.x - camera.x + 16
            cy = player.transform.y - camera.y + 16
            
            darkness.blit(light_surf, (cx - vision_radius, cy - vision_radius), special_flags=pygame.BLEND_RGBA_SUB)
            
            screen.blit(darkness, (0, 0))

    def _draw_map(self, screen, camera, map_manager):
        vw, vh = camera.width, camera.height
        cam_x, cam_y = camera.x, camera.y
        
        start_col = int(max(0, cam_x // TILE_SIZE))
        start_row = int(max(0, cam_y // TILE_SIZE))
        end_col = int(min(map_manager.width, (cam_x + vw) // TILE_SIZE + 2))
        end_row = int(min(map_manager.height, (cam_y + vh) // TILE_SIZE + 2))

        floors = map_manager.map_data['floor']
        walls = map_manager.map_data['wall']
        objects = map_manager.map_data['object']

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                draw_x = c * TILE_SIZE - cam_x
                draw_y = r * TILE_SIZE - cam_y
                
                # Floor -> Wall -> Object 순서
                for layer in [floors, walls, objects]:
                    tile_data = layer[r][c]
                    tid = tile_data[0]
                    rot = tile_data[1]
                    if tid != 0:
                        img = get_texture(tid, rot)
                        if img: screen.blit(img, (draw_x, draw_y))

    def _draw_entity(self, screen, entity, cx, cy, viewer_role, current_phase, viewer_device_on):
        # Stats 컴포넌트가 있고 죽었으면 그리지 않거나 시체로 그림 (여기서는 alive 체크)
        if hasattr(entity, 'stats') and not entity.stats.alive:
            # 시체 그리기 로직 (간단히 회색 박스 또는 누워있는 스프라이트)
            # 기존 로직: pygame.draw.rect(screen, (50, 50, 50), draw_rect)
            draw_rect = entity.transform.rect.move(-cx, -cy)
            pygame.draw.rect(screen, (50, 50, 50), draw_rect)
            return

        # 은신 처리
        alpha = 255
        is_highlighted = (viewer_role == "MAFIA" and viewer_device_on)
        
        if entity.graphics.is_hiding and not is_highlighted:
            is_visible = False
            # 본인 확인 (ECS에서는 ID비교 등으로 해야함, 여기서는 viewer_entity와 비교 불가하므로 이름 등 임시 사용)
            if getattr(entity, 'name', '') == "Player": is_visible, alpha = True, 120
            elif viewer_role == "SPECTATOR": is_visible, alpha = True, 120
            
            if not is_visible: return

        # 캐시 키 생성
        skin = entity.role.skin_idx
        cloth = entity.role.clothes_idx
        hat = entity.role.hat_idx
        role = entity.role.main_role
        sub_role = entity.role.sub_role
        facing = entity.transform.facing
        
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
            
        screen.blit(final_surf, (entity.transform.x - cx, entity.transform.y - cy))
        
        # 이름 그리기
        self._draw_name(screen, entity, entity.transform.x - cx, entity.transform.y - cy, viewer_role)

    def _create_entity_surface(self, entity, is_highlighted, current_phase):
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        
        # 색상 결정
        skin_idx = entity.role.skin_idx % len(CUSTOM_COLORS['SKIN'])
        cloth_idx = entity.role.clothes_idx % len(CUSTOM_COLORS['CLOTHES'])
        body_color = CUSTOM_COLORS['SKIN'][skin_idx]
        clothes_color = CUSTOM_COLORS['CLOTHES'][cloth_idx]

        if is_highlighted:
            body_color = (255, 50, 50)
            clothes_color = (150, 0, 0)

        # 그림자
        pygame.draw.ellipse(surf, (0, 0, 0, 80), (4, TILE_SIZE - 8, TILE_SIZE - 8, 6))
        # 몸통
        pygame.draw.rect(surf, body_color, self.RECT_BODY, border_radius=6)
        
        # 직업별 의상
        role = entity.role.main_role
        sub_role = entity.role.sub_role
        
        if role == "MAFIA":
            if current_phase == "NIGHT":
                 pygame.draw.rect(surf, (30, 30, 35), self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                 pygame.draw.polygon(surf, (180, 0, 0), [(16, 14), (13, 22), (19, 22)]) # 넥타이
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
            pygame.draw.rect(surf, (255, 50, 50), (14, 16, 4, 10)) # 십자가
            pygame.draw.rect(surf, (255, 50, 50), (11, 19, 10, 4))
        
        elif role == "POLICE":
            pygame.draw.rect(surf, (20, 40, 120), self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
            pygame.draw.circle(surf, (255, 215, 0), (10, 18), 3) # 뱃지
            
        else: # CITIZEN etc
            pygame.draw.rect(surf, clothes_color, self.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
            if sub_role == "FARMER":
                pygame.draw.rect(surf, (120, 80, 40), self.RECT_ARM_L)
                pygame.draw.rect(surf, (120, 80, 40), self.RECT_ARM_R)

        # 눈 (방향에 따라 이동)
        f_dir = entity.transform.facing
        ox, oy = f_dir[0] * 3, f_dir[1] * 2
        pygame.draw.circle(surf, (255, 255, 255), (16 - 5 + ox, 12 + oy), 3)
        pygame.draw.circle(surf, (0, 0, 0), (16 - 5 + ox + f_dir[0], 12 + oy + f_dir[1]), 1)
        pygame.draw.circle(surf, (255, 255, 255), (16 + 5 + ox, 12 + oy), 3)
        pygame.draw.circle(surf, (0, 0, 0), (16 + 5 + ox + f_dir[0], 12 + oy + f_dir[1]), 1)

        # 모자
        hat_idx = entity.role.hat_idx % len(CUSTOM_COLORS['HAT'])
        if hat_idx > 0:
            hat_color = CUSTOM_COLORS['HAT'][hat_idx]
            pygame.draw.rect(surf, hat_color, self.RECT_HAT_TOP)
            pygame.draw.rect(surf, hat_color, self.RECT_HAT_RIM)
            
        return surf

    def _draw_name(self, screen, entity, dx, dy, viewer_role):
        name = getattr(entity, 'name', 'Unknown')
        
        name_color = (230, 230, 230)
        role = entity.role.main_role
        
        if role == "POLICE" and viewer_role in ["POLICE", "SPECTATOR"]: name_color = (100, 180, 255)
        elif role == "MAFIA" and viewer_role in ["MAFIA", "SPECTATOR"]: name_color = (255, 100, 100)
        
        key = (id(entity), name, name_color)
        if key in self._name_surface_cache:
            name_surf = self._name_surface_cache[key]
        else:
            name_surf = self.font_name.render(name, True, name_color)
            self._name_surface_cache[key] = name_surf
            
        text_x = dx + (TILE_SIZE // 2) - (name_surf.get_width() // 2)
        screen.blit(name_surf, (text_x, dy - 14))
