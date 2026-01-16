import pygame
import random
from .base_system import BaseSystem
from settings import TILE_SIZE, VENDING_MACHINE_TID, WORK_SEQ, MINIGAME_MAP, TREASURE_CHEST_RATES, ITEMS, HIDEABLE_TILES, BED_TILES
from world.tiles import get_tile_category, get_tile_interaction, get_tile_function, get_tile_name

class InteractionSystem(BaseSystem):
    def __init__(self, event_bus, map_manager, ui_manager):
        self.event_bus = event_bus
        self.map_manager = map_manager
        self.ui_manager = ui_manager
        
        # 이벤트 구독
        self.event_bus.subscribe("MINIGAME_RESULT", self._on_minigame_result)
        self.event_bus.subscribe("USE_ITEM_REQUEST", self._on_use_item)
        self.event_bus.subscribe("BUY_ITEM_REQUEST", self._on_buy_item)
        self.event_bus.subscribe("TRIGGER_BLACKOUT", self._on_trigger_blackout_request)
        
        self.time_system = None 

    def process(self, entity, keys_pressed):
        # E키 상호작용 로직 (Player Only)
        interaction = entity.interaction
        
        if keys_pressed[pygame.K_e]:
            if not interaction.e_key_pressed:
                interaction.e_key_pressed = True
                interaction.interaction_hold_timer = pygame.time.get_ticks()
        else:
            if interaction.e_key_pressed:
                # 키 뗌 -> 상호작용 시도
                hold_time = pygame.time.get_ticks() - interaction.interaction_hold_timer
                mode = 'long' if hold_time >= 500 else 'short'
                self._try_interact(entity, mode)
                interaction.e_key_pressed = False

    def handle_special_key(self, entity, key):
        """PlayState의 handle_event에서 직접 호출됨"""
        if key == pygame.K_q:
            self._use_active_skill(entity)
        elif key == pygame.K_r:
            self._reload_or_action(entity)

    def _on_use_item(self, data):
        item_key = data.get('item_key')
        player = self.ui_manager.player
        if not player or not player.stats.alive: return

        if not player.inventory.has_item(item_key):
            return

        used = False
        sound = "GULP"
        stats = player.stats
        
        if item_key == 'TANGERINE':
            if stats.hp < stats.max_hp:
                stats.hp = min(stats.max_hp, stats.hp + 20); used = True; sound = "CRUNCH"
        elif item_key == 'CHOCOBAR':
            if stats.ap < stats.max_ap:
                stats.ap = min(stats.max_ap, stats.ap + 20); used = True; sound = "CRUNCH"
        elif item_key == 'TORTILLA':
            if stats.hp < stats.max_hp or stats.ap < stats.max_ap:
                stats.hp = min(stats.max_hp, stats.hp + 30)
                stats.ap = min(stats.max_ap, stats.ap + 30); used = True; sound = "CRUNCH"
        elif item_key == 'MEDKIT':
            if stats.hp < stats.max_hp:
                stats.hp = stats.max_hp; used = True; sound = "CLICK"
        elif item_key == 'ENERGY_DRINK':
            stats.status_effects['INFINITE_STAMINA'] = True
            used = True; sound = "GULP"
        elif item_key == 'BATTERY':
            if player.graphics.device_battery < 100:
                player.graphics.device_battery = min(100, player.graphics.device_battery + 50)
                used = True; sound = "CLICK"

        if used:
            player.inventory.remove_item(item_key)
            self.event_bus.publish("SHOW_ALERT", {'text': f"Used {ITEMS[item_key]['name']}", 'color': (100, 255, 100)})
            self._play_sound(sound, player.transform.x // TILE_SIZE, player.transform.y // TILE_SIZE)

    def _on_buy_item(self, data):
        item_key = data.get('item_key')
        player = self.ui_manager.player
        price = ITEMS[item_key]['price']
        if player.inventory.coins >= price:
            player.inventory.coins -= price
            player.inventory.add_item(item_key)
            self.event_bus.publish("SHOW_ALERT", {'text': f"Bought {ITEMS[item_key]['name']}", 'color': (255, 215, 0)})
            self._play_sound("KA-CHING", player.transform.x // TILE_SIZE, player.transform.y // TILE_SIZE)
        else:
            self.event_bus.publish("SHOW_ALERT", {'text': "Not enough money!", 'color': (255, 50, 50)})

    def _use_active_skill(self, entity):
        role = entity.role.main_role
        if role == "MAFIA":
            if entity.stats.ap >= 50:
                entity.stats.ap -= 50
                self.event_bus.publish("TRIGGER_BLACKOUT", {'duration': 10000})
            else:
                self.event_bus.publish("SHOW_ALERT", {'text': "Not enough AP (50)", 'color': (255, 50, 50)})
        elif role == "POLICE":
            if entity.stats.ap >= 30:
                entity.stats.ap -= 30
                self.event_bus.publish("TRIGGER_SIREN", {'x': entity.transform.x, 'y': entity.transform.y, 'radius': 300})
        elif role in ["CITIZEN", "DOCTOR"]:
            entity.graphics.device_on = not entity.graphics.device_on
            state = "ON" if entity.graphics.device_on else "OFF"
            self.event_bus.publish("SHOW_ALERT", {'text': f"Device {state}", 'color': (100, 255, 100)})

    def _reload_or_action(self, entity):
        self.event_bus.publish("SHOW_ALERT", {'text': "Reloading..."})

    def _try_interact(self, entity, mode):
        if entity.graphics.is_hiding:
            entity.graphics.is_hiding = False
            self.event_bus.publish("SHOW_ALERT", {'text': "Revealed"})
            return

        cx, cy = entity.transform.rect.centerx, entity.transform.rect.centery
        tx, ty = int(cx // TILE_SIZE), int(cy // TILE_SIZE)
        dx, dy = entity.transform.facing
        fx, fy = tx + dx, ty + dy
        
        target_tid = 0
        target_pos = (tx, ty)
        
        for layer in ['object', 'floor']:
            tid = self.map_manager.get_tile(tx, ty, layer)
            if tid in HIDEABLE_TILES or tid in BED_TILES:
                target_tid, target_pos = tid, (tx, ty); break
        
        if target_tid == 0:
            for layer in ['object', 'wall']:
                tid = self.map_manager.get_tile(fx, fy, layer)
                if tid != 0:
                    cat = get_tile_category(tid)
                    if cat in [5, 9] or tid == VENDING_MACHINE_TID or tid == 5321025:
                        target_tid, target_pos = tid, (fx, fy); break
        
        if target_tid != 0:
            self._execute_interaction(entity, target_pos[0], target_pos[1], target_tid, mode)

    def _execute_interaction(self, entity, gx, gy, tid, mode):
        if tid in HIDEABLE_TILES:
            entity.graphics.is_hiding = True; entity.graphics.hiding_type = 1
            self.event_bus.publish("SHOW_ALERT", {'text': "Hiding...", 'color': (100, 100, 255)}); return
        if tid in BED_TILES:
            entity.graphics.is_hiding = True; entity.graphics.hiding_type = 2
            self.event_bus.publish("SHOW_ALERT", {'text': "Resting...", 'color': (100, 100, 255)}); return
        if tid == VENDING_MACHINE_TID:
            if mode == 'short': self.event_bus.publish("TOGGLE_SHOP", {})
            return
        if tid == 5321025:
            if mode == 'short': self.event_bus.publish("SHOW_ALERT", {'text': "Hold 'E' to Unlock"})
            elif mode == 'long':
                 self.event_bus.publish("START_MINIGAME", {'type': 'MASHING', 'difficulty': 1, 'context': {'action': 'OPEN_CHEST', 'gx': gx, 'gy': gy, 'entity': entity}})
            return

        cat = get_tile_category(tid)
        d_val = get_tile_interaction(tid)
        name = get_tile_name(tid)

        if cat == 5:
            if d_val == 1:
                if mode == 'short': self.map_manager.open_door(gx, gy); self._play_sound("CREAK", gx, gy)
                elif mode == 'long':
                    if self._has_key(entity) and entity.stats.ap >= 5:
                        entity.stats.ap -= 5
                        if self.map_manager.lock_door(gx, gy):
                            self.event_bus.publish("SHOW_ALERT", {'text': "Locked Door"}); self._play_sound("CLICK", gx, gy)
            elif d_val == 3:
                if mode == 'short': self.event_bus.publish("SHOW_ALERT", {'text': "It's Locked."})
                elif mode == 'long':
                    if self._use_key(entity): self.map_manager.unlock_door(gx, gy); self.event_bus.publish("SHOW_ALERT", {'text': "Unlocked"}); self._play_sound("CLICK", gx, gy)
                    elif entity.stats.ap >= 5:
                        self.event_bus.publish("START_MINIGAME", {'type': 'LOCKPICK', 'difficulty': 2, 'context': {'action': 'UNLOCK_DOOR', 'gx': gx, 'gy': gy, 'entity': entity}})
            elif "Open" in name:
                if mode == 'short': self.map_manager.close_door(gx, gy); self._play_sound("SLAM", gx, gy)

        job = entity.role.main_role if entity.role.main_role == "DOCTOR" else entity.role.sub_role
        if job in WORK_SEQ:
            seq = WORK_SEQ[job]; target_idx = entity.role.work_step % len(seq)
            if tid == seq[target_idx]:
                if entity.stats.ap >= 10:
                    m_type = MINIGAME_MAP.get(job, {}).get(target_idx, 'MASHING')
                    self.event_bus.publish("START_MINIGAME", {'type': m_type, 'difficulty': 1, 'context': {'action': 'DO_WORK', 'gx': gx, 'gy': gy, 'entity': entity, 'seq': seq, 'idx': target_idx}})
                else: self.event_bus.publish("SHOW_ALERT", {'text': "Not enough AP (10)", 'color': (255, 50, 50)})

    def _on_minigame_result(self, data):
        result = data.get('result'); ctx = data.get('context', {}); action = ctx.get('action'); entity = ctx.get('entity'); gx, gy = ctx.get('gx'), ctx.get('gy')
        if result == 'SUCCESS':
            if action == 'OPEN_CHEST': self._open_chest_reward(entity, gx, gy)
            elif action == 'UNLOCK_DOOR':
                entity.stats.ap -= 5; self.map_manager.unlock_door(gx, gy); self.event_bus.publish("SHOW_ALERT", {'text': "Picklock Success!"}); self._play_sound("CLICK", gx, gy)
            elif action == 'DO_WORK':
                entity.stats.ap -= 10; seq = ctx['seq']; idx = ctx['idx']; next_tile = seq[(idx + 1) % len(seq)]
                if entity.role.sub_role == 'FARMER': self.map_manager.set_tile(gx, gy, next_tile)
                entity.inventory.coins += 1; entity.role.daily_work_count += 1; entity.role.work_step += 1
                self.event_bus.publish("SHOW_ALERT", {'text': "Work Done! (+1 G)", 'color': (255, 215, 0)}); self._play_sound("WORK", gx, gy)
        else:
            if entity: entity.stats.ap = max(0, entity.stats.ap - 2)
            self.event_bus.publish("SHOW_ALERT", {'text': "Failed...", 'color': (255, 100, 100)})

    def _open_chest_reward(self, entity, gx, gy):
        if entity.stats.ap < 5: self.event_bus.publish("SHOW_ALERT", {'text': "Not enough AP", 'color': (255, 50, 50)}); return
        entity.stats.ap -= 5; roll = random.random(); cumulative = 0.0; selected = TREASURE_CHEST_RATES[-1]
        for rate in TREASURE_CHEST_RATES:
            cumulative += rate['prob']
            if roll < cumulative: selected = rate; break
        msg = selected['msg']
        if selected['type'] == 'GOLD': entity.inventory.coins += selected['amount']
        elif selected['type'] == 'ITEM':
            item = random.choice(selected['items']); entity.inventory.add_item(item); msg = msg.format(item=ITEMS[item]['name'])
        self.map_manager.set_tile(gx, gy, 5310025, layer='object'); self.event_bus.publish("SHOW_ALERT", {'text': msg, 'color': (255, 215, 0)}); self._play_sound("KA-CHING", gx, gy)

    def _has_key(self, entity): return entity.inventory.has_item('KEY') or entity.inventory.has_item('MASTER_KEY')
    def _use_key(self, entity):
        if entity.inventory.has_item('KEY'): entity.inventory.remove_item('KEY'); return True
        elif entity.inventory.has_item('MASTER_KEY'): return True
        return False

    def _play_sound(self, name, x, y): self.event_bus.publish("PLAY_SOUND", {'name': name, 'x': x * TILE_SIZE, 'y': y * TILE_SIZE})
    def _on_trigger_blackout_request(self, data): pass # TimeSystem handles this