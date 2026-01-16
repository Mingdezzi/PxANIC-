from dataclasses import dataclass, field
from typing import Dict

@dataclass
class Inventory:
    items: Dict[str, int] = field(default_factory=dict)  # {'BATTERY': 1, ...}
    coins: int = 0
    
    def add_item(self, item_key: str, count: int = 1):
        self.items[item_key] = self.items.get(item_key, 0) + count
        
    def remove_item(self, item_key: str, count: int = 1) -> bool:
        if self.items.get(item_key, 0) >= count:
            self.items[item_key] -= count
            if self.items[item_key] <= 0:
                del self.items[item_key]
            return True
        return False
    
    def has_item(self, item_key: str, count: int = 1) -> bool:
        return self.items.get(item_key, 0) >= count
