import random
import uuid
from world.map_manager import MapManager
from entities.player import Player
from entities.npc import Dummy
from settings import TILE_SIZE, ZONES
from core.spatial_grid import SpatialGrid

class GameWorld:
    def __init__(self, game):
        self.game = game
        self.map_manager = MapManager()
        
        # [Spatial Partitioning]
        # Map dimensions are loaded later, so init with defaults, resize later if needed
        self.spatial_grid = None
        
        # [Entity Management]
        self.player = None
        self.npcs = []
        self.bullets = []
        
        # {uid: entity_obj} for fast lookup
        self.entities_by_id = {} 
        
        self.effects = []
        self.indicators = []
        self.noise_list = []
        self.bloody_footsteps = []
        
        # Events
        self.is_blackout = False
        self.blackout_timer = 0
        self.is_mafia_frozen = False
        self.frozen_timer = 0
        self.has_murder_occurred = False

    def load_map(self, filename="map.json"):
        self.map_manager.load_map(filename)
        # Initialize Spatial Grid with correct map size
        self.spatial_grid = SpatialGrid(self.map_manager.width, self.map_manager.height, cell_size=10)

    def find_safe_spawn(self):
        c = self.map_manager.get_spawn_points(zone_id=1)
        return random.choice(c) if c else (100, 100)

    def register_entity(self, entity):
        # Assign UUID if not present (simple integer ID for now for performance, or uuid4)
        if not hasattr(entity, 'uid') or entity.uid is None:
            entity.uid = str(uuid.uuid4())[:8] # Short unique ID
        
        self.entities_by_id[entity.uid] = entity
        if self.spatial_grid:
            self.spatial_grid.add(entity)
            
        # Inject world reference into entity for convenience
        entity.world = self

    def init_entities(self):
        participants = self.game.shared_data.get('participants', [])
        cit_jobs = ["FARMER", "MINER", "FISHER"]

        random_indices = [i for i, p in enumerate(participants) if p['group'] == 'PLAYER' and p['role'] == 'RANDOM']
        if random_indices:
            r_pool = ["MAFIA", "POLICE", "DOCTOR"]
            while len(r_pool) < len(random_indices): r_pool.append("CITIZEN")
            if len(participants) >= 4 and "MAFIA" not in [p['role'] for p in participants if p['role'] != 'RANDOM']:
                if "MAFIA" not in r_pool: r_pool[0] = "MAFIA"
            
            random.shuffle(r_pool)
            for p in participants:
                if p['role'] in r_pool: r_pool.remove(p['role'])
            random.shuffle(random_indices)
            for idx in random_indices:
                if r_pool: participants[idx]['role'] = r_pool.pop(0)
                else: participants[idx]['role'] = random.choice(cit_jobs)

        sx, sy = self.find_safe_spawn()
        self.player = Player(sx, sy, self.map_manager.width, self.map_manager.height, None, self.map_manager.zone_map, map_manager=self.map_manager)
        self.player.is_player = True
        
        self.register_entity(self.player) # Register Player

        my_data = next((p for p in participants if p['type'] == 'PLAYER'), None)
        if my_data:
            self.player.name = my_data['name']
            if my_data['group'] == 'SPECTATOR':
                self.player.change_role("SPECTATOR")
            else:
                if my_data['role'] in cit_jobs: self.player.change_role("CITIZEN", my_data['role'])
                else: self.player.change_role(my_data['role'])

        self.npcs = []
        for p in participants:
            if p['type'] == 'BOT':
                if p['group'] == 'SPECTATOR':
                    pass
                else:
                    nx, ny = self.find_safe_spawn()
                    rt = "CITIZEN" if p['role'] in cit_jobs else p['role']
                    n = Dummy(nx, ny, None, self.map_manager.width, self.map_manager.height, name=p['name'], role=rt, zone_map=self.map_manager.zone_map, map_manager=self.map_manager)
                    if p['role'] in cit_jobs: n.sub_role = p['role']
                    n.vote_count = 0 
                    self.register_entity(n) # Register NPC
                    self.npcs.append(n)

    def update(self, dt, current_phase, weather, day_count):
        # Update Event Timers
        now = pygame.time.get_ticks()
        
        if self.is_blackout and now > self.blackout_timer: self.is_blackout = False
        if self.is_mafia_frozen and now > self.frozen_timer: self.is_mafia_frozen = False

        self.map_manager.update_doors(dt, [self.player] + self.npcs)
        
        # Bloody Footsteps cleanup
        self.bloody_footsteps = [bf for bf in self.bloody_footsteps if now < bf[2]]

        # Effects & Indicators cleanup
        for e in self.effects[:]: e.update()
        self.effects = [e for e in self.effects if e.alive]
        
        for i in self.indicators[:]: 
            i.update()
            if not i.alive: self.indicators.remove(i)

    def get_nearby_entities(self, entity, radius_tiles=None):
        """Proxy to spatial grid"""
        if not self.spatial_grid: return []
        
        uids = self.spatial_grid.get_nearby_entities(entity, radius_tiles)
        entities = []
        for uid in uids:
            if uid in self.entities_by_id:
                ent = self.entities_by_id[uid]
                if ent.alive: # Only return alive entities
                    entities.append(ent)
        return entities

import pygame