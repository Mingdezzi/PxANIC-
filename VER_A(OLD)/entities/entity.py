import pygame
import random
from settings import TILE_SIZE, ITEMS
from colors import CUSTOM_COLORS
from world.tiles import check_collision, get_tile_function, get_tile_category, BED_TILES, HIDEABLE_TILES

class Entity:
    def __init__(self, x, y, map_data, map_width, map_height, zone_map, name="Entity", role="CITIZEN", map_manager=None):

        # [Optimization] Hitbox reduction: 32x32 -> 20x20 for smoother passage through doors
        self.rect = pygame.Rect(x + 6, y + 6, TILE_SIZE - 12, TILE_SIZE - 12)
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        self.color = (255, 255, 255)

        self.map_data = map_data
        self.map_width = map_width
        self.map_height = map_height
        self.zone_map = zone_map
        self.map_manager = map_manager

        self.name = name
        self.role = role
        self.sub_role = None

        # [수정] 기본 스탯 100으로 확장
        self.max_hp = 100
        self.hp = 100
        self.max_ap = 100
        self.ap = 100

        self.coins = 0
        self.alive = True

        # [New] Status Effects & Emotions
        self.status_effects = {
            'ANXIETY': 0,    # 0~10: Anxiety Level (Heartbeat)
            'PAIN': False,   # Low HP
            'FATIGUE': False,# Low AP
            'FEAR': False,   # Encounter Mafia
            'RAGE': False,   # Police/Mafia Buff
            'DOPAMINE': False# Mafia Chase Buff
        }

        self.is_hiding = False
        self.hiding_type = 0
        self.hidden_in_solid = False
        self.inventory = {k: 0 for k in ITEMS.keys()}
        self.inventory['BATTERY'] = 1
        self.emotions = {}

        self.buffs = {
            'INFINITE_STAMINA': False,
            'SILENT': False,
            'FAST_WORK': False,
            'NO_PAIN': False
        }

        self.is_moving = False
        self.custom = {
            'skin': random.randint(0, len(CUSTOM_COLORS['SKIN'])-1),
            'clothes': random.randint(0, len(CUSTOM_COLORS['CLOTHES'])-1),
            'hat': random.randint(0, len(CUSTOM_COLORS['HAT'])-1)
        }
        self.facing_right = True
        self.facing_dir = (0, 1)
        self.stun_timer = 0
        self.device_on = False
        self.device_battery = 100.0
        self.powerbank_uses = 0


        self.popups = []

    def add_popup(self, text, color=(255, 255, 255)):
        """엔티티 머리 위에 1.5초간 지속되는 팝업 메시지 추가"""
        self.popups.append({
            'text': text,
            'color': color,
            'timer': pygame.time.get_ticks() + 1500
        })

    # [추가] 경찰이 확인하는 공개 외형 정보
    def is_visible_villain(self, phase):
        """
        현재 페이즈에 이 엔티티가 '빌런의 모습'을 하고 있는지 반환합니다.
        마피아는 밤/새벽에 '작업복(빌런 룩)'으로 자동 환복한다고 가정합니다.
        """
        if self.role == "MAFIA" and phase in ['NIGHT', 'DAWN']:
            return True
        return False

    def morning_process(self):
        """아침마다 상태 리셋 (하위 클래스에서 호출 필요)"""

        for k in self.buffs: self.buffs[k] = False
        self.hp = min(self.max_hp, self.hp + 1)

    def is_stunned(self):
        return pygame.time.get_ticks() < self.stun_timer

    def take_stun(self, duration_ms=2000):
        self.stun_timer = pygame.time.get_ticks() + duration_ms
        self.is_moving = False
        if hasattr(self, 'path'): self.path = []

    def take_damage(self, amount):
        if not self.alive: return "ALREADY_DEAD"
        if self.role == "POLICE": return "IMMUNE"


        if self.inventory.get('ARMOR', 0) > 0:
            self.inventory['ARMOR'] -= 1
            return "BLOCKED"

        if self.inventory.get('POTION', 0) > 0 and self.hp - amount <= 0:
            self.inventory['POTION'] -= 1
            self.hp = 5
            self.alive = False
            return "DIED_BUT_REVIVABLE"

        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return "DIED"
        return "HIT"

    def heal(self, amount):
        if self.alive and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + amount)
            return True
        return False

    def try_spend_ap(self, amount, allow_health_cost=True):
        if self.ap >= amount:
            self.ap -= amount
            return True
        else:
            if self.role == "POLICE": self.ap = 0; return True
            if not allow_health_cost: return False
            
            if self.buffs['NO_PAIN']: hp_cost = 0
            else: hp_cost = amount * 2

            if hp_cost > 0: self.take_damage(hp_cost)
            return True

    def use_item(self, item_key):
        """[Ver 10.0] 공통 아이템 사용 로직"""
        if not self.alive: return False
        if self.inventory.get(item_key, 0) <= 0: return False

        used = False
        s_type = "CRUNCH"

        if item_key == 'TANGERINE':
            if self.hp < self.max_hp: self.hp = min(self.max_hp, self.hp + 2); used = True
        elif item_key == 'CHOCOBAR':
            if self.ap < self.max_ap: self.ap = min(self.max_ap, self.ap + 2); used = True
        elif item_key == 'TORTILLA':
            if self.hp < self.max_hp or self.ap < self.max_ap:
                self.hp = min(self.max_hp, self.hp + 3)
                self.ap = min(self.max_ap, self.ap + 3)
                used = True
        elif item_key == 'MEDKIT':
            if self.hp < self.max_hp: self.hp = self.max_hp; used = True
            s_type = "CLICK"

        elif item_key == 'ENERGY_DRINK':
            if not self.buffs['INFINITE_STAMINA']:
                self.hp = max(1, self.hp - 3)
                self.buffs['INFINITE_STAMINA'] = True
                used = True; s_type = "GULP"
        elif item_key == 'PEANUT_BUTTER':
            if not self.buffs['SILENT']: self.buffs['SILENT'] = True; used = True
        elif item_key == 'COFFEE':
            if not self.buffs['FAST_WORK']: self.buffs['FAST_WORK'] = True; used = True; s_type = "GULP"
        elif item_key == 'PAINKILLER':
            if not self.buffs['NO_PAIN']: self.buffs['NO_PAIN'] = True; used = True; s_type = "GULP"

        elif item_key == 'BATTERY':
            if self.device_battery < 100: self.device_battery = min(100, self.device_battery + 50); used = True; s_type = "CLICK"
        elif item_key == 'POWERBANK':
            if self.device_battery < 100:
                self.device_battery = 100
                self.powerbank_uses += 1
                if self.powerbank_uses >= 2:
                    self.powerbank_uses = 0
                    used = True
                else:
                    self.add_popup("Used once (1 left)", (100, 255, 100))
                    return ("Used once (1 left)", ("CLICK", self.rect.centerx, self.rect.centery, 3 * TILE_SIZE, self.role))
                s_type = "CLICK"

        if used:
            self.inventory[item_key] -= 1
            return ("Used " + ITEMS[item_key]['name'], (s_type, self.rect.centerx, self.rect.centery, 4 * TILE_SIZE, self.role))
        return False

    def move_single_axis(self, dx, dy, npcs=None):
        if dx > 0: self.facing_right = True; self.facing_dir = (1, 0)
        elif dx < 0: self.facing_right = False; self.facing_dir = (-1, 0)
        if dy > 0: self.facing_dir = (0, 1)
        elif dy < 0: self.facing_dir = (0, -1)

        self.pos_x += dx; self.pos_y += dy
        self.rect.x, self.rect.y = round(self.pos_x), round(self.pos_y)

        if self.hidden_in_solid: return

        # 충돌 검사 범위 계산
        start_gx = max(0, self.rect.left // TILE_SIZE)
        end_gx = min(self.map_width, (self.rect.right // TILE_SIZE) + 1)
        start_gy = max(0, self.rect.top // TILE_SIZE)
        end_gy = min(self.map_height, (self.rect.bottom // TILE_SIZE) + 1)

        # [최적화] 캐시 조회용 변수 미리 할당
        collision_cache = getattr(self.map_manager, 'collision_cache', None)

        for y in range(start_gy, end_gy):
            for x in range(start_gx, end_gx):
                is_blocking = False
                
                # [핵심 최적화] 복잡한 타일 조회 대신 캐시된 불리언 값(True/False)만 확인
                if collision_cache:
                    if collision_cache[y][x]:
                        is_blocking = True
                else:
                    # 백업 로직
                    tids_to_check = []
                    if self.map_manager:
                        for layer in ['wall', 'object']:
                            val = self.map_manager.get_tile_full(x, y, layer)
                            if val[0] != 0: tids_to_check.append(val[0])
                    else: tids_to_check.append(self.map_data[y][x])

                    for tid in tids_to_check:
                        if check_collision(tid):
                            if tid not in BED_TILES and tid not in HIDEABLE_TILES and tid != 5310005:
                                is_blocking = True; break

                if is_blocking:
                    # [최적화] Rect 객체 생성 없이 좌표 비교로 충돌 해결
                    tile_left = x * TILE_SIZE
                    tile_top = y * TILE_SIZE
                    tile_right = tile_left + TILE_SIZE
                    tile_bottom = tile_top + TILE_SIZE
                    
                    if (self.rect.right > tile_left and self.rect.left < tile_right and
                        self.rect.bottom > tile_top and self.rect.top < tile_bottom):
                        
                        if dx > 0: self.rect.right = tile_left
                        elif dx < 0: self.rect.left = tile_right
                        if dy > 0: self.rect.bottom = tile_top
                        elif dy < 0: self.rect.top = tile_bottom
                        
                        self.pos_x, self.pos_y = float(self.rect.x), float(self.rect.y)

        map_w_px, map_h_px = self.map_width * TILE_SIZE, self.map_height * TILE_SIZE
        if self.rect.left < 0: self.rect.left = 0
        elif self.rect.right > map_w_px: self.rect.right = map_w_px
        if self.rect.top < 0: self.rect.top = 0
        elif self.rect.bottom > map_h_px: self.rect.bottom = map_h_px
        self.pos_x, self.pos_y = self.rect.x, self.rect.y
