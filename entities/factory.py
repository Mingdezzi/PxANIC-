from core.ecs_manager import ECSManager
from components.common import Transform, Velocity, Sprite, Animation
from components.status import Stats, StatusEffects
from components.interaction import Inventory, InteractionState
from components.ai import AIBrain
from components.identity import Identity
from components.vision import Vision
from settings import TILE_SIZE
import random
from colors import CUSTOM_COLORS

class EntityFactory:
    def __init__(self, ecs_manager: ECSManager):
        self.ecs = ecs_manager

    def create_player(self, x, y, name="Player", role="CITIZEN", sub_role=None):
        entity = self.ecs.create_entity()
        
        # 1. Common Components
        self.ecs.add_component(entity, Transform(x=x, y=y, width=TILE_SIZE-12, height=TILE_SIZE-12))
        self.ecs.add_component(entity, Velocity())
        self.ecs.add_component(entity, Sprite(
            role=role, 
            sub_role=sub_role,
            custom_data={
                'skin': 0, # 플레이어는 커스터마이징 가능하도록 0으로 초기화 (추후 설정)
                'clothes': 2 if role == "POLICE" else (6 if role == "DOCTOR" else 0),
                'hat': 0
            }
        ))
        self.ecs.add_component(entity, Animation())
        
        # 2. Status & Identity
        self.ecs.add_component(entity, Stats())
        self.ecs.add_component(entity, StatusEffects())
        self.ecs.add_component(entity, Identity(name=name, role=role, sub_role=sub_role, group_id="PLAYER", is_player=True))
        
        # 3. Interaction & Inventory
        inv = Inventory()
        inv.items['BATTERY'] = 1 # 기본 지급 아이템
        self.ecs.add_component(entity, inv)
        self.ecs.add_component(entity, InteractionState())
        
        # 4. Vision
        self.ecs.add_component(entity, Vision())
        
        return entity

    def create_npc(self, x, y, name="Bot", role="CITIZEN", sub_role=None):
        entity = self.ecs.create_entity()
        
        # 1. Common Components
        self.ecs.add_component(entity, Transform(x=x, y=y, width=TILE_SIZE-12, height=TILE_SIZE-12))
        self.ecs.add_component(entity, Velocity())
        
        # Random Appearance for NPCs
        skin = random.randint(0, len(CUSTOM_COLORS['SKIN'])-1)
        clothes = random.randint(0, len(CUSTOM_COLORS['CLOTHES'])-1)
        hat = random.randint(0, len(CUSTOM_COLORS['HAT'])-1)
        
        if role == "POLICE": clothes = 2
        elif role == "DOCTOR": clothes = 6
        
        self.ecs.add_component(entity, Sprite(
            role=role,
            sub_role=sub_role,
            custom_data={'skin': skin, 'clothes': clothes, 'hat': hat}
        ))
        self.ecs.add_component(entity, Animation())
        
        # 2. Status & Identity
        self.ecs.add_component(entity, Stats())
        self.ecs.add_component(entity, StatusEffects())
        self.ecs.add_component(entity, Identity(name=name, role=role, sub_role=sub_role, group_id="BOT", is_player=False))
        
        # 3. AI Brain
        self.ecs.add_component(entity, AIBrain())
        
        # 4. Interaction & Inventory
        inv = Inventory()
        inv.items['BATTERY'] = 1
        self.ecs.add_component(entity, inv)
        self.ecs.add_component(entity, InteractionState())
        
        # 5. Vision (NPC도 시야 가짐)
        self.ecs.add_component(entity, Vision())
        
        return entity
