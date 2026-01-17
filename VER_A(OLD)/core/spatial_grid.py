from settings import TILE_SIZE

class SpatialGrid:
    def __init__(self, map_width, map_height, cell_size=10):
        self.map_width = map_width
        self.map_height = map_height
        self.cell_size = cell_size # in Tiles
        self.inv_cell_size = 1.0 / cell_size # [Optimization] Precompute inverse
        
        self.cells = {} # {(gx, gy): {entity_uid, ...}}
        self.entity_locations = {} # {entity_uid: (gx, gy)}

    def _get_cell_coords(self, tx, ty):
        # [Optimization] Use multiplication instead of division
        return int(tx * self.inv_cell_size), int(ty * self.inv_cell_size)

    def add(self, entity):
        if not hasattr(entity, 'uid'): return
        
        tx = int(entity.rect.centerx / TILE_SIZE)
        ty = int(entity.rect.centery / TILE_SIZE)
        gx, gy = self._get_cell_coords(tx, ty)
        
        if (gx, gy) not in self.cells:
            self.cells[(gx, gy)] = set()
            
        self.cells[(gx, gy)].add(entity.uid)
        self.entity_locations[entity.uid] = (gx, gy)

    def remove(self, entity):
        if not hasattr(entity, 'uid'): return
        loc = self.entity_locations.get(entity.uid)
        if loc:
            gx, gy = loc
            if (gx, gy) in self.cells and entity.uid in self.cells[(gx, gy)]:
                self.cells[(gx, gy)].remove(entity.uid)
                if not self.cells[(gx, gy)]:
                    del self.cells[(gx, gy)]
            del self.entity_locations[entity.uid]

    def update_entity(self, entity):
        if not hasattr(entity, 'uid'): return
        
        tx = int(entity.rect.centerx / TILE_SIZE)
        ty = int(entity.rect.centery / TILE_SIZE)
        new_gx, new_gy = self._get_cell_coords(tx, ty)
        
        old_loc = self.entity_locations.get(entity.uid)
        
        if old_loc != (new_gx, new_gy):
            self.remove(entity) # Remove from old
            self.add(entity)    # Add to new

    def get_nearby_entities(self, entity, radius_tiles=None):
        if not hasattr(entity, 'uid'): return set()
        
        tx = int(entity.rect.centerx / TILE_SIZE)
        ty = int(entity.rect.centery / TILE_SIZE)
        gx, gy = self._get_cell_coords(tx, ty)
        
        search_radius = 1
        if radius_tiles:
            search_radius = int(radius_tiles * self.inv_cell_size) + 1
            
        nearby_uids = set()
        
        # [Optimization] Local var access
        cells = self.cells
        
        for dy in range(-search_radius, search_radius + 1):
            for dx in range(-search_radius, search_radius + 1):
                cell_key = (gx + dx, gy + dy)
                if cell_key in cells:
                    nearby_uids.update(cells[cell_key])
                    
        if entity.uid in nearby_uids:
            nearby_uids.remove(entity.uid)
            
        return nearby_uids