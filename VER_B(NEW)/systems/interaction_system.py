import pygame
import random
from core.ecs_manager import ECSManager
from core.event_bus import EventBus
from core.game_state_manager import GameStateManager
from components.common import Transform, Animation
from components.interaction import InteractionState, Inventory
from components.status import Stats, StatusEffects
from components.identity import Identity
from world.map_manager import MapManager
from world.tiles import get_tile_category, get_tile_interaction, get_tile_function, get_tile_name, WORK_SEQ, VENDING_MACHINE_TID
from settings import TILE_SIZE, ITEMS

class InteractionSystem:
    def __init__(self, ecs: ECSManager, event_bus: EventBus, map_manager: MapManager):
        self.ecs = ecs
        self.event_bus = event_bus
        self.map_manager = map_manager
        self.game_state = GameStateManager.get_instance()
        
        self.event_bus.subscribe("INTERACTION_REQUEST", self.handle_interaction_request)
        self.event_bus.subscribe("USE_ITEM", self.handle_use_item)
        self.event_bus.subscribe("ACTION_REQUEST", self.handle_action_request)

    def handle_action_request(self, data):
        action_type = data['type'] # 'SKILL', 'ATTACK'
        entity_id = data['entity_id']
        
        if action_type == 'SKILL':
            self._handle_active_skill(entity_id)
        elif action_type == 'ATTACK':
            self._handle_attack(entity_id)

    def _handle_active_skill(self, entity_id):
        ident = self.ecs.get_component(entity_id, Identity)
        inter = self.ecs.get_component(entity_id, InteractionState)
        stats = self.ecs.get_component(entity_id, Stats)
        trans = self.ecs.get_component(entity_id, Transform)
        
        if inter.ability_used:
            self.event_bus.publish("SHOW_POPUP", "Skill already used today!")
            return

        cost = 50
        if ident.role == "MAFIA":
            if self.game_state.current_phase != "NIGHT":
                self.event_bus.publish("SHOW_POPUP", "Can only use at Night!")
                return
            if stats.ap < cost:
                self.event_bus.publish("SHOW_POPUP", f"Not enough AP ({cost})")
                return
            
            stats.ap -= cost
            inter.ability_used = True
            self.game_state.trigger_blackout(30000) # 30s Blackout
            self.event_bus.publish("SHOW_POPUP", "SABOTAGE ACTIVATED!", (255, 0, 0))
            self.event_bus.publish("PLAY_SOUND", ("BOOM", trans.x, trans.y, 999*TILE_SIZE, ident.role))
            
        elif ident.role == "POLICE":
            if stats.ap < cost:
                self.event_bus.publish("SHOW_POPUP", f"Not enough AP ({cost})")
                return
            
            stats.ap -= cost
            inter.ability_used = True
            self.game_state.trigger_siren(15000) # 15s Siren
            self.event_bus.publish("SHOW_POPUP", "SIREN ACTIVATED!", (0, 0, 255))
            self.event_bus.publish("PLAY_SOUND", ("SIREN", trans.x, trans.y, 999*TILE_SIZE, ident.role))

    def _handle_attack(self, entity_id):
        ident = self.ecs.get_component(entity_id, Identity)
        trans = self.ecs.get_component(entity_id, Transform)
        anim = self.ecs.get_component(entity_id, Animation)
        stats = self.ecs.get_component(entity_id, Stats)
        inv = self.ecs.get_component(entity_id, Inventory)
        inter = self.ecs.get_component(entity_id, InteractionState)

        now = pygame.time.get_ticks()
        if now - inter.last_attack_time < 500: return
        inter.last_attack_time = now

        # 1. Taser (Priority)
        if inv.items.get('TASER', 0) > 0:
            if stats.ap >= 10:
                target = self._get_target_in_front(entity_id)
                if target:
                    inv.items['TASER'] -= 1
                    stats.ap -= 10
                    t_status = self.ecs.get_component(target, StatusEffects)
                    t_status.stun_timer = now + 3000
                    self.event_bus.publish("SHOW_POPUP", "TASER SHOT!")
                    self.event_bus.publish("PLAY_SOUND", ("ZAP", trans.x, trans.y, 4*TILE_SIZE, ident.role))
                    return
        
        # 2. Role Attack
        if self.game_state.current_phase != "NIGHT": 
            self.event_bus.publish("SHOW_POPUP", "Can only attack at Night!")
            return

        attack_cost = 10
        if stats.ap < attack_cost:
            self.event_bus.publish("SHOW_POPUP", "Not enough AP!")
            return

        if ident.role == "MAFIA":
            target = self._get_target_in_front(entity_id)
            if target:
                stats.ap -= attack_cost
                t_stats = self.ecs.get_component(target, Stats)
                t_ident = self.ecs.get_component(target, Identity)
                t_inv = self.ecs.get_component(target, Inventory)
                
                if t_ident.role == "POLICE":
                    t_status = self.ecs.get_component(target, StatusEffects)
                    t_status.stun_timer = now + 2000
                    self.event_bus.publish("SHOW_POPUP", "STUNNED POLICE!")
                elif t_inv.items.get('ARMOR', 0) > 0:
                    t_inv.items['ARMOR'] -= 1
                    self.event_bus.publish("SHOW_POPUP", "BLOCKED!")
                    self.event_bus.publish("PLAY_SOUND", ("CLICK", trans.x, trans.y, 3*TILE_SIZE, ident.role))
                else:
                    t_stats.hp -= 70
                    self.event_bus.publish("SHOW_POPUP", "STABBED!", (255, 0, 0))
                    self.event_bus.publish("PLAY_SOUND", ("SLASH", trans.x, trans.y, 5*TILE_SIZE, ident.role))
                    if t_stats.hp <= 0:
                        t_stats.alive = False
                        self.event_bus.publish("ENTITY_DIED", target)

        elif ident.role == "POLICE":
            if inter.bullets_fired_today >= 1:
                self.event_bus.publish("SHOW_POPUP", "No bullets left!")
                return
            
            inter.bullets_fired_today += 1
            stats.ap -= attack_cost
            # 총알 발사 로직 (히트스캔 방식 단순화)
            self.event_bus.publish("PLAY_SOUND", ("GUNSHOT", trans.x, trans.y, 25*TILE_SIZE, ident.role))
            
            target = self._get_target_in_line(entity_id)
            if target:
                t_stats = self.ecs.get_component(target, Stats)
                t_stats.hp -= 70
                self.event_bus.publish("SHOW_POPUP", "HIT!", (255, 200, 50))
                if t_stats.hp <= 0:
                    t_stats.alive = False
                    self.event_bus.publish("ENTITY_DIED", target)

    def _get_target_in_front(self, entity_id):
        # 근접 타겟 찾기 (앞 1칸)
        trans = self.ecs.get_component(entity_id, Transform)
        anim = self.ecs.get_component(entity_id, Animation)
        
        front_x = trans.x + anim.facing_dir[0] * TILE_SIZE + 16
        front_y = trans.y + anim.facing_dir[1] * TILE_SIZE + 16
        
        targets = self.ecs.get_entities_with(Transform, Stats, Identity)
        for t in targets:
            if t == entity_id: continue
            t_trans = self.ecs.get_component(t, Transform)
            t_stats = self.ecs.get_component(t, Stats)
            if not t_stats.alive: continue
            
            if t_trans.rect.collidepoint(front_x, front_y):
                return t
        return None

    def _get_target_in_line(self, entity_id):
        # 원거리 타겟 찾기 (단순화: 10칸 직선)
        trans = self.ecs.get_component(entity_id, Transform)
        anim = self.ecs.get_component(entity_id, Animation)
        
        start_x, start_y = trans.x + 16, trans.y + 16
        dx, dy = anim.facing_dir
        
        targets = self.ecs.get_entities_with(Transform, Stats, Identity)
        best_target = None
        min_dist = 9999
        
        for i in range(1, 10):
            check_x = start_x + dx * TILE_SIZE * i
            check_y = start_y + dy * TILE_SIZE * i
            
            # 벽 충돌 체크
            if self.map_manager.check_any_collision(int(check_x//TILE_SIZE), int(check_y//TILE_SIZE)):
                break
                
            for t in targets:
                if t == entity_id: continue
                t_trans = self.ecs.get_component(t, Transform)
                t_stats = self.ecs.get_component(t, Stats)
                if not t_stats.alive: continue
                
                if t_trans.rect.collidepoint(check_x, check_y):
                    dist = i * TILE_SIZE
                    if dist < min_dist:
                        min_dist = dist
                        best_target = t
        return best_target

    def _open_chest_reward(self, gx, gy, entity_id):
        stats = self.ecs.get_component(entity_id, Stats)
        inv = self.ecs.get_component(entity_id, Inventory)
        
        roll = random.random()
        cumulative = 0.0
        selected = None
        
        # TREASURE_CHEST_RATES (settings.py 참조)
        from settings import TREASURE_CHEST_RATES, ITEMS
        for rate in TREASURE_CHEST_RATES:
            cumulative += rate['prob']
            if roll < cumulative: selected = rate; break
        if not selected: selected = TREASURE_CHEST_RATES[-1]
        
        msg = ""
        if selected['type'] == 'EMPTY': msg = selected['msg']
        elif selected['type'] == 'GOLD': 
            stats.coins += selected['amount']
            msg = selected['msg']
        elif selected['type'] == 'ITEM':
            item = random.choice(selected['items'])
            inv.items[item] = inv.items.get(item, 0) + 1
            msg = selected['msg'].format(item=ITEMS[item]['name'])
            
        self.map_manager.set_tile(gx, gy, 5310025, layer='object') # 빈 상자
        self.event_bus.publish("SHOW_POPUP", msg, (255, 215, 0))

    def update(self, dt):
        # 타일 쿨타임, 작업 진행 등은 필요하다면 여기서 매 프레임 체크
        # 현재 구조에서는 미니게임 완료 콜백이나 즉시 처리 위주
        pass

    def handle_use_item(self, data):
        item_key = data['item_key']
        entity_id = data['entity_id'] # If None, assume local player
        
        if entity_id is None:
            players = [e for e in self.ecs.get_entities_with(Identity) if self.ecs.get_component(e, Identity).is_player]
            if players:
                entity_id = players[0]
            else:
                return

        stats = self.ecs.get_component(entity_id, Stats)
        status = self.ecs.get_component(entity_id, StatusEffects)
        inv = self.ecs.get_component(entity_id, Inventory)
        ident = self.ecs.get_component(entity_id, Identity)
        trans = self.ecs.get_component(entity_id, Transform)
        
        if not inv or inv.items.get(item_key, 0) <= 0: return
        
        used = False
        s_type = "CRUNCH"
        msg = f"Used {ITEMS[item_key]['name']}"
        
        if item_key == 'TANGERINE':
            if stats.hp < stats.max_hp: stats.hp = min(stats.max_hp, stats.hp + 2); used = True
        elif item_key == 'CHOCOBAR':
            if stats.ap < stats.max_ap: stats.ap = min(stats.max_ap, stats.ap + 2); used = True
        elif item_key == 'TORTILLA':
            if stats.hp < stats.max_hp or stats.ap < stats.max_ap:
                stats.hp = min(stats.max_hp, stats.hp + 3)
                stats.ap = min(stats.max_ap, stats.ap + 3)
                used = True
        elif item_key == 'MEDKIT':
            if stats.hp < stats.max_hp: stats.hp = stats.max_hp; used = True; s_type = "CLICK"
        elif item_key == 'ENERGY_DRINK':
            if not status.buffs['INFINITE_STAMINA']:
                stats.hp = max(1, stats.hp - 3)
                status.buffs['INFINITE_STAMINA'] = True
                used = True; s_type = "GULP"
        elif item_key == 'PEANUT_BUTTER':
            if not status.buffs['SILENT']: status.buffs['SILENT'] = True; used = True
        elif item_key == 'COFFEE':
            if not status.buffs['FAST_WORK']: status.buffs['FAST_WORK'] = True; used = True; s_type = "GULP"
        elif item_key == 'PAINKILLER':
            if not status.buffs['NO_PAIN']: status.buffs['NO_PAIN'] = True; used = True; s_type = "GULP"
        elif item_key == 'BATTERY':
            if inv.device_battery < 100: inv.device_battery = min(100, inv.device_battery + 50); used = True; s_type = "CLICK"
        elif item_key == 'POWERBANK':
            if inv.device_battery < 100:
                inv.device_battery = 100
                inv.powerbank_uses += 1
                if inv.powerbank_uses >= 2:
                    inv.powerbank_uses = 0
                    used = True
                else:
                    self.event_bus.publish("SHOW_POPUP", "Used once (1 left)")
                    self.event_bus.publish("PLAY_SOUND", ("CLICK", trans.x, trans.y, 3*TILE_SIZE, ident.role))
                    return
                s_type = "CLICK"
        
        if used:
            inv.items[item_key] -= 1
            self.event_bus.publish("SHOW_POPUP", msg)
            self.event_bus.publish("PLAY_SOUND", (s_type, trans.x, trans.y, 4*TILE_SIZE, ident.role))

    def handle_interaction_request(self, data):
        entity_id = data['entity_id']
        mode = data['mode'] # 'short' or 'long'
        
        transform = self.ecs.get_component(entity_id, Transform)
        interaction = self.ecs.get_component(entity_id, InteractionState)
        inventory = self.ecs.get_component(entity_id, Inventory)
        identity = self.ecs.get_component(entity_id, Identity)
        stats = self.ecs.get_component(entity_id, Stats)
        
        if not transform or not interaction: return

        # 바라보는 방향의 타일 좌표 계산 (Animation 컴포넌트 필요, 혹은 Velocity 기반 추정)
        # 여기서는 Velocity 기반으로 추정하거나 InputSystem에서 전달받은 facing_dir 사용
        # 편의상 현재 위치 기준 가장 가까운 상호작용 가능 타일 검색 (기존 로직과 유사)
        
        gx = int(transform.x // TILE_SIZE)
        gy = int(transform.y // TILE_SIZE)
        
        # 4방향 검색
        target_pos = None
        target_tid = 0
        target_layer = None
        
        # 우선순위: 현재 위치 -> 앞 -> 주변
        candidates = [(0,0), (0,1), (0,-1), (1,0), (-1,0)]
        for dx, dy in candidates:
            nx, ny = gx + dx, gy + dy
            if 0 <= nx < self.map_manager.width and 0 <= ny < self.map_manager.height:
                if self.map_manager.is_tile_on_cooldown(nx, ny): continue
                
                for layer in ['object', 'wall', 'floor']:
                    val = self.map_manager.get_tile_full(nx, ny, layer)
                    tid = val[0]
                    if tid != 0:
                        cat = get_tile_category(tid)
                        d_val = get_tile_interaction(tid)
                        func = get_tile_function(tid)
                        if cat in [5, 9] or d_val > 0 or func in [2, 3] or tid == 5321025:
                            target_pos = (nx, ny)
                            target_tid = tid
                            target_layer = layer
                            break
                if target_pos: break
        
        if not target_pos: return
        
        tx, ty = target_pos
        
        if tid == 5321025: # Treasure Chest Closed
            if mode == 'short':
                self.event_bus.publish("SHOW_POPUP", "Hold 'E' to Unlock")
            elif mode == 'long':
                if stats.ap < 5:
                    self.event_bus.publish("SHOW_POPUP", "Not enough AP (5)")
                    return
                
                self.event_bus.publish("START_MINIGAME", {
                    'type': 'MASHING', 'difficulty': 2, # Hacking 대체
                    'on_success': lambda: self._open_chest_reward(tx, ty, entity_id),
                    'on_fail': lambda: stats.ap - 2
                })
            return

        cat = get_tile_category(target_tid)
        d_val = get_tile_interaction(target_tid)
        
        # 문 (Door)
        if cat == 5:
            if d_val == 1: # Open -> Close/Lock
                if mode == 'short':
                    self.map_manager.close_door(tx, ty, target_layer)
                    self.event_bus.publish("PLAY_SOUND", ("SLAM", tx*TILE_SIZE, ty*TILE_SIZE, 6*TILE_SIZE, identity.role))
                elif mode == 'long':
                    # Lock
                    has_key = inventory.items.get('KEY', 0) > 0 or inventory.items.get('MASTER_KEY', 0) > 0
                    if has_key:
                        if inventory.items.get('KEY', 0) > 0: inventory.items['KEY'] -= 1
                        self.map_manager.lock_door(tx, ty, target_layer)
                        self.event_bus.publish("PLAY_SOUND", ("CLICK", tx*TILE_SIZE, ty*TILE_SIZE, 3*TILE_SIZE, identity.role))
                    else:
                        # 미니게임 트리거
                        self.event_bus.publish("START_MINIGAME", {
                            'type': 'TIMING', 'difficulty': 2,
                            'on_success': lambda: self.map_manager.lock_door(tx, ty, target_layer),
                            'on_fail': lambda: stats.ap - 2
                        })
            
            elif d_val == 3: # Locked -> Unlock
                if mode == 'short':
                    self.event_bus.publish("SHOW_POPUP", "It's Locked.")
                elif mode == 'long':
                    if inventory.items.get('KEY', 0) > 0:
                        inventory.items['KEY'] -= 1
                        self.map_manager.unlock_door(tx, ty, target_layer)
                        self.event_bus.publish("PLAY_SOUND", ("CLICK", tx*TILE_SIZE, ty*TILE_SIZE, 3*TILE_SIZE, identity.role))
                    else:
                        # 락픽 미니게임
                        self.event_bus.publish("START_MINIGAME", {
                            'type': 'LOCKPICK', 'difficulty': 3,
                            'on_success': lambda: self.map_manager.unlock_door(tx, ty, target_layer),
                            'on_fail': lambda: stats.ap - 2
                        })
            
            elif "Open" in get_tile_name(target_tid): # Closed -> Open
                 if mode == 'short':
                    self.map_manager.open_door(tx, ty, target_layer)
                    self.event_bus.publish("PLAY_SOUND", ("CREAK", tx*TILE_SIZE, ty*TILE_SIZE, 5*TILE_SIZE, identity.role))

        # 작업 (Work)
        if mode == 'short':
            job_key = identity.role if identity.role == "DOCTOR" else identity.sub_role
            if job_key in WORK_SEQ:
                seq = WORK_SEQ[job_key]
                target_idx = interaction.work_step % len(seq)
                if target_tid == seq[target_idx]:
                    # 작업 미니게임 시작
                    if stats.ap < 10:
                        self.event_bus.publish("SHOW_POPUP", "Not enough AP!")
                        return
                    
                    # 성공 시 콜백
                    def on_work_success():
                        stats.ap -= 10
                        stats.coins += 1
                        interaction.daily_work_count += 1
                        self.map_manager.set_tile_cooldown(tx, ty, 3000)
                        
                        # [NEW] Generate TAP sound
                        self.event_bus.publish("PLAY_SOUND", ("TAP", tx*TILE_SIZE + 16, ty*TILE_SIZE + 16, 4*TILE_SIZE, identity.role))
                        
                        # 다음 타일로 변경 (농부 등)
                        next_tile = seq[(target_idx + 1) % len(seq)]
                        # 단순화를 위해 농부만 타일 변경한다고 가정 (기존 로직 참조)
                        if identity.sub_role == 'FARMER':
                            self.map_manager.set_tile(tx, ty, next_tile, layer=target_layer)
                            
                    self.event_bus.publish("START_MINIGAME", {
                        'type': 'MASHING', 'difficulty': 1,
                        'on_success': on_work_success,
                        'on_fail': lambda: stats.ap - 2
                    })