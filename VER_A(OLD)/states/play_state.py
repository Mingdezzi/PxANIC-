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
        self.world = GameWorld(game)
        self.time_system = TimeSystem(game)
        self.lighting = LightingManager(self)
        self.console = DebugConsole(game, self)
        self.map_renderer = None
        self.camera = None
        self.fov = None
        self.visible_tiles = set()
        self.tile_alphas = {} 
        self.zoom_level = 1.5
        self.effect_surf = pygame.Surface((self.game.screen_width, self.game.screen_height), pygame.SRCALPHA)
        self.ui = None
        self.is_chatting = False
        self.chat_text = ""
        self.show_vote_ui = False
        self.my_vote_target = None
        self.candidate_rects = []
        self.heartbeat_timer = 0
        self.last_sent_pos = (0, 0)
        self.time_system.on_phase_change = self.on_phase_change
        self.time_system.on_morning = self.on_morning

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

        # [Network] Send Initial Spawn Position
        if self.player and hasattr(self.game, 'network') and self.game.network.connected:
            self.game.network.send_move(int(self.player.pos_x), int(self.player.pos_y), False, (0, 1))
            self.last_sent_pos = (int(self.player.pos_x), int(self.player.pos_y))

        self.ui = UI(self)
        if self.weather == 'RAIN': self.ui.show_alert("It's Raining...", (100, 100, 255))
        elif self.weather == 'FOG': self.ui.show_alert("Dense Fog...", (150, 150, 150))
        elif self.weather == 'SNOW': self.ui.show_alert("It's Snowing...", (200, 200, 255))

    def on_phase_change(self, old_phase, new_phase):
        if old_phase == "AFTERNOON": self.show_vote_ui = False; self._process_voting_results()

    def on_morning(self):
        gx, gy = int(self.player.rect.centerx // TILE_SIZE), int(self.player.rect.centery // TILE_SIZE)
        is_indoors = (0 <= gx < self.world.map_manager.width and 0 <= gy < self.world.map_manager.height and self.world.map_manager.zone_map[gy][gx] in INDOOR_ZONES)
        self.player.morning_process(is_indoors)
        for n in self.npcs: n.morning_process()
        self.world.has_murder_occurred = False
        if self.time_system.daily_news_log: self.ui.show_daily_news(self.time_system.daily_news_log); self.time_system.daily_news_log = []

    def update(self, dt):
        if not self.player: return
        if self.player.is_dead and self.player.role != "SPECTATOR": self.player.change_role("SPECTATOR"); self.ui.show_alert("YOU DIED!", (255, 0, 0))
        if hasattr(self.game, 'network') and self.game.network.connected:
            for e in self.game.network.get_events():
                if e.get('type') == 'MOVE' and e.get('id') in self.world.entities_by_id:
                    ent = self.world.entities_by_id[e['id']]
                    if isinstance(ent, Dummy): ent.sync_state(e['x'], e['y'], 100, 100, 'CITIZEN', e['is_moving'], e['facing'])
                elif e.get('type') == 'TIME_SYNC': self.time_system.sync_time(e['phase_idx'], e['timer'], e['day'])
        if self.player.alive:
            curr_pos = (int(self.player.pos_x), int(self.player.pos_y))
            if curr_pos != self.last_sent_pos and hasattr(self.game, 'network') and self.game.network.connected:
                self.game.network.send_move(curr_pos[0], curr_pos[1], self.player.is_moving, self.player.facing_dir); self.last_sent_pos = curr_pos
        if hasattr(self.game, 'network') and self.game.network.connected:
            for n in self.npcs:
                if n.is_master:
                    n_pos = (int(n.pos_x), int(n.pos_y))
                    if not hasattr(n, 'last_sent_pos'): n.last_sent_pos = (0, 0)
                    if n_pos != n.last_sent_pos: self.game.network.send({"type": "MOVE", "id": n.uid, "x": n_pos[0], "y": n_pos[1], "is_moving": n.is_moving, "facing": n.facing_dir}); n.last_sent_pos = n_pos
        self.time_system.update(dt); self.world.update(dt, self.current_phase, self.weather, self.day_count); self.lighting.update(dt)
        if self.camera: self.camera.resize(self.game.screen_width, self.game.screen_height)
        if not self.player.is_dead and not (self.ui.show_vending or self.ui.show_inventory or self.ui.show_voting or self.is_chatting):
            if not self.player.is_stunned():
                fx = self.player.update(self.current_phase, self.npcs, self.world.is_blackout, self.weather)
                if fx:
                    for f in fx: self._process_sound_effect(f)
                for p in self.player.popups:
                    if p['text'] == "OPEN_SHOP": self.ui.toggle_vending_machine(); self.player.popups.remove(p); break
            self.player.update_bullets(self.npcs)
        if self.player.role in ["CITIZEN", "DOCTOR", "FARMER", "MINER", "FISHER"] and self.current_phase == "NIGHT":
            nearest = min([math.hypot(n.rect.centerx-self.player.rect.centerx, n.rect.centery-self.player.rect.centery) for n in self.npcs if n.role == "MAFIA" and n.alive] + [float('inf')])
            if nearest < 640:
                self.player.emotions['ANXIETY'] = int((640 - nearest) / 60)
                if pygame.time.get_ticks() - self.heartbeat_timer > max(300, int(nearest * 2)):
                    self.heartbeat_timer = pygame.time.get_ticks(); self.world.effects.append(VisualSound(self.player.rect.centerx, self.player.rect.centery, "THUMP", (100, 0, 0), size_scale=0.5))
            else: self.player.emotions['ANXIETY'] = 0
        if self.current_phase == "NIGHT" and random.random() < 0.005:
            for n in self.npcs:
                if n.role == "MAFIA" and n.alive:
                    gx, gy = int(n.rect.centerx // TILE_SIZE), int(n.rect.centery // TILE_SIZE)
                    if 0 <= gy < self.world.map_manager.height and 0 <= gx < self.world.map_manager.width:
                        zid = self.world.map_manager.zone_map[gy][gx]
                        if zid in ZONES and zid != 1: self.time_system.mafia_last_seen_zone = ZONES[zid]['name']
        for n in self.npcs:
            if not n.is_stunned(): self._handle_npc_action(n.update(self.current_phase, self.player, self.npcs, self.world.is_mafia_frozen, self.world.noise_list, self.day_count, self.world.bloody_footsteps), n, 0)
        if self.player.role == "SPECTATOR": self._update_spectator_camera()
        else: self.camera.update(self.player.rect.centerx, self.player.rect.centery)

        # FOV & Rendering Prep
        if self.player.role == "SPECTATOR":
            rad = 100 # Unlimited vision for spectator
            direction = None
        else:
            rad = self.player.get_vision_radius(self.lighting.current_vision_factor, self.world.is_blackout, self.weather)
            direction = None
            if self.player.role == "POLICE" and self.player.flashlight_on and self.current_phase in ['EVENING', 'NIGHT', 'DAWN']:
                direction = self.player.facing_dir
        
        self.visible_tiles = self.fov.cast_rays(self.player.rect.centerx, self.player.rect.centery, rad, direction, 60)
        for tile in self.visible_tiles: self.tile_alphas[tile] = min(255, self.tile_alphas.get(tile, 0) + 15)
        for tile in list(self.tile_alphas.keys()):
            if tile not in self.visible_tiles:
                self.tile_alphas[tile] -= 15
                if self.tile_alphas[tile] <= 0: del self.tile_alphas[tile]
        if self.state_timer <= 0: self._advance_phase()

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
            if t.alive:
                self.camera.update(t.rect.centerx, t.rect.centery)
            else:
                self.ui.spectator_follow_target = None

    def execute_siren(self):
        for n in [x for x in self.npcs if x.role == "MAFIA" and x.alive]:
            n.is_frozen = True; n.frozen_timer = pygame.time.get_ticks() + 5000; self.world.effects.append(VisualSound(n.rect.centerx, n.rect.centery, "SIREN", (0, 0, 255), 2.0))
        self.world.is_mafia_frozen = True; self.world.frozen_timer = pygame.time.get_ticks() + 5000
        self.ui.show_alert("!!! SIREN !!!", (100, 100, 255))

    def execute_sabotage(self):
        self.world.is_blackout = True; self.world.blackout_timer = pygame.time.get_ticks() + 10000
        self.world.effects.append(VisualSound(self.player.rect.centerx, self.player.rect.centery, "BOOM", (50, 50, 50), 3.0))
        self.ui.show_alert("!!! SABOTAGE !!!", (255, 0, 0))
        for t in [x for x in self.npcs + [self.player] if x.role in ["CITIZEN", "DOCTOR"] and x.alive]: t.emotions['FEAR'] = 1

    def execute_gunshot(self, shooter, target_pos=None):
        angle = math.atan2(target_pos[1]-shooter.rect.centery, target_pos[0]-shooter.rect.centerx) if target_pos else math.atan2(shooter.facing_dir[1], shooter.facing_dir[0])
        self.player.bullets.append(Bullet(shooter.rect.centerx, shooter.rect.centery, angle, is_enemy=(shooter.role != "PLAYER")))
        self.world.effects.append(VisualSound(shooter.rect.centerx, shooter.rect.centery, "BANG!", (255, 200, 50), 2.0))

    def trigger_sabotage(self): self.execute_sabotage()
    def trigger_siren(self): self.execute_siren()

    def _handle_npc_action(self, action, n, now):
        if action == "USE_SIREN": self.execute_siren()
        elif action == "USE_SABOTAGE": self.execute_sabotage()
        elif action == "SHOOT_TARGET" and n.chase_target: self.execute_gunshot(n, (n.chase_target.rect.centerx, n.chase_target.rect.centery))
        elif action == "MURDER_OCCURRED": self.world.has_murder_occurred = True
        elif action == "FOOTSTEP": self._process_sound_effect(("FOOTSTEP", n.rect.centerx, n.rect.centery, TILE_SIZE*6, n.role))

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
            
            # --- [Listener-Speaker Importance Logic] ---
            if my_role in ["CITIZEN", "DOCTOR"]:
                if source_role == "MAFIA":
                    importance = 2.0
                    final_color = (255, 50, 50) # Red (Danger)
                    shake = True 
                    if s_type in ["BANG!", "SLASH", "SCREAM", "GUNSHOT"]: importance = 2.5
                elif source_role == "POLICE":
                    importance = 1.5
                    final_color = (50, 150, 255) # Blue (Rescue)
            
            elif my_role == "MAFIA":
                if source_role == "POLICE":
                    importance = 2.5
                    final_color = (200, 50, 255) # Purple (Warning)
                    blink = True 
                    if s_type == "SIREN": importance = 3.0
                elif source_role in ["CITIZEN", "DOCTOR"]:
                    importance = 1.5
                    final_color = (255, 255, 100) # Yellow (Prey)
            
            elif my_role == "POLICE":
                if source_role == "MAFIA":
                    importance = 2.0
                    final_color = (255, 150, 0) # Orange (Target)
                elif source_role in ["CITIZEN", "DOCTOR"]:
                    importance = 0.6 # Low importance (Noise)

            if s_type in ["SIREN", "BOOM"]: 
                importance = 2.5
                blink = True

            # --- [Size Calculation] ---
            # Distance Falloff: Closer is bigger
            dist_factor = 1.0 - (dist / (rad * 1.5))
            dist_factor = max(0.2, dist_factor)
            
            # Base Scale (based on radius relative to footstep)
            base_scale = (rad / (6 * TILE_SIZE))
            
            # Final Scale
            final_scale = base_scale * importance * dist_factor
            final_scale = max(0.5, min(2.5, final_scale))

            self.world.effects.append(VisualSound(fx_x, fx_y, s_type, final_color, size_scale=final_scale, shake=shake, blink=blink))
            self.world.indicators.append(SoundDirectionIndicator(fx_x, fx_y))

    def _handle_v_action(self):
        targets = sorted([(math.hypot(n.rect.centerx-self.player.rect.centerx, n.rect.centery-self.player.rect.centery), n) for n in self.npcs if n.alive], key=lambda x: x[0])
        target = targets[0][1] if targets and targets[0][0] <= 100 else None
        if self.player.role == "DOCTOR":
            res = self.player.do_heal(target)
            if res: self.player.add_popup(res[0] if isinstance(res, tuple) else res, (200, 200, 255))
        else:
            res = self.player.do_attack(target)
            if res: self.player.add_popup(res[0][0], (255, 50, 50)); self._process_sound_effect(res[1])

    def _process_voting_results(self):
        if self.my_vote_target: self.my_vote_target.vote_count += 1; self.my_vote_target = None
        for n in [x for x in self.npcs if x.alive]:
            if random.random() < 0.3: target = random.choice([self.player] + [x for x in self.npcs if x.alive]); target.vote_count += 1
        candidates = sorted([self.player] + self.npcs, key=lambda x: x.vote_count, reverse=True)
        if candidates and candidates[0].vote_count >= 2:
            top = random.choice([c for c in candidates if c.vote_count == candidates[0].vote_count])
            top.is_dead = True; self.player.add_popup("EXECUTION!", (255, 0, 0))

    def draw(self, screen):
        screen.fill(COLORS['BG'])
        if not self.camera: return
        canvas = self.lighting.draw(screen, self.camera)
        canvas.fill(COLORS['BG'])
        if self.map_renderer:
            vis = self.visible_tiles if self.player.role != "SPECTATOR" else None
            self.map_renderer.draw(canvas, self.camera, 0, visible_tiles=vis, tile_alphas=self.tile_alphas)
        
        for n in self.npcs:
            if (int(n.rect.centerx//TILE_SIZE), int(n.rect.centery//TILE_SIZE)) in self.visible_tiles or self.player.role == "SPECTATOR":
                n.draw(canvas, self.camera.x, self.camera.y, self.player.role, self.current_phase, self.player.device_on)
        if not self.player.is_dead: CharacterRenderer.draw_entity(canvas, self.player, self.camera.x, self.camera.y, self.player.role, self.current_phase, self.player.device_on)
        for fx in self.world.effects: fx.draw(canvas, self.camera.x, self.camera.y)
        for i in self.world.indicators: i.draw(canvas, self.player.rect, self.camera.x, self.camera.y)
        if self.player.role != "SPECTATOR": self.lighting.apply_lighting(self.camera)
        if self.player.minigame.active: self.player.minigame.draw(canvas, self.player.rect.centerx - self.camera.x, self.player.rect.top - self.camera.y - 60)
        screen.blit(pygame.transform.scale(canvas, (self.game.screen_width, self.game.screen_height)), (0, 0))
        if self.weather == 'RAIN':
            for p in self.weather_particles: pygame.draw.line(screen, (150, 150, 255, 150), (p[0], p[1]), (p[0]-2, p[1]+10))
        elif self.weather == 'SNOW':
            for p in self.weather_particles: pygame.draw.circle(screen, (255, 255, 255, 200), (int(p[0]), int(p[1])), 2)
        if self.ui: self.ui.draw(screen)
        self.console.draw(screen)

    def handle_event(self, event):
        if self.console.handle_event(event): return
        if self.ui.show_vending or self.ui.show_inventory or self.ui.show_voting or self.ui.show_news:
            if event.type == pygame.KEYDOWN:
                res = self.ui.handle_keyboard(event.key, self.npcs)
                if res:
                    if isinstance(res, tuple):
                        if res[0]: self.player.add_popup(res[0]); self._process_sound_effect(res[1])
                    else: self.player.add_popup(res)
            return
        if event.type == pygame.KEYDOWN:
            if not self.player.is_dead:
                if event.key == pygame.K_z and self.current_phase == "AFTERNOON": self.show_vote_ui = not self.show_vote_ui
                elif event.key == pygame.K_v: self._handle_v_action()
                elif event.key == pygame.K_f: self.player.toggle_flashlight()
                elif event.key == pygame.K_q:
                    msg = self.player.toggle_device()
                    if msg: self.player.add_popup(msg)
                elif event.key == pygame.K_i: self.ui.toggle_inventory()
                elif event.key == pygame.K_r:
                    msg = self.player.use_active_skill()
                    if msg == "USE_SABOTAGE": self.execute_sabotage()
                    elif msg == "USE_SIREN": self.execute_siren()
                    elif msg: self.player.add_popup(msg)
                else:
                    for k, v in ITEMS.items():
                        if v['key'] == event.key:
                            res = self.player.use_item(k)
                            if isinstance(res, tuple): self.player.add_popup(res[0]); self._process_sound_effect(res[1])
                            elif res: self.player.add_popup(res)
                            break
        if self.player.minigame.active: self.player.minigame.handle_event(event); return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # 1. Minimap Click (All roles if needed, mostly spectator)
                mm_rect = self.ui.minimap_rect
                if mm_rect.collidepoint(event.pos):
                    # Calculate map relative pos
                    rx = (event.pos[0] - mm_rect.x) / mm_rect.width
                    ry = (event.pos[1] - mm_rect.y) / mm_rect.height
                    
                    target_world_x = rx * (self.world.map_manager.width * TILE_SIZE)
                    target_world_y = ry * (self.world.map_manager.height * TILE_SIZE)
                    
                    self.ui.spectator_follow_target = None # Manual move breaks follow
                    self.camera.update(target_world_x, target_world_y)
                    return

                if self.show_vote_ui and self.candidate_rects:
                    for target, rect in self.candidate_rects:
                        if rect.collidepoint(event.pos):
                            self.my_vote_target = target
                            self.player.add_popup(f"Voted for {target.name}", (100, 255, 100))

                if self.player.role == "SPECTATOR":
                    # 2. Click Entity list in UI
                    for rect, ent in self.ui.entity_rects:
                        if rect.collidepoint(event.pos): self.ui.spectator_follow_target = ent; break
                    
                    # 3. Skip Phase Button
                    if hasattr(self.ui, 'skip_btn_rect') and self.ui.skip_btn_rect.collidepoint(event.pos):
                        self.time_system.state_timer = 0
                    
                    # 4. Click Entity in World
                    mx, my = event.pos
                    world_mx = mx / self.zoom_level + self.camera.x
                    world_my = my / self.zoom_level + self.camera.y
                    
                    click_rect = pygame.Rect(world_mx - 10, world_my - 10, 20, 20)
                    for ent in [self.player] + self.npcs:
                        if ent.alive and click_rect.colliderect(ent.rect):
                            self.ui.spectator_follow_target = ent
                            self.player.add_popup(f"Following {ent.name}", (100, 100, 255))
                            break
        if event.type == pygame.MOUSEWHEEL and self.player.role == "SPECTATOR":
            if pygame.mouse.get_pos()[0] > self.game.screen_width - 300: self.ui.spectator_scroll_y = max(0, self.ui.spectator_scroll_y - event.y * 20)
            else: self.zoom_level = max(0.2, min(4.0, self.zoom_level + (0.2 if event.y > 0 else -0.2))); self.camera.set_zoom(self.zoom_level)