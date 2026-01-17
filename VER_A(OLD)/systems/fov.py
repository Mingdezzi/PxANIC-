import math
import pygame
from settings import TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, INDOOR_ZONES
from world.tiles import check_collision, TRANSPARENT_TILES

class FOV:
    def __init__(self, map_width, map_height, map_manager):
        self.map_width = map_width
        self.map_height = map_height
        self.map_manager = map_manager
        
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
            if center_angle < 0: center_angle += 360
            
            start_angle = int(center_angle - angle_width / 2)
            end_angle = int(center_angle + angle_width / 2)
            angle_step = 2
        else:
            start_angle = 0
            end_angle = 360
            angle_step = 3 

        wall_data = self.map_manager.map_data['wall']
        obj_data = self.map_manager.map_data['object']
        zone_data = self.map_manager.zone_map
        width, height = self.map_width, self.map_height
        
        sin_tbl = self.sin_table
        cos_tbl = self.cos_table

        for angle_deg in range(start_angle, end_angle, angle_step):
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

                # Collision & Visibility Check
                w_val = wall_data[gy][gx]
                tid_wall = w_val[0] if isinstance(w_val, (tuple, list)) else w_val
                
                is_blocking = False
                is_transparent = False

                # Wall Check
                if tid_wall != 0:
                    if check_collision(tid_wall): is_blocking = True
                    if tid_wall in TRANSPARENT_TILES: is_transparent = True
                
                # Object Check
                if not is_blocking:
                    o_val = obj_data[gy][gx]
                    tid_obj = o_val[0] if isinstance(o_val, (tuple, list)) else o_val
                    if tid_obj != 0:
                        if check_collision(tid_obj): is_blocking = True
                        if tid_obj in TRANSPARENT_TILES: is_transparent = True

                # Zone Logic (Indoor/Outdoor)
                target_zone = zone_data[gy][gx]
                is_target_indoors = (target_zone in INDOOR_ZONES)
                
                if not is_player_indoors and is_target_indoors:
                    # Outside looking In
                    if is_transparent:
                        pass # Can see through glass
                    elif is_blocking:
                        break # Wall blocks view
                    else:
                        break # Floor inside is not visible unless through glass
                
                if is_blocking and not is_transparent:
                    break
        return visible_tiles

    def get_poly_points(self, px, py, radius, direction=None, angle_width=60):
        points = []
        points.append((px, py)) 

        if radius <= 0: return points

        cx, cy = int(px // TILE_SIZE), int(py // TILE_SIZE)
        player_zone = 0
        if 0 <= cx < self.map_width and 0 <= cy < self.map_height:
             player_zone = self.map_manager.zone_map[cy][cx]
        is_player_indoors = (player_zone in INDOOR_ZONES)

        max_dist_px = radius * TILE_SIZE
        step_size = 16.0 
        
        start_angle, end_angle, angle_step = 0, 360, 2
        if direction and (direction[0] != 0 or direction[1] != 0):
            center_angle = math.degrees(math.atan2(direction[1], direction[0]))
            if center_angle < 0: center_angle += 360
            
            start_angle = int(center_angle - angle_width / 2)
            end_angle = int(center_angle + angle_width / 2)
            angle_step = 1

        width, height = self.map_width, self.map_height
        wall_data = self.map_manager.map_data['wall']
        obj_data = self.map_manager.map_data['object']
        zone_data = self.map_manager.zone_map
        
        sin_tbl = self.sin_table
        cos_tbl = self.cos_table

        for angle_deg in range(start_angle, end_angle + 1, angle_step):
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
                
                if not (0 <= gx < width and 0 <= gy < height):
                    hit_x, hit_y = nx, ny
                    break
                
                is_blocking = False
                is_transparent = False
                
                # Wall
                w_val = wall_data[gy][gx]
                tid_wall = w_val[0] if isinstance(w_val, (tuple, list)) else w_val
                if tid_wall != 0:
                    if check_collision(tid_wall): is_blocking = True
                    if tid_wall in TRANSPARENT_TILES: is_transparent = True
                
                # Object
                if not is_blocking:
                    o_val = obj_data[gy][gx]
                    tid_obj = o_val[0] if isinstance(o_val, (tuple, list)) else o_val
                    if tid_obj != 0:
                        if check_collision(tid_obj): is_blocking = True
                        if tid_obj in TRANSPARENT_TILES: is_transparent = True

                # Zone Logic
                target_zone = zone_data[gy][gx]
                is_target_indoors = (target_zone in INDOOR_ZONES)
                
                if not is_player_indoors and is_target_indoors:
                    if is_transparent:
                        pass # Glass -> Continue ray
                    elif is_blocking:
                        is_blocking = True # Wall -> Block
                    else:
                        is_blocking = True # Floor inside -> Block visibility from outside
                
                if is_blocking and not is_transparent:
                    hit_x, hit_y = nx, ny
                    break
                
                hit_x, hit_y = nx, ny
            
            points.append((hit_x, hit_y))
            
        return points