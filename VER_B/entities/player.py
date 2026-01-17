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
from entities.bullet import Bullet

# Logic Modules
from entities.player_logic.movement import MovementLogic
from entities.player_logic.status import StatusLogic
from entities.player_logic.actions import ActionLogic
from entities.player_logic.inventory import InventoryLogic

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
        
        # [Logic Components]
        self.logic_move = MovementLogic(self)
        self.logic_status = StatusLogic(self)
        self.logic_action = ActionLogic(self)
        self.logic_inventory = InventoryLogic(self)

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
        
        if slept_at_home:
            self.hp = min(self.max_hp, self.hp + 10)
            self.ap = min(self.max_ap, self.ap + 10)
        else:
            self.hp = max(0, self.hp - 30)
            self.ap = max(0, self.ap - 30)
        
        if self.role in ["CITIZEN", "DOCTOR"]:
            if self.daily_work_count < 5: self.hp -= 10 
            self.daily_work_count = 0; self.work_step = (self.day_count - 1) % 3
            
        self.is_hiding = False; self.hiding_type = 0; self.hidden_in_solid = False; self.exhausted = False
        self.ability_used = False; self.bullets_fired_today = 0
        
        if self.role != "POLICE" and self.hp <= 0: self.alive = False
        self.logger.info("PLAYER", "Morning Process Complete")
        return slept_at_home

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
        
        # Delegate to Logic Components
        self.calculate_emotions(phase, npcs, is_blackout)
        
        is_moving = self._handle_movement_input()
        
        sound_events = self._update_devices_and_battery(now)
        
        self._update_stamina(is_moving)
        
        sound_events.extend(self._generate_status_noises(now, is_moving))
        
        self._update_special_states(now)

        # Interaction Input
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

    # [Delegation Wrappers]
    def calculate_emotions(self, phase, npcs, is_blackout):
        self.logic_status.calculate_emotions(phase, npcs, is_blackout)

    def get_current_speed(self, weather_type='CLEAR'):
        return self.logic_move.get_current_speed(weather_type)

    def _handle_movement_input(self):
        return self.logic_move.handle_input()

    def _update_stamina(self, is_moving):
        self.logic_move.update_stamina(is_moving)

    def _generate_status_noises(self, now, is_moving):
        return self.logic_status.generate_noises(now, is_moving)

    def _update_special_states(self, now):
        self.logic_status.update_special_states(now)

    def get_vision_radius(self, vision_factor, is_blackout, weather_type='CLEAR', remaining_time=60, total_duration=60):
        return self.logic_status.get_vision_radius(vision_factor, is_blackout, weather_type)

    def interact_tile(self, gx, gy, npcs, mode='short'):
        return self.logic_action.interact_tile(gx, gy, npcs, mode)

    def do_attack(self, target):
        return self.logic_action.do_attack(target)

    def do_heal(self, target):
        return self.logic_action.do_heal(target)

    def use_active_skill(self):
        return self.logic_action.use_active_skill()

    def update_bullets(self, npcs):
        self.logic_action.update_bullets(npcs)

    def use_item(self, item_key):
        return self.logic_inventory.use_item(item_key)

    def buy_item(self, item_key):
        return self.logic_inventory.buy_item(item_key)

    # [Internal Helpers - Kept in Player as they modify simple state directly or are small]
    def _update_devices_and_battery(self, now):
        sound_events = []
        if self.device_on:
            self.device_battery -= 0.05
            if self.device_battery <= 0: self.device_battery, self.device_on = 0, False; self.add_popup("Battery Depleted!", (255, 50, 50))
            if self.role in ["CITIZEN", "DOCTOR"] and now % 2000 < 50: sound_events.append(("BEEP", self.rect.centerx, self.rect.centery, 4 * TILE_SIZE))
        return sound_events

    def heal_full(self): 
        self.hp, self.ap, self.ability_used = self.max_hp, self.max_ap, False

    # [Callback Wrappers needed for Minigame lambdas which expect methods on self]
    def fail_penalty(self): self.try_spend_ap(2)
    def _open_chest_reward(self, gx, gy): self.logic_action._open_chest_reward(gx, gy)
    def work_complete(self, px, py, next_tile, reward=False): self.logic_action.work_complete(px, py, next_tile, reward)
    def do_break(self, px, py): self.logic_action.do_break(px, py)

    def draw(self, screen, camera_x, camera_y):
        if self.role == "SPECTATOR":
            draw_x = self.rect.centerx - camera_x; draw_y = self.rect.centery - camera_y
            s = pygame.Surface((40, 40), pygame.SRCALPHA); pygame.draw.circle(s, (100, 100, 255, 120), (20, 20), 15); pygame.draw.circle(s, (255, 255, 255, 180), (20, 20), 15, 2); screen.blit(s, (draw_x - 20, draw_y - 20))
            return
        if self.is_dead:
            draw_rect = self.rect.move(-camera_x, -camera_y); pygame.draw.rect(screen, (50, 50, 50), draw_rect)
        else: CharacterRenderer.draw_entity(screen, self, camera_x, camera_y, self.role, self.current_phase_ref, self.device_on) # Added device_on
        for b in self.bullets: b.draw(screen, camera_x, camera_y)