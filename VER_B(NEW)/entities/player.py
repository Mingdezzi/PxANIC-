import pygame
import math
import random
from settings import *
from colors import *
from world.tiles import *
from systems.minigame import MiniGameManager
from systems.renderer import CharacterRenderer
from .entity import Entity
from systems.logger import GameLogger

class Bullet:
    def __init__(self, x, y, angle, is_enemy=False):
        self.x = x; self.y = y; self.angle = angle
        self.speed = 12; self.radius = 4; self.alive = True; self.is_enemy = is_enemy
    def update(self): self.x += math.cos(self.angle) * self.speed; self.y += math.sin(self.angle) * self.speed
    def draw(self, screen, camera_x, camera_y):
        color = (255, 100, 100) if self.is_enemy else COLORS['BULLET']
        pygame.draw.circle(screen, color, (int(self.x - camera_x), int(self.y - camera_y)), self.radius)

class Player(Entity):
    def __init__(self, x, y, width, height, map_data, zone_map, map_manager=None):
        super().__init__(x, y, map_data, map_width=width, map_height=height, zone_map=zone_map, name="Player", role="CITIZEN", map_manager=map_manager)
        self.logger = GameLogger.get_instance()
        self.start_x = float(self.rect.x); self.start_y = float(self.rect.y)
        
        self.color = COLORS['CLOTHES']
        self.emotions = {}
        self.pre_hide_pos = None; self.flashlight_on = False; self.breath_gauge = 100
        self.infinite_stamina_buff = False; self.ability_used = False
        self.sound_timers = {'HEARTBEAT': 0, 'COUGH': 0, 'SCREAM': 0, 'FOOTSTEP': 0}
        self.shiver_timer = 0; self.blink_timer = 0
        self.is_eyes_closed = False; self.vibration_offset = (0, 0)
        self.bullets = []; self.last_attack_time = 0; self.attack_cooldown = 500
        self.minigame = MiniGameManager()
        self.vote_count = 0; self.daily_work_count = 0; self.work_step = 0
        self.bullets_fired_today = 0; self.day_count = 0; self.exhausted = False; self.exhaust_timer = 0
        self.doors_to_close = []; self.current_phase_ref = "MORNING"
        self.custom = {'skin': 0, 'clothes': 0, 'hat': 0}
        self.move_state = "WALK"; self.facing_dir = (0, 1); self.interaction_hold_timer = 0; self.e_key_pressed = False
        self.logger.info("PLAYER", f"Initialized at ({x}, {y}) Role: {self.role}")

    @property
    def is_dead(self): return not self.alive
    @is_dead.setter
    def is_dead(self, value): self.alive = not value

    def reset(self):
        self.pos_x = self.start_x; self.pos_y = self.start_y
        self.rect.x = int(self.pos_x); self.rect.y = int(self.pos_y)
        self.hp, self.ap, self.coins = self.max_hp, self.max_ap, 0
        self.alive = True; self.is_hiding = False; self.hiding_type = 0
        self.bullets.clear(); self.inventory = {k: 0 for k in ITEMS.keys()}; self.inventory['BATTERY'] = 1
        for k in self.buffs: self.buffs[k] = False
        self.flashlight_on, self.device_on, self.minigame.active = False, False, False
        self.breath_gauge = 100; self.ability_used = False
        self.daily_work_count = 0; self.work_step = 0; self.bullets_fired_today = 0
        self.day_count = 0; self.exhausted = False; self.hidden_in_solid = False
        self.emotions = {}; self.move_state = "WALK"; self.device_battery = 100.0; self.infinite_stamina_buff = False; self.powerbank_uses = 0

    def change_role(self, new_role, sub_role=None):
        self.role = new_role
        if self.role == "CITIZEN": self.sub_role = sub_role if sub_role else random.choice(["FARMER", "MINER", "FISHER"])
        else: self.sub_role = None
        if self.role == "DOCTOR": self.custom['clothes'] = 6
        elif self.role == "POLICE": self.custom['clothes'] = 2
        self.logger.info("PLAYER", f"Role changed to {self.role} ({self.sub_role})")

    def morning_process(self, slept_at_home):
        if self.role == "SPECTATOR": return False
        super().morning_process()
        self.day_count += 1
        
        # [개편] 수면 효과 (집 안 +10, 집 밖 -30)
        if slept_at_home:
            self.hp = min(self.max_hp, self.hp + 10)
            self.ap = min(self.max_ap, self.ap + 10)
        else:
            self.hp = max(0, self.hp - 30)
            self.ap = max(0, self.ap - 30)
        
        # [개편] 업무 페널티
        if self.role in ["CITIZEN", "DOCTOR"]:
            if self.daily_work_count < 5: self.hp -= 10 
            self.daily_work_count = 0; self.work_step = (self.day_count - 1) % 3
            
        self.is_hiding = False; self.hiding_type = 0; self.hidden_in_solid = False; self.exhausted = False
        self.ability_used = False; self.bullets_fired_today = 0
        
        if self.role != "POLICE" and self.hp <= 0: self.alive = False
        self.logger.info("PLAYER", "Morning Process Complete")
        return slept_at_home

    # [복구] 누락되었던 메서드 복구
    def toggle_flashlight(self): 
        self.flashlight_on = not self.flashlight_on

    def toggle_device(self):
        if self.role in ["CITIZEN", "DOCTOR", "POLICE", "MAFIA"]:
            if self.device_battery > 0:
                self.device_on = not self.device_on
                self.logger.debug("PLAYER", f"Device toggled: {self.device_on}")
                return "Device ON" if self.device_on else "Device OFF"
            else:
                self.device_on = False
                return "Battery Empty!"
        return "Device unavailable for this role."

    def update(self, phase, npcs, is_blackout, weather_type='CLEAR'):
        self.current_phase_ref = phase
        self.weather = weather_type 
        if not self.alive: return []
        if self.minigame.active: self.minigame.update(); return []
        
        now = pygame.time.get_ticks()
        
        # 1. 감정 계산 (5단계 시스템)
        self.calculate_emotions(phase, npcs, is_blackout)
        
        # 2. 이동 처리 (단계별 속도 적용)
        is_moving = self._handle_movement_input()
        
        # 3. 장비 및 배터리
        sound_events = self._update_devices_and_battery(now)
        
        # 4. 스태미나 및 호흡
        self._update_stamina(is_moving)
        
        # 5. 상태 소음 생성 (기침, 심장박동, 발소리)
        sound_events.extend(self._generate_status_noises(now, is_moving))
        
        # 6. 특수 상태 업데이트 (기면증, 떨림, 은신해제)
        self._update_special_states(now)

        # 7. 상호작용 키 입력 (E)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_e]:
            if not self.e_key_pressed: 
                self.e_key_pressed = True
                self.interaction_hold_timer = now
                self.logger.debug("INPUT", "E Key Pressed")
        else:
            if self.e_key_pressed:
                hold_time = now - self.interaction_hold_timer
                tx = int((self.rect.centerx + self.facing_dir[0]*TILE_SIZE)//TILE_SIZE)
                ty = int((self.rect.centery + self.facing_dir[1]*TILE_SIZE)//TILE_SIZE)
                self.logger.debug("INPUT", f"E Key Released (Hold: {hold_time}ms) Target: ({tx}, {ty})")
                
                if hold_time < 500:
                    res = self.interact_tile(tx, ty, npcs, mode='short')
                    if isinstance(res, tuple):
                        msg, sound = res
                        if msg: self.add_popup(msg)
                        if sound: sound_events.append(sound)
                    elif res: self.add_popup(res)
                else:
                    res = self.interact_tile(tx, ty, npcs, mode='long')
                    if isinstance(res, tuple):
                        msg, sound = res
                        if msg: self.add_popup(msg, (255, 100, 100))
                        if sound: sound_events.append(sound)
                    elif res: self.add_popup(res, (255, 100, 100))
                self.e_key_pressed = False
                
        return sound_events

    def calculate_emotions(self, phase, npcs, is_blackout):
        self.emotions = {}
        if not self.alive or self.role == "SPECTATOR": return

        # 1. 행복 (HAPPINESS): HP, AP 모두 80 이상
        if self.hp >= 80 and self.ap >= 80:
            self.emotions['HAPPINESS'] = 1

        # 2. 고통 (PAIN): HP 50 이하부터 5단계
        if self.hp <= 50:
            if self.hp <= 10: level = 5
            elif self.hp <= 20: level = 4
            elif self.hp <= 30: level = 3
            elif self.hp <= 40: level = 2
            else: level = 1
            self.emotions['PAIN'] = level

        # 3. 피로 (FATIGUE): AP 50 이하부터 5단계
        if self.ap <= 50:
            if self.ap <= 10: level = 5
            elif self.ap <= 20: level = 4
            elif self.ap <= 30: level = 3
            elif self.ap <= 40: level = 2
            else: level = 1
            self.emotions['FATIGUE'] = level

        # 4. 공포 (FEAR): 사보타주(정전) 시
        if is_blackout:
            self.emotions['FEAR'] = 1

        # 5. 거리 기반 감정 (불안, 도파민, 분노)
        dist_thresholds = [30, 25, 20, 10, 5] 
        
        target_role = None
        my_emotion = None
        
        # [수정] 마피아와 경찰의 특수 감정은 'NIGHT' 또는 'DAWN'에만 작동하도록 조건 추가
        if self.role == "MAFIA" and phase in ["NIGHT", "DAWN"]: # 도파민 (밤 한정)
            target_role = ["CITIZEN", "DOCTOR", "FARMER", "MINER", "FISHER", "POLICE"] 
            my_emotion = 'DOPAMINE'
        elif self.role == "POLICE" and phase in ["NIGHT", "DAWN"]: # 분노 (밤 한정)
            target_role = ["MAFIA"]
            my_emotion = 'RAGE'
        elif phase in ["EVENING", "NIGHT", "DAWN"]: # 불안 (저녁/밤/새벽)
            target_role = ["MAFIA"]
            my_emotion = 'ANXIETY'

        if my_emotion and target_role:
            min_dist_tile = 999
            for n in npcs:
                if n.role in target_role and n.alive:
                    d_px = math.hypot(self.rect.centerx - n.rect.centerx, self.rect.centery - n.rect.centery)
                    d_tile = d_px / TILE_SIZE
                    if d_tile < min_dist_tile: min_dist_tile = d_tile
            
            level = 0
            if min_dist_tile <= 5: level = 5
            elif min_dist_tile <= 10: level = 4
            elif min_dist_tile <= 20: level = 3
            elif min_dist_tile <= 25: level = 2
            elif min_dist_tile <= 30: level = 1
            
            if level > 0:
                self.emotions[my_emotion] = level

        if not self.emotions: self.emotions['CALM'] = 1

    def get_current_speed(self, weather_type='CLEAR'):
        if self.move_state == "RUN": base = SPEED_RUN
        elif self.move_state == "CROUCH": base = SPEED_CROUCH
        else: base = SPEED_WALK
        
        multiplier = 1.0
        
        # 1. 긍정적 효과
        if 'HAPPINESS' in self.emotions: multiplier += 0.10
        if 'DOPAMINE' in self.emotions:
            level = self.emotions['DOPAMINE']
            bonus = [0, 0.05, 0.10, 0.15, 0.20, 0.30]
            multiplier += bonus[level]
        if 'RAGE' in self.emotions:
            level = self.emotions['RAGE']
            bonus = [0, 0.05, 0.10, 0.15, 0.20, 0.30]
            multiplier += bonus[level]

        # 2. 부정적 효과
        if 'FEAR' in self.emotions: multiplier -= 0.30
        
        if 'FATIGUE' in self.emotions:
            level = self.emotions['FATIGUE']
            penalty = [0, 0.05, 0.10, 0.15, 0.20, 0.30]
            multiplier -= penalty[level]
            
        if 'PAIN' in self.emotions and not self.buffs['NO_PAIN']:
            level = self.emotions['PAIN']
            penalty = [0, 0.05, 0.10, 0.15, 0.20, 0.30]
            multiplier -= penalty[level]

        if self.role == "POLICE": multiplier *= POLICE_SPEED_MULTI
        if self.buffs.get('FAST_WORK'): multiplier *= 1.2
        if weather_type == 'SNOW': multiplier *= 0.8
        
        return base * max(0.2, multiplier)

    def _handle_movement_input(self):
        keys = pygame.key.get_pressed(); dx, dy = 0, 0
        if keys[pygame.K_LEFT]: dx = -1
        if keys[pygame.K_RIGHT]: dx = 1
        if keys[pygame.K_UP]: dy = -1
        if keys[pygame.K_DOWN]: dy = 1
        
        infinite_stamina = ('RAGE' in self.emotions and self.role == "POLICE") or self.buffs['INFINITE_STAMINA']
        
        if keys[pygame.K_LSHIFT] and (self.breath_gauge > 0 or infinite_stamina): 
            self.move_state = "RUN"
        elif keys[pygame.K_LCTRL]: 
            self.move_state = "CROUCH"
        else: 
            self.move_state = "WALK"
            
        is_moving = False
        if dx != 0 or dy != 0:
            speed = self.get_current_speed(getattr(self, 'weather', 'CLEAR'))
            if dx != 0 and dy != 0: speed *= 0.7071
            self.move_single_axis(dx * speed, 0); self.move_single_axis(0, dy * speed)
            is_moving = True
            if dx != 0: self.facing_dir = (dx, 0)
            elif dy != 0: self.facing_dir = (0, dy)

        self.is_moving = is_moving
        return is_moving

    def _update_devices_and_battery(self, now):
        sound_events = []
        if self.device_on:
            self.device_battery -= 0.05
            if self.device_battery <= 0: self.device_battery, self.device_on = 0, False; self.add_popup("Battery Depleted!", (255, 50, 50))
            if self.role in ["CITIZEN", "DOCTOR"] and now % 2000 < 50: sound_events.append(("BEEP", self.rect.centerx, self.rect.centery, 4 * TILE_SIZE))
        return sound_events

    def _update_stamina(self, is_moving):
        infinite = ('RAGE' in self.emotions and self.role == "POLICE") or self.buffs['INFINITE_STAMINA']
        if self.move_state == "RUN" and is_moving and not infinite: self.breath_gauge -= 0.5
        elif self.move_state != "RUN": self.breath_gauge = min(100, self.breath_gauge + 0.5)

    def _generate_status_noises(self, now, is_moving):
        sound_events = []
        if is_moving:
            step_interval = 600 if self.move_state == "WALK" else (300 if self.move_state == "RUN" else 800)
            if now > self.sound_timers['FOOTSTEP']:
                self.sound_timers['FOOTSTEP'] = now + step_interval
                s_type = "THUD" if self.move_state == "RUN" else ("RUSTLE" if self.move_state == "CROUCH" else "FOOTSTEP")
                radius = NOISE_RADIUS.get(self.move_state, 0)
                if self.buffs['SILENT']: radius *= 0.7
                if getattr(self, 'weather', 'CLEAR') == 'RAIN': radius *= 0.8
                if radius > 0: sound_events.append((s_type, self.rect.centerx, self.rect.centery, radius, self.role))
        
        if 'FEAR' in self.emotions:
            if now > self.sound_timers['SCREAM']:
                self.sound_timers['SCREAM'] = now + random.randint(3000, 6000)
                sound_events.append(("SCREAM", self.rect.centerx, self.rect.centery, 15 * TILE_SIZE, self.role))

        if self.emotions.get('PAIN', 0) >= 5 and not self.buffs['NO_PAIN']:
            if now > self.sound_timers['COUGH']:
                self.sound_timers['COUGH'] = now + 4000
                sound_events.append(("COUGH", self.rect.centerx, self.rect.centery, 8 * TILE_SIZE, self.role))
        
        heartbeat_level = 0
        for emo in ['ANXIETY', 'DOPAMINE', 'RAGE']:
            if emo in self.emotions:
                heartbeat_level = max(heartbeat_level, self.emotions[emo])
        
        if heartbeat_level > 0:
            interval = 1500 - (heartbeat_level * 200)
            if now > self.sound_timers['HEARTBEAT']:
                self.sound_timers['HEARTBEAT'] = now + interval
                if heartbeat_level >= 3: radius = 5 * TILE_SIZE 
                else: radius = 0 
                sound_events.append(("HEARTBEAT", self.rect.centerx, self.rect.centery, radius, self.role))
            
        return sound_events

    def _update_special_states(self, now):
        if 'FEAR' in self.emotions or self.emotions.get('PAIN', 0) >= 3:
            if now > self.shiver_timer: 
                self.shiver_timer = now + 50
                intensity = 2 if 'FEAR' in self.emotions else 1
                self.vibration_offset = (random.randint(-intensity, intensity), random.randint(-intensity, intensity))
        else: self.vibration_offset = (0, 0)
        
        if self.emotions.get('FATIGUE', 0) >= 5:
            if not hasattr(self, 'narcolepsy_timer'): self.narcolepsy_timer = now
            if (now - self.narcolepsy_timer) % 5000 > 4000:
                if not self.is_eyes_closed: self.is_eyes_closed = True; self.add_popup("Sleepy...", (100, 100, 200))
            else: self.is_eyes_closed = False
        else: self.is_eyes_closed = False

        if 'FEAR' in self.emotions:
            if self.is_hiding:
                self.is_hiding = False; self.hiding_type = 0; self.add_popup("PANIC! Cannot Hide!", (255, 50, 50))
            return

        gx, gy = int(self.rect.centerx // TILE_SIZE), int(self.rect.centery // TILE_SIZE)
        current_tid = 0; hiding_val = 0
        if 0 <= gx < self.map_width and 0 <= gy < self.map_height:
            if self.map_manager:
                val = self.map_manager.get_tile_full(gx, gy, 'object')
                current_tid = val[0]
                hiding_val = get_tile_hiding(current_tid)
                if hiding_val == 0:
                    val = self.map_manager.get_tile_full(gx, gy, 'floor')
                    current_tid = val[0]
                    hiding_val = get_tile_hiding(current_tid)
            else:
                current_tid = self.map_data[gy][gx]
                hiding_val = get_tile_hiding(current_tid)

        is_passive_tile = (hiding_val == 1)
        is_active_tile = (hiding_val == 2)
        
        if is_passive_tile:
            if not self.is_hiding: self.is_hiding, self.hiding_type = True, 1
        elif is_active_tile:
            if self.move_state == "CROUCH":
                if not self.is_hiding: self.is_hiding, self.hiding_type = True, 2; self.rect.center = (gx*TILE_SIZE + 16, gy*TILE_SIZE + 16); self.pos_x, self.pos_y = self.rect.x, self.rect.y
            else:
                if self.is_hiding and self.hiding_type == 2: self.is_hiding, self.hiding_type = False, 0
        else:
            if self.is_hiding: self.is_hiding, self.hiding_type = False, 0

    def get_vision_radius(self, vision_factor, is_blackout, weather_type='CLEAR', remaining_time=60, total_duration=60):
        if self.role == "SPECTATOR": return 40
        if self.is_eyes_closed: return 0
        
        day_vision = VISION_RADIUS['DAY']
        if self.role == "MAFIA": night_vision = VISION_RADIUS['NIGHT_MAFIA']
        elif self.role == "POLICE": night_vision = VISION_RADIUS['NIGHT_POLICE_FLASH'] if self.flashlight_on else 2.0
        else: night_vision = VISION_RADIUS['NIGHT_CITIZEN'] 

        if self.current_phase_ref == 'DAWN' and self.role != "MAFIA": night_vision = 0.0

        current_rad = night_vision + (day_vision - night_vision) * vision_factor
        
        if weather_type == 'FOG': current_rad *= 0.7
        if 'FATIGUE' in self.emotions: 
            current_rad = max(1.0, current_rad - self.emotions['FATIGUE'] * 0.5)

        if is_blackout and self.role != "MAFIA": return 1.5
        return max(0, current_rad)

    def heal_full(self): self.hp, self.ap, self.ability_used = self.max_hp, self.max_ap, False

    def buy_item(self, item_key):
        if self.role == "SPECTATOR": return
        if item_key in ITEMS:
            p = ITEMS[item_key]['price']
            if self.coins >= p: 
                self.coins -= p; self.inventory[item_key] = self.inventory.get(item_key, 0) + 1; 
                self.logger.info("PLAYER", f"Bought {item_key}")
                return ("Bought " + ITEMS[item_key]['name'], ("KA-CHING", self.rect.centerx, self.rect.centery, 5 * TILE_SIZE, self.role))
            else: print("Not enough coins!")

    def use_active_skill(self):
        if not self.alive: return None
        if self.role == "SPECTATOR": return None
        if self.ability_used: return "Skill already used today!"
        
        cost = 50
        if self.role == "MAFIA":
            if self.current_phase_ref != "NIGHT": return "Can only use at Night!"
            if not self.try_spend_ap(cost, allow_health_cost=False): return f"Not enough AP (Need {cost})!"
            self.ability_used = True; return "USE_SABOTAGE"
        elif self.role == "POLICE":
            if not self.try_spend_ap(cost, allow_health_cost=False): return f"Not enough AP (Need {cost})!"
            self.ability_used = True; return "USE_SIREN"
        return "No Active Skill for this role."

    def do_attack(self, target):
        if not self.alive or self.role == "SPECTATOR": return None
        if not target or not target.alive: return None
        now = pygame.time.get_ticks()
        if now - self.last_attack_time < self.attack_cooldown: return None
        self.last_attack_time = now
        
        attack_cost = 10
        if self.inventory.get('TASER', 0) > 0 and self.try_spend_ap(attack_cost, allow_health_cost=False):
            self.inventory['TASER'] -= 1; self.logger.info("PLAYER", "Used TASER"); target.take_stun(3000)
            return ("TASER SHOT!", (self.rect.centerx, self.rect.centery)), ("ZAP", self.rect.centerx, self.rect.centery, 4*TILE_SIZE, self.role)
            
        if self.current_phase_ref != "NIGHT": return None
        
        if self.role == "MAFIA" and self.try_spend_ap(attack_cost, allow_health_cost=False):
            if target.role == "POLICE": 
                target.take_stun(2000)
                return ("STUNNED POLICE!", (self.rect.centerx, self.rect.centery)), ("SLASH", self.rect.centerx, self.rect.centery, 5*TILE_SIZE, self.role)
            if target.inventory.get('ARMOR', 0) > 0: 
                target.inventory['ARMOR'] -= 1
                return ("BLOCKED", (self.rect.centerx, self.rect.centery)), ("CLICK", self.rect.centerx, self.rect.centery, 3*TILE_SIZE, self.role)
            target.take_damage(70)
            self.logger.info("PLAYER", f"Attacked {target.name}")
            return ("STAB", (self.rect.centerx, self.rect.centery)), ("SLASH", self.rect.centerx, self.rect.centery, 5*TILE_SIZE, self.role)
            
        elif self.role == "POLICE" and self.try_spend_ap(attack_cost, allow_health_cost=False):
            if self.current_phase_ref in ['MORNING', 'DAY', 'VOTE', 'NOON', 'AFTERNOON'] or self.bullets_fired_today >= 1: return None
            self.bullets_fired_today += 1
            dx = target.rect.centerx - self.rect.centerx; dy = target.rect.centery - self.rect.centery; angle = math.atan2(dy, dx)
            self.bullets.append(Bullet(self.rect.centerx, self.rect.centery, angle, is_enemy=False))
            self.logger.info("PLAYER", "Fired Gun")
            return ("GUNSHOT", (self.rect.centerx, self.rect.centery)), ("GUNSHOT", self.rect.centerx, self.rect.centery, 25*TILE_SIZE, self.role)
        return None

    def do_heal(self, target):
        if self.role != "DOCTOR" or not self.alive: return None
        if not self.try_spend_ap(10, allow_health_cost=False): return "Not enough AP!"
        if target and target.alive:
            target.hp = min(target.max_hp, target.hp + 50)
            self.logger.info("PLAYER", f"Doctor Healed {target.name}")
            return f"Healed {target.name}!", ("GULP", target.rect.centerx, target.rect.centery, 4*TILE_SIZE, self.role)
        return "No target to heal."

    def interact_tile(self, gx, gy, npcs, mode='short'):
        px, py = self.rect.centerx // TILE_SIZE, self.rect.centery // TILE_SIZE
        dist = abs(px - gx) + abs(py - gy)
        if dist != 1: return None

        tid = 0; target_layer = None
        if 0 <= gx < self.map_width and 0 <= gy < self.map_height:
            if self.map_manager and self.map_manager.is_tile_on_cooldown(gx, gy): return "Cooldown!"
            for layer in ['object', 'wall', 'floor']:
                val = self.map_manager.get_tile_full(gx, gy, layer)
                if val[0] != 0:
                    tid_check = val[0]; cat = get_tile_category(tid_check); d_val = get_tile_interaction(tid_check); func = get_tile_function(tid_check)
                    if cat in [5, 9] or d_val > 0 or func in [2, 3] or tid_check == 5321025: tid = tid_check; target_layer = layer; break

        if tid == 0: return None
        self.logger.info("PLAYER", f"Interact with {tid} at ({gx}, {gy}) Mode: {mode}")

        if tid == VENDING_MACHINE_TID: return "OPEN_SHOP" if mode == 'short' else None

        if tid == 5321025: 
            if mode == 'short': return "Hold 'E' to Unlock"
            elif mode == 'long':
                if self.ap < 5: return "Not enough AP (5)"
                self.minigame.start(random.choice(['HACKING', 'MEMORY']), 2, lambda: self._open_chest_reward(gx, gy), self.fail_penalty)
                return f"Unlocking..."

        cat = get_tile_category(tid); d_val = get_tile_interaction(tid)
        if cat == 5:
            if d_val == 1: 
                if mode == 'short': 
                    self.map_manager.open_door(gx, gy, target_layer)
                    return "Opened", ("CREAK", gx*TILE_SIZE, gy*TILE_SIZE, 5*TILE_SIZE, self.role)
                elif mode == 'long':
                    from settings import INDOOR_ZONES
                    is_inside = (self.zone_map[py][px] in INDOOR_ZONES)
                    if is_inside or self.inventory.get('KEY', 0) > 0 or self.inventory.get('MASTER_KEY', 0) > 0:
                        if self.ap < 5: return "Not enough AP (5)"
                        if not is_inside and self.inventory.get('KEY', 0) > 0: self.inventory['KEY'] -= 1
                        self.try_spend_ap(5); self.map_manager.lock_door(gx, gy, target_layer)
                        return "Locked Door", ("CLICK", gx*TILE_SIZE, gy*TILE_SIZE, 3*TILE_SIZE, self.role)
                    else:
                        if self.ap < 5: return "Not enough AP (5)"
                        self.minigame.start('TIMING', 2, lambda: self.map_manager.lock_door(gx, gy, target_layer), self.fail_penalty)
                        return "Locking..."
            elif d_val == 3: 
                if mode == 'short': return "It's Locked."
                elif mode == 'long':
                    if self.inventory.get('KEY', 0) > 0: 
                        self.inventory['KEY'] -= 1; self.map_manager.unlock_door(gx, gy, target_layer)
                        return "Unlocked with Key", ("CLICK", gx*TILE_SIZE, gy*TILE_SIZE, 3*TILE_SIZE, self.role)
                    elif self.inventory.get('MASTER_KEY', 0) > 0: 
                        self.map_manager.unlock_door(gx, gy, target_layer)
                        return "Unlocked with Master Key", ("CLICK", gx*TILE_SIZE, gy*TILE_SIZE, 3*TILE_SIZE, self.role)
                    else:
                        if "Glass" in get_tile_name(tid): return "Cannot Pick Lock!"
                        if self.ap < 5: return "Not enough AP (5)"
                        self.minigame.start('LOCKPICK', 3, lambda: self.map_manager.unlock_door(gx, gy, target_layer), self.fail_penalty)
                        return "Picking Lock..."
            elif "Open" in get_tile_name(tid):
                if mode == 'short': self.map_manager.close_door(gx, gy, target_layer); return "Closed", ("SLAM", gx*TILE_SIZE, gy*TILE_SIZE, 6*TILE_SIZE, self.role)

        if mode == 'short':
            if self.role == "MAFIA" and self.current_phase_ref == "NIGHT":
                 cat = get_tile_category(tid)
                 if cat in [3, 5, 6]:
                     self.minigame.start('MASHING', 2, lambda: self.do_break(gx, gy), self.fail_penalty)
                     return "Breaking...", ("BANG!", gx*TILE_SIZE, gy*TILE_SIZE, 12*TILE_SIZE, self.role)

            job_key = self.role if self.role == "DOCTOR" else self.sub_role
            if job_key in WORK_SEQ:
                seq = WORK_SEQ[job_key]; target_idx = self.work_step % len(seq); target_tid = seq[target_idx]
                if tid == target_tid:
                    m_type = MINIGAME_MAP[job_key].get(target_idx, 'MASHING')
                    next_t = seq[(target_idx + 1) % len(seq)]; is_final = (target_idx == len(seq) - 1)
                    if self.ap < 10: return "Not enough AP (10)"
                    self.minigame.start(m_type, 1, lambda: self.work_complete(gx*TILE_SIZE, gy*TILE_SIZE, next_t, is_final), self.fail_penalty)
                    return f"Working ({m_type})..."
                elif tid in seq: return "Not today's task."
        return None

    def _open_chest_reward(self, gx, gy):
        self.try_spend_ap(5)
        roll = random.random(); cumulative = 0.0; selected_reward = None
        for rate in TREASURE_CHEST_RATES:
            cumulative += rate['prob']
            if roll < cumulative: selected_reward = rate; break
        if not selected_reward: selected_reward = TREASURE_CHEST_RATES[-1]
        
        msg = ""
        if selected_reward['type'] == 'EMPTY': msg = selected_reward['msg']
        elif selected_reward['type'] == 'GOLD': self.coins += selected_reward['amount']; msg = selected_reward['msg']
        elif selected_reward['type'] == 'ITEM':
            item = random.choice(selected_reward['items']); self.inventory[item] = self.inventory.get(item, 0) + 1
            msg = selected_reward['msg'].format(item=ITEMS[item]['name'])
            
        if self.map_manager: self.map_manager.set_tile(gx, gy, 5310025, layer='object')
        self.add_popup(msg, (255, 215, 0))

    def work_complete(self, px, py, next_tile, reward=False):
        self.try_spend_ap(10); gx, gy = px // TILE_SIZE, py // TILE_SIZE
        if self.sub_role == 'FARMER' and next_tile is not None: self.map_manager.set_tile(gx, gy, next_tile)
        if self.map_manager: self.map_manager.set_tile_cooldown(gx, gy, 3000)
        self.coins += 1; self.daily_work_count += 1

    def do_break(self, px, py):
        gx, gy = (px, py) if isinstance(px, int) and px < self.map_width else (px // TILE_SIZE, py // TILE_SIZE)
        if self.try_spend_ap(2): self.map_manager.set_tile(gx, gy, 5310005)

    def fail_penalty(self): self.try_spend_ap(2)

    def update_bullets(self, npcs):
        for b in self.bullets[:]:
            b.update()
            if b.x < 0 or b.x > self.map_width * TILE_SIZE or b.y < 0 or b.y > self.map_height * TILE_SIZE: self.bullets.remove(b); continue
            gx = int(b.x // TILE_SIZE); gy = int(b.y // TILE_SIZE)
            if 0 <= gx < self.map_width and 0 <= gy < self.map_height:
                hit_wall = False
                if self.map_manager:
                    if self.map_manager.check_any_collision(gx, gy): hit_wall = True
                else:
                    tid = self.map_data[gy][gx]; tid = tid[0] if isinstance(tid, (tuple, list)) else tid
                    if check_collision(tid): hit_wall = True
                if hit_wall: b.alive = False; self.bullets.remove(b); continue
            bullet_rect = pygame.Rect(b.x-2, b.y-2, 4, 4)
            targets = [self] if b.is_enemy else npcs
            for t in targets:
                if t.alive and bullet_rect.colliderect(t.rect): t.take_damage(70); b.alive = False; self.bullets.remove(b); break

    def draw(self, screen, camera_x, camera_y):
        if self.role == "SPECTATOR":
            draw_x = self.rect.centerx - camera_x; draw_y = self.rect.centery - camera_y
            s = pygame.Surface((40, 40), pygame.SRCALPHA); pygame.draw.circle(s, (100, 100, 255, 120), (20, 20), 15); pygame.draw.circle(s, (255, 255, 255, 180), (20, 20), 15, 2); screen.blit(s, (draw_x - 20, draw_y - 20))
            return
        if self.is_dead:
            draw_rect = self.rect.move(-camera_x, -camera_y); pygame.draw.rect(screen, (50, 50, 50), draw_rect)
        else: CharacterRenderer.draw_entity(screen, self, camera_x, camera_y)
        for b in self.bullets: b.draw(screen, camera_x, camera_y)
