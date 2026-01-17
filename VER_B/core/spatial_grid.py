from settings import TILE_SIZE

class SpatialGrid:
    def __init__(self, map_width, map_height, cell_size=10):
        self.map_width = map_width
        self.map_height = map_height
        self.cell_size = cell_size # in Tiles
        
        # Grid dimensions
        self.cols = (map_width // cell_size) + 1
        self.rows = (map_height // cell_size) + 1
        
        # The Grid: A dictionary or list of sets
        # using dict for sparse efficiency {(gx, gy): {entity_uid, ...}}
        self.cells = {}
        
        # Tracking where each entity is: {entity_uid: (gx, gy)}
        self.entity_locations = {}

    def _get_cell_coords(self, tx, ty):
        return int(tx // self.cell_size), int(ty // self.cell_size)

    def add(self, entity):
        if not hasattr(entity, 'uid'): return
        
        tx, ty = entity.rect.centerx // TILE_SIZE, entity.rect.centery // TILE_SIZE
        gx, gy = self._get_cell_coords(tx, ty)
        
        if (gx, gy) not in self.cells:
            self.cells[(gx, gy)] = set()
            
        self.cells[(gx, gy)].add(entity.uid)
        self.entity_locations[entity.uid] = (gx, gy)

    def remove(self, entity):
        if not hasattr(entity, 'uid'): return
        if entity.uid not in self.entity_locations: return
        
        gx, gy = self.entity_locations.pop(entity.uid)
        if (gx, gy) in self.cells:
            if entity.uid in self.cells[(gx, gy)]:
                self.cells[(gx, gy)].remove(entity.uid)
                # Cleanup empty cells to save memory (optional)
                if not self.cells[(gx, gy)]:
                    del self.cells[(gx, gy)]

    def update_entity(self, entity):
        """Call this when entity moves"""
        if not hasattr(entity, 'uid'): return
        
        tx, ty = entity.rect.centerx // TILE_SIZE, entity.rect.centery // TILE_SIZE
        new_gx, new_gy = self._get_cell_coords(tx, ty)
        
        old_loc = self.entity_locations.get(entity.uid)
        
        # Only update if cell changed
        if old_loc != (new_gx, new_gy):
            self.remove(entity) # Remove from old
            self.add(entity)    # Add to new

    def get_nearby_entities(self, entity, radius_tiles=None):
        """Returns a set of entity UIDs in adjacent cells"""
        if not hasattr(entity, 'uid'): return set()
        
        tx, ty = entity.rect.centerx // TILE_SIZE, entity.rect.centery // TILE_SIZE
        gx, gy = self._get_cell_coords(tx, ty)
        
        # Determine search range (default: 3x3 grid around entity)
        # If radius is large, we might need to search more cells
        search_radius = 1
        if radius_tiles:
            search_radius = int((radius_tiles / self.cell_size) + 1)
            
        nearby_uids = set()
        
        for dy in range(-search_radius, search_radius + 1):
            for dx in range(-search_radius, search_radius + 1):
                cell_key = (gx + dx, gy + dy)
                if cell_key in self.cells:
                    nearby_uids.update(self.cells[cell_key])
                    
        # Exclude self
        if entity.uid in nearby_uids:
            nearby_uids.remove(entity.uid)
            
        return nearby_uids
