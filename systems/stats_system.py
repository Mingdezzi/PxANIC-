import pygame
import math
import random
from .base_system import BaseSystem
from settings import TILE_SIZE, NOISE_RADIUS

class StatsSystem(BaseSystem):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.sound_timers = {} 

    def update(self, dt, entities, player, is_blackout, phase):
        now = pygame.time.get_ticks()
        
        # 1. 플레이어 상태 업데이트
        if player and player.stats.alive:
            self._update_emotions(player, entities, is_blackout, phase)
            self._update_stamina(player)
            self._update_battery(player, now)
            self._update_status_noises(player, now)
            self._update_special_states(player, now)

    def _update_emotions(self, player, entities, is_blackout, phase):
        emotions = {}
        hp = player.stats.hp
        ap = player.stats.ap
        
        if hp >= 80 and ap >= 80: emotions['HAPPINESS'] = 1
        
        if hp <= 50:
            if hp <= 10: level = 5
            elif hp <= 20: level = 4
            elif hp <= 30: level = 3
            elif hp <= 40: level = 2
            else: level = 1
            emotions['PAIN'] = level
            
        if ap <= 50:
            if ap <= 10: level = 5
            elif ap <= 20: level = 4
            elif ap <= 30: level = 3
            elif ap <= 40: level = 2
            else: level = 1
            emotions['FATIGUE'] = level
            
        if is_blackout: emotions['FEAR'] = 1
        
        # 거리 기반 감정
        role = player.role.main_role
        target_role = None
        my_emotion = None
        
        if role == "MAFIA" and phase in ["NIGHT", "DAWN"]:
            target_role = ["CITIZEN", "DOCTOR", "POLICE"]
            my_emotion = 'DOPAMINE'
        elif role == "POLICE" and phase in ["NIGHT", "DAWN"]:
            target_role = ["MAFIA"]
            my_emotion = 'RAGE'
        elif phase in ["EVENING", "NIGHT", "DAWN"]:
            target_role = ["MAFIA"]
            my_emotion = 'ANXIETY'
            
        if my_emotion and target_role:
            min_dist = 999
            for e in entities:
                if e == player: continue
                if e.role.main_role in target_role and e.stats.alive:
                    dist = math.sqrt((player.transform.x - e.transform.x)**2 + (player.transform.y - e.transform.y)**2)
                    dist_tile = dist / TILE_SIZE
                    if dist_tile < min_dist: min_dist = dist_tile
            
            level = 0
            if min_dist <= 5: level = 5
            elif min_dist <= 10: level = 4
            elif min_dist <= 20: level = 3
            elif min_dist <= 25: level = 2
            elif min_dist <= 30: level = 1
            if level > 0: emotions[my_emotion] = level
            
        player.stats.emotions = emotions

    def _update_stamina(self, player):
        # [수정] buffs -> status_effects
        is_running = (player.physics.move_state == "RUN" and player.physics.velocity != (0, 0))
        infinite = player.stats.status_effects.get('INFINITE_STAMINA', False) or \
                   ('RAGE' in player.stats.emotions and player.role.main_role == "POLICE")
        
        if is_running and not infinite:
            player.stats.breath_gauge = max(0, player.stats.breath_gauge - 0.5)
        elif player.physics.move_state != "RUN":
            player.stats.breath_gauge = min(100, player.stats.breath_gauge + 0.5)

    def _update_battery(self, player, now):
        if player.graphics.device_on:
            player.inventory.battery_level -= 0.05
            if player.inventory.battery_level <= 0:
                player.inventory.battery_level = 0
                player.graphics.device_on = False
                self.event_bus.publish("SHOW_ALERT", {'text': "Battery Depleted!", 'color': (255, 50, 50)})
            
            if player.role.main_role in ["CITIZEN", "DOCTOR"] and now % 2000 < 50:
                self.event_bus.publish("PLAY_SOUND", {'name': "BEEP", 'x': player.transform.x, 'y': player.transform.y})

    def _update_status_noises(self, player, now):
        pid = id(player)
        if pid not in self.sound_timers:
            self.sound_timers[pid] = {'FOOTSTEP': 0, 'SCREAM': 0, 'COUGH': 0, 'HEARTBEAT': 0}
        timers = self.sound_timers[pid]
        
        if player.physics.velocity != (0, 0):
            state = player.physics.move_state
            interval = 600 if state == "WALK" else (300 if state == "RUN" else 800)
            if now > timers['FOOTSTEP']:
                timers['FOOTSTEP'] = now + interval
                s_type = "THUD" if state == "RUN" else ("RUSTLE" if state == "CROUCH" else "FOOTSTEP")
                radius = NOISE_RADIUS.get(state, 0)
                
                # [수정] buffs -> status_effects
                if player.stats.status_effects.get('SILENT'): radius *= 0.7
                
                if radius > 0:
                    self.event_bus.publish("PLAY_SOUND", {'name': s_type, 'x': player.transform.x, 'y': player.transform.y, 'role': player.role.main_role})

        if 'FEAR' in player.stats.emotions:
            if now > timers['SCREAM']:
                timers['SCREAM'] = now + random.randint(3000, 6000)
                self.event_bus.publish("PLAY_SOUND", {'name': "SCREAM", 'x': player.transform.x, 'y': player.transform.y, 'role': player.role.main_role})

        if player.stats.emotions.get('PAIN', 0) >= 5:
            if now > timers['COUGH']:
                timers['COUGH'] = now + 4000
                self.event_bus.publish("PLAY_SOUND", {'name': "COUGH", 'x': player.transform.x, 'y': player.transform.y, 'role': player.role.main_role})

        hb_level = 0
        for emo in ['ANXIETY', 'DOPAMINE', 'RAGE']:
            hb_level = max(hb_level, player.stats.emotions.get(emo, 0))
        
        if hb_level > 0:
            interval = 1500 - (hb_level * 200)
            if now > timers['HEARTBEAT']:
                timers['HEARTBEAT'] = now + interval
                radius = 5 * TILE_SIZE if hb_level >= 3 else 0
                self.event_bus.publish("PLAY_SOUND", {'name': "HEARTBEAT", 'x': player.transform.x, 'y': player.transform.y, 'role': player.role.main_role})

    def _update_special_states(self, player, now):
        # [복구] 떨림(Shiver) 효과 데이터 설정
        if 'FEAR' in player.stats.emotions or player.stats.emotions.get('PAIN', 0) >= 3:
            # shiver_timer가 없으면 초기화
            if not hasattr(player.stats, 'shiver_timer'): player.stats.shiver_timer = 0
            
            if now > player.stats.shiver_timer: 
                player.stats.shiver_timer = now + 50
                intensity = 2 if 'FEAR' in player.stats.emotions else 1
                # Graphics 컴포넌트에 오프셋 적용
                player.graphics.vibration_offset = (random.randint(-intensity, intensity), random.randint(-intensity, intensity))
        else:
            player.graphics.vibration_offset = (0, 0)
        
        # [복구] 기면증(Narcolepsy) 눈 깜빡임
        if player.stats.emotions.get('FATIGUE', 0) >= 5:
            if not hasattr(player.stats, 'narcolepsy_timer'): player.stats.narcolepsy_timer = now
            
            # 5초 주기, 4초 깨어있고 1초 눈감음
            if (now - player.stats.narcolepsy_timer) % 5000 > 4000:
                if not player.graphics.is_eyes_closed:
                    player.graphics.is_eyes_closed = True
                    self.event_bus.publish("SHOW_ALERT", {'text': "Sleepy...", 'color': (100, 100, 200)})
            else:
                player.graphics.is_eyes_closed = False
        else:
            player.graphics.is_eyes_closed = False

        # [복구] 공포 시 은신 강제 해제
        if 'FEAR' in player.stats.emotions and player.graphics.is_hiding:
            player.graphics.is_hiding = False
            self.event_bus.publish("SHOW_ALERT", {'text': "PANIC! Cannot Hide!", 'color': (255, 50, 50)})