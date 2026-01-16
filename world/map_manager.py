import json
import os
import pygame
from settings import TILE_SIZE
from world.tiles import check_collision, NEW_ID_MAP, TILE_DATA, BED_TILES, HIDEABLE_TILES

class MapManager:
    def __init__(self):
        self.map_data = {
            'floor': [],
            'wall': [],
            'object': []
        }
        self.zone_map = []
        self.collision_cache = []
        self.width = 0
        self.height = 0
        self.spawn_x = 100
        self.spawn_y = 100
        self.tile_cache = {}
        self.tile_cooldowns = {}
        self.open_doors = {}
        
        self.name_to_tid = {data['name']: tid for tid, data in TILE_DATA.items()}

    def load_map(self, filename="map.json"):
        if not os.path.exists(filename): 
            self.create_default_map()
            return True
            
        try:
            with open(filename, 'r', encoding='utf-8') as f: 
                data = json.load(f)
                
            self.width = data.get('width', 50)
            self.height = data.get('height', 50)
            
            # 맵 데이터 초기화
            for k in self.map_data:
                self.map_data[k] = [[(0, 0) for _ in range(self.width)] for _ in range(self.height)]
            
            if 'layers' in data:
                loaded_layers = data['layers']
                for ln in ['floor', 'wall', 'object']:
                    if ln in loaded_layers:
                        grid = loaded_layers[ln]
                        for y in range(min(len(grid), self.height)):
                            for x in range(min(len(grid[y]), self.width)):
                                val = grid[y][x]
                                self.map_data[ln][y][x] = (val, 0) if isinstance(val, int) else tuple(val)
            elif 'tiles' in data:
                # 구버전 맵 호환
                old_tiles = data['tiles']
                for y in range(min(len(old_tiles), self.height)):
                    for x in range(min(len(old_tiles[y]), self.width)):
                        new_id = NEW_ID_MAP.get(old_tiles[y][x], old_tiles[y][x])
                        self.set_tile(x, y, new_id)
                        
            self.zone_map = data.get('zones', [[0 for _ in range(self.width)] for _ in range(self.height)])
            
            self.build_collision_cache()
            self.build_tile_cache()
            
            # 스폰 포인트 설정
            for y in range(self.height):
                for x in range(self.width):
                    if self.zone_map[y][x] == 1: 
                        self.spawn_x, self.spawn_y = x * TILE_SIZE, y * TILE_SIZE
                        break
            return True
        except Exception as e:
            print(f"[MapManager] Failed to load map: {e}")
            self.create_default_map()
            return False

    def get_tile(self, gx, gy, layer='floor'):
        if 0 <= gx < self.width and 0 <= gy < self.height:
            return self.map_data[layer][gy][gx][0]
        return 0

    def get_tile_full(self, gx, gy, layer='floor'):
        if 0 <= gx < self.width and 0 <= gy < self.height:
            return self.map_data[layer][gy][gx]
        return (0, 0)

    def set_tile(self, gx, gy, tid, rotation=0, layer=None):
        if not (0 <= gx < self.width and 0 <= gy < self.height): return
        
        if layer is None:
            if 1000000 <= tid < 3000000: layer = 'floor'
            elif 3000000 <= tid < 5000000: layer = 'wall'
            else: layer = 'object'
            
        self.map_data[layer][gy][gx] = (tid, rotation)
        self._update_collision_at(gx, gy)

    def _update_collision_at(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height): return
        
        is_blocked = False
        for layer in ['floor', 'wall', 'object']:
            tid = self.map_data[layer][y][x][0]
            if tid != 0 and check_collision(tid):
                if tid not in BED_TILES and tid not in HIDEABLE_TILES and tid != 5310005:
                    is_blocked = True
                    break
            
        self.collision_cache[y][x] = is_blocked

    def build_collision_cache(self):
        self.collision_cache = [[False for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                self._update_collision_at(x, y)

    def check_any_collision(self, gx, gy):
        if not (0 <= gx < self.width and 0 <= gy < self.height):
            return True 
        return self.collision_cache[gy][gx]

    def get_spawn_points(self, zone_id=1):
        points = []
        for y in range(self.height):
            for x in range(self.width):
                if self.zone_map[y][x] == zone_id:
                    if not self.check_any_collision(x, y):
                        points.append((x * TILE_SIZE, y * TILE_SIZE))
        return points

    def build_tile_cache(self):
        self.tile_cache = {}
        for ln in ['floor', 'wall', 'object']:
            grid = self.map_data[ln]
            for y in range(len(grid)):
                for x in range(len(grid[y])):
                    val = grid[y][x]
                    tid = val[0]
                    if tid == 0: continue
                    if tid not in self.tile_cache: self.tile_cache[tid] = []
                    # 픽셀 좌표로 저장 (중심점 아님, 좌상단)
                    self.tile_cache[tid].append((x * TILE_SIZE, y * TILE_SIZE))

    def get_random_floor_tile(self):
        # 이동 가능한 랜덤 타일 반환 (충돌 체크 포함)
        floor_tids = [tid for tid in self.tile_cache if 1000000 <= tid < 2000000]
        if not floor_tids: return None
        
        # 최대 10번 시도하여 충돌 없는 바닥 찾기
        for _ in range(10):
            tid = random.choice(floor_tids)
            if self.tile_cache[tid]:
                px, py = random.choice(self.tile_cache[tid])
                gx, gy = px // TILE_SIZE, py // TILE_SIZE
                
                # 해당 위치에 충돌체가 없는지 확인
                if not self.check_any_collision(gx, gy):
                    return (px, py)
                    
        return None

    # ... (기존 메서드들)
        self.width, self.height = 40, 30
        for k in self.map_data: self.map_data[k] = [[(0,0) for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width): self.set_tile(x, y, 1110000)
        # 벽
        for x in range(self.width):
            self.set_tile(x, 0, 3220000); self.set_tile(x, self.height-1, 3220000)
        for y in range(self.height):
            self.set_tile(0, y, 3220000); self.set_tile(self.width-1, y, 3220000)
            
        self.zone_map = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.open_doors = {}
        self.build_tile_cache()
        self.build_collision_cache()

    # 문 관련 메서드들 (InteractionSystem에서 주로 사용하겠지만 MapManager가 데이터 소유)
    def open_door(self, gx, gy):
        tid, rot = self.get_tile_full(gx, gy, 'object')
        target_tid = self._find_state_tile(tid, "Closed", "Open")
        if not target_tid: target_tid = self._find_state_tile(tid, "Locked", "Open")
            
        if target_tid:
            self.set_tile(gx, gy, target_tid, rotation=rot, layer='object')
            self.open_doors[(gx, gy)] = pygame.time.get_ticks()

    def close_door(self, gx, gy):
        tid, rot = self.get_tile_full(gx, gy, 'object')
        target_tid = self._find_state_tile(tid, "Open", "Closed")
        
        if target_tid:
            self.set_tile(gx, gy, target_tid, rotation=rot, layer='object')
            if (gx, gy) in self.open_doors: del self.open_doors[(gx, gy)]

    def lock_door(self, gx, gy):
        tid, rot = self.get_tile_full(gx, gy, 'object')
        target_tid = self._find_state_tile(tid, "Closed", "Locked")
        if target_tid:
            self.set_tile(gx, gy, target_tid, rotation=rot, layer='object')
            return True
        return False

    def unlock_door(self, gx, gy):
        tid, rot = self.get_tile_full(gx, gy, 'object')
        target_tid = self._find_state_tile(tid, "Locked", "Closed")
        if target_tid:
            self.set_tile(gx, gy, target_tid, rotation=rot, layer='object')
            return True
        return False

    def _find_state_tile(self, current_tid, find_str, replace_str):
        if current_tid not in TILE_DATA: return None
        current_name = TILE_DATA[current_tid]['name']
        target_name = current_name.replace(find_str, replace_str)
        if target_name in self.name_to_tid: return self.name_to_tid[target_name]
        
        # 한글 대응
        korean_map = {"Closed": "닫힘", "Open": "열림", "Locked": "잠김"}
        if find_str in korean_map and replace_str in korean_map:
            k_find, k_replace = korean_map[find_str], korean_map[replace_str]
            target_name_fixed = target_name.replace(k_find, k_replace)
            if target_name_fixed in self.name_to_tid: return self.name_to_tid[target_name_fixed]
        return None

    def update_doors(self, dt, active_rects):
        # 자동 문 닫힘 로직 (System에서 호출)
        now = pygame.time.get_ticks()
        to_close = []
        for (gx, gy), open_time in list(self.open_doors.items()):
            if now < open_time + 5000: continue 
            door_rect = pygame.Rect(gx * TILE_SIZE, gy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if door_rect.collidelist(active_rects) != -1: continue
            to_close.append((gx, gy))
        
        for (gx, gy) in to_close:
            self.close_door(gx, gy)
