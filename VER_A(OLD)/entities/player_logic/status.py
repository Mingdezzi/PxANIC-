import pygame
import math
import random
from settings import VISION_RADIUS, TILE_SIZE, NOISE_RADIUS, INDOOR_ZONES
from world.tiles import get_tile_hiding, get_tile_function

class StatusLogic:
    def __init__(self, player):
        self.p = player

    def calculate_emotions(self, phase, npcs, is_blackout):
        self.p.emotions = {}
        if not self.p.alive or self.p.role == "SPECTATOR": return

        # 1. 행복 (HAPPINESS)
        if self.p.hp >= 80 and self.p.ap >= 80:
            self.p.emotions['HAPPINESS'] = 1

        # 2. 고통 (PAIN)
        if self.p.hp <= 50:
            if self.p.hp <= 10: level = 5
            elif self.p.hp <= 20: level = 4
            elif self.p.hp <= 30: level = 3
            elif self.p.hp <= 40: level = 2
            else: level = 1
            self.p.emotions['PAIN'] = level

        # 3. 피로 (FATIGUE)
        if self.p.ap <= 50:
            if self.p.ap <= 10: level = 5
            elif self.p.ap <= 20: level = 4
            elif self.p.ap <= 30: level = 3
            elif self.p.ap <= 40: level = 2
            else: level = 1
            self.p.emotions['FATIGUE'] = level

        # 4. 공포 (FEAR)
        if is_blackout:
            self.p.emotions['FEAR'] = 1

        # 5. 거리 기반 감정 (Spatial Optimization)
        target_role = None
        my_emotion = None
        
        if self.p.role == "MAFIA" and phase in ["NIGHT", "DAWN"]:
            target_role = ["CITIZEN", "DOCTOR", "FARMER", "MINER", "FISHER", "POLICE"] 
            my_emotion = 'DOPAMINE'
        elif self.p.role == "POLICE" and phase in ["NIGHT", "DAWN"]:
            target_role = ["MAFIA"]
            my_emotion = 'RAGE'
        elif phase in ["EVENING", "NIGHT", "DAWN"]:
            target_role = ["MAFIA"]
            my_emotion = 'ANXIETY'

        if my_emotion and target_role:
            min_dist_tile = 999
            
            # [Optimization] Use Spatial Grid instead of iterating all NPCs
            search_targets = npcs
            if hasattr(self.p, 'world'):
                # Search within 30 tiles radius (max emotion range)
                search_targets = self.p.world.get_nearby_entities(self.p, radius_tiles=30)
            
            for n in search_targets:
                if n.role in target_role and n.alive:
                    d_px = math.hypot(self.p.rect.centerx - n.rect.centerx, self.p.rect.centery - n.rect.centery)
                    d_tile = d_px / TILE_SIZE
                    if d_tile < min_dist_tile: min_dist_tile = d_tile
            
            level = 0
            if min_dist_tile <= 5: level = 5
            elif min_dist_tile <= 10: level = 4
            elif min_dist_tile <= 20: level = 3
            elif min_dist_tile <= 25: level = 2
            elif min_dist_tile <= 30: level = 1
            
            if level > 0:
                self.p.emotions[my_emotion] = level

        if not self.p.emotions: self.p.emotions['CALM'] = 1

    def generate_noises(self, now, is_moving):
        sound_events = []
        if is_moving:
            step_interval = 600 if self.p.move_state == "WALK" else (300 if self.p.move_state == "RUN" else 800)
            if now > self.p.sound_timers['FOOTSTEP']:
                self.p.sound_timers['FOOTSTEP'] = now + step_interval
                s_type = "THUD" if self.p.move_state == "RUN" else ("RUSTLE" if self.p.move_state == "CROUCH" else "FOOTSTEP")
                radius = NOISE_RADIUS.get(self.p.move_state, 0)
                if self.p.buffs['SILENT']: radius *= 0.7
                if getattr(self.p, 'weather', 'CLEAR') == 'RAIN': radius *= 0.8
                if radius > 0: sound_events.append((s_type, self.p.rect.centerx, self.p.rect.centery, radius, self.p.role))
        
        if 'FEAR' in self.p.emotions:
            if now > self.p.sound_timers['SCREAM']:
                self.p.sound_timers['SCREAM'] = now + random.randint(3000, 6000)
                sound_events.append(("SCREAM", self.p.rect.centerx, self.p.rect.centery, 15 * TILE_SIZE, self.p.role))

        if self.p.emotions.get('PAIN', 0) >= 5 and not self.p.buffs['NO_PAIN']:
            if now > self.p.sound_timers['COUGH']:
                self.p.sound_timers['COUGH'] = now + 4000
                sound_events.append(("COUGH", self.p.rect.centerx, self.p.rect.centery, 8 * TILE_SIZE, self.p.role))
        
        heartbeat_level = 0
        for emo in ['ANXIETY', 'DOPAMINE', 'RAGE']:
            if emo in self.p.emotions:
                heartbeat_level = max(heartbeat_level, self.p.emotions[emo])
        
        if heartbeat_level > 0:
            interval = 1500 - (heartbeat_level * 200)
            if now > self.p.sound_timers['HEARTBEAT']:
                self.p.sound_timers['HEARTBEAT'] = now + interval
                if heartbeat_level >= 3: radius = 5 * TILE_SIZE 
                else: radius = 0 
                sound_events.append(("HEARTBEAT", self.p.rect.centerx, self.p.rect.centery, radius, self.p.role))
            
        return sound_events

    def update_special_states(self, now):
        if 'FEAR' in self.p.emotions or self.p.emotions.get('PAIN', 0) >= 3:
            if now > self.p.shiver_timer: 
                self.p.shiver_timer = now + 50
                intensity = 2 if 'FEAR' in self.p.emotions else 1
                self.p.vibration_offset = (random.randint(-intensity, intensity), random.randint(-intensity, intensity))
        else: self.p.vibration_offset = (0, 0)
        
        if self.p.emotions.get('FATIGUE', 0) >= 5:
            if not hasattr(self.p, 'narcolepsy_timer'): self.p.narcolepsy_timer = now
            if (now - self.p.narcolepsy_timer) % 5000 > 4000:
                if not self.p.is_eyes_closed: self.p.is_eyes_closed = True; self.p.add_popup("Sleepy...", (100, 100, 200))
            else: self.p.is_eyes_closed = False
        else: self.p.is_eyes_closed = False

        if 'FEAR' in self.p.emotions:
            if self.p.is_hiding:
                self.p.is_hiding = False; self.p.hiding_type = 0; self.p.add_popup("PANIC! Cannot Hide!", (255, 50, 50))
            return

        gx, gy = int(self.p.rect.centerx // TILE_SIZE), int(self.p.rect.centery // TILE_SIZE)
        current_tid = 0; hiding_val = 0
        if 0 <= gx < self.p.map_width and 0 <= gy < self.p.map_height:
            if self.p.map_manager:
                val = self.p.map_manager.get_tile_full(gx, gy, 'object')
                current_tid = val[0]
                hiding_val = get_tile_hiding(current_tid)
                if hiding_val == 0:
                    val = self.p.map_manager.get_tile_full(gx, gy, 'floor')
                    current_tid = val[0]
                    hiding_val = get_tile_hiding(current_tid)
            else:
                current_tid = self.p.map_data[gy][gx]
                hiding_val = get_tile_hiding(current_tid)

        is_passive_tile = (hiding_val == 1)
        is_active_tile = (hiding_val == 2)
        
        if is_passive_tile:
            if not self.p.is_hiding: self.p.is_hiding, self.p.hiding_type = True, 1
        elif is_active_tile:
            if self.p.move_state == "CROUCH":
                if not self.p.is_hiding: 
                    self.p.is_hiding, self.p.hiding_type = True, 2
                    self.p.rect.center = (gx*TILE_SIZE + 16, gy*TILE_SIZE + 16)
                    self.p.pos_x, self.p.pos_y = self.p.rect.x, self.p.rect.y
            else:
                if self.p.is_hiding and self.p.hiding_type == 2: self.p.is_hiding, self.p.hiding_type = False, 0
        else:
            if self.p.is_hiding: self.p.is_hiding, self.p.hiding_type = False, 0

    def get_vision_radius(self, vision_factor, is_blackout, weather_type):
        if self.p.role == "SPECTATOR": return 40
        if self.p.is_eyes_closed: return 0
        
        day_vision = VISION_RADIUS['DAY']
        if self.p.role == "MAFIA": night_vision = VISION_RADIUS['NIGHT_MAFIA']
        elif self.p.role == "POLICE": night_vision = VISION_RADIUS['NIGHT_POLICE_FLASH'] if self.p.flashlight_on else 2.0
        else: night_vision = VISION_RADIUS['NIGHT_CITIZEN'] 

        if self.p.current_phase_ref == 'DAWN' and self.p.role != "MAFIA": night_vision = 0.0

        current_rad = night_vision + (day_vision - night_vision) * vision_factor
        
        if weather_type == 'FOG': current_rad *= 0.7
        if 'FATIGUE' in self.p.emotions: 
            current_rad = max(1.0, current_rad - self.p.emotions['FATIGUE'] * 0.5)

        if is_blackout and self.p.role != "MAFIA": return 1.5
        return max(0, current_rad)