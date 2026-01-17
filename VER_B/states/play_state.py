import pygame
import random
import math
from core.base_state import BaseState
from settings import *
from systems.camera import Camera
from systems.fov import FOV
from systems.effects import VisualSound, SoundDirectionIndicator
from systems.renderer import CharacterRenderer, MapRenderer
from systems.lighting import LightingManager
from systems.time_system import TimeSystem
from core.world import GameWorld
from colors import COLORS
from managers.resource_manager import ResourceManager
from ui import UI
from entities.bullet import Bullet
from systems.debug_console import DebugConsole
from entities.npc import Dummy

class PlayState(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.logger = game.logger
        self.resource_manager = ResourceManager.get_instance()

        # [Systems]
        self.world = GameWorld(game)
        self.time_system = TimeSystem(game)
        self.lighting = LightingManager(self)
        self.console = DebugConsole(game, self)

        self.map_renderer = None
        self.camera = None
        self.fov = None

        # [Rendering Caches]
        self.visible_tiles = set()
        self.tile_alphas = {}
        self.zoom_level = 1.5
        self.effect_surf = pygame.Surface((self.game.screen_width, self.game.screen_height), pygame.SRCALPHA)

        # [UI]
        self.ui = None
        self.is_chatting = False
        self.chat_text = ""
        self.show_vote_ui = False
        self.my_vote_target = None
        self.vote_btn_rect = None
        self.candidate_rects = []

        # [Logic Timers]
        self.heartbeat_timer = 0
        self.blink_timer = 0
        self.last_sent_pos = (0, 0)

        # [Callbacks Setup]
        self.time_system.on_phase_change = self.on_phase_change
        self.time_system.on_morning = self.on_morning

    # [Proxy Properties]
    @property
    def player(self): return self.world.player
    @property
    def npcs(self): return self.world.npcs
    @property
    def map_manager(self): return self.world.map_manager
    @property
    def current_phase(self): return self.time_system.current_phase
    @property
    def current_phase_idx(self): return self.time_system.current_phase_idx
    @property
    def phases(self): return self.time_system.phases
    @property
    def state_timer(self): return self.time_system.state_timer
    @property
    def day_count(self): return self.time_system.day_count
    @property
    def weather(self): return self.time_system.weather
    @property
    def weather_particles(self): return self.time_system.weather_particles
    @property
    def is_blackout(self): return self.world.is_blackout
    @property
    def is_mafia_frozen(self): return self.world.is_mafia_frozen

    def enter(self, params=None):
        self.logger.info("PLAY", "Entering PlayState...")

        self.world.load_map("map.json")
        self.map_renderer = MapRenderer(self.world.map_manager)

        self.camera = Camera(self.game.screen_width, self.game.screen_height, self.world.map_manager.width, self.world.map_manager.height)
        self.camera.set_bounds(self.world.map_manager.width * TILE_SIZE, self.world.map_manager.height * TILE_SIZE)
        self.camera.set_zoom(self.zoom_level)
        self.fov = FOV(self.world.map_manager.width, self.world.map_manager.height, self.world.map_manager)

        self.world.init_entities()
        self.time_system.init_timer() 

        # [Multiplayer Setup]
        if hasattr(self.game, 'network') and self.game.network.connected:
            my_id = self.game.network.my_id
            self.player.uid = my_id
            print(f"[PLAY] Assigned Network ID {my_id} to Player")
            
            participants = self.game.shared_data.get('participants', [])
            npc_idx = 0
            for p in participants:
                pid = p['id']
                if pid == my_id: continue
                if npc_idx < len(self.npcs):
                    self.npcs[npc_idx].uid = pid
                    self.npcs[npc_idx].name = p['name']
                    self.npcs[npc_idx].is_master = False # Remote player
                    self.world.register_entity(self.npcs[npc_idx])
                    npc_idx += 1

        self.ui = UI(self)
        
        if self.weather == 'RAIN': self.ui.show_alert("It's Raining...", (100, 100, 255))
        elif self.weather == 'FOG': self.ui.show_alert("Dense Fog...", (150, 150, 150))
        elif self.weather == 'SNOW': self.ui.show_alert("It's Snowing...", (200, 200, 255))

    def on_phase_change(self, old_phase, new_phase):
        if old_phase == "AFTERNOON":
            self.show_vote_ui = False
            self._process_voting_results()

    def on_morning(self):
        gx, gy = int(self.player.rect.centerx // TILE_SIZE), int(self.player.rect.centery // TILE_SIZE)
        is_indoors = False
        if 0 <= gx < self.world.map_manager.width and 0 <= gy < self.world.map_manager.height:
            if self.world.map_manager.zone_map[gy][gx] in INDOOR_ZONES:
                is_indoors = True
        
        self.player.morning_process(is_indoors)
        for n in self.npcs: n.morning_process()
        self.world.has_murder_occurred = False
        
        if self.time_system.daily_news_log:
            self.ui.show_daily_news(self.time_system.daily_news_log)
            self.time_system.daily_news_log = []

    def update(self, dt):
        if not self.player: return

        if self.player.is_dead and self.player.role != "SPECTATOR":
            self.logger.info("GAME", "PLAYER DIED - GAME OVER")
            self.ui.show_alert("YOU DIED!", (255, 0, 0))
            self.player.change_role("SPECTATOR")

        # [Network] Receive Packets
        if hasattr(self.game, 'network') and self.game.network.connected:
            events = self.game.network.get_events()
            for e in events:
                ptype = e.get('type')
                sender_id = e.get('id')
                if ptype == 'MOVE':
                    if sender_id in self.world.entities_by_id:
                        ent = self.world.entities_by_id[sender_id]
                        if isinstance(ent, Dummy):
                            ent.sync_state(e['x'], e['y'], 100, 100, 'CITIZEN', e['is_moving'], e['facing'])

        # [Network] Send My Pos
        if self.player and self.player.alive:
            curr_pos = (int(self.player.pos_x), int(self.player.pos_y))
            if curr_pos != self.last_sent_pos:
                if hasattr(self.game, 'network') and self.game.network.connected:
                    self.game.network.send_move(curr_pos[0], curr_pos[1], self.player.is_moving, self.player.facing_dir)
                self.last_sent_pos = curr_pos

        self.time_system.update(dt)
        self.world.update(dt, self.current_phase, self.weather, self.day_count)
        self.lighting.update(dt)

        now = pygame.time.get_ticks()
        
        if self.camera:
            self.camera.resize(self.game.screen_width, self.game.screen_height)

        if not self.player.is_dead:
            if not (self.ui.show_vending or self.ui.show_inventory or self.ui.show_voting or self.is_chatting):
                if not self.player.is_stunned():
                    fx = self.player.update(self.current_phase, self.npcs, self.world.is_blackout, self.weather)
                    if fx:
                        for f in fx: self._process_sound_effect(f)

                    for p in self.player.popups:
                        if p['text'] == "OPEN_SHOP":
                            self.ui.toggle_vending_machine()
                            self.player.popups.remove(p); break

                self.player.update_bullets(self.npcs)

        # [Original Logic Restored] Emotion System
        if self.player.role in ["CITIZEN", "DOCTOR", "FARMER", "MINER", "FISHER"]:
            if self.current_phase == "NIGHT":
                nearest_dist = float('inf')
                for n in self.npcs:
                    if n.role == "MAFIA" and n.alive:
                        d = math.hypot(n.rect.centerx - self.player.rect.centerx, n.rect.centery - self.player.rect.centery)
                        if d < nearest_dist: nearest_dist = d
                
                if nearest_dist < 640:
                    intensity = int((640 - nearest_dist) / 60)
                    self.player.emotions['ANXIETY'] = intensity
                    beat_interval = max(300, int(nearest_dist * 2))
                    if now - self.heartbeat_timer > beat_interval:
                        self.heartbeat_timer = now
                        self.world.effects.append(VisualSound(self.player.rect.centerx, self.player.rect.centery, "THUMP", (100, 0, 0), size_scale=0.5))
                else: self.player.emotions['ANXIETY'] = 0
            else: self.player.emotions['ANXIETY'] = 0

            self.player.status_effects['FATIGUE'] = (self.player.ap <= 5)

            if self.player.hp <= 5:
                self.player.emotions['PAIN'] = 5 
                self.player.is_hiding = False
                if random.random() < 0.02:
                    self.world.effects.append(VisualSound(self.player.rect.centerx, self.player.rect.centery, "GROAN...", (200, 200, 200), 1.0))
            else: self.player.emotions['PAIN'] = 0

        # [Original Logic Restored] Mafia Sighting
        if self.current_phase == "NIGHT" and random.random() < 0.005:
            for n in self.npcs:
                if n.role == "MAFIA" and n.alive:
                    gx, gy = int(n.rect.centerx // TILE_SIZE), int(n.rect.centery // TILE_SIZE)
                    if 0 <= gy < self.world.map_manager.height and 0 <= gx < self.world.map_manager.width:
                        zid = self.world.map_manager.zone_map[gy][gx]
                        if zid in ZONES and zid != 1:
                            self.time_system.mafia_last_seen_zone = ZONES[zid]['name']

        # NPC Update
        for n in self.npcs:
            if n.is_stunned(): continue
            action = n.update(self.current_phase, self.player, self.npcs, self.world.is_mafia_frozen, self.world.noise_list, self.day_count, self.world.bloody_footsteps)
            self._handle_npc_action(action, n, now)

        if self.player.role == "SPECTATOR":
            self._update_spectator_camera()
        else:
            self.camera.update(self.player.rect.centerx, self.player.rect.centery)

        # FOV & Visibility
        rad = self.player.get_vision_radius(self.lighting.current_vision_factor, self.world.is_blackout, self.weather)
        direction = None
        angle = 60
        if self.player.role == "POLICE" and self.player.flashlight_on and self.current_phase in ['EVENING', 'NIGHT', 'DAWN']:
            direction = self.player.facing_dir
            
        self.visible_tiles = self.fov.cast_rays(self.player.rect.centerx, self.player.rect.centery, rad, direction, angle)

        fade_speed = 15 
        for tile in self.visible_tiles:
            current_alpha = self.tile_alphas.get(tile, 0)
            if current_alpha < 255:
                self.tile_alphas[tile] = min(255, current_alpha + fade_speed)
        
        for tile in list(self.tile_alphas.keys()):
            if tile not in self.visible_tiles:
                self.tile_alphas[tile] -= fade_speed
                if self.tile_alphas[tile] <= 0:
                    del self.tile_alphas[tile]

    def _update_spectator_camera(self):
        keys = pygame.key.get_pressed()
        cam_dx, cam_dy = 0, 0
        cam_speed = 15

        if keys[pygame.K_LEFT]: cam_dx = -cam_speed
        if keys[pygame.K_RIGHT]: cam_dx = cam_speed
        if keys[pygame.K_UP]: cam_dy = -cam_speed
        if keys[pygame.K_DOWN]: cam_dy = cam_speed

        if cam_dx != 0 or cam_dy != 0:
            self.ui.spectator_follow_target = None
            self.camera.move(cam_dx, cam_dy)
        elif self.ui.spectator_follow_target:
            t = self.ui.spectator_follow_target
            if t.alive: self.camera.update(t.rect.centerx, t.rect.centery)
            else: self.ui.spectator_follow_target = None

    def execute_siren(self):
        count = 0
        for n in self.npcs:
            if n.role == "MAFIA" and n.alive:
                n.is_frozen = True
                n.frozen_timer = pygame.time.get_ticks() + 5000
                count += 1
                self.world.effects.append(VisualSound(n.rect.centerx, n.rect.centery, "SIREN", (0, 0, 255), 2.0))
        
        self.world.is_mafia_frozen = True
        self.world.frozen_timer = pygame.time.get_ticks() + 5000

        if self.player.role == "MAFIA" and self.player.alive:
             self.player.add_popup("FROZEN BY SIREN!", (0, 0, 255))

        self.logger.info("GAME", f"Siren Triggered! {count} Mafias frozen.")
        self.time_system.daily_news_log.append("Last night, the Police used the Siren to freeze Mafias!")
        self.ui.show_alert("!!! SIREN !!!", (100, 100, 255))

    def execute_sabotage(self):
        self.world.is_blackout = True
        self.world.blackout_timer = pygame.time.get_ticks() + 10000
        self.logger.info("GAME", "Sabotage Triggered! Blackout started.")
        self.world.effects.append(VisualSound(self.player.rect.centerx, self.player.rect.centery, "BOOM", (50, 50, 50), 3.0))
        self.time_system.daily_news_log.append("마피아, 사회에 공포 조성!!")
        self.ui.show_alert("!!! SABOTAGE !!!", (255, 0, 0))
        
        targets = [n for n in self.npcs if n.role in ["CITIZEN", "DOCTOR"]]
        if self.player.role in ["CITIZEN", "DOCTOR"]: targets.append(self.player)
        
        for t in targets:
            if t.alive:
                t.emotions['FEAR'] = 1
                if t.is_hiding:
                    t.is_hiding = False
                    t.hiding_type = 0
                    t.add_popup("REVEALED!", (255, 0, 0))

    def execute_gunshot(self, shooter, target_pos=None):
        start_x, start_y = shooter.rect.centerx, shooter.rect.centery
        angle = 0
        if target_pos:
            dx, dy = target_pos[0] - start_x, target_pos[1] - start_y
            angle = math.atan2(dy, dx)
        else:
            angle = math.atan2(shooter.facing_dir[1], shooter.facing_dir[0])
            
        is_enemy = (shooter.role != "PLAYER")
        self.player.bullets.append(Bullet(start_x, start_y, angle, is_enemy=is_enemy))
        self.world.effects.append(VisualSound(start_x, start_y, "BANG!", (255, 200, 50), 2.0))
        if shooter.role == "POLICE":
             self.time_system.daily_news_log.append(f"Gunshots fired by Police near {shooter.name}.")

    def trigger_sabotage(self): self.execute_sabotage()
    def trigger_siren(self): self.execute_siren()

    def _handle_npc_action(self, action, n, now):
        if action == "USE_SIREN":
            self.execute_siren()
        elif action == "USE_SABOTAGE":
            self.execute_sabotage()
        elif action == "SHOOT_TARGET" and n.chase_target:
            self.execute_gunshot(n, (n.chase_target.rect.centerx, n.chase_target.rect.centery))
        elif action == "MURDER_OCCURRED":
            self.world.has_murder_occurred = True
            self.time_system.daily_news_log.append("A tragic murder occurred last night.")
        elif action == "FOOTSTEP":
            from settings import TILE_SIZE
            radius = 6 * TILE_SIZE
            if hasattr(self, 'weather') and self.weather == 'RAIN':
                radius *= 0.8
            sound_data = ("FOOTSTEP", n.rect.centerx, n.rect.centery, radius, n.role)
            self._process_sound_effect(sound_data)

    def _process_sound_effect(self, f):
        if len(f) == 5:
            s_type, fx_x, fx_y, rad, source_role = f
        else:
            s_type, fx_x, fx_y, rad = f
            source_role = "UNKNOWN"

        if hasattr(self, 'weather') and self.weather == 'RAIN': rad *= 0.8

        dist = math.sqrt((self.player.rect.centerx - fx_x)**2 + (self.player.rect.centery - fx_y)**2)
        
        if dist < rad * 1.5:
            from settings import SOUND_INFO, TILE_SIZE
            info = SOUND_INFO.get(s_type, {'base_rad': 5, 'color': (200, 200, 200)})
            base_color = info['color']
            
            my_role = self.player.role
            importance = 1.0
            final_color = base_color
            shake = False
            blink = False
            
            if my_role in ["CITIZEN", "DOCTOR"]:
                if source_role == "MAFIA":
                    importance = 2.0
                    final_color = (255, 50, 50) 
                    shake = True 
                    if s_type in ["BANG!", "SLASH", "SCREAM", "GUNSHOT"]: importance = 2.5
                elif source_role == "POLICE":
                    importance = 1.5
                    final_color = (50, 150, 255) 
            
            elif my_role == "MAFIA":
                if source_role == "POLICE":
                    importance = 2.5
                    final_color = (200, 50, 255) 
                    blink = True 
                    if s_type == "SIREN": importance = 3.0
                elif source_role in ["CITIZEN", "DOCTOR"]:
                    importance = 1.5
                    final_color = (255, 255, 100) 
            
            elif my_role == "POLICE":
                if source_role == "MAFIA":
                    importance = 2.0
                    final_color = (255, 150, 0) 
                elif source_role in ["CITIZEN", "DOCTOR"]:
                    importance = 0.6 

            if s_type in ["SIREN", "BOOM"]:
                importance = 2.5
                blink = True

            dist_factor = 1.0 - (dist / (rad * 1.5))
            dist_factor = max(0.2, dist_factor)
            
            base_scale = (rad / (6 * TILE_SIZE))
            final_scale = base_scale * importance * dist_factor
            final_scale = max(0.5, min(2.5, final_scale))

            self.world.effects.append(VisualSound(fx_x, fx_y, s_type, final_color, size_scale=final_scale, shake=shake, blink=blink))
            self.world.indicators.append(SoundDirectionIndicator(fx_x, fx_y))

    def _handle_v_action(self):
        if not self.player.alive: return
        
        targets = []
        action_range = 100
        
        for n in self.npcs:
            if not n.alive: continue
            dist = math.hypot(n.rect.centerx - self.player.rect.centerx, n.rect.centery - self.player.rect.centery)
            if dist <= action_range:
                targets.append((dist, n))
        
        targets.sort(key=lambda x: x[0])
        closest_target = targets[0][1] if targets else None
        
        if self.player.role == "DOCTOR":
            res = self.player.do_heal(closest_target)
            if res:
                if isinstance(res, tuple):
                    msg, sound = res
                    if msg: self.player.add_popup(msg, (200, 200, 255))
                    if sound: self._process_sound_effect(sound)
                else:
                    self.player.add_popup(res, (200, 200, 255))
        else:
            res = self.player.do_attack(closest_target)
            if res:
                popup_data, sound_data = res
                self.player.add_popup(popup_data[0], (255, 50, 50))
                if sound_data:
                    self._process_sound_effect(sound_data)
                    if "GUNSHOT" in popup_data[0]:
                        self.time_system.daily_news_log.append("Gunshots heard!")

    def _process_voting_results(self):
        if self.my_vote_target:
            self.my_vote_target.vote_count += 1
            self.my_vote_target = None

        for n in self.npcs:
            if n.alive and random.random() < 0.3:
                target = random.choice([self.player] + [x for x in self.npcs if x.alive])
                target.vote_count += 1

        candidates = [self.player] + self.npcs
        candidates.sort(key=lambda x: x.vote_count, reverse=True)
        
        if candidates:
            max_votes = candidates[0].vote_count
            
            if max_votes >= 2:
                top_candidates = [c for c in candidates if c.vote_count == max_votes]
                top = random.choice(top_candidates)
                
                top.is_dead = True
                role_reveal = top.role
                news_msg = f"BREAKING NEWS: {top.name} was EXECUTED! And he was a [{role_reveal}]."
                self.time_system.daily_news_log.append(news_msg) 
                self.player.add_popup("EXECUTION!", (255, 0, 0))
                self.world.effects.append(VisualSound(self.player.rect.centerx, self.player.rect.centery - 50, "EXECUTION!", (255, 0, 0), 5.0))
                self.world.effects.append(VisualSound(top.rect.centerx, top.rect.centery, "DEAD", (150, 0, 0), 3.0))
            else:
                self.player.add_popup("Vote Failed", (200, 200, 200))

        for c in candidates: c.vote_count = 0

    def draw(self, screen):
        screen.fill(COLORS['BG'])

        if not self.camera: return

        canvas = self.lighting.draw(screen, self.camera)
        canvas.fill(COLORS['BG']) 

        if self.map_renderer:
            self.map_renderer.draw(canvas, self.camera, 0)

        vw, vh = int(self.game.screen_width / self.zoom_level), int(self.game.screen_height / self.zoom_level)
        offscreen_pins = []
        if not self.player.is_dead:
            job_k = "DOCTOR" if self.player.role == "DOCTOR" else self.player.sub_role
            if job_k in WORK_SEQ:
                target_tid = WORK_SEQ[job_k][self.player.work_step % 3]
                if target_tid in self.world.map_manager.tile_cache:
                    target_pixels = self.world.map_manager.tile_cache[target_tid]
                    sum_x, sum_y, count, off_screen_exists = 0, 0, 0, False
                    for (px, py) in target_pixels:
                        if self.camera.x - TILE_SIZE <= px <= self.camera.x + vw + TILE_SIZE and \
                           self.camera.y - TILE_SIZE <= py <= self.camera.y + vh + TILE_SIZE:
                            pygame.draw.rect(canvas, (255, 255, 0), (px - self.camera.x, py - self.camera.y, TILE_SIZE, TILE_SIZE), 2)
                        else: off_screen_exists = True
                        sum_x += px; sum_y += py; count += 1
                    
                    if off_screen_exists and count > 0:
                        avg_x = sum_x / count; avg_y = sum_y / count
                        center_x = self.camera.x + vw / 2; center_y = self.camera.y + vh / 2
                        dx = (avg_x + TILE_SIZE / 2) - center_x; dy = (avg_y + TILE_SIZE / 2) - center_y
                        if dx != 0 or dy != 0:
                            margin = 30; half_w = self.game.screen_width / 2 - margin; half_h = self.game.screen_height / 2 - margin
                            scale_x = abs(half_w / dx) if dx != 0 else float('inf'); scale_y = abs(half_h / dy) if dy != 0 else float('inf')
                            scale = min(scale_x, scale_y)
                            pin_x = self.game.screen_width / 2 + dx * scale; pin_y = self.game.screen_height / 2 + dy * scale
                            offscreen_pins.append((int(pin_x), int(pin_y)))

        for n in self.npcs:
            if (int(n.rect.centerx//TILE_SIZE), int(n.rect.centery//TILE_SIZE)) in self.visible_tiles or self.player.role == "SPECTATOR":
                n.draw(canvas, self.camera.x, self.camera.y, self.player.role, self.current_phase, self.player.device_on)

        if not self.player.is_dead:
            CharacterRenderer.draw_entity(canvas, self.player, self.camera.x, self.camera.y, self.player.role, self.current_phase, self.player.device_on)

        for fx in self.world.effects: fx.draw(canvas, self.camera.x, self.camera.y)
        for i in self.world.indicators: i.draw(canvas, self.player.rect, self.camera.x, self.camera.y)

        if self.player.role != "SPECTATOR":
            self.lighting.apply_lighting(self.camera)

        if self.player.minigame.active:
            self.player.minigame.draw(canvas, self.player.rect.centerx - self.camera.x, self.player.rect.top - self.camera.y - 60)

        screen.blit(pygame.transform.scale(canvas, (self.game.screen_width, self.game.screen_height)), (0, 0))

        sw, sh = screen.get_width(), screen.get_height()
        for (px, py) in offscreen_pins:
            pygame.draw.circle(screen, (255, 50, 50), (px, py), 8)
            pygame.draw.circle(screen, (255, 255, 255), (px, py), 10, 2)

        if self.weather == 'RAIN':
            for p in self.weather_particles:
                start_pos = (p[0], p[1]); end_pos = (p[0] - 2, p[1] + 10)
                pygame.draw.line(screen, (150, 150, 255, 150), start_pos, end_pos, 1)
        elif self.weather == 'SNOW':
            for p in self.weather_particles:
                pygame.draw.circle(screen, (255, 255, 255, 200), (int(p[0]), int(p[1])), 2)
        elif self.weather == 'FOG':
            if self.effect_surf.get_size() != (sw, sh): self.effect_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            alpha = 100 + int(math.sin(pygame.time.get_ticks() * 0.002) * 20)
            self.effect_surf.fill((200, 200, 220, alpha))
            screen.blit(self.effect_surf, (0, 0))

        anxiety_level = self.player.emotions.get('ANXIETY', 0)
        if anxiety_level > 0:
            pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) * 0.5
            alpha = int(anxiety_level * 10 * pulse)
            if self.effect_surf.get_size() != (sw, sh): self.effect_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            self.effect_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(self.effect_surf, (255, 0, 0, alpha), (0, 0, sw, sh), 30)
            screen.blit(self.effect_surf, (0, 0))

        if self.ui:
            self.ui.draw(screen)
            if self.show_vote_ui:
                self.candidate_rects = self.ui.draw_vote_popup(screen, self.game.screen_width, self.game.screen_height, self.npcs, self.player, self.my_vote_target)
            else:
                self.candidate_rects = []

        if self.is_chatting:
            chat_bg = pygame.Surface((self.game.screen_width, 40))
            chat_bg.fill((0, 0, 0)); chat_bg.set_alpha(200)
            screen.blit(chat_bg, (0, self.game.screen_height - 40))
            font = pygame.font.SysFont("arial", 24)
            txt_surf = font.render(f"Chat: {self.chat_text}", True, (255, 255, 255))
            screen.blit(txt_surf, (10, self.game.screen_height - 35))
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                cursor_x = 10 + txt_surf.get_width()
                pygame.draw.line(screen, (255, 255, 255), (cursor_x, self.game.screen_height - 35), (cursor_x, self.game.screen_height - 5), 2)
        
        # Draw Console last (on top)
        self.console.draw(screen)

    def handle_event(self, event):
        if self.console.handle_event(event): return
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.is_chatting = not self.is_chatting
            if not self.is_chatting:
                if self.chat_text.strip():
                    self.player.add_popup(self.chat_text, (255, 255, 255))
                    self.chat_text = ""
            return

        if self.is_chatting:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE: self.chat_text = self.chat_text[:-1]
                else:
                    if len(self.chat_text) < 50: self.chat_text += event.unicode
            return

        if self.ui.show_vending or self.ui.show_inventory or self.ui.show_voting or self.ui.show_news:
            if event.type == pygame.KEYDOWN:
                res = self.ui.handle_keyboard(event.key, self.npcs)
                if res:
                    if isinstance(res, tuple):
                        msg, sound = res
                        if msg: self.player.add_popup(msg)
                        if sound: self._process_sound_effect(sound)
                    elif isinstance(res, str):
                        self.player.add_popup(res)
                return

        if event.type == pygame.KEYDOWN:
            if not self.player.is_dead and self.player.role != "SPECTATOR":
                if event.key == pygame.K_z:
                    if self.current_phase == "AFTERNOON": self.show_vote_ui = not self.show_vote_ui
                    else: self.player.add_popup("Vote in AFTERNOON", (255, 100, 100))
                elif event.key == pygame.K_v: self._handle_v_action()
                elif event.key == pygame.K_f: self.player.toggle_flashlight()
                elif event.key == pygame.K_q:
                    msg = self.player.toggle_device()
                    if msg: self.player.add_popup(msg)
                elif event.key == pygame.K_i: self.ui.toggle_inventory()
                elif event.key == pygame.K_r:
                    msg = self.player.use_active_skill()
                    if msg:
                        if msg == "USE_SABOTAGE": self.execute_sabotage()
                        elif msg == "USE_SIREN": self.execute_siren()
                        else: self.player.add_popup(msg)
                    else: self.player.add_popup("Cannot use skill yet!", (150, 150, 150))
                else:
                    for k, v in ITEMS.items():
                        if v['key'] == event.key:
                            res = self.player.use_item(k)
                            if isinstance(res, tuple):
                                msg, sound = res
                                if msg: self.player.add_popup(msg)
                                if sound: self._process_sound_effect(sound)
                            elif res: self.player.add_popup(res)
                            break

        if self.player.minigame.active:
            self.player.minigame.handle_event(event)
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.show_vote_ui and self.candidate_rects:
                    for target, rect in self.candidate_rects:
                        if rect.collidepoint(event.pos):
                            self.my_vote_target = target
                            self.player.add_popup(f"Voted for {target.name}", (100, 255, 100))

                if self.player.role == "SPECTATOR":
                    for rect, ent in self.ui.entity_rects:
                        if rect.collidepoint(event.pos): self.ui.spectator_follow_target = ent; break
                    if hasattr(self.ui, 'skip_btn_rect') and self.ui.skip_btn_rect.collidepoint(event.pos):
                        self.time_system.state_timer = 0 # Directly accessing time_system state_timer

        if event.type == pygame.MOUSEWHEEL:
            if self.player.role == "SPECTATOR":
                mx, my = pygame.mouse.get_pos()
                if mx > self.game.screen_width - 300:
                    self.ui.spectator_scroll_y = max(0, self.ui.spectator_scroll_y - event.y * 20)
                else:
                    self.zoom_level = max(0.2, min(4.0, self.zoom_level + (0.2 if event.y > 0 else -0.2)))
                    self.camera.set_zoom(self.zoom_level)
