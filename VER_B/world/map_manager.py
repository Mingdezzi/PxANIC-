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
        self.collision_cache = []  # [최적화] 충돌 맵 캐시 추가
        self.width = 0
        self.height = 0
        self.spawn_x = 100
        self.spawn_y = 100
        self.tile_cache = {}
        self.tile_cooldowns = {}
        self.open_doors = {}
        
        self.name_to_tid = {data['name']: tid for tid, data in TILE_DATA.items()}

    def get_tile(self, gx, gy, layer='floor'):
        # [최적화] 범위 검사 후 직접 접근 (isinstance 제거)
        if 0 <= gx < self.width and 0 <= gy < self.height:
            # 모든 타일 데이터는 (tid, rot) 튜플 형태임을 보장
            return self.map_data[layer][gy][gx][0]
        return 0

    def get_tile_full(self, gx, gy, layer='floor'):
        if 0 <= gx < self.width and 0 <= gy < self.height:
            return self.map_data[layer][gy][gx]
        return (0, 0)

    def set_tile(self, gx, gy, tid, rotation=0, layer=None):
        if not (0 <= gx < self.width and 0 <= gy < self.height): return
        
        if layer is None:
            # 간단한 ID 범위 체크 (tiles.py의 get_tile_type 로직 인라인화 가능하면 더 좋음)
            if 1000000 <= tid < 3000000: layer = 'floor'
            elif 3000000 <= tid < 5000000: layer = 'wall'
            else: layer = 'object'
            
        # [최적화] 항상 튜플로 저장
        self.map_data[layer][gy][gx] = (tid, rotation)
        
        # [최적화] 타일 변경 시 해당 위치의 충돌 캐시만 즉시 갱신
        self._update_collision_at(gx, gy)

    # [최적화] 단일 타일 충돌 갱신 헬퍼
    def _update_collision_at(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height): return
        
        is_blocked = False
        
        # 각 레이어별 충돌 체크
        for layer in ['floor', 'wall', 'object']:
            tid = self.map_data[layer][y][x][0]
            if tid != 0 and check_collision(tid):
                # 예외 타일(이동 가능) 체크
                if tid not in BED_TILES and tid not in HIDEABLE_TILES and tid != 5310005:
                    is_blocked = True
                    break
            
        self.collision_cache[y][x] = is_blocked

    # [최적화] 전체 맵 로드 시 충돌 맵 전체 빌드
    def build_collision_cache(self):
        self.collision_cache = [[False for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                self._update_collision_at(x, y)

    def get_spawn_points(self, zone_id=1):
        points = []
        for y in range(self.height):
            for x in range(self.width):
                if self.zone_map[y][x] == zone_id:
                    if not self.check_any_collision(x, y):
                        points.append((x * TILE_SIZE, y * TILE_SIZE))
        return points

    def check_any_collision(self, gx, gy):
        # [최적화] 캐시된 2차원 배열 조회로 대체 (O(1))
        # [수정] 맵 밖은 이동 불가(True)로 처리해야 함
        if not (0 <= gx < self.width and 0 <= gy < self.height):
            return True 
        
        return self.collision_cache[gy][gx]

    def update_doors(self, dt, entities):
        now = pygame.time.get_ticks()
        to_close = []
        
        # [최적화] 살아있는 엔티티의 Rect만 미리 계산 (배치 처리)
        # collidelist 사용을 위해 Rect 리스트 생성
        active_rects = [ent.rect.inflate(-15, -15) for ent in entities if ent.alive]
        
        for (gx, gy), open_time in list(self.open_doors.items()):
            if now < open_time + 5000: continue 

            door_rect = pygame.Rect(gx * TILE_SIZE, gy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            
            # [최적화] 파이썬 루프 대신 C로 구현된 collidelist 사용
            # 충돌하는 엔티티가 하나라도 있으면 닫지 않음
            if door_rect.collidelist(active_rects) != -1:
                continue
            
            to_close.append((gx, gy))
        
        for (gx, gy) in to_close:
            self.close_door(gx, gy)

    def _find_state_tile(self, current_tid, find_str, replace_str):
        if current_tid not in TILE_DATA: return None
        current_name = TILE_DATA[current_tid]['name']
        
        target_name = current_name.replace(find_str, replace_str)
        
        if target_name in self.name_to_tid:
            return self.name_to_tid[target_name]

        korean_map = {"Closed": "닫힘", "Open": "열림", "Locked": "잠김"}
        
        if find_str in korean_map and replace_str in korean_map:
            k_find = korean_map[find_str]
            k_replace = korean_map[replace_str]
            target_name_fixed = target_name.replace(k_find, k_replace)
            if target_name_fixed in self.name_to_tid:
                return self.name_to_tid[target_name_fixed]
                
        return None

    def open_door(self, gx, gy, layer='object'):
        tid, rot = self.get_tile_full(gx, gy, layer)
        target_tid = self._find_state_tile(tid, "Closed", "Open")
        if not target_tid:
            target_tid = self._find_state_tile(tid, "Locked", "Open")
            
        if target_tid:
            self.set_tile(gx, gy, target_tid, rotation=rot, layer=layer)
            self.open_doors[(gx, gy)] = pygame.time.get_ticks()

    def close_door(self, gx, gy, layer='object'):
        tid, rot = self.get_tile_full(gx, gy, layer)
        target_tid = self._find_state_tile(tid, "Open", "Closed")
        
        if target_tid:
            self.set_tile(gx, gy, target_tid, rotation=rot, layer=layer)
            if (gx, gy) in self.open_doors: del self.open_doors[(gx, gy)]

    def lock_door(self, gx, gy, layer='object'):
        tid, rot = self.get_tile_full(gx, gy, layer)
        target_tid = self._find_state_tile(tid, "Closed", "Locked")
        
        if target_tid:
            self.set_tile(gx, gy, target_tid, rotation=rot, layer=layer)
            return True
        return False

    def unlock_door(self, gx, gy, layer='object'):
        tid, rot = self.get_tile_full(gx, gy, layer)
        target_tid = self._find_state_tile(tid, "Locked", "Closed")
        
        if target_tid:
            self.set_tile(gx, gy, target_tid, rotation=rot, layer=layer)
            return True
        return False

    def load_map(self, filename="map.json"):
        if not os.path.exists(filename): self.create_default_map(); return True
        try:
            with open(filename, 'r', encoding='utf-8') as f: data = json.load(f)
            self.width, self.height = data.get('width', 50), data.get('height', 50)
            
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
                                # [최적화] 로드 시점에 항상 튜플로 변환하여 저장
                                self.map_data[ln][y][x] = (val, 0) if isinstance(val, int) else tuple(val)
            elif 'tiles' in data:
                old_tiles = data['tiles']
                for y in range(min(len(old_tiles), self.height)):
                    for x in range(min(len(old_tiles[y]), self.width)):
                        new_id = NEW_ID_MAP.get(old_tiles[y][x], old_tiles[y][x])
                        self.set_tile(x, y, new_id)
                        
            self.zone_map = data.get('zones', [[0 for _ in range(self.width)] for _ in range(self.height)])
            # [최적화] 맵 로드 후 캐시 생성
            self.build_collision_cache()
            self.build_tile_cache()
            
            for y in range(self.height):
                for x in range(self.width):
                    if self.zone_map[y][x] == 1: 
                        self.spawn_x, self.spawn_y = x * TILE_SIZE, y * TILE_SIZE
                        break
            return True
        except Exception as e:
            import traceback; traceback.print_exc(); self.create_default_map(); return True

    def build_tile_cache(self):
        self.tile_cache = {}
        for ln in ['floor', 'wall', 'object']:
            grid = self.map_data[ln]
            for y in range(len(grid)):
                for x in range(len(grid[y])):
                    tid = grid[y][x][0]
                    if tid == 0: continue
                    if tid not in self.tile_cache: self.tile_cache[tid] = []
                    self.tile_cache[tid].append((x * TILE_SIZE, y * TILE_SIZE))
        return self.tile_cache

    def create_default_map(self):
        self.width, self.height = 40, 30
        for k in self.map_data: self.map_data[k] = [[(0,0) for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width): self.set_tile(x, y, 1110000)
        for x in range(self.width):
            self.set_tile(x, 0, 3220000); self.set_tile(x, self.height-1, 3220000)
        for y in range(self.height):
            self.set_tile(0, y, 3220000); self.set_tile(self.width-1, y, 3220000)
            
        self.zone_map = [[0 for _ in range(self.width)] for _ in range(self.height)]
        for y in range(2, 5):
            for x in range(2, 5): self.zone_map[y][x] = 1
        self.open_doors = {}
        self.build_tile_cache()
        self.build_collision_cache() # [최적화]

    def is_tile_on_cooldown(self, gx, gy):
        now = pygame.time.get_ticks()
        if (gx, gy) in self.tile_cooldowns:
            if now < self.tile_cooldowns[(gx, gy)]: return True
            else: del self.tile_cooldowns[(gx, gy)]
        return False

    def set_tile_cooldown(self, gx, gy, duration_ms=3000):
        self.tile_cooldowns[(gx, gy)] = pygame.time.get_ticks() + duration_ms