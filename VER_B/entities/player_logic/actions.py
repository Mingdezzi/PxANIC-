import pygame
import math
import random
from settings import TILE_SIZE, VENDING_MACHINE_TID, TREASURE_CHEST_RATES, ITEMS, WORK_SEQ, MINIGAME_MAP, INDOOR_ZONES, ZONES
from world.tiles import get_tile_category, get_tile_interaction, get_tile_function, get_tile_name, check_collision
from entities.bullet import Bullet
from systems.logger import GameLogger

class ActionLogic:
    def __init__(self, player):
        self.p = player
        self.logger = GameLogger.get_instance()

    def interact_tile(self, gx, gy, npcs, mode='short'):
        px, py = self.p.rect.centerx // TILE_SIZE, self.p.rect.centery // TILE_SIZE
        dist = abs(px - gx) + abs(py - gy)
        if dist != 1: return None

        tid = 0; target_layer = None
        map_mgr = self.p.map_manager
        
        if 0 <= gx < self.p.map_width and 0 <= gy < self.p.map_height:
            if map_mgr and map_mgr.is_tile_on_cooldown(gx, gy): return "Cooldown!"
            for layer in ['object', 'wall', 'floor']:
                val = map_mgr.get_tile_full(gx, gy, layer)
                if val[0] != 0:
                    tid_check = val[0]; cat = get_tile_category(tid_check); d_val = get_tile_interaction(tid_check); func = get_tile_function(tid_check)
                    if cat in [5, 9] or d_val > 0 or func in [2, 3] or tid_check == 5321025: tid = tid_check; target_layer = layer; break

        if tid == 0: return None
        self.logger.info("PLAYER", f"Interact with {tid} at ({gx}, {gy}) Mode: {mode}")

        if tid == VENDING_MACHINE_TID: return "OPEN_SHOP" if mode == 'short' else None

        if tid == 5321025: 
            if mode == 'short': return "Hold 'E' to Unlock"
            elif mode == 'long':
                if self.p.ap < 5: return "Not enough AP (5)"
                self.p.minigame.start(random.choice(['MEMORY']), 2, lambda: self._open_chest_reward(gx, gy), self.p.fail_penalty)
                return f"Unlocking..."

        cat = get_tile_category(tid); d_val = get_tile_interaction(tid)
        if cat == 5:
            if d_val == 1: 
                if mode == 'short': 
                    map_mgr.open_door(gx, gy, target_layer)
                    return "Opened", ("CREAK", gx*TILE_SIZE, gy*TILE_SIZE, 5*TILE_SIZE, self.p.role)
                elif mode == 'long':
                    is_inside = (self.p.zone_map[py][px] in INDOOR_ZONES)
                    if is_inside or self.p.inventory.get('KEY', 0) > 0 or self.p.inventory.get('MASTER_KEY', 0) > 0:
                        if self.p.ap < 5: return "Not enough AP (5)"
                        if not is_inside and self.p.inventory.get('KEY', 0) > 0: self.p.inventory['KEY'] -= 1
                        self.p.try_spend_ap(5); map_mgr.lock_door(gx, gy, target_layer)
                        return "Locked Door", ("CLICK", gx*TILE_SIZE, gy*TILE_SIZE, 3*TILE_SIZE, self.p.role)
                    else:
                        if self.p.ap < 5: return "Not enough AP (5)"
                        self.p.minigame.start('TIMING', 2, lambda: map_mgr.lock_door(gx, gy, target_layer), self.p.fail_penalty)
                        return "Locking..."
            elif d_val == 3: 
                if mode == 'short': return "It's Locked."
                elif mode == 'long':
                    if self.p.inventory.get('KEY', 0) > 0: 
                        self.p.inventory['KEY'] -= 1; map_mgr.unlock_door(gx, gy, target_layer)
                        return "Unlocked with Key", ("CLICK", gx*TILE_SIZE, gy*TILE_SIZE, 3*TILE_SIZE, self.p.role)
                    elif self.p.inventory.get('MASTER_KEY', 0) > 0: 
                        map_mgr.unlock_door(gx, gy, target_layer)
                        return "Unlocked with Master Key", ("CLICK", gx*TILE_SIZE, gy*TILE_SIZE, 3*TILE_SIZE, self.p.role)
                    else:
                        if "Glass" in get_tile_name(tid): return "Cannot Pick Lock!"
                        if self.p.ap < 5: return "Not enough AP (5)"
                        self.p.minigame.start('LOCKPICK', 3, lambda: map_mgr.unlock_door(gx, gy, target_layer), self.p.fail_penalty)
                        return "Picking Lock..."
            elif "Open" in get_tile_name(tid):
                if mode == 'short': map_mgr.close_door(gx, gy, target_layer); return "Closed", ("SLAM", gx*TILE_SIZE, gy*TILE_SIZE, 6*TILE_SIZE, self.p.role)

        if mode == 'short':
            if self.p.role == "MAFIA" and self.p.current_phase_ref == "NIGHT":
                 cat = get_tile_category(tid)
                 if cat in [3, 5, 6]:
                     self.p.minigame.start('MASHING', 2, lambda: self.do_break(gx, gy), self.p.fail_penalty)
                     return "Breaking...", ("BANG!", gx*TILE_SIZE, gy*TILE_SIZE, 12*TILE_SIZE, self.p.role)

            job_key = self.p.role if self.p.role == "DOCTOR" else self.p.sub_role
            if job_key in WORK_SEQ:
                seq = WORK_SEQ[job_key]; target_idx = self.p.work_step % len(seq); target_tid = seq[target_idx]
                if tid == target_tid:
                    m_type = MINIGAME_MAP[job_key].get(target_idx, 'MASHING')
                    next_t = seq[(target_idx + 1) % len(seq)]; is_final = (target_idx == len(seq) - 1)
                    if self.p.ap < 10: return "Not enough AP (10)"
                    self.p.minigame.start(m_type, 1, lambda: self.work_complete(gx*TILE_SIZE, gy*TILE_SIZE, next_t, is_final), self.p.fail_penalty)
                    return f"Working ({m_type})..."
                elif tid in seq: return "Not today's task."
        return None

    def _open_chest_reward(self, gx, gy):
        self.p.try_spend_ap(5)
        roll = random.random(); cumulative = 0.0; selected_reward = None
        for rate in TREASURE_CHEST_RATES:
            cumulative += rate['prob']
            if roll < cumulative: selected_reward = rate; break
        if not selected_reward: selected_reward = TREASURE_CHEST_RATES[-1]
        
        msg = ""
        if selected_reward['type'] == 'EMPTY': msg = selected_reward['msg']
        elif selected_reward['type'] == 'GOLD': self.p.coins += selected_reward['amount']; msg = selected_reward['msg']
        elif selected_reward['type'] == 'ITEM':
            item = random.choice(selected_reward['items']); self.p.inventory[item] = self.p.inventory.get(item, 0) + 1
            msg = selected_reward['msg'].format(item=ITEMS[item]['name'])
            
        if self.p.map_manager: self.p.map_manager.set_tile(gx, gy, 5310025, layer='object')
        self.p.add_popup(msg, (255, 215, 0))

    def work_complete(self, px, py, next_tile, reward=False):
        self.p.try_spend_ap(10); gx, gy = px // TILE_SIZE, py // TILE_SIZE
        if self.p.sub_role == 'FARMER' and next_tile is not None: self.p.map_manager.set_tile(gx, gy, next_tile)
        if self.p.map_manager: self.p.map_manager.set_tile_cooldown(gx, gy, 3000)
        self.p.coins += 1; self.p.daily_work_count += 1

    def do_break(self, px, py):
        gx, gy = (px, py) if isinstance(px, int) and px < self.p.map_width else (px // TILE_SIZE, py // TILE_SIZE)
        if self.p.try_spend_ap(2): self.p.map_manager.set_tile(gx, gy, 5310005)

    def do_attack(self, target):
        if not self.p.alive or self.p.role == "SPECTATOR": return None
        if not target or not target.alive: return None
        now = pygame.time.get_ticks()
        if now - self.p.last_attack_time < self.p.attack_cooldown: return None
        self.p.last_attack_time = now
        
        attack_cost = 10
        if self.p.inventory.get('TASER', 0) > 0 and self.p.try_spend_ap(attack_cost, allow_health_cost=False):
            self.p.inventory['TASER'] -= 1; self.logger.info("PLAYER", "Used TASER"); target.take_stun(3000)
            return ("TASER SHOT!", (self.p.rect.centerx, self.p.rect.centery)), ("ZAP", self.p.rect.centerx, self.p.rect.centery, 4*TILE_SIZE, self.p.role)
            
        if self.p.current_phase_ref != "NIGHT": return None
        
        if self.p.role == "MAFIA" and self.p.try_spend_ap(attack_cost, allow_health_cost=False):
            if target.role == "POLICE": 
                target.take_stun(2000)
                return ("STUNNED POLICE!", (self.p.rect.centerx, self.p.rect.centery)), ("SLASH", self.p.rect.centerx, self.p.rect.centery, 5*TILE_SIZE, self.p.role)
            if target.inventory.get('ARMOR', 0) > 0: 
                target.inventory['ARMOR'] -= 1
                return ("BLOCKED", (self.p.rect.centerx, self.p.rect.centery)), ("CLICK", self.p.rect.centerx, self.p.rect.centery, 3*TILE_SIZE, self.p.role)
            target.take_damage(70)
            self.logger.info("PLAYER", f"Attacked {target.name}")
            return ("STAB", (self.p.rect.centerx, self.p.rect.centery)), ("SLASH", self.p.rect.centerx, self.p.rect.centery, 5*TILE_SIZE, self.p.role)
            
        elif self.p.role == "POLICE" and self.p.try_spend_ap(attack_cost, allow_health_cost=False):
            if self.p.current_phase_ref in ['MORNING', 'DAY', 'VOTE', 'NOON', 'AFTERNOON'] or self.p.bullets_fired_today >= 1: return None
            self.p.bullets_fired_today += 1
            dx = target.rect.centerx - self.p.rect.centerx; dy = target.rect.centery - self.p.rect.centery; angle = math.atan2(dy, dx)
            self.p.bullets.append(Bullet(self.p.rect.centerx, self.p.rect.centery, angle, is_enemy=False))
            self.logger.info("PLAYER", "Fired Gun")
            return ("GUNSHOT", (self.p.rect.centerx, self.p.rect.centery)), ("GUNSHOT", self.p.rect.centerx, self.p.rect.centery, 25*TILE_SIZE, self.p.role)
        return None

    def do_heal(self, target):
        if self.p.role != "DOCTOR" or not self.p.alive: return None
        if not self.p.try_spend_ap(10, allow_health_cost=False): return "Not enough AP!"
        if target and target.alive:
            target.hp = min(target.max_hp, target.hp + 50)
            self.logger.info("PLAYER", f"Doctor Healed {target.name}")
            return f"Healed {target.name}!", ("GULP", target.rect.centerx, target.rect.centery, 4*TILE_SIZE, self.p.role)
        return "No target to heal."

    def use_active_skill(self):
        if not self.p.alive: return None
        if self.p.role == "SPECTATOR": return None
        if self.p.ability_used: return "Skill already used today!"
        
        cost = 50
        if self.p.role == "MAFIA":
            if self.p.current_phase_ref != "NIGHT": return "Can only use at Night!"
            if not self.p.try_spend_ap(cost, allow_health_cost=False): return f"Not enough AP (Need {cost})!"
            self.p.ability_used = True; return "USE_SABOTAGE"
        elif self.p.role == "POLICE":
            if not self.p.try_spend_ap(cost, allow_health_cost=False): return f"Not enough AP (Need {cost})!"
            self.p.ability_used = True; return "USE_SIREN"
        return "No Active Skill for this role."

    def update_bullets(self, npcs):
        for b in self.p.bullets[:]:
            b.update()
            if b.x < 0 or b.x > self.p.map_width * TILE_SIZE or b.y < 0 or b.y > self.p.map_height * TILE_SIZE: self.p.bullets.remove(b); continue
            gx = int(b.x // TILE_SIZE); gy = int(b.y // TILE_SIZE)
            if 0 <= gx < self.p.map_width and 0 <= gy < self.p.map_height:
                hit_wall = False
                if self.p.map_manager:
                    if self.p.map_manager.check_any_collision(gx, gy): hit_wall = True
                else:
                    tid = self.p.map_data[gy][gx]; tid = tid[0] if isinstance(tid, (tuple, list)) else tid
                    if check_collision(tid): hit_wall = True
                if hit_wall: b.alive = False; self.p.bullets.remove(b); continue
            bullet_rect = pygame.Rect(b.x-2, b.y-2, 4, 4)
            targets = [self.p] if b.is_enemy else npcs
            for t in targets:
                if t.alive and bullet_rect.colliderect(t.rect): t.take_damage(70); b.alive = False; self.p.bullets.remove(b); break
