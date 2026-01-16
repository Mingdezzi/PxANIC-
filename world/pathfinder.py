import heapq
from settings import TILE_SIZE
from world.tiles import check_collision, get_tile_category

class Pathfinder:
    def __init__(self, map_manager):
        self.map_manager = map_manager

    def find_path(self, start_pos, end_pos):
        """
        A* 알고리즘을 사용해 경로를 계산합니다.
        start_pos, end_pos: (x, y) 픽셀 좌표
        반환값: [(x, y), ...] 픽셀 좌표 리스트 (출발지 제외)
        """
        start_gx = int(start_pos[0] // TILE_SIZE)
        start_gy = int(start_pos[1] // TILE_SIZE)
        target_gx = int(end_pos[0] // TILE_SIZE)
        target_gy = int(end_pos[1] // TILE_SIZE)
        
        # 맵 범위 체크
        if not (0 <= target_gx < self.map_manager.width and 0 <= target_gy < self.map_manager.height):
            return []

        if (start_gx, start_gy) == (target_gx, target_gy):
            return []

        open_set = []
        heapq.heappush(open_set, (0, start_gx, start_gy))
        came_from = {}
        g_score = {(start_gx, start_gy): 0}
        
        # 안전장치: 너무 긴 경로 탐색 방지
        max_iterations = 5000
        iterations = 0

        while open_set and iterations < max_iterations:
            iterations += 1
            _, cx, cy = heapq.heappop(open_set)

            if (cx, cy) == (target_gx, target_gy):
                return self._reconstruct_path(came_from, (target_gx, target_gy))

            # 4방향 탐색
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy

                if 0 <= nx < self.map_manager.width and 0 <= ny < self.map_manager.height:
                    # 충돌 체크 (시작점 포함)
                    if not self._is_walkable(nx, ny, target_gx, target_gy, start_gx, start_gy):
                        continue

                    new_g = g_score[(cx, cy)] + 1
                    
                    if (nx, ny) not in g_score or new_g < g_score[(nx, ny)]:
                        g_score[(nx, ny)] = new_g
                        priority = new_g + abs(target_gx - nx) + abs(target_gy - ny) # Manhattan distance
                        heapq.heappush(open_set, (priority, nx, ny))
                        came_from[(nx, ny)] = (cx, cy)
                        
        return [] # 경로 없음

    def _is_walkable(self, x, y, tx, ty, start_gx=None, start_gy=None):
        # 시작점과 목적지는 충돌체여도 이동 가능 (끼임 탈출 및 상호작용)
        if (x == tx and y == ty) or (x == start_gx and y == start_gy):
            return True
            
        # MapManager의 충돌 캐시 활용
        if self.map_manager.check_any_collision(x, y):
             # 문(Category 5)은 통과 가능으로 간주 (NPC가 열 수 있으므로)
            tid = self.map_manager.get_tile(x, y, 'object')
            if get_tile_category(tid) == 5:
                return True
            return False
            
        return True

    def find_path(self, start_pos, end_pos):
        start_gx = int(start_pos[0] // TILE_SIZE)
        start_gy = int(start_pos[1] // TILE_SIZE)
        target_gx = int(end_pos[0] // TILE_SIZE)
        target_gy = int(end_pos[1] // TILE_SIZE)
        
        # ... (생략)

        while open_set and iterations < max_iterations:
            iterations += 1
            _, cx, cy = heapq.heappop(open_set)

            if (cx, cy) == (target_gx, target_gy):
                return self._reconstruct_path(came_from, (target_gx, target_gy))

            # 4방향 탐색
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy

                if 0 <= nx < self.map_manager.width and 0 <= ny < self.map_manager.height:
                    # 충돌 체크 (start 좌표 전달)
                    if not self._is_walkable(nx, ny, target_gx, target_gy, start_gx, start_gy):
                        continue

                    new_g = g_score[(cx, cy)] + 1
                    
                    if (nx, ny) not in g_score or new_g < g_score[(nx, ny)]:
                        g_score[(nx, ny)] = new_g
                        priority = new_g + abs(target_gx - nx) + abs(target_gy - ny) # Manhattan distance
                        heapq.heappush(open_set, (priority, nx, ny))
                        came_from[(nx, ny)] = (cx, cy)
                        
        return [] # 경로 없음
        path = []
        while current in came_from:
            path.append((current[0] * TILE_SIZE + TILE_SIZE//2, current[1] * TILE_SIZE + TILE_SIZE//2))
            current = came_from[current]
        return path[::-1] # 역순 반환
