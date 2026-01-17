import pygame
import random
import math
import heapq
import threading
from settings import *
from world.tiles import check_collision, get_tile_function, BED_TILES, HIDEABLE_TILES, get_tile_interaction, get_tile_category, get_tile_name
from systems.logger import GameLogger
from colors import *
from .entity import Entity
from systems.renderer import CharacterRenderer
from systems.behavior_tree import BTNode, Composite, Selector, Sequence, Action, Condition, BTState

FONT_POPUP = None

class Dummy(Entity):
    def __init__(self, x, y, map_data, map_width, map_height, name="Dummy", role="CITIZEN", tile_cache=None, zone_map=None, map_manager=None, is_master=True):
        super().__init__(x, y, map_data, map_width=map_width, map_height=map_height, zone_map=zone_map, name=name, role=role, map_manager=map_manager)

        self.tile_cache = tile_cache if tile_cache else {}
        self.logger = GameLogger.get_instance()
        
        # [Multiplayer Architecture]
        self.is_master = is_master # True: AI runs locally (Host), False: AI runs remotely (Client)

        global FONT_POPUP
        if FONT_POPUP is None:
            try: FONT_POPUP = pygame.font.SysFont("arial", 14, bold=True)
            except: FONT_POPUP = pygame.font.Font(None, 20)

        self.coins = 0
        self.sub_role = random.choice(["FARMER", "MINER", "FISHER"]) if role in ["CITIZEN", "MAFIA"] else None

        self.morph_active = False; self.vote_count = 0
        self.move_state = "WALK"; self.speed = SPEED_WALK; self.is_moving = False

        self.path = []
        self.current_path_target = None
        self.last_pos = (self.pos_x, self.pos_y)
        self.stuck_timer = pygame.time.get_ticks() + 2000
        self.failed_targets = {}

        self.is_pathfinding = False
        self.pending_path = None
        self.path_cooldown = 0

        self.action_cooldown = 0
        self.ability_used = False
        self.last_attack_time = 0

        self.is_working = False
        self.work_finish_timer = 0
        self.is_unlocking = False
        self.unlock_finish_timer = 0

        self.daily_work_count = 0
        self.work_tile_pos = None
        self.target_house_pos = None

        self.footstep_timer = 0
        self.popups = []
        self.last_stats = {'hp': self.hp, 'coins': self.coins}

        self.suspicion_meter = {}
        self.chase_target = None
        self.last_seen_pos = None
        self.investigate_pos = None

        self.device_on = False
        self.device_battery = 100.0

        # AI Tree is only needed if we are the master
        if self.is_master:
            self.tree = self._build_behavior_tree()
        else:
            self.tree = None

        # [Slave Mode Interpolation]
        self.target_pos = (x, y)
        self.lerp_factor = 0.1

    def add_popup(self, text, color=(255, 255, 255)):
        self.popups.append({'text': text, 'color': color, 'timer': pygame.time.get_ticks() + 1500})

    def add_suspicion(self, target_name, amount):
        self.suspicion_meter[target_name] = self.suspicion_meter.get(target_name, 0) + amount

    def morning_process(self):
        if not self.alive: return
        self.morph_active = False
        gx, gy = int(self.rect.centerx // TILE_SIZE), int(self.rect.centery // TILE_SIZE)
        is_indoors = False
        if 0 <= gx < self.map_width and 0 <= gy < self.map_height:
             is_indoors = (self.zone_map[gy][gx] in INDOOR_ZONES)
             
        if self.is_hiding and is_indoors:
            self.hp, self.ap = self.max_hp, self.max_ap
            self.add_popup("Rested", (100, 255, 255))

        if self.role == "DOCTOR" and random.random() < 0.33: self.inventory['POTION'] += 1
        self.daily_work_count = 0; self.ability_used = False; self.is_hiding = False; self.hiding_type = 0; self.target_house_pos = None
        self.is_working = False; self.work_finish_timer = 0; self.is_unlocking = False
        self.path, self.current_path_target, self.work_tile_pos = [], None, None
        self.failed_targets = {}; self.investigate_pos, self.chase_target = None, None
        self.suspicion_meter = {k: max(0, v - 30) for k, v in self.suspicion_meter.items()}
        self.device_battery = min(100, self.device_battery + 20)


    def _build_behavior_tree(self):
        survival_seq = Sequence([Condition(self.check_danger), Action(self.do_flee_or_hide)])
        shopping_seq = Sequence([Condition(self.check_needs_shopping), Action(self.do_shopping)])

        if self.role == "POLICE":
            return Selector([
                shopping_seq,
                Sequence([Condition(self.police_scan_targets), Action(self.police_chase_attack)]),
                Sequence([Condition(self.has_last_seen_pos), Action(self.police_investigate_last_pos)]),
                Sequence([Condition(self.has_investigate_pos), Action(self.police_investigate_noise)]),
                Action(self.do_patrol)
            ])
        elif self.role == "MAFIA":
            return Selector([
                Sequence([Condition(self.mafia_scan_targets), Action(self.mafia_kill)]),
                Sequence([Condition(self.can_sabotage), Action(self.mafia_sabotage)]),
                shopping_seq,
                Action(self.do_work_fake)
            ])
        else:
            return Selector([
                survival_seq,
                shopping_seq,
                Sequence([Condition(self.is_work_time), Action(self.do_work)]),
                Sequence([Condition(self.is_night_time), Action(self.do_go_home)]),
                Action(self.do_wander)
            ])


    def police_scan_targets(self, entity, bb):
        # [수정] 낮 시간 추격 금지
        current_phase = bb.get('phase')
        if current_phase not in ['NIGHT', 'DAWN']:
            self.chase_target = None
            return False

        if self.chase_target and self.chase_target.alive and not self.chase_target.is_hiding:
            if self.has_line_of_sight(self.chase_target): return True
        
        # [핵심 수정] "마피아인가?"(신상조회) -> "빌런의 모습인가?"(외형관찰) 로 변경
        for t in bb.get('targets', []):
            if t != self and t.alive:
                is_villain_look = t.is_visible_villain(current_phase)
                
                if (is_villain_look and self.has_line_of_sight(t)) or (self.suspicion_meter.get(t.name, 0) >= 100):
                    if self.has_line_of_sight(t) and not t.is_hiding:
                        self.chase_target = t; self.last_seen_pos = (t.rect.centerx, t.rect.centery)
                        return True
        return False

    def mafia_scan_targets(self, entity, bb):
        if bb.get('phase') != 'NIGHT': return False
        if self.chase_target and self.chase_target.alive and self.has_line_of_sight(self.chase_target): return True
        visible_victims = []
        for t in bb.get('targets', []):
            if t != self and t.alive and t.role not in ["MAFIA", "SPECTATOR"]:
                if self.has_line_of_sight(t) and not t.is_hiding:
                    dist = math.sqrt((self.rect.centerx - t.rect.centerx)**2 + (self.rect.centery - t.rect.centery)**2)
                    visible_victims.append((dist, t))
        if visible_victims:
            visible_victims.sort(key=lambda x: x[0]); self.chase_target = visible_victims[0][1]
            return True
        return False

    def has_last_seen_pos(self, entity, bb): return self.last_seen_pos is not None
    def has_investigate_pos(self, entity, bb):
        if self.investigate_pos: return True
        noise = bb.get('noise_list', [])
        if noise:
            noise.sort(key=lambda n: (self.rect.centerx-n[0])**2 + (self.rect.centery-n[1])**2)
            self.investigate_pos = (noise[0][0], noise[0][1]); return True
        return False

    def check_danger(self, entity, bb):
        if self.role in ["CITIZEN", "DOCTOR"] and bb.get('phase') == 'NIGHT':
            for n in bb.get('npcs', []):
                if n != self and n.alive and self.has_line_of_sight(n):
                    dist = math.sqrt((self.rect.centerx-n.rect.centerx)**2+(self.rect.centery-n.rect.centery)**2)
                    if dist < TILE_SIZE * 2: return True
        return False

    def check_needs_shopping(self, entity, bb):
        return (self.hp < 5 or self.ap < 4) and self.coins >= 3 and not self.is_hiding

    def is_work_time(self, entity, bb): return bb.get('phase') in ['MORNING', 'DAY'] and self.daily_work_count < DAILY_QUOTA
    def is_night_time(self, entity, bb): return bb.get('phase') in ['EVENING', 'NIGHT']
    def can_sabotage(self, entity, bb): return self.role == "MAFIA" and bb.get('phase') == 'NIGHT' and not self.ability_used and self.ap >= 5


    def police_chase_attack(self, entity, bb):
        if not self.chase_target: return BTState.FAILURE
        dist = math.sqrt((self.rect.centerx - self.chase_target.rect.centerx)**2 + (self.rect.centery - self.chase_target.rect.centery)**2)
        if dist > 200 and not self.ability_used and self.ap >= 5:
            self.ability_used = True; self.ap -= 5; return "USE_SIREN"
        now = pygame.time.get_ticks()
        if dist < 400 and now > self.last_attack_time + 1000:
            if self.try_spend_ap(1): self.last_attack_time = now; return "SHOOT_TARGET"
        self.set_destination(self.chase_target.rect.centerx, self.chase_target.rect.centery, "Chasing")
        return BTState.RUNNING

    def police_investigate_last_pos(self, entity, bb):
        if not self.last_seen_pos: return BTState.FAILURE
        dist = math.sqrt((self.rect.centerx - self.last_seen_pos[0])**2 + (self.rect.centery - self.last_seen_pos[1])**2)
        if dist < TILE_SIZE: self.last_seen_pos = None; self.chase_target = None; return BTState.SUCCESS
        self.set_destination(self.last_seen_pos[0], self.last_seen_pos[1], "Investigating")
        return BTState.RUNNING

    def police_investigate_noise(self, entity, bb):
        if not self.investigate_pos: return BTState.FAILURE
        dist = math.sqrt((self.rect.centerx - self.investigate_pos[0])**2 + (self.rect.centery - self.investigate_pos[1])**2)
        if dist < TILE_SIZE: self.investigate_pos = None; return BTState.SUCCESS
        self.set_destination(self.investigate_pos[0], self.investigate_pos[1], "Checking Noise")
        return BTState.RUNNING

    def do_patrol(self, entity, bb):
        if not self.path and not self.is_pathfinding: self.random_move()
        return BTState.RUNNING

    def do_flee_or_hide(self, entity, bb):
        if not self.path:
            if not self.find_hiding_spot(bb.get('npcs', [])): self.random_move()
        return BTState.RUNNING

    def do_shopping(self, entity, bb):
        if not self.path:
            vending_pos = self.find_tile([VENDING_MACHINE_TID], npcs=bb.get('npcs', []))
            if vending_pos:
                dist = math.sqrt((self.rect.centerx - vending_pos[0])**2 + (self.rect.centery - vending_pos[1])**2)
                if dist < TILE_SIZE * 1.5:
                    if self.hp < 5: self.coins -= 3; self.hp += 2
                    return BTState.SUCCESS
                self.set_destination(vending_pos[0], vending_pos[1], "Shopping")
        return BTState.RUNNING

    def do_work(self, entity, bb):
        now = pygame.time.get_ticks()
        if self.is_working:
            if now >= self.work_finish_timer:
                self.ap -= 1; self.coins += 1; self.daily_work_count += 1
                self.is_working = False; self.work_tile_pos = None; return BTState.SUCCESS
            return BTState.RUNNING
        if not self.work_tile_pos:
            job_key = "DOCTOR" if self.role == "DOCTOR" else self.sub_role
            target_tid = WORK_SEQ[job_key][(bb.get('day_count', 1) - 1) % 3]
            candidates = self.map_manager.tile_cache.get(target_tid, []) if self.map_manager else []
            if candidates:
                raw_px, raw_py = random.choice(candidates); valid_pos = self.get_valid_neighbor(raw_px // TILE_SIZE, raw_py // TILE_SIZE)
                if valid_pos: self.work_tile_pos = valid_pos; self.set_destination(valid_pos[0], valid_pos[1], "Work Start")
                else: return BTState.FAILURE
            else: return BTState.FAILURE
        dist = math.sqrt((self.rect.centerx - self.work_tile_pos[0])**2 + (self.rect.centery - self.work_tile_pos[1])**2)
        if dist < TILE_SIZE * 0.8:
            if self.ap > 0:
                self.is_working = True; self.work_finish_timer = now + 3000; self.path = []; self.is_moving = False; self.add_popup("Working...")
            else: self.work_tile_pos = None
        elif not self.path and not self.is_pathfinding: self.work_tile_pos = None; return BTState.FAILURE
        return BTState.RUNNING

    def do_work_fake(self, entity, bb):
        if not self.path and not self.is_pathfinding: self.random_move()
        return BTState.RUNNING

    def do_go_home(self, entity, bb):
        if self.is_hiding: return BTState.SUCCESS
        if not self.target_house_pos: self.target_house_pos = self.find_house_door(bb.get('npcs', []))
        if self.target_house_pos:
            dist = math.sqrt((self.rect.centerx - self.target_house_pos[0])**2 + (self.rect.centery - self.target_house_pos[1])**2)
            if dist < TILE_SIZE:
                self.is_hiding = True; self.hiding_type = 2; self.is_moving = False; self.path = []; return BTState.SUCCESS
            self.set_destination(self.target_house_pos[0], self.target_house_pos[1], "Go Home")
        return BTState.RUNNING

    def mafia_kill(self, entity, bb):
        if self.ap >= 1 and self.chase_target:
            dist = math.sqrt((self.rect.centerx - self.chase_target.rect.centerx)**2 + (self.rect.centery - self.chase_target.rect.centery)**2)
            if dist < TILE_SIZE * 1.5:
                self.ap -= 1; self.chase_target.take_damage(10); self.action_cooldown = pygame.time.get_ticks() + 1000
                return "MURDER_OCCURRED"
            self.set_destination(self.chase_target.rect.centerx, self.chase_target.rect.centery, "Killing")
        return BTState.RUNNING

    def mafia_sabotage(self, entity, bb):
        self.ability_used = True; self.ap -= 5; return "USE_SABOTAGE"

    def do_wander(self, entity, bb):
        if not self.path and not self.is_pathfinding: self.random_move()
        return BTState.RUNNING


    def _validate_environment(self):
        gx = int(self.rect.centerx // TILE_SIZE); gy = int(self.rect.centery // TILE_SIZE)
        if not (0 <= gx < self.map_width and 0 <= gy < self.map_height): return
        tid_obj = self.map_manager.get_tile(gx, gy, 'object') if self.map_manager else 0
        tid_floor = self.map_manager.get_tile(gx, gy, 'floor') if self.map_manager else 0
        zone_id = self.zone_map[gy][gx]; is_hiding_tile = (tid_obj in HIDEABLE_TILES) or (tid_floor in HIDEABLE_TILES)
        is_resting_tile = (tid_obj in BED_TILES); is_indoors = (zone_id in INDOOR_ZONES)
        if self.is_moving:
            if self.is_hiding: self.is_hiding = False; self.hiding_type = 0
            return
        if is_hiding_tile and not self.is_hiding: self.is_hiding = True; self.hiding_type = 1
        if self.is_hiding:
            if self.hiding_type == 1 and not is_hiding_tile: self.is_hiding = False; self.hiding_type = 0
            elif self.hiding_type == 2 and not (is_indoors or is_resting_tile): self.is_hiding = False; self.hiding_type = 0

    def update(self, phase, player, npcs, is_mafia_frozen, noise_list, day_count, bloody_footsteps, siren_timer=0):
        if not self.alive: return None
        self._validate_environment()
        now = pygame.time.get_ticks(); self.check_stat_changes()
        
        # [Sync Logic] Only Master updates logic
        if self.is_master:
            if self.role == "MAFIA" and is_mafia_frozen:
                self.is_moving = False
                return None
            if self.is_unlocking:
                if now >= self.unlock_finish_timer:
                    self.is_unlocking = False
                    if self.path:
                        nx, ny = self.path[0]
                        if self.map_manager: self.map_manager.unlock_door(nx, ny); self.add_popup("Unlocked!")
                    return None
                return BTState.RUNNING
            if self.pending_path is not None:
                if not self.is_hiding: self.path = self.pending_path
                self.pending_path = None; self.is_pathfinding = False
            
            blackboard = {'phase': phase, 'player': player, 'npcs': npcs, 'targets': npcs + [player], 'noise_list': noise_list, 'bloody_footsteps': bloody_footsteps, 'day_count': day_count, 'is_mafia_frozen': is_mafia_frozen}
            result = self.tree.tick(self, blackboard)
            if isinstance(result, str): return result
            return self.process_movement(phase, npcs, slow_down=is_mafia_frozen if self.role == "MAFIA" else False)
        
        else:
            # [Slave Mode] Just interpolate position (No AI)
            self._update_slave_movement()
            return None

    def _update_slave_movement(self):
        # Simple lerp to target position
        dx = self.target_pos[0] - self.pos_x
        dy = self.target_pos[1] - self.pos_y
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist > 1.0:
            move_x = dx * self.lerp_factor
            move_y = dy * self.lerp_factor
            self.pos_x += move_x
            self.pos_y += move_y
            self.rect.x = round(self.pos_x)
            self.rect.y = round(self.pos_y)
            
            # Update facing
            if abs(dx) > abs(dy):
                self.facing_dir = (1, 0) if dx > 0 else (-1, 0)
            else:
                self.facing_dir = (0, 1) if dy > 0 else (0, -1)
            self.is_moving = True
        else:
            self.is_moving = False

    def sync_state(self, x, y, hp, ap, role, is_moving, facing):
        """Called by network manager to update slave state"""
        self.target_pos = (x, y)
        # If distance is too big, teleport
        if math.hypot(x - self.pos_x, y - self.pos_y) > TILE_SIZE * 5:
            self.pos_x, self.pos_y = x, y
            self.rect.x, self.rect.y = int(x), int(y)
            
        self.hp = hp
        self.ap = ap
        # Role shouldn't change often but sync it anyway if needed
        self.is_moving = is_moving
        self.facing_dir = facing

    def set_destination(self, tx, ty, reason="Unknown"):
        if self.is_hiding: self.is_hiding = False; self.hiding_type = 0
        tgx, tgy = int(tx // TILE_SIZE), int(ty // TILE_SIZE)
        if self.path and self.current_path_target == (tgx, tgy): return True
        if self.is_pathfinding: return False
        
        # [수정] 현재 경로가 없고 멈춰있는 상태라면 쿨타임 무시 (즉시 반응)
        now = pygame.time.get_ticks()
        if self.path or self.is_moving:
            if now < self.path_cooldown: return False
            
        self.path_cooldown = now + 500
        self.is_pathfinding = True
        
        # [수정] 스레드 안전성 확보: 현재 위치를 미리 계산하여 전달
        start_gx = int(self.rect.centerx // TILE_SIZE)
        start_gy = int(self.rect.centery // TILE_SIZE)
        
        thread = threading.Thread(target=self._threaded_calculate_path, args=(start_gx, start_gy, tgx, tgy, reason))
        thread.daemon = True; thread.start(); return True

    def _threaded_calculate_path(self, start_gx, start_gy, target_gx, target_gy, reason):
        try:
            # start_gx, start_gy는 인자로 받음 (self.rect 접근 제거)
            if (start_gx, start_gy) == (target_gx, target_gy): self.pending_path = []; return
            open_set = []; heapq.heappush(open_set, (0, start_gx, start_gy)); came_from = {}; g_score = {(start_gx, start_gy): 0}
            while open_set and len(came_from) < 5000:
                _, cx, cy = heapq.heappop(open_set)
                if (cx, cy) == (target_gx, target_gy): break
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.map_width and 0 <= ny < self.map_height:
                        tid_obj = self.map_manager.get_tile(nx, ny, 'object') if self.map_manager else 0
                        tid_wall = self.map_manager.get_tile(nx, ny, 'wall') if self.map_manager else self.map_data[ny][nx]
                        blocked = check_collision(tid_wall) or (tid_obj != 0 and check_collision(tid_obj))
                        if get_tile_category(tid_obj) == 5: blocked = False
                        if (nx, ny) == (target_gx, target_gy): blocked = False
                        if not blocked:
                            new_g = g_score[(cx, cy)] + 1
                            if (nx, ny) not in g_score or new_g < g_score[(nx, ny)]:
                                g_score[(nx, ny)] = new_g; priority = new_g + abs(target_gx - nx) + abs(target_gy - ny)
                                heapq.heappush(open_set, (priority, nx, ny)); came_from[(nx, ny)] = (cx, cy)
            if (target_gx, target_gy) in came_from:
                path = []; curr = (target_gx, target_gy)
                while curr in came_from: path.append(curr); curr = came_from[curr]
                self.pending_path = path[::-1]; self.current_path_target = (target_gx, target_gy)
            else: self.pending_path = None; self.is_pathfinding = False
        except: self.is_pathfinding = False

    def process_movement(self, phase, npcs=None, slow_down=False):
        if self.is_hiding: return None
        if slow_down:
            self.is_moving = False
            return None
        
        # [New] Update Emotion State (AI)
        if self.role == "MAFIA" and self.chase_target:
            self.status_effects['DOPAMINE'] = True
        else:
            self.status_effects['DOPAMINE'] = False

        now = pygame.time.get_ticks(); self.move_state, self.speed = "WALK", SPEED_WALK
        if self.chase_target: 
            self.move_state, self.speed = "RUN", SPEED_RUN
            # [New] Dopamine Effect: Faster Chase
            if self.status_effects.get('DOPAMINE'):
                self.speed *= 1.2

        if not self.path: self.is_moving = False; return None
        ngx, ngy = self.path[0]; tid = self.map_manager.get_tile(ngx, ngy, 'object') if self.map_manager else 0
        cat = get_tile_category(tid); d_val = get_tile_interaction(tid)
        if cat == 5:
            dist = math.sqrt((self.rect.centerx - (ngx*TILE_SIZE+16))**2 + (self.rect.centery - (ngy*TILE_SIZE+16))**2)
            if dist < TILE_SIZE * 1.2:
                # [New] Mafia Rage: Destroy Doors at Night
                if self.role == "MAFIA" and phase == "NIGHT":
                    if self.map_manager:
                        self.map_manager.set_tile(ngx, ngy, 0, layer='object')
                        # self.logger.info("MAFIA", "Smashed a door!")
                    return None

                if d_val == 1: self.map_manager.open_door(ngx, ngy); return None
                elif d_val == 3:
                    if self.inventory.get('KEY', 0) > 0: self.inventory['KEY'] -= 1; self.map_manager.unlock_door(ngx, ngy); return None
                    elif self.role == "MAFIA": self.map_manager.set_tile(ngx, ngy, 5310005); return "MURDER_OCCURRED"
                    elif not self.is_unlocking: self.is_unlocking = True; self.unlock_finish_timer = now + 5000; self.add_popup("Lockpicking..."); return None
                    return None
        target_px, target_py = ngx * TILE_SIZE + 16, ngy * TILE_SIZE + 16
        dx, dy = target_px - self.rect.centerx, target_py - self.rect.centery; dist = math.sqrt(dx**2 + dy**2)
        if dist < 5:
            self.path.pop(0);
            if not self.path: self.is_moving = False
        else:
            self.is_moving = True; mx, my = (dx/dist)*self.speed, (dy/dist)*self.speed
            self.move_single_axis(mx, 0, npcs); self.move_single_axis(0, my, npcs)
            
            # [Optimization] Update Spatial Grid
            if hasattr(self, 'world') and self.world.spatial_grid:
                self.world.spatial_grid.update_entity(self)
        return True


    def random_move(self):
        # [수정] 무작위 좌표 대신 '갈 수 있는 바닥' 중에서 랜덤 선택
        target_pos = None
        
        if self.map_manager:
            # 1. 캐시된 바닥 타일 중 하나를 랜덤 선택 (카테고리 1: 외부바닥, 2: 내부바닥)
            valid_keys = [k for k in self.map_manager.tile_cache.keys() if get_tile_category(k) in [1, 2]]
            if valid_keys:
                rand_tid = random.choice(valid_keys)
                if self.map_manager.tile_cache[rand_tid]:
                    rx, ry = random.choice(self.map_manager.tile_cache[rand_tid])
                    target_pos = (rx + 16, ry + 16)

        # 2. 캐시가 없거나 실패하면 기존 방식대로 하되, 충돌 체크 반복
        if not target_pos:
            for _ in range(10): # 최대 10번 시도
                tx = random.randint(0, self.map_width - 1)
                ty = random.randint(0, self.map_height - 1)
                if self.map_manager and not self.map_manager.check_any_collision(tx, ty):
                    target_pos = (tx * TILE_SIZE + 16, ty * TILE_SIZE + 16)
                    break
        
        if target_pos:
            self.set_destination(target_pos[0], target_pos[1], "Random Move")
    def find_tile(self, target_ids, sort_by_distance=True, npcs=None):
        candidates = []; tile_cache = self.map_manager.tile_cache if self.map_manager else {}
        for tid in target_ids:
            if tid in tile_cache:
                for px, py in tile_cache[tid]:
                    dist_sq = (self.rect.centerx - px)**2 + (self.rect.centery - py)**2
                    if dist_sq > (60 * TILE_SIZE)**2: continue
                    neighbor = self.get_valid_neighbor(px//TILE_SIZE, py//TILE_SIZE)
                    if neighbor: candidates.append((neighbor, dist_sq))
        if candidates:
            if sort_by_distance: candidates.sort(key=lambda c: c[1])
            return candidates[0][0]
        return None
    def get_valid_neighbor(self, tx, ty):
        offsets = [(0, 1), (0, -1), (1, 0), (-1, 0)]; random.shuffle(offsets)
        for dx, dy in offsets:
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < self.map_width and 0 <= ny < self.map_height:
                if self.map_manager and not self.map_manager.check_any_collision(nx, ny): return (nx * TILE_SIZE + 16, ny * TILE_SIZE + 16)
        return None
    def has_line_of_sight(self, target): return math.sqrt((self.rect.centerx - target.rect.centerx)**2 + (self.rect.centery - target.rect.centery)**2) < VISION_RADIUS['DAY'] * TILE_SIZE
    def check_stat_changes(self):
        if self.hp != self.last_stats['hp']: diff = self.hp-self.last_stats['hp']; self.add_popup(f"{diff} HP", (255, 50, 50) if diff < 0 else (50, 255, 50)); self.last_stats['hp'] = self.hp
        if self.coins != self.last_stats['coins']: diff = self.coins-self.last_stats['coins']; self.add_popup(f"+{diff} G", (255, 215, 0)); self.last_stats['coins'] = self.coins
    def find_house_door(self, npcs=None):
        candidates = []
        for y in range(self.map_height):
            for x in range(self.map_width):
                if self.zone_map[y][x] in INDOOR_ZONES:
                    tid = self.map_manager.get_tile(x, y, 'object') if self.map_manager else 0
                    if get_tile_function(tid) in [2, 3]: candidates.append((x*TILE_SIZE+16, y*TILE_SIZE+16))
        return random.choice(candidates) if candidates else None
    def find_hiding_spot(self, npcs):
        found = self.find_tile(HIDEABLE_TILES, npcs=npcs)
        if found:
            if math.sqrt((self.rect.centerx - found[0])**2 + (self.rect.centery - found[1])**2) < TILE_SIZE: self.is_hiding, self.hiding_type, self.path = True, 2, []; self.is_moving = False; return True
            return self.set_destination(found[0], found[1], "Moving to Hide")
        return False
    def draw(self, screen, camera_x, camera_y, viewer_role="PLAYER", phase="DAY", viewer_device_on=False):
        if self.alive: CharacterRenderer.draw_entity(screen, self, camera_x, camera_y, viewer_role, phase, viewer_device_on)
        rx, ry = self.rect.x - camera_x, self.rect.y - camera_y
        if not self.is_hiding or self.hiding_type == 2:
            y_off = 0
            for p in reversed(self.popups):
                if pygame.time.get_ticks() < p['timer']:
                    txt = FONT_POPUP.render(p['text'], True, p['color']); screen.blit(txt, (rx + TILE_SIZE//2 - txt.get_width()//2, ry - 20 - y_off)); y_off += 15
