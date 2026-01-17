import pygame
import random
import math
import os
import glob
import time

P = {
    'VOID': (5, 5, 8),
    'WHITE': (200, 200, 205), 'BLACK': (25, 25, 30),
    'GREY_L': (150, 150, 160), 'GREY_M': (100, 100, 110), 'GREY_D': (50, 50, 60),
    'RED': (150, 50, 50), 'GREEN': (50, 90, 50), 'BLUE': (50, 70, 130),
    'YELLOW': (170, 150, 40), 'ORANGE': (150, 80, 30),
    'BROWN_L': (130, 100, 60), 'BROWN_M': (90, 60, 40), 'BROWN_D': (50, 35, 20),
    'WOOD_BASE': (90, 50, 30), 'WOOD_LIGHT': (120, 80, 50), 'WOOD_SHADOW': (50, 25, 15),
    'STONE_BASE': (70, 75, 85), 'STONE_LIGHT': (100, 105, 115), 'STONE_SHADOW': (40, 40, 50),
    'CONCRETE': (110, 110, 115), 'ASPHALT': (50, 50, 55), 'MARBLE': (200, 200, 210),
    'WATER_BASE': (40, 60, 100), 'WATER_LIGHT': (80, 120, 200), 'ICE_BASE': (180, 210, 230),
    'DIRT_BASE': (80, 65, 45), 'SAND_BASE': (170, 160, 110),
    'GRASS_BASE': (40, 70, 50), 'GRASS_LIGHT': (70, 110, 70), 'GRASS_SHADOW': (20, 35, 20),
    'BRICK_RED': (120, 50, 40), 'GOLD': (180, 140, 40), 'LAMP_ON': (255, 240, 180),
    'METAL_BASE': (90, 90, 95), 'METAL_LIGHT': (140, 140, 150), 'METAL_RUST': (110, 60, 50),
}

# --- 캐시 설정 ---
TEXTURE_CACHE = {}
CACHE_DIR = "cache_tiles"
MAX_CACHE_SIZE_MB = 50  # 최대 디스크 캐시 용량 (MB)

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def cleanup_disk_cache():
    """디스크 캐시 용량이 한계를 초과하면 오래된 파일부터 삭제"""
    try:
        files = glob.glob(os.path.join(CACHE_DIR, "*.png"))
        total_size = sum(os.path.getsize(f) for f in files)
        limit_size = MAX_CACHE_SIZE_MB * 1024 * 1024

        if total_size > limit_size:
            # 수정 시간(mtime) 기준 오름차순 정렬 (오래된 순)
            files.sort(key=os.path.getmtime)
            
            deleted_size = 0
            for f in files:
                sz = os.path.getsize(f)
                try:
                    os.remove(f)
                    deleted_size += sz
                    # 용량이 충분히 확보되면 중단 (여유분 10% 확보)
                    if total_size - deleted_size < limit_size * 0.9:
                        break
                except OSError:
                    pass
            print(f"[System] Cache Cleanup: Freed {deleted_size / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"[System] Cache Cleanup Error: {e}")

def clear_memory_cache():
    """메모리(RAM) 캐시 비우기 - 맵 변경 시 호출 권장"""
    TEXTURE_CACHE.clear()

# 모듈 로드 시 한 번 실행하여 디스크 용량 관리
cleanup_disk_cache()

def get_texture(tid, rotation=0):
    """캐시된 텍스처를 반환하거나 생성하여 저장 (Disk Cache 적용)"""
    key = (tid, rotation)

    # 1. 메모리 캐시 확인
    if key in TEXTURE_CACHE:
        return TEXTURE_CACHE[key]

    # 2. 디스크 캐시 확인
    filename = os.path.join(CACHE_DIR, f"tile_{tid}_{rotation}.png")
    if os.path.exists(filename):
        try:
            surf = pygame.image.load(filename).convert_alpha()
            TEXTURE_CACHE[key] = surf
            return surf
        except Exception as e:
            # 파일 손상 시 삭제 후 재생성
            try: os.remove(filename)
            except: pass

    # 3. 텍스처 신규 생성
    surf = create_texture(tid)

    if rotation != 0:
        surf = pygame.transform.rotate(surf, rotation)

    # 생성된 텍스처를 디스크에 저장
    try:
        pygame.image.save(surf, filename)
    except Exception as e:
        print(f"Error saving cache for {tid}: {e}")

    TEXTURE_CACHE[key] = surf
    return surf

def get_tile_category(tid): return tid // 1000000
def get_tile_type(tid): return (tid // 100000) % 10
def check_collision(tid): return ((tid // 10000) % 10) == 2
def get_tile_interaction(tid): return (tid // 1000) % 10
def get_tile_hiding(tid): return (tid // 100) % 10
def get_tile_name(tid): return TILE_DATA.get(tid, {}).get('name', 'Unknown')
def get_tile_function(tid): return get_tile_hiding(tid)

def fill(s, c): s.fill(c)
def rect(s, c, r, w=0, **kwargs): pygame.draw.rect(s, c, r, w, **kwargs)
def line(s, c, p1, p2, w=1, **kwargs): pygame.draw.line(s, c, p1, p2, w, **kwargs)
def circle(s, c, p, r, w=0, **kwargs): pygame.draw.circle(s, c, p, r, w, **kwargs)
def pixel(s, c, p): s.set_at(p, c)
def poly(s, c, pts, w=0, **kwargs): pygame.draw.polygon(s, c, pts, w, **kwargs)

def blend(c1, c2, r):
    return (int(c1[0]*(1-r)+c2[0]*r), int(c1[1]*(1-r)+c2[1]*r), int(c1[2]*(1-r)+c2[2]*r))

def noise_color(color, intensity=15):
    var = random.randint(-intensity, intensity)
    return (max(0, min(255, color[0]+var)), max(0, min(255, color[1]+var)), max(0, min(255, color[2]+var)))

def draw_pro_noise(surf, color, intensity=20):
    surf.fill(color)
    for _ in range(150):
        x, y = random.randint(0, 31), random.randint(0, 31)
        pixel(surf, noise_color(color, intensity), (x, y))

def draw_pixel_bevel(surf, rect_obj, base_col, light_col, dark_col, thickness=1):
    pygame.draw.rect(surf, base_col, rect_obj)
    pygame.draw.line(surf, dark_col, rect_obj.bottomleft, (rect_obj.right, rect_obj.bottom), thickness)
    pygame.draw.line(surf, dark_col, (rect_obj.right-1, rect_obj.top), (rect_obj.right-1, rect_obj.bottom), thickness)
    pygame.draw.line(surf, light_col, rect_obj.topleft, (rect_obj.right, rect_obj.top), thickness)
    pygame.draw.line(surf, light_col, rect_obj.topleft, (rect_obj.left, rect_obj.bottom), thickness)

def draw_wood_base(surf, color, vertical=False):
    dark = blend(color, P['BLACK'], 0.3)
    draw_pro_noise(surf, color, 15)
    if vertical:
        for x in range(0, 32, 8):
            line(surf, dark, (x, 0), (x, 31))
    else:
        for y in range(0, 32, 8):
            line(surf, dark, (0, y), (31, y))

def draw_brick_base(surf, color):
    fill(surf, P['GREY_D'])
    for y in range(0, 32, 8):
        off = 8 if (y // 8) % 2 else 0
        for x in range(off - 16, 32, 16):
            r_obj = pygame.Rect(x + 1, y + 1, 14, 6)
            draw_pixel_bevel(surf, r_obj, color, blend(color, P['WHITE'], 0.15), blend(color, P['BLACK'], 0.3))

def draw_grass_detailed(surf, base_col):
    fill(surf, base_col)
    light, shadow = P['GRASS_LIGHT'], P['GRASS_SHADOW']
    for _ in range(15):
        cx, cy = random.randint(2, 28), random.randint(2, 28)
        line(surf, shadow, (cx, cy), (cx, cy+3), 1)
        pixel(surf, light, (cx-1, cy-1))
        pixel(surf, light, (cx+1, cy-1))
        pixel(surf, light, (cx, cy))

def draw_10001(s):
    draw_pro_noise(s, P['DIRT_BASE'], 25)

def draw_10002(s):
    fill(s, P['GRASS_BASE'])
    for _ in range(15):
        cx, cy = random.randint(2, 28), random.randint(2, 28)
        line(s, P['GRASS_SHADOW'], (cx, cy), (cx, cy+3))
        pixel(s, P['GRASS_LIGHT'], (cx-1, cy-1))

def draw_10003(s):
    draw_pro_noise(s, P['GREY_M'], 10)
    for _ in range(15):
        circle(s, P['GREY_D'], (random.randint(4,27), random.randint(4,27)), 2)

def draw_10004(s):
    draw_pro_noise(s, P['SAND_BASE'], 10)
    for y in [10, 22]:
        for x in range(0, 32, 4):
            pixel(s, P['BROWN_L'], (x, y + int(math.sin(x)*2)))

def draw_10005(s):
    fill(s, P['WATER_BASE'])
    for y in range(4, 32, 8):
        line(s, P['WHITE'], (4, y), (12, y), 1)

def draw_10006(s):
    draw_pro_noise(s, P['STONE_SHADOW'], 40)
    for _ in range(3):
        circle(s, P['BLACK'], (random.randint(5,25), random.randint(5,25)), 4)

def draw_10007(s):
    draw_pro_noise(s, P['STONE_BASE'], 20)
    for _ in range(6):
        circle(s, P['GREEN'], (random.randint(4,27), random.randint(4,27)), random.randint(3,6))

def draw_10008(s):
    draw_pro_noise(s, P['WOOD_LIGHT'], 15)
    for y in range(0, 32, 8):
        line(s, P['BROWN_D'], (0, y), (31, y))

def draw_10009(s):
    draw_pro_noise(s, P['WOOD_BASE'], 15)
    for x in range(0, 32, 8):
        line(s, P['BROWN_D'], (x, 0), (x, 31))

def draw_10010(s):
    draw_pro_noise(s, P['WHITE'], 5)
    for _ in range(3):
        line(s, P['GREY_L'], (random.randint(0,31), 0), (random.randint(0,31), 31))

def draw_10011(s):
    for y in range(0, 32, 16):
        for x in range(0, 32, 16):
            c = P['WHITE'] if (x+y)%32==0 else P['GREY_M']
            rect(s, c, (x, y, 16, 16))
            rect(s, P['BLACK'], (x, y, 16, 16), 1)

def draw_10012(s):
    draw_pro_noise(s, P['RED'], 5)
    rect(s, P['GOLD'], (2, 2, 28, 28), 1)
    circle(s, P['GOLD'], (16, 16), 4, 1)

def draw_10013(s):
    draw_pro_noise(s, P['BLUE'], 5)
    for i in range(4, 32, 8):
        line(s, P['WHITE'], (i, 4), (i, 28))

def draw_10014(s):
    draw_pro_noise(s, P['CONCRETE'], 10)
    rect(s, P['GREY_D'], (4, 4, 2, 2))
    rect(s, P['GREY_D'], (24, 24, 2, 2))

def draw_10015(s):
    draw_pro_noise(s, P['ASPHALT'], 30)
    for _ in range(20):
        pixel(s, P['GREY_L'], (random.randint(0,31), random.randint(0,31)))

def draw_10016(s):
    draw_pro_noise(s, P['ASPHALT'], 20)
    rect(s, P['WHITE'], (12, 2, 8, 28))

def draw_10017(s):
    draw_pro_noise(s, P['CONCRETE'], 15)
    line(s, P['BLACK'], (16, 16), (4, 4))
    line(s, P['BLACK'], (16, 16), (28, 10))

def draw_10018(s):
    draw_pro_noise(s, P['WHITE'], 5)
    rect(s, P['GREY_L'], (0, 0, 32, 32), 1)
    line(s, P['GREY_L'], (16, 0), (16, 31))
    line(s, P['GREY_L'], (0, 16), (31, 16))

def draw_10019(s):
    fill(s, P['BLACK'])
    for i in range(4, 32, 8):
        line(s, P['METAL_BASE'], (i, 0), (i, 31), 2)
        line(s, P['METAL_BASE'], (0, i), (31, i), 2)

def draw_10020(s):
    draw_pro_noise(s, P['ICE_BASE'], 5)
    line(s, (255, 255, 255, 150), (5, 5), (20, 25), 2)

def draw_11001(s):
    fill(s, (20, 30, 60))
    for y in range(0, 32, 4):
        line(s, (10, 20, 40), (0, y), (31, y))

def draw_11002(s):
    fill(s, P['RED'])
    for _ in range(5):
        circle(s, P['ORANGE'], (random.randint(4, 27), random.randint(4, 27)), 5)
    for _ in range(3):
        pixel(s, P['BLACK'], (random.randint(0, 31), random.randint(0, 31)))

def draw_11003(s):
    fill(s, P['BROWN_D'])
    poly(s, P['BLACK'], [(0, 0), (15, 0), (0, 31)])

def draw_21001(s):
    fill(s, P['GREY_D'])
    for y in range(0, 32, 8):
        off = 8 if (y//8)%2 else 0
        for x in range(off-16, 32, 16):
            rect(s, P['BRICK_RED'], (x+1, y+1, 14, 6))

def draw_21002(s):
    fill(s, P['BLACK'])
    for y in range(0, 32, 8):
        for x in range(0, 32, 8):
            rect(s, P['STONE_BASE'], (x+1, y+1, 6, 6))

def draw_21003(s):
    fill(s, P['STONE_BASE'])
    for y in range(0, 32, 8):
        off = 8 if (y // 8) % 2 else 0
        for x in range(off - 16, 32, 16):
            r_obj = pygame.Rect(x + 1, y + 1, 14, 6)
            draw_pixel_bevel(s, r_obj, P['STONE_BASE'], P['STONE_LIGHT'], P['STONE_SHADOW'])
    for _ in range(4):
        circle(s, blend(P['GREEN'], P['BLACK'], 0.2), (random.randint(5, 25), random.randint(5, 25)), random.randint(4, 7))

def draw_21004(s):
    dark = blend(P['WOOD_BASE'], P['BLACK'], 0.3)
    draw_pro_noise(s, P['WOOD_BASE'], 15)
    for x in range(0, 32, 8):
        line(s, dark, (x, 0), (x, 31))

def draw_21005(s):
    dark = blend(P['WOOD_SHADOW'], P['BLACK'], 0.3)
    draw_pro_noise(s, P['WOOD_SHADOW'], 15)
    for y in range(0, 32, 8):
        line(s, dark, (0, y), (31, y))

def draw_21006(s):
    draw_pro_noise(s, P['WHITE'], 8)
    rect(s, P['GREY_M'], (0, 30, 32, 2))

def draw_21007(s):
    draw_pro_noise(s, (200, 160, 160), 5)
    for y in range(4, 32, 12):
        for x in range(4, 32, 12):
            poly(s, P['RED'], [(x, y-3), (x+3, y), (x, y+3), (x-3, y)])

def draw_21008(s):
    fill(s, (220, 230, 255))
    for i in range(0, 32, 8):
        line(s, (180, 190, 220), (i, 0), (i, 31))
        line(s, (180, 190, 220), (0, i), (31, i))

def draw_21009(s):
    draw_pixel_bevel(s, pygame.Rect(0, 0, 32, 32), P['METAL_LIGHT'], P['WHITE'], P['BLACK'])
    circle(s, P['GREY_D'], (4, 4), 1)
    circle(s, P['GREY_D'], (28, 28), 1)

def draw_21010(s):
    draw_pro_noise(s, P['METAL_BASE'], 10)
    for _ in range(12):
        circle(s, P['METAL_RUST'], (random.randint(0, 31), random.randint(0, 31)), random.randint(2, 4))

def draw_21011(s):
    fill(s, (150, 200, 255, 100))
    line(s, P['WHITE'], (5, 31), (31, 5), 2)

def draw_21012(s):
    fill(s, (150, 200, 255, 120))
    for i in range(0, 32, 8):
        line(s, P['BLACK'], (i, 0), (i, 31))
        line(s, P['BLACK'], (0, i), (31, i))

def draw_21013(s):
    draw_pro_noise(s, P['BROWN_M'], 15)
    for x in range(0, 32, 8):
        line(s, P['BLACK'], (x, 0), (x, 31))
    for y in [6, 16, 26]:
        rect(s, P['BLACK'], (2, y, 28, 2))
        for x in range(4, 28, 4):
            if random.random() > 0.3:
                rect(s, random.choice([P['RED'], P['BLUE'], P['WHITE']]), (x, y-4, 3, 4))

def draw_21014(s):
    draw_pro_noise(s, P['STONE_SHADOW'], 40)
    line(s, P['BLACK'], (0, 10), (12, 15), 2)
    line(s, P['BLACK'], (12, 15), (31, 12), 2)

def draw_21015(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_M'], (4, 0, 6, 32))
    rect(s, P['BROWN_M'], (22, 0, 6, 32))
    rect(s, P['BROWN_D'], (0, 6, 32, 4))
    rect(s, P['BROWN_D'], (0, 22, 32, 4))

def draw_21016(s):
    fill(s, (0, 0, 0, 0))
    for x in [4, 12, 20, 28]:
        rect(s, P['METAL_BASE'], (x, 0, 2, 32))
    rect(s, P['GREY_D'], (0, 4, 32, 2))

def draw_21017(s):
    fill(s, (0, 0, 0, 0))
    for x in range(4, 32, 8):
        rect(s, P['GREY_D'], (x, 0, 3, 32))

def draw_door(s, tid, name, col):
    draw_brick_base(s, P['STONE_SHADOW'])
    if "Open" in name:
        rect(s, P['BLACK'], (4, 4, 24, 24))
        rect(s, col, (24, 4, 4, 24))
    elif tid == 5310005:
        rect(s, P['BLACK'], (4, 4, 24, 24))
        line(s, col, (4, 4), (20, 20), 3)
    else:

        draw_pixel_bevel(s, pygame.Rect(4,4,24,24), col, blend(col, P['WHITE'], 0.2), blend(col, P['BLACK'], 0.3))
        if "Locked" in name:
            rect(s, P['GOLD'], (13, 14, 6, 5))
            circle(s, P['GOLD'], (16, 14), 2, 1)
        else:
            circle(s, P['YELLOW'], (22, 16), 2)

def draw_chest(s, tid, name):
    rect(s, P['WOOD_BASE'], (4, 8, 24, 16))
    rect(s, P['BLACK'], (4, 8, 24, 16), 1)
    if "Closed" in name:
        rect(s, P['WOOD_LIGHT'], (2, 6, 28, 6))
        rect(s, P['GOLD'], (14, 10, 4, 6))
        rect(s, P['GOLD'], (2, 6, 28, 2))
    else:
        rect(s, P['BLACK'], (6, 10, 20, 12))
        rect(s, P['WOOD_SHADOW'], (2, 2, 28, 6))

def draw_40101(s):
    fill(s, (0, 0, 0, 0))
    for ox, oy in [(10, 14), (22, 14), (16, 8), (16, 22)]:
        circle(s, P['GRASS_BASE'], (ox, oy), 8)

def draw_40102(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['GREEN'], (14, 10, 4, 22))
    circle(s, P['YELLOW'], (16, 8), 5)

def draw_40103(s):
    fill(s, (200, 200, 200, 80))
    for _ in range(3):
        circle(s, (255, 255, 255, 40), (random.randint(8, 24), random.randint(8, 24)), 8)

def draw_40104(s):
    fill(s, (0, 0, 0, 0))
    circle(s, (0, 0, 0, 120), (16, 16), 12)

def draw_40105(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['WHITE'], (6, 6, 20, 24))
    circle(s, P['BLUE'], (16, 16), 6, 2)

def draw_flower(s, col):
    fill(s, (0, 0, 0, 0))
    line(s, P['GREEN'], (16, 31), (16, 16), 2)
    circle(s, col, (16, 12), 6)
    circle(s, P['YELLOW'], (16, 12), 2)

def draw_40001(s): draw_flower(s, P['RED'])
def draw_40002(s): draw_flower(s, P['YELLOW'])

def draw_40003(s):
    fill(s, (0, 0, 0, 0))
    for _ in range(3):
        line(s, P['GREEN'], (16, 31), (random.randint(10, 22), 10), 2)

def draw_40004(s):
    fill(s, (0, 0, 0, 0))
    circle(s, P['GREY_M'], (12, 20), 4)
    circle(s, P['GREY_L'], (20, 24), 3)

def draw_40005(s):
    fill(s, (0, 0, 0, 0))
    circle(s, P['GREEN'], (16, 16), 12)
    poly(s, (0, 0, 0, 0), [(16, 16), (28, 8), (28, 24)])

def draw_41001(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['WOOD_SHADOW'], (12, 0, 8, 32))
    line(s, P['BLACK'], (12, 10), (20, 10))

def draw_41002(s):
    fill(s, (0, 0, 0, 0))
    line(s, P['WOOD_SHADOW'], (16, 31), (16, 10), 3)
    line(s, P['WOOD_SHADOW'], (16, 20), (6, 10), 2)

def draw_41003(s):
    fill(s, (0, 0, 0, 0))
    poly(s, P['STONE_BASE'], [(8, 28), (4, 16), (16, 4), (28, 16), (24, 28)])

def draw_41004(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['GREEN'], (13, 8, 6, 24))
    rect(s, P['GREEN'], (6, 14, 8, 4))

def draw_41005(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['GREY_M'], (4, 24, 24, 6))
    rect(s, P['BLUE'], (14, 10, 4, 14))

def draw_41006(s):
    fill(s, (0, 0, 0, 0))
    circle(s, P['GREY_D'], (16, 16), 14, 3)
    circle(s, P['BLACK'], (16, 16), 10)

def draw_51201(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_L'], (4, 8, 24, 20))
    line(s, P['BLACK'], (4, 8), (28, 28))

def draw_51202(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_M'], (4, 2, 24, 28))
    line(s, P['BLACK'], (16, 2), (16, 30))

def draw_51203(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_M'], (2, 10, 28, 12))
    rect(s, P['BROWN_D'], (4, 22, 4, 8))

def draw_51204(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_D'], (2, 4, 28, 24))
    rect(s, P['WHITE'], (4, 6, 24, 8))
    rect(s, P['BLUE'], (4, 14, 24, 14))

def draw_51205(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['GREY_M'], (10, 10, 12, 18))

def draw_51206(s):
    fill(s, P['GREY_M'])
    for i in range(6, 30, 6):
        line(s, P['BLACK'], (4, i), (28, i), 2)

def draw_51207(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['RED'], (8, 4, 16, 24), border_radius=3)

def draw_51208(s):
    fill(s, (0, 0, 0, 0))
    circle(s, P['WHITE'], (16, 22), 8)
    rect(s, P['WHITE'], (8, 4, 16, 10))

def draw_51001(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_M'], (2, 8, 28, 16))
    rect(s, P['BROWN_D'], (4, 24, 4, 6))

def draw_51002(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_L'], (8, 4, 16, 16))
    rect(s, P['BROWN_M'], (8, 20, 3, 8))

def draw_51003(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_D'], (4, 8, 24, 16), border_radius=4)

def draw_51004(s):
    draw_wood_base(s, P['BROWN_M'], True)
    for y in [10, 22]:
        line(s, P['BLACK'], (2, y), (30, y), 2)

def draw_51005(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BLACK'], (2, 6, 28, 20))
    rect(s, P['GREY_D'], (4, 8, 24, 16))

def draw_51006(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['WHITE'], (4, 2, 24, 28))
    line(s, P['GREY_M'], (4, 12), (28, 12))

def draw_51007(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['RED'], (4, 2, 24, 28))
    rect(s, P['BLACK'], (8, 6, 16, 12))

def draw_51008(s):
    fill(s, P['BLACK'])
    rect(s, P['WHITE'], (4, 20, 24, 8))
    for x in range(6, 28, 4):
        rect(s, P['BLACK'], (x, 20, 2, 5))

def draw_51301(s):
    draw_pro_noise(s, P['STONE_SHADOW'], 20)
    for _ in range(4):
        circle(s, P['METAL_LIGHT'], (random.randint(8, 24), random.randint(8, 24)), 4)

def draw_51302(s):
    fill(s, (0, 0, 0, 0))
    for _ in range(6):
        pts_list = [(random.randint(0, 31), random.randint(0, 31)) for _ in range(3)]
        poly(s, P['GREY_M'], pts_list)

def draw_51303(s):
    fill(s, P['GREY_D'])
    rect(s, P['BLACK'], (8, 12, 16, 16), border_top_left_radius=8)
    circle(s, P['ORANGE'], (16, 22), 5)

def draw_51305(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_L'], (4, 12, 24, 14))
    rect(s, P['WHITE'], (10, 14, 12, 8))

def draw_51309(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BLACK'], (10, 24, 12, 4))
    line(s, P['BLACK'], (16, 24), (16, 10), 4)

def draw_51310(s):
    fill(s, P['METAL_LIGHT'])
    rect(s, P['RED'], (14, 2, 4, 4))

def draw_51311(s):
    draw_pro_noise(s, P['METAL_RUST'], 10)
    circle(s, P['YELLOW'], (16, 16), 2)

def draw_51312(s):
    fill(s, P['METAL_BASE'])
    rect(s, P['BLACK'], (6, 6, 20, 14))

def draw_farm(s, tid, name):
    fill(s, P['DIRT_BASE'])
    for i in range(4, 32, 8):
        line(s, P['BROWN_D'], (0, i), (31, i), 1)
    if "Sprout" in name:
        line(s, P['GREEN'], (16, 20), (16, 12), 2)
    elif "Grown" in name:
        circle(s, P['ORANGE'], (16, 15), 4)

def draw_61001(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['METAL_BASE'], (15, 10, 2, 22))
    circle(s, P['LAMP_ON'], (16, 10), 6)

def draw_61002(s):
    fill(s, (0, 0, 0, 0))
    rect(s, P['BROWN_D'], (14, 20, 4, 12))
    poly(s, P['YELLOW'], [(8, 20), (24, 20), (16, 8)])

def draw_61003(s):
    fill(s, P['BRICK_RED'])
    rect(s, P['BLACK'], (8, 12, 16, 20), border_top_left_radius=8)

def draw_61004(s):
    fill(s, P['GREEN'])
    rect(s, P['WHITE'], (6, 10, 20, 12), 1)

def draw_61005(s):
    fill(s, (0, 0, 0, 0))
    poly(s, P['GREY_M'], [(4, 4), (16, 10), (4, 16)])
    circle(s, P['RED'], (16, 10), 2)

def draw_60001(s):
    fill(s, (0, 0, 0, 0))
    for _ in range(5):
        circle(s, (100, 50, 200, 100), (16, 16), random.randint(5, 15))

def draw_60002(s):
    fill(s, (0, 0, 0, 0))
    poly(s, P['YELLOW'], [(4, 16), (16, 4), (16, 12), (28, 12), (28, 20), (16, 20), (16, 28)])

def draw_60003(s):
    fill(s, P['METAL_BASE'])
    for x in [8, 24]:
        poly(s, P['GREY_L'], [(x, 31), (x-4, 16), (x+4, 16)])

def create_texture(tid):
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    if tid not in TILE_DATA:
        fill(s, (255, 0, 255)); return s
    d = TILE_DATA[tid]
    name, col = d['name'], d.get('color', P['GREY_M'])

    if tid == 1110000: draw_10001(s)
    elif tid == 1110001: draw_10002(s)
    elif tid == 1110002: draw_10003(s)
    elif tid == 1110003: draw_10004(s)
    elif tid == 1110004: draw_10005(s)
    elif tid == 1110005: draw_10006(s)
    elif tid == 1110006: draw_10007(s)
    elif tid == 1110007: draw_10008(s)
    elif tid == 1110008: draw_10009(s)
    elif tid == 1110009: draw_10010(s)
    elif tid == 1110010: draw_10014(s)
    elif tid == 1110011: draw_10015(s)
    elif tid == 1110012: draw_10016(s)
    elif tid == 1110013: draw_10017(s)
    elif tid == 1110014: draw_10019(s)
    elif tid == 1110015: draw_10020(s)
    elif tid == 1120016: draw_11001(s)
    elif tid == 1120017: draw_11002(s)
    elif tid == 1120018: draw_11003(s)
    elif tid == 2110000: draw_10011(s)
    elif tid == 2110001: draw_10012(s)
    elif tid == 2110002: draw_10013(s)
    elif tid == 2110003: draw_10018(s)
    elif tid == 3220000: draw_21001(s)
    elif tid == 3220001: draw_21002(s)
    elif tid == 3220002: draw_21003(s)
    elif tid == 3220003: draw_21004(s)
    elif tid == 3220004: draw_21005(s)
    elif tid == 3220005: draw_21006(s)
    elif tid == 3220006: draw_21007(s)
    elif tid == 3220007: draw_21008(s)
    elif tid == 3220008: draw_21009(s)
    elif tid == 3220009: draw_21010(s)
    elif tid == 3220010: draw_21011(s)
    elif tid == 3220011: draw_21012(s)
    elif tid == 3220012: draw_21013(s)
    elif tid == 3220013: draw_21014(s)
    elif tid == 4220000: draw_21015(s)
    elif tid == 4220001: draw_21016(s)
    elif tid == 4220002: draw_21017(s)
    elif tid // 1000000 == 5:
        if tid in [5321025, 5310025]: draw_chest(s, tid, name)
        else: draw_door(s, tid, name, col)
    elif tid == 6310000: draw_40001(s)
    elif tid == 6310001: draw_40002(s)
    elif tid == 6310002: draw_40003(s)
    elif tid == 6310003: draw_40005(s)
    elif tid == 6310008: draw_41004(s)
    elif tid == 6310104: draw_40101(s)
    elif tid == 6310105: draw_40102(s)
    elif tid == 6310106: draw_41001(s)
    elif tid == 6310107: draw_41002(s)
    elif tid == 7310000: draw_40004(s)
    elif tid == 7310007: draw_60001(s)
    elif tid == 7310008: draw_60002(s)
    elif tid == 7310009: draw_60003(s)
    elif tid == 7310010: draw_61001(s)
    elif tid == 7310011: draw_61005(s)
    elif tid == 7310101: draw_40103(s)
    elif tid == 7310102: draw_40104(s)
    elif tid == 7310103: draw_40105(s)
    elif tid == 7320005: draw_41005(s)
    elif tid == 7320006: draw_41006(s)
    elif tid == 7320204: draw_41003(s)
    elif tid == 8310016: draw_61002(s)
    elif tid == 8310208: draw_51201(s)
    elif tid == 8320001: draw_51002(s)
    elif tid == 8320004: draw_51005(s)
    elif tid == 8320007: draw_51008(s)
    elif tid == 8320017: draw_61003(s)
    elif tid == 8320018: draw_61004(s)
    elif tid == 8320200: draw_51001(s)
    elif tid == 8320202: draw_51003(s)
    elif tid == 8320203: draw_51004(s)
    elif tid == 8320205: draw_51006(s)
    elif tid == 8320209: draw_51202(s)
    elif tid == 8320210: draw_51203(s)
    elif tid == 8320212: draw_51205(s)
    elif tid == 8320213: draw_51206(s)
    elif tid == 8320214: draw_51207(s)
    elif tid == 8320215: draw_51208(s)
    elif tid == 8321006: draw_51007(s)
    elif tid == 8321211: draw_51204(s)
    elif tid == 9312000: draw_farm(s, tid, name)
    elif tid == 9312001: draw_farm(s, tid, name)
    elif tid == 9312002: draw_farm(s, tid, name)
    elif tid == 9312003: draw_10005(s)
    elif tid == 9322004: draw_51301(s)
    elif tid == 9322005: draw_51302(s)
    elif tid == 9322006: draw_51303(s)
    elif tid == 9322007: draw_51305(s)
    elif tid == 9322008: draw_51309(s)
    elif tid == 9322009: draw_51310(s)
    elif tid == 9322010: draw_51311(s)
    elif tid == 9322011: draw_51312(s)
    else:
        draw_pro_noise(s, col, 20)
    return s

TILE_DATA = {
    1110000: {'name': 'Dirt Floor (흙 바닥)', 'color': P['DIRT_BASE']},
    1110001: {'name': 'Grass Floor (풀 바닥)', 'color': P['GRASS_BASE']},
    1110002: {'name': 'Gravel Floor (자갈 바닥)', 'color': P['STONE_BASE']},
    1110003: {'name': 'Sand Floor (모래 바닥)', 'color': P['SAND_BASE']},
    1110004: {'name': 'Shallow Water (얕은 물)', 'color': P['WATER_BASE']},
    1110005: {'name': 'Cave Floor (동굴 바닥)', 'color': P['STONE_SHADOW']},
    1110006: {'name': 'Mossy Stone (이끼 낀 돌)', 'color': P['STONE_BASE']},
    1110007: {'name': 'Wood Floor L (밝은 나무)', 'color': P['WOOD_LIGHT']},
    1110008: {'name': 'Wood Floor D (어두운 나무)', 'color': P['WOOD_BASE']},
    1110009: {'name': 'Marble Floor (대리석)', 'color': P['MARBLE']},
    1110010: {'name': 'Concrete Floor (콘크리트)', 'color': P['CONCRETE']},
    1110011: {'name': 'Asphalt Road (아스팔트)', 'color': P['BLACK']},
    1110012: {'name': 'Road Line (차선)', 'color': P['ASPHALT']},
    1110013: {'name': 'Broken Concrete (깨진 바닥)', 'color': P['CONCRETE']},
    1110014: {'name': 'Iron Grate (철창 바닥)', 'color': P['METAL_BASE']},
    1110015: {'name': 'Ice (얼음)', 'color': P['ICE_BASE']},
    1120016: {'name': 'Deep Water (깊은 물)', 'color': (20, 30, 60)},
    1120017: {'name': 'Lava (용암)', 'color': P['RED']},
    1120018: {'name': 'Cliff (절벽)', 'color': P['BROWN_D']},
    2110000: {'name': 'Checkered Tile (체크무늬)', 'color': P['WHITE']},
    2110001: {'name': 'Red Carpet (레드 카펫)', 'color': P['RED']},
    2110002: {'name': 'Blue Carpet (블루 카펫)', 'color': P['BLUE']},
    2110003: {'name': 'Lab Tile (실험실 바닥)', 'color': P['WHITE']},
    3220000: {'name': 'Red Brick Wall (붉은 벽돌)', 'color': P['BRICK_RED']},
    3220001: {'name': 'Grey Brick Wall (회색 벽돌)', 'color': P['STONE_BASE']},
    3220002: {'name': 'Mossy Wall (이끼 벽)', 'color': P['STONE_BASE']},
    3220003: {'name': 'Wood Wall (나무 벽)', 'color': P['WOOD_BASE']},
    3220004: {'name': 'Log Wall (통나무 벽)', 'color': P['WOOD_SHADOW']},
    3220005: {'name': 'White Wall (흰 벽)', 'color': P['WHITE']},
    3220006: {'name': 'Wallpaper (벽지)', 'color': (200, 160, 160)},
    3220007: {'name': 'Toilet Tile Wall (타일 벽)', 'color': (200, 220, 255)},
    3220008: {'name': 'Lab Metal Wall (금속 벽)', 'color': P['METAL_LIGHT']},
    3220009: {'name': 'Rusty Wall (녹슨 벽)', 'color': P['ORANGE']},
    3220010: {'name': 'Glass Wall (유리 벽)', 'color': (200, 220, 255)},
    3220011: {'name': 'Reinforced Glass (강화 유리)', 'color': (150, 180, 200)},
    3220012: {'name': 'Bookshelf Wall (책장 벽)', 'color': P['BROWN_M']},
    3220013: {'name': 'Cave Wall (동굴 벽)', 'color': P['STONE_SHADOW']},
    4220000: {'name': 'Wood Fence (나무 울타리)', 'color': P['WOOD_LIGHT']},
    4220001: {'name': 'Iron Fence (철 울타리)', 'color': P['METAL_BASE']},
    4220002: {'name': 'Prison Bars (창살)', 'color': P['STONE_SHADOW']},
    5310000: {'name': 'Wood Door Open (나무문 열림)', 'color': P['WOOD_BASE']},
    5310001: {'name': 'Iron Door Open (철문 열림)', 'color': P['METAL_BASE']},
    5310002: {'name': 'Glass Door Open (유리문 열림)', 'color': (200, 220, 255)},
    5310003: {'name': 'Prison Door Open (철창문 열림)', 'color': P['STONE_SHADOW']},
    5310004: {'name': 'Lab Door Open (연구소문 열림)', 'color': P['WHITE']},
    5310005: {'name': 'Broken Door (부서진 문)', 'color': P['WOOD_SHADOW']},
    5321008: {'name': 'Glass Door Closed (유리문 닫힘)', 'color': (200, 220, 255)},
    5321009: {'name': 'Prison Door Closed (철창문 닫힘)', 'color': P['STONE_SHADOW']},
    5321010: {'name': 'Lab Door Closed (연구소문 닫힘)', 'color': P['WHITE']},
    5321206: {'name': 'Wood Door Closed (나무문 닫힘)', 'color': P['WOOD_BASE']},
    5321207: {'name': 'Iron Door Closed (철문 닫힘)', 'color': P['METAL_BASE']},
    5323220: {'name': 'Wood Door Locked (나무문 잠김)', 'color': P['WOOD_BASE']},
    5323221: {'name': 'Iron Door Locked (철문 잠김)', 'color': P['METAL_BASE']},
    5323022: {'name': 'Glass Door Locked (유리문 잠김)', 'color': (200, 220, 255)},
    5323023: {'name': 'Prison Door Locked (철창문 잠김)', 'color': P['STONE_SHADOW']},
    5323024: {'name': 'Lab Door Locked (연구소문 잠김)', 'color': P['WHITE']},


    5321025: {'name': 'Treasure Chest Closed (보물상자)', 'color': P['WOOD_LIGHT']},
    5310025: {'name': 'Treasure Chest Open (빈 상자)', 'color': P['WOOD_SHADOW']},

    6310000: {'name': 'Red Flower (빨간 꽃)', 'color': P['RED']},
    6310001: {'name': 'Yellow Flower (노란 꽃)', 'color': P['YELLOW']},
    6310002: {'name': 'Weed (잡초)', 'color': P['GREEN']},
    6310003: {'name': 'Lotus (연잎)', 'color': P['GRASS_BASE']},
    6310008: {'name': 'Cactus (선인장)', 'color': P['GREEN']},
    6310104: {'name': 'Tall Bush (덤불)', 'color': P['GRASS_BASE']},
    6310105: {'name': 'Corn Field (옥수수)', 'color': P['YELLOW']},
    6310106: {'name': 'Tree Trunk (나무)', 'color': P['WOOD_SHADOW']},
    6310107: {'name': 'Dead Tree (죽은 나무)', 'color': P['WOOD_SHADOW']},
    7310000: {'name': 'Pebble (자갈)', 'color': P['STONE_LIGHT']},
    7310007: {'name': 'Portal (포털)', 'color': (100, 50, 200)},
    7310008: {'name': 'Exit Mark (출구)', 'color': P['YELLOW']},
    7310009: {'name': 'Spike Trap (함정)', 'color': P['METAL_BASE']},
    7310010: {'name': 'Street Light (가로등)', 'color': P['METAL_BASE']},
    7310011: {'name': 'CCTV Camera (CCTV)', 'color': P['METAL_LIGHT']},
    7310101: {'name': 'Dense Fog (안개)', 'color': P['GREY_L']},
    7310102: {'name': 'Shadow (그림자)', 'color': P['BLACK']},
    7310103: {'name': 'Laundry (빨래)', 'color': P['WHITE']},
    7320005: {'name': 'Fountain (분수)', 'color': P['STONE_LIGHT']},
    7320006: {'name': 'Well (우물)', 'color': P['STONE_SHADOW']},
    7320204: {'name': 'Rock (바위)', 'color': P['STONE_BASE']},
    8310016: {'name': 'Lamp (램프)', 'color': P['YELLOW']},
    8310208: {'name': 'Box (상자)', 'color': P['WOOD_LIGHT']},
    8320001: {'name': 'Wood Chair (의자)', 'color': P['WOOD_LIGHT']},
    8320004: {'name': 'TV (텔레비전)', 'color': P['BLACK']},
    8320007: {'name': 'Piano (피아노)', 'color': P['BLACK']},
    8320017: {'name': 'Fireplace (벽난로)', 'color': P['BRICK_RED']},
    8320018: {'name': 'Exit Sign (비상구)', 'color': P['GREEN']},
    8320200: {'name': 'Dining Table (식탁)', 'color': P['WOOD_BASE']},
    8320202: {'name': 'Sofa (소파)', 'color': P['WOOD_SHADOW']},
    8320203: {'name': 'Bookshelf (책장)', 'color': P['WOOD_BASE']},
    8320205: {'name': 'Refrigerator (냉장고)', 'color': P['WHITE']},
    8320209: {'name': 'Closet (옷장)', 'color': P['WOOD_BASE']},
    8320210: {'name': 'Desk (책상)', 'color': P['WOOD_BASE']},
    8320212: {'name': 'Trash Can (쓰레기통)', 'color': P['METAL_BASE']},
    8320213: {'name': 'Vent (환풍구)', 'color': P['METAL_BASE']},
    8320214: {'name': 'Drum Barrel (드럼통)', 'color': P['RED']},
    8320215: {'name': 'Toilet (변기)', 'color': P['WHITE']},
    8321006: {'name': 'Vending Machine (자판기)', 'color': P['RED']},
    8321211: {'name': 'Bed (침대)', 'color': P['BLUE']},
    9312000: {'name': 'Empty Field (빈 밭)', 'color': P['DIRT_BASE']},
    9312001: {'name': 'Sprout Field (새싹)', 'color': P['DIRT_BASE']},
    9312002: {'name': 'Grown Field (수확)', 'color': P['DIRT_BASE']},
    9312003: {'name': 'Fishing Spot (낚시터)', 'color': P['BLUE']},
    9322004: {'name': 'Iron Ore (철광석)', 'color': P['STONE_SHADOW']},
    9322005: {'name': 'Rubble (잔해)', 'color': P['STONE_BASE']},
    9322006: {'name': 'Furnace (용광로)', 'color': P['STONE_SHADOW']},
    9322007: {'name': 'Cutting Board (도마)', 'color': P['WOOD_LIGHT']},
    9322008: {'name': 'Microscope (현미경)', 'color': P['WHITE']},
    9322009: {'name': 'Surgery Table (수술대)', 'color': P['METAL_LIGHT']},
    9322010: {'name': 'Broken Panel (고장난 패널)', 'color': P['METAL_RUST']},
    9322011: {'name': 'Computer (컴퓨터)', 'color': P['METAL_BASE']},
}

NEW_ID_MAP = {
    10001: 1110000, 10002: 1110001, 10003: 1110002, 10004: 1110003, 10005: 1110004, 10006: 1110005,
    10007: 1110006, 10008: 1110007, 10009: 1110008, 10010: 1110009, 10014: 1110010, 10015: 1110011,
    10016: 1110012, 10017: 1110013, 10019: 1110014, 10020: 1110015, 11001: 1120016, 11002: 1120017,
    11003: 1120018, 10011: 2110000, 10012: 2110001, 10013: 2110002, 10018: 2110003, 21001: 3220000,
    21002: 3220001, 21003: 3220002, 21004: 3220003, 21005: 3220004, 21006: 3220005, 21007: 3220006,
    21008: 3220007, 21009: 3220008, 21010: 3220009, 21011: 3220010, 21012: 3220011, 21013: 3220012,
    21014: 3220013, 21015: 4220000, 21016: 4220001, 21017: 4220002, 30001: 5310000, 30002: 5310001,
    30003: 5310002, 30004: 5310003, 30005: 5310004, 30099: 5310005, 31303: 5321008, 31304: 5321009,
    31305: 5321010, 31301: 5321206, 31302: 5321207, 40001: 6310000, 40002: 6310001, 40003: 6310002,
    40005: 6310003, 41004: 6310008, 40101: 6310104, 40102: 6310105, 41001: 6310106, 41002: 6310107,
    40004: 7310000, 60001: 7310007, 60002: 7310008, 60003: 7310009, 61001: 7310010, 61005: 7310011,
    40103: 7310101, 40104: 7310102, 40105: 7310103, 41005: 7320005, 41006: 7320006, 41003: 7320204,
    61002: 8310016, 51201: 8310208, 51002: 8320001, 51005: 8320004, 51008: 8320007, 61003: 8320017,
    61004: 8320018, 51001: 8320200, 51003: 8320202, 51004: 8320203, 51006: 8320205, 51202: 8320209,
    51203: 8320210, 51205: 8320212, 51206: 8320213, 51207: 8320214, 51208: 8320215, 51007: 8321006,
    51204: 8321211, 10306: 9312000, 10307: 9312001, 10308: 9312002, 50304: 9312003, 51301: 9322004,
    51302: 9322005, 51303: 9322006, 51305: 9322007, 51309: 9322008, 51310: 9322009, 51311: 9322010,
    51312: 9322011
}

BED_TILES = [8321211, 9322009]
HIDEABLE_TILES = [6310104, 8310208, 8320209, 8320210, 8321211, 8320212]

# [Data-Driven Override]
try:
    from managers.data_manager import DataManager
    dm = DataManager.get_instance()
    if dm.tiles:
        # Update existing TILE_DATA instead of replacing to keep P constant safe if used elsewhere
        TILE_DATA.update(dm.tiles)
        print("[Tiles] TILE_DATA updated from DataManager")
except Exception as e:
    print(f"[Tiles] Failed to load data: {e}")