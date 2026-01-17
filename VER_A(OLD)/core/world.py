import random
import uuid
import pygame
from world.map_manager import MapManager
from entities.player import Player
from entities.npc import Dummy
from settings import TILE_SIZE, ZONES
from core.spatial_grid import SpatialGrid

class GameWorld:
    def __init__(self, game):
        self.game = game
        self.map_manager = MapManager()
        self.spatial_grid = None
        self.player = None
        self.npcs = []
        self.bullets = []
        self.entities_by_id = {} 
        self.effects = []
        self.indicators = []
        self.noise_list = []
        self.bloody_footsteps = []
        self.is_blackout = False
        self.blackout_timer = 0
        self.is_mafia_frozen = False
        self.frozen_timer = 0
        self.has_murder_occurred = False

    def load_map(self, filename="map.json"):
        self.map_manager.load_map(filename)
        self.spatial_grid = SpatialGrid(self.map_manager.width, self.map_manager.height, cell_size=10)

    def find_safe_spawn(self):
        c = self.map_manager.get_spawn_points(zone_id=1)
        if c:
            return random.choice(c)
        return (self.map_manager.spawn_x, self.map_manager.spawn_y)

    def register_entity(self, entity):
        if not hasattr(entity, 'uid') or entity.uid is None:
            entity.uid = str(uuid.uuid4())[:8]
        self.entities_by_id[entity.uid] = entity
        if self.spatial_grid: self.spatial_grid.add(entity)
        entity.world = self

    def init_entities(self):
        """Creates entities based on participants list from server/lobby"""
        participants = self.game.shared_data.get('participants', [])
        my_id = -1
        if hasattr(self.game, 'network') and self.game.network.connected:
            my_id = self.game.network.my_id
        else:
            my_id = 0 # Default for offline

        self.npcs = []
        self.entities_by_id = {}
        player_created = False

        mw, mh = self.map_manager.width, self.map_manager.height
        zm = self.map_manager.zone_map

        for p in participants:
            # Create entities for both PLAYERS and SPECTATORS
            pid = p.get('id')
            role = p.get('role', 'CITIZEN')
            name = p.get('name', 'Unknown')
            p_type = p.get('type', 'PLAYER')
            p_group = p.get('group', 'PLAYER')
            
            sx, sy = self.find_safe_spawn()
            
            if pid == my_id:
                # This is ME (could be Player or Spectator)
                self.player = Player(sx, sy, mw, mh, None, zm, map_manager=self.map_manager)
                self.player.uid = pid
                self.player.name = name
                self.player.is_player = True
                
                # Assign role correctly (Lobby 'group' takes precedence for role assignment)
                if p_group == 'SPECTATOR':
                    self.player.change_role("SPECTATOR")
                else:
                    self.player.change_role(role)
                    
                self.register_entity(self.player)
                player_created = True
            elif p_group == 'PLAYER':
                # This is a BOT or ANOTHER PLAYER (only if they are in PLAYER group)
                n = Dummy(sx, sy, None, mw, mh, name=name, role=role, zone_map=zm, map_manager=self.map_manager)
                n.uid = pid
                
                # Logic: Master if I am host AND it's a BOT. Otherwise Slave.
                if p_type == 'BOT' and my_id == 0:
                    n.is_master = True
                else:
                    n.is_master = False
                
                self.register_entity(n)
                self.npcs.append(n)

        # [Safety Fallback] If no player data was found, create a default local player
        if not player_created:
            sx, sy = self.find_safe_spawn()
            self.player = Player(sx, sy, mw, mh, None, zm, map_manager=self.map_manager)
            self.player.uid = my_id if my_id != -1 else 0
            self.player.is_player = True
            self.register_entity(self.player)

    def update(self, dt, current_phase, weather, day_count):
        now = pygame.time.get_ticks()
        if self.is_blackout and now > self.blackout_timer: self.is_blackout = False
        if self.is_mafia_frozen and now > self.frozen_timer: self.is_mafia_frozen = False
        self.map_manager.update_doors(dt, [self.player] + self.npcs)
        self.bloody_footsteps = [bf for bf in self.bloody_footsteps if now < bf[2]]
        for e in self.effects[:]: e.update()
        self.effects = [e for e in self.effects if e.alive]
        for i in self.indicators[:]: 
            i.update()
            if not i.alive: self.indicators.remove(i)

    def get_nearby_entities(self, entity, radius_tiles=None):
        if not self.spatial_grid: return []
        uids = self.spatial_grid.get_nearby_entities(entity, radius_tiles)
        return [self.entities_by_id[uid] for uid in uids if uid in self.entities_by_id and self.entities_by_id[uid].alive]