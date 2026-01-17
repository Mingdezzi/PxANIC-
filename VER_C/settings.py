import pygame

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TILE_SIZE = 32
FPS = 60

# [최적화] 전역 폰트 캐시 저장소 추가
SHARED_FONTS = {}

MAX_PLAYERS = 15
MAX_SPECTATORS = 5
MAX_TOTAL_USERS = 20
DAILY_QUOTA = 5

# [Update] Weather System
WEATHER_TYPES = ['CLEAR', 'RAIN', 'FOG', 'SNOW']
WEATHER_PROBS = [0.7, 0.1, 0.1, 0.1]

# [Update] Movement Speeds (Pixels per Frame at 60 FPS)
# Goal: 6 Tiles (192px) per Second -> 192 / 60 = 3.2
SPEED_WALK = 3.2      # Approx 6 Tiles/sec
SPEED_RUN = 4.8       # Approx 9 Tiles/sec
SPEED_CROUCH = 1.5    # Approx 3 Tiles/sec

BASE_SPEED_PPS = 192 # Base Pixels Per Second (Reference for UI)

POLICE_SPEED_MULTI = 1.25

NOISE_RADIUS = {
    'RUN': 10 * TILE_SIZE,
    'WALK': 6 * TILE_SIZE,
    'CROUCH': 1 * TILE_SIZE,
    'GUN': 25 * TILE_SIZE,
    'SCREAM': 15 * TILE_SIZE
}

# [Update] Enhanced Sound Information
# Key: Sound Type, Value: {base_rad: Tile Radius, color: (R, G, B)}
SOUND_INFO = {
    # [Movement]
    'FOOTSTEP': {'base_rad': 6, 'color': (200, 200, 200)},
    'THUD':     {'base_rad': 10, 'color': (150, 150, 150)}, # Run
    'RUSTLE':   {'base_rad': 4, 'color': (100, 200, 100)},  # Crouch/Bush
    
    # [Status]
    'HEARTBEAT':{'base_rad': 5, 'color': (200, 50, 50)},    # Anxiety
    'COUGH':    {'base_rad': 8, 'color': (200, 200, 100)},  # Pain
    'SCREAM':   {'base_rad': 15, 'color': (255, 0, 0)},     # Fear
    
    # [Environment/Door]
    'CREAK':    {'base_rad': 5, 'color': (180, 180, 180)},  # Open Door
    'SLAM':     {'base_rad': 8, 'color': (150, 150, 150)},  # Close Door
    'CLICK':    {'base_rad': 4, 'color': (200, 200, 200)},  # Lock/Unlock
    'BANG!':    {'base_rad': 12, 'color': (200, 50, 50)},   # Break/Impact
    'CRASH':    {'base_rad': 15, 'color': (200, 100, 50)},  # Destroy
    
    # [Item/Work]
    'GULP':     {'base_rad': 4, 'color': (100, 200, 255)},  # Drink
    'CRUNCH':   {'base_rad': 4, 'color': (200, 150, 50)},   # Eat
    'KA-CHING': {'base_rad': 5, 'color': (255, 215, 0)},    # Buy
    'TAP':      {'base_rad': 4, 'color': (200, 200, 200)},  # Work
    'BEEP':     {'base_rad': 4, 'color': (100, 255, 255)},  # Device
    
    # [Combat/Skill]
    'GUNSHOT':  {'base_rad': 25, 'color': (255, 200, 50)},
    'SLASH':    {'base_rad': 4, 'color': (255, 0, 0)},      # Knife
    'ZAP':      {'base_rad': 4, 'color': (100, 100, 255)},  # Taser
    'SIREN':    {'base_rad': 999, 'color': (0, 100, 255)},  # Global
    'BOOM':     {'base_rad': 999, 'color': (100, 100, 100)} # Global
}

# Compatibility
SOUND_COLORS = {k: v['color'] for k, v in SOUND_INFO.items()}
SOUND_COLORS['NOISE'] = (150, 150, 150)
SOUND_COLORS['TALK'] = (255, 255, 100)

VENDING_MACHINE_TID = 8321006
CCTV_TID = 7310011

DEFAULT_PHASE_DURATIONS = {
    'DAWN': 20,
    'MORNING': 20,
    'NOON': 40,
    'AFTERNOON': 40,
    'EVENING': 20,
    'NIGHT': 100
}

# [추가] 시간대별 조명 및 시야 설정
# alpha: 화면 어두움 정도 (0: 완전 밝음 ~ 255: 완전 암전)
# vision_factor: 시야 거리 비율 (1.0:멀리 ~ 0.0:코앞)
# clarity: 시야 내부 선명도 (255:선명 ~ 0:흐릿함/어두움) << [NEW]
PHASE_SETTINGS = {
    'DAWN':      {'alpha': 240, 'vision_factor': 0.0, 'clarity': 50}, 
    'MORNING':   {'alpha': 40,  'vision_factor': 0.8, 'clarity': 200}, 
    'NOON':      {'alpha': 0,   'vision_factor': 1.0, 'clarity': 255}, 
    'AFTERNOON': {'alpha': 20,  'vision_factor': 1.0, 'clarity': 255}, 
    'EVENING':   {'alpha': 150, 'vision_factor': 0.6, 'clarity': 180}, 
    'NIGHT':     {'alpha': 245, 'vision_factor': 0.0, 'clarity': 80}  
}

VISION_RADIUS = {
    'DAY': 12,
    'NIGHT_CITIZEN': 5,
    'NIGHT_POLICE_FLASH': 12,
    'NIGHT_MAFIA': 8,
    'BLACKOUT': 1.5,
    'DAWN': 0,
    'SPECTATOR': 40
}

MAFIA_DETECT_RANGE = 200

TREASURE_CHEST_RATES = [
    {'type': 'EMPTY', 'prob': 0.3, 'msg': "Empty..."},
    {'type': 'GOLD',  'prob': 0.6, 'amount': 3, 'msg': "Found 3 Gold!"},
    {'type': 'ITEM',  'prob': 0.1, 'items': ['TANGERINE', 'CHOCOBAR', 'BATTERY'], 'msg': "Found {item}!"}
]

AP_COSTS = {
    'WORK': 1, 'HEAL': 1, 'LOCKPICK': 1, 'REPAIR': 1, 'KILL': 1,
    'SEARCH': 2, 'BREAK_DOOR': 2, 'SABOTAGE': 5, 'SIREN': 5, 'INTERROGATE': 1
}

ITEMS = {
    'TANGERINE':    {'name': '귤', 'price': 3, 'desc': 'HP +2', 'key': pygame.K_1},
    'CHOCOBAR':     {'name': '초코바', 'price': 3, 'desc': 'AP +2', 'key': pygame.K_2},
    'TORTILLA':     {'name': '치즈또띠아', 'price': 7, 'desc': 'HP +3, AP +3', 'key': pygame.K_3},
    'MEDKIT':       {'name': '구급키트', 'price': 15, 'desc': 'HP Full Recovery', 'key': pygame.K_4},
    'ENERGY_DRINK': {'name': '에너지드링크', 'price': 10, 'desc': 'HP -3, Infinite Stamina (Night)', 'key': pygame.K_5},
    'PEANUT_BUTTER':{'name': '땅콩버터', 'price': 15, 'desc': 'Noise -30% (Night)', 'key': pygame.K_6},
    'COFFEE':       {'name': '커피', 'price': 8, 'desc': 'Job Speed x2', 'key': pygame.K_7},
    'PAINKILLER':   {'name': '진통제', 'price': 12, 'desc': 'Ignore Pain Penalty', 'key': pygame.K_8},
    'BATTERY':      {'name': '건전지', 'price': 3, 'desc': 'Battery +50%', 'key': pygame.K_9},
    'POWERBANK':    {'name': '보조배터리', 'price': 10, 'desc': 'Battery +100% (2 Uses)', 'key': pygame.K_0},
    'KEY':          {'name': '열쇠', 'price': 5, 'desc': 'Open Locked Door', 'key': pygame.K_MINUS},
    'MASTER_KEY':   {'name': '만능키', 'price': 20, 'desc': 'Open Locked Door (3 Uses)', 'key': pygame.K_EQUALS},
    'SMOKE_BOMB':   {'name': '연막탄', 'price': 10, 'desc': 'Auto-Smoke on Danger', 'key': None},
    'ARMOR':        {'name': '방탄방검복', 'price': 30, 'desc': 'Block 1 Attack', 'key': None},
    'POTION':       {'name': '소생약', 'price': 50, 'desc': 'Revive Next Morning', 'key': None},
    'TASER':        {'name': '테이저건', 'price': 25, 'desc': 'Stun Enemy 3s (1 Use)', 'key': None},
    'TRAP':         {'name': '덫', 'price': 10, 'desc': 'Place Trap (Stun 3s)', 'key': None}
}

WORK_SEQ = {
    'FARMER': [9312000, 9312001, 9312002], # Empty -> Sprout -> Harvest
    'MINER': [9322004, 9322005, 9322006],  # Ore -> Rubble -> Furnace
    'FISHER': [9312003, 9322007, 8320205], # Spot -> Cutting Board -> Fridge
    'DOCTOR': [9322008, 9322009, 9322011], # Microscope -> Surgery Table -> Computer
}

MINIGAME_MAP = {
    'FARMER': {0: 'MASHING', 1: 'CIRCLE', 2: 'TIMING'},
    'MINER': {0: 'MASHING', 1: 'CIRCLE', 2: 'TIMING'},
    'FISHER': {0: 'MASHING', 1: 'TIMING', 2: 'FREQUENCY'},
    'DOCTOR': {0: 'WIRING', 1: 'MEMORY', 2: 'CIRCLE'},
    'COMMON': {'LOCKPICK': 'WIRING', 'REPAIR': 'WIRING', 'BREAK': 'MASHING'}
}

BED_TILES = [8321211, 9322009]

# Hiding logic is now handled dynamically based on Tile ID structure (5th digit E)
# E=1: Passive Hide, E=2: Active Hide


ZONES = {
    0: {'name': 'None', 'color': (0, 0, 0, 0)},
    1: {'name': 'Spawn/Safety', 'color': (0, 255, 0, 50)},
    2: {'name': 'Work: Farmer', 'color': (255, 255, 0, 50)},
    3: {'name': 'Work: Miner', 'color': (150, 150, 150, 50)},
    4: {'name': 'Work: Fisher', 'color': (0, 0, 255, 50)},
    5: {'name': 'Mafia Hideout', 'color': (255, 0, 0, 50)},
    6: {'name': 'House/Residential', 'color': (200, 150, 100, 50)},
    7: {'name': 'Hospital/Medical', 'color': (255, 255, 255, 50)},
    8: {'name': 'Building/Indoor', 'color': (100, 100, 120, 50)}
}

INDOOR_ZONES = [6, 7, 8]

# [Data-Driven Override]
try:
    from managers.data_manager import DataManager
    dm = DataManager.get_instance()
    if dm.items:
        ITEMS = dm.items
        print("[Settings] ITEMS loaded from DataManager")
except Exception as e:
    print(f"[Settings] Failed to load data: {e}")

# [Network Settings]
NETWORK_PORT = 5555
SERVER_IP = "127.0.0.1" # Localhost default
BUFFER_SIZE = 4096