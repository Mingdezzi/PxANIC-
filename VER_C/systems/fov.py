import math
import pygame
from settings import TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, INDOOR_ZONES
from world.tiles import check_collision

class FOV:
    def __init__(self, map_width, map_height, map_manager):
        self.map_width = map_width
        self.map_height = map_height
        self.map_manager = map_manager
        
        # [최적화] 삼각함수 Lookup Table 생성 (0도 ~ 360도)
        self.sin_table = {}
        self.cos_table = {}
        for deg in range(361):
            rad = math.radians(deg)
            self.sin_table[deg] = math.sin(rad)
            self.cos_table[deg] = math.cos(rad)
        
    def cast_rays(self, px, py, radius, direction=None, angle_width=60):
        visible_tiles = set()
        
        cx, cy = int(px // TILE_SIZE), int(py // TILE_SIZE)
        visible_tiles.add((cx, cy)) 
        
        if radius <= 0: return visible_tiles

        player_zone = 0
        if 0 <= cx < self.map_width and 0 <= cy < self.map_height:
            player_zone = self.map_manager.zone_map[cy][cx]
        is_player_indoors = (player_zone in INDOOR_ZONES)

        max_dist_px = radius * TILE_SIZE
        step_size = TILE_SIZE / 2.0  
        
        if direction and (direction[0] != 0 or direction[1] != 0):
            center_angle = math.degrees(math.atan2(direction[1], direction[0]))
            # 음수 각도 보정
            if center_angle < 0: center_angle += 360
            
            start_angle = int(center_angle - angle_width / 2)
            end_angle = int(center_angle + angle_width / 2)
            angle_step = 2
        else:
            start_angle = 0
            end_angle = 360
            angle_step = 3 

        # [최적화] 지역 변수 캐싱
        wall_data = self.map_manager.map_data['wall']
        obj_data = self.map_manager.map_data['object']
        zone_data = self.map_manager.zone_map
        width, height = self.map_width, self.map_height
        
        # Lookup table 캐싱
        sin_tbl = self.sin_table
        cos_tbl = self.cos_table

        for angle_deg in range(start_angle, end_angle, angle_step):
            # [최적화] 각도 정규화 (0~360) 및 테이블 조회
            norm_deg = angle_deg % 360
            sin_a = sin_tbl[norm_deg]
            cos_a = cos_tbl[norm_deg]
            
            current_dist = 0
            while current_dist < max_dist_px:
                current_dist += step_size
                
                nx = px + cos_a * current_dist
                ny = py + sin_a * current_dist
                
                gx, gy = int(nx // TILE_SIZE), int(ny // TILE_SIZE)
                
                if not (0 <= gx < width and 0 <= gy < height):
                    break
                
                visible_tiles.add((gx, gy))

                # [최적화] 직접 배열 접근 및 인라인 충돌 검사
                # get_tile 함수 호출 제거
                
                # 1. 벽 충돌 검사
                w_val = wall_data[gy][gx]
                tid_wall = w_val[0] if isinstance(w_val, (tuple, list)) else w_val
                
                is_blocking = False
                if tid_wall != 0 and check_collision(tid_wall):
                    is_blocking = True
                
                # 2. 오브젝트(문 등) 충돌 검사
                if not is_blocking:
                    o_val = obj_data[gy][gx]
                    tid_obj = o_val[0] if isinstance(o_val, (tuple, list)) else o_val
                    
                    if tid_obj != 0 and check_collision(tid_obj):
                        is_blocking = True

                # 3. 실내/실외 시야 차단 로직
                target_zone = zone_data[gy][gx]
                is_target_indoors = (target_zone in INDOOR_ZONES)
                
                if not is_player_indoors and is_target_indoors:
                    if is_blocking:
                        break # 외벽은 보이고 그 뒤는 안 보임
                    else:
                        break # 내부 바닥도 안 보임
                
                if is_blocking:
                    break
        return visible_tiles

    # [추가] 렌더링용 고해상도 다각형 계산 메서드
    def get_poly_points(self, px, py, radius, direction=None, angle_width=60):
        points = []
        points.append((px, py)) # 중심점 추가

        if radius <= 0: return points

        cx, cy = int(px // TILE_SIZE), int(py // TILE_SIZE)
        player_zone = 0
        if 0 <= cx < self.map_width and 0 <= cy < self.map_height:
             player_zone = self.map_manager.zone_map[cy][cx]
        is_player_indoors = (player_zone in INDOOR_ZONES)

        max_dist_px = radius * TILE_SIZE
        
        # [설정] 품질 조절: step이 작을수록 벽에 딱 붙어서 매끄러움 (4px 권장)
        # angle_step이 작을수록 원이 부드러움 (1~2도 권장)
        step_size = 4.0 
        
        start_angle, end_angle, angle_step = 0, 360, 2
        if direction and (direction[0] != 0 or direction[1] != 0):
            center_angle = math.degrees(math.atan2(direction[1], direction[0]))
            if center_angle < 0: center_angle += 360
            
            start_angle = int(center_angle - angle_width / 2)
            end_angle = int(center_angle + angle_width / 2)
            angle_step = 1 # 손전등은 더 정밀하게

        # 최적화를 위한 지역 변수
        width, height = self.map_width, self.map_height
        wall_data = self.map_manager.map_data['wall']
        obj_data = self.map_manager.map_data['object']
        zone_data = self.map_manager.zone_map
        
        # Lookup table 캐싱
        sin_tbl = self.sin_table
        cos_tbl = self.cos_table

        # 모든 각도에 대해 레이캐스팅
        for angle_deg in range(start_angle, end_angle + 1, angle_step):
            # [최적화] 테이블 조회
            norm_deg = angle_deg % 360
            sin_a = sin_tbl[norm_deg]
            cos_a = cos_tbl[norm_deg]
            
            current_dist = 0
            hit_x, hit_y = px, py
            
            while current_dist < max_dist_px:
                current_dist += step_size
                nx = px + cos_a * current_dist
                ny = py + sin_a * current_dist
                
                gx, gy = int(nx // TILE_SIZE), int(ny // TILE_SIZE)
                
                # 맵 밖으로 나가면 종료
                if not (0 <= gx < width and 0 <= gy < height):
                    hit_x, hit_y = nx, ny
                    break
                
                # 충돌 검사
                is_blocking = False
                
                # 1. Wall
                w_val = wall_data[gy][gx]
                tid_wall = w_val[0] if isinstance(w_val, (tuple, list)) else w_val
                if tid_wall != 0 and check_collision(tid_wall): is_blocking = True
                
                # 2. Object
                if not is_blocking:
                    o_val = obj_data[gy][gx]
                    tid_obj = o_val[0] if isinstance(o_val, (tuple, list)) else o_val
                    if tid_obj != 0 and check_collision(tid_obj): is_blocking = True

                # 3. Zone
                target_zone = zone_data[gy][gx]
                is_target_indoors = (target_zone in INDOOR_ZONES)
                if not is_player_indoors and is_target_indoors:
                    is_blocking = True # 실내 타일 진입 시 시야 차단
                
                if is_blocking:
                    hit_x, hit_y = nx, ny
                    break
                
                hit_x, hit_y = nx, ny
            
            points.append((hit_x, hit_y))
            
        return points
