import json
import pygame
from settings import ITEMS
from world.tiles import TILE_DATA

# 1. Items
# Pygame Key constant를 정수로 변환해야 JSON 저장 가능
items_export = {}
for k, v in ITEMS.items():
    item_data = v.copy()
    if 'key' in item_data and item_data['key'] is not None:
        item_data['key'] = item_data['key'] # Already int
    items_export[k] = item_data

with open('data/items.json', 'w', encoding='utf-8') as f:
    json.dump(items_export, f, indent=4, ensure_ascii=False)

# 2. Tiles
# Key(int)가 JSON에서는 문자열로 저장되므로 나중에 로드할 때 int로 변환 필요
tiles_export = {}
for k, v in TILE_DATA.items():
    tiles_export[str(k)] = v # color 튜플은 리스트로 자동 변환됨

with open('data/tiles.json', 'w', encoding='utf-8') as f:
    json.dump(tiles_export, f, indent=4, ensure_ascii=False)

# 3. Roles (Settings에 없던 정보도 구조화)
roles_export = {
    "CITIZEN": {"hp": 100, "ap": 100, "speed_mod": 1.0},
    "POLICE": {"hp": 100, "ap": 100, "speed_mod": 1.25},
    "MAFIA": {"hp": 100, "ap": 100, "speed_mod": 1.0},
    "DOCTOR": {"hp": 100, "ap": 100, "speed_mod": 1.0},
    "SPECTATOR": {"hp": 999, "ap": 999, "speed_mod": 2.0}
}
with open('data/roles.json', 'w', encoding='utf-8') as f:
    json.dump(roles_export, f, indent=4, ensure_ascii=False)

print("Data extraction complete.")
