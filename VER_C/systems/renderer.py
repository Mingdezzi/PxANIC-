import pygame
from settings import *
from colors import *

class CharacterRenderer:
    _sprite_cache = {}
    
    # [추가] 폰트 객체 미리 생성 (클래스 변수)
    pygame.font.init()
    NAME_FONT = pygame.font.SysFont("arial", 11, bold=True)
    POPUP_FONT = pygame.font.SysFont("arial", 12, bold=True)

    # [최적화] 반복 사용되는 Rect 객체 상수화
    RECT_BODY = pygame.Rect(4, 4, 24, 24)
    RECT_CLOTH = pygame.Rect(4, 14, 24, 14)
    RECT_ARM_L = pygame.Rect(8, 14, 4, 14)
    RECT_ARM_R = pygame.Rect(20, 14, 4, 14)
    RECT_HAT_TOP = pygame.Rect(2, 2, 28, 5)
    RECT_HAT_RIM = pygame.Rect(6, 0, 20, 7)

    # [최적화] 텍스트 서피스 캐시 저장소
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
        
        return (
            skin_idx, cloth_idx, hat_idx,
            entity.role, entity.sub_role,
            facing, is_highlighted
        )

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
            is_highlighted = True
            alpha = 255 

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

            if is_highlighted:
                body_color = (255, 50, 50)
                clothes_color = (150, 0, 0)

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
                    if entity.sub_role == "FARMER":
                        pygame.draw.rect(base_surf, (120, 80, 40), CharacterRenderer.RECT_ARM_L)
                        pygame.draw.rect(base_surf, (120, 80, 40), CharacterRenderer.RECT_ARM_R)

            elif entity.role == "DOCTOR":
                pygame.draw.rect(base_surf, (240, 240, 250), CharacterRenderer.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                pygame.draw.rect(base_surf, (255, 50, 50), (14, 16, 4, 10))
                pygame.draw.rect(base_surf, (255, 50, 50), (11, 19, 10, 4))
            elif entity.role == "POLICE":
                pygame.draw.rect(base_surf, (20, 40, 120), CharacterRenderer.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                pygame.draw.circle(base_surf, (255, 215, 0), (10, 18), 3)
            else:
                pygame.draw.rect(base_surf, clothes_color, CharacterRenderer.RECT_CLOTH, border_bottom_left_radius=6, border_bottom_right_radius=6)
                if entity.sub_role == "FARMER":
                    pygame.draw.rect(base_surf, (120, 80, 40), CharacterRenderer.RECT_ARM_L)
                    pygame.draw.rect(base_surf, (120, 80, 40), CharacterRenderer.RECT_ARM_R)

            f_dir = getattr(entity, 'facing_dir', (0, 1))
            ox, oy = f_dir[0] * 3, f_dir[1] * 2
            pygame.draw.circle(base_surf, (255, 255, 255), (16 - 5 + ox, 12 + oy), 3)
            pygame.draw.circle(base_surf, (0, 0, 0), (16 - 5 + ox + f_dir[0], 12 + oy + f_dir[1]), 1)
            pygame.draw.circle(base_surf, (255, 255, 255), (16 + 5 + ox, 12 + oy), 3)
            pygame.draw.circle(base_surf, (0, 0, 0), (16 + 5 + ox + f_dir[0], 12 + oy + f_dir[1]), 1)

            hat_idx = entity.custom.get('hat', 0) % len(CUSTOM_COLORS['HAT'])
            if hat_idx > 0:
                hat_color = CUSTOM_COLORS['HAT'][hat_idx]
                pygame.draw.rect(base_surf, hat_color, CharacterRenderer.RECT_HAT_TOP)
                pygame.draw.rect(base_surf, hat_color, CharacterRenderer.RECT_HAT_RIM)
            
            CharacterRenderer._sprite_cache[cache_key] = base_surf

        final_surf = base_surf
        if alpha < 255:
            final_surf = base_surf.copy()
            final_surf.set_alpha(alpha)

        screen.blit(final_surf, (draw_x, draw_y))

        # [최적화] 텍스트 렌더링 캐싱 시스템 적용
        name_color = (230, 230, 230)

        if entity.role == "POLICE" and viewer_role in ["POLICE", "SPECTATOR"]: name_color = (100, 180, 255)
        elif entity.role == "MAFIA" and viewer_role in ["MAFIA", "SPECTATOR"]: name_color = (255, 100, 100)
        
        # 캐시 키: (엔티티ID 혹은 이름, 색상)
        text_cache_key = (id(entity), entity.name, name_color)
        
        if text_cache_key in CharacterRenderer._name_surface_cache:
            name_surf = CharacterRenderer._name_surface_cache[text_cache_key]
        else:
            name_surf = CharacterRenderer.NAME_FONT.render(entity.name, True, name_color)
            CharacterRenderer._name_surface_cache[text_cache_key] = name_surf

        # 캐릭터 가로 중심(TILE_SIZE/2)에서 텍스트 절반 너비만큼 빼서 중앙 정렬
        text_x = draw_x + (TILE_SIZE // 2) - (name_surf.get_width() // 2)
        screen.blit(name_surf, (text_x, draw_y - 14))

        # [최적화] 팝업 텍스트도 최초 1회만 렌더링 후 p['surface']에 저장하여 재사용
        if hasattr(entity, 'popups'):
            for p in entity.popups[:]:
                if pygame.time.get_ticks() > p['timer']:
                    entity.popups.remove(p)
                    continue
                
                if 'surface' not in p:
                    p['surface'] = CharacterRenderer.POPUP_FONT.render(p['text'], True, p.get('color', (255, 255, 0)))
                
                p_surf = p['surface']
                
                elapsed = 1500 - (p['timer'] - pygame.time.get_ticks())
                offset_y = int(elapsed * 0.03)
                
                # 중앙 정렬
                popup_x = draw_x + (TILE_SIZE // 2) - (p_surf.get_width() // 2)
                popup_y = draw_y - 20 - offset_y
                
                screen.blit(p_surf, (popup_x, popup_y))

from world.tiles import get_texture

class MapRenderer:
    """
    [New] 화면에 보이는 타일만 렌더링하는 최적화된 맵 렌더러 (Culling 적용)
    """
    def __init__(self, map_manager):
        self.map_manager = map_manager

    def draw(self, screen, camera, dt):
        # 1. 카메라가 비추는 영역(Viewport) 계산
        # 화면보다 여유 있게(-1 ~ +1 타일) 그려서 끊김 방지
        vw, vh = camera.width / camera.zoom_level, camera.height / camera.zoom_level
        
        start_col = int(max(0, camera.x // TILE_SIZE))
        start_row = int(max(0, camera.y // TILE_SIZE))
        end_col = int(min(self.map_manager.width, (camera.x + vw) // TILE_SIZE + 2))
        end_row = int(min(self.map_manager.height, (camera.y + vh) // TILE_SIZE + 2))

        # 2. 오프셋 미리 계산
        cam_x, cam_y = camera.x, camera.y
        
        # 3. 최적화된 지역 변수 참조
        floors = self.map_manager.map_data['floor']
        walls = self.map_manager.map_data['wall']
        objects = self.map_manager.map_data['object']

        # 4. 보이는 범위(Viewport)만 이중 반복문 순회
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                draw_x = c * TILE_SIZE - cam_x
                draw_y = r * TILE_SIZE - cam_y

                # (1) 바닥 (Floor)
                tile_data = floors[r][c]
                tid = tile_data[0] if isinstance(tile_data, (tuple, list)) else tile_data
                rot = tile_data[1] if isinstance(tile_data, (tuple, list)) else 0
                if tid != 0:
                    img = get_texture(tid, rot)
                    if img: screen.blit(img, (draw_x, draw_y))

                # (2) 벽 (Wall)
                tile_data = walls[r][c]
                tid = tile_data[0] if isinstance(tile_data, (tuple, list)) else tile_data
                rot = tile_data[1] if isinstance(tile_data, (tuple, list)) else 0
                if tid != 0:
                    img = get_texture(tid, rot)
                    if img: screen.blit(img, (draw_x, draw_y))

                # (3) 오브젝트 (Object)
                tile_data = objects[r][c]
                tid = tile_data[0] if isinstance(tile_data, (tuple, list)) else tile_data
                rot = tile_data[1] if isinstance(tile_data, (tuple, list)) else 0
                if tid != 0:
                    img = get_texture(tid, rot)
                    if img: screen.blit(img, (draw_x, draw_y))
