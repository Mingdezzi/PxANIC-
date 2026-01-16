import pygame
import math
from .base_system import BaseSystem
from settings import *
from world.tiles import check_collision, BED_TILES, HIDEABLE_TILES

class MovementSystem(BaseSystem):
    def update(self, dt, entities, map_manager, weather_type='CLEAR'):
        for entity in entities:
            if not hasattr(entity, 'transform') or not hasattr(entity, 'physics'):
                continue
            
            # 정지 상태(Stun) 체크
            if hasattr(entity, 'stats') and entity.stats.status_effects.get('STUNNED'):
                entity.physics.is_moving = False
                continue

            dx, dy = entity.physics.velocity
            
            # 이동 없음
            if dx == 0 and dy == 0:
                entity.physics.is_moving = False
                # 스태미나 회복 로직 등은 StatsSystem에서 처리
                continue
            
            entity.physics.is_moving = True
            
            # 속도 계산
            speed = self._calculate_speed(entity, weather_type)
            
            # 대각선 이동 보정
            if dx != 0 and dy != 0:
                speed *= 0.7071
                
            move_x = dx * speed
            move_y = dy * speed
            
            # 축별 이동 및 충돌 처리
            self._move_single_axis(entity, move_x, 0, map_manager)
            self._move_single_axis(entity, 0, move_y, map_manager)
            
            # 최종 위치 정수화 (렌더링 떨림 방지) -> rect 갱신
            entity.transform.rect.x = int(entity.transform.x)
            entity.transform.rect.y = int(entity.transform.y)

    def _calculate_speed(self, entity, weather_type):
        base = SPEED_WALK
        if entity.physics.move_state == "RUN": base = SPEED_RUN
        elif entity.physics.move_state == "CROUCH": base = SPEED_CROUCH
        
        multiplier = 1.0
        
        if hasattr(entity, 'stats') and hasattr(entity, 'role'):
            emotions = entity.stats.emotions
            
            # 긍정 효과
            if 'HAPPINESS' in emotions: multiplier += 0.10
            if 'DOPAMINE' in emotions: # 레벨별 처리는 생략하고 단순화하거나 추가 구현
                multiplier += 0.20
            if 'RAGE' in emotions:
                multiplier += 0.20
                
            # 부정 효과
            if 'FEAR' in emotions: multiplier -= 0.30
            if 'FATIGUE' in emotions: multiplier -= 0.15 # 평균치
            if 'PAIN' in emotions and not entity.stats.status_effects.get('NO_PAIN'): multiplier -= 0.15
            
            # 직업/버프 효과
            if entity.role.main_role == "POLICE": multiplier *= POLICE_SPEED_MULTI
            if entity.stats.status_effects.get('FAST_WORK'): multiplier *= 1.2
            
        if weather_type == 'SNOW': multiplier *= 0.8
        
        return base * max(0.2, multiplier)

    def _move_single_axis(self, entity, dx, dy, map_manager):
        # 1. 위치 이동
        entity.transform.x += dx
        entity.transform.y += dy
        
        # Rect 갱신 (충돌 체크용)
        # 히트박스 보정: 기존 코드처럼 rect를 약간 줄여서 사용
        # entity.rect는 32x32지만 실제 충돌 판정은 +6, +6, -12, -12
        cx = entity.transform.x + 6
        cy = entity.transform.y + 6
        cw = TILE_SIZE - 12
        ch = TILE_SIZE - 12
        hitbox = pygame.Rect(cx, cy, cw, ch)
        
        # 2. 맵 경계 체크
        map_w_px = map_manager.width * TILE_SIZE
        map_h_px = map_manager.height * TILE_SIZE
        
        if hitbox.left < 0: 
            entity.transform.x = -6
            hitbox.x = 0
        elif hitbox.right > map_w_px:
            entity.transform.x = map_w_px - TILE_SIZE + 6
            hitbox.right = map_w_px
            
        if hitbox.top < 0:
            entity.transform.y = -6
            hitbox.y = 0
        elif hitbox.bottom > map_h_px:
            entity.transform.y = map_h_px - TILE_SIZE + 6
            hitbox.bottom = map_h_px
            
        # 3. 타일 충돌 체크
        if entity.physics.no_clip: return

        # 충돌 검사 범위
        start_gx = max(0, int(hitbox.left // TILE_SIZE))
        end_gx = min(map_manager.width, int(hitbox.right // TILE_SIZE) + 1)
        start_gy = max(0, int(hitbox.top // TILE_SIZE))
        end_gy = min(map_manager.height, int(hitbox.bottom // TILE_SIZE) + 1)
        
        for y in range(start_gy, end_gy):
            for x in range(start_gx, end_gx):
                if map_manager.check_any_collision(x, y):
                    # 충돌 대상 타일 Rect
                    tile_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    
                    if hitbox.colliderect(tile_rect):
                        # 충돌 해결 및 위치 보정
                        if dx > 0: # 오른쪽 이동 중 충돌
                            hitbox.right = tile_rect.left
                            entity.transform.x = hitbox.x - 6
                        elif dx < 0: # 왼쪽 이동 중 충돌
                            hitbox.left = tile_rect.right
                            entity.transform.x = hitbox.x - 6
                            
                        if dy > 0: # 아래쪽 이동 중 충돌
                            hitbox.bottom = tile_rect.top
                            entity.transform.y = hitbox.y - 6
                        elif dy < 0: # 위쪽 이동 중 충돌
                            hitbox.top = tile_rect.bottom
                            entity.transform.y = hitbox.y - 6
