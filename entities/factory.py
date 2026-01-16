from . import Entity
from components.transform import Transform
from components.stats import Stats
from components.role import Role
from components.inventory import Inventory
from components.graphics import Graphics
from components.physics import Physics
from components.ai_brain import AIBrain
from components.interaction import Interaction
from settings import *
from colors import CUSTOM_COLORS
import random

class EntityFactory:
    @staticmethod
    def create_player(x, y, role="CITIZEN", sub_role=None):
        e = Entity("Player")
        
        # 1. Transform (히트박스 보정 포함: 기존 +6, +6, -12, -12 로직은 Rect 생성시 처리 필요)
        # Transform 컴포넌트는 기본적으로 32x32로 생성되므로, 충돌 처리는 MovementSystem에서 보정된 Rect를 쓰거나
        # Transform 자체에 collider_offset을 두는 게 좋음. 여기서는 단순화.
        e.add_component(Transform(x, y))
        
        # 2. Stats
        e.add_component(Stats(hp=100, ap=100))
        
        # 3. Role (외형 랜덤)
        skin = random.randint(0, len(CUSTOM_COLORS['SKIN'])-1)
        clothes = random.randint(0, len(CUSTOM_COLORS['CLOTHES'])-1)
        hat = random.randint(0, len(CUSTOM_COLORS['HAT'])-1)
        
        # 직업별 고정 외형 (기존 Player.__init__ 참조)
        if role == "DOCTOR": clothes = 6
        elif role == "POLICE": clothes = 2
        
        e.add_component(Role(main_role=role, sub_role=sub_role, 
                             skin_idx=skin, clothes_idx=clothes, hat_idx=hat))
        
        # 4. Inventory
        inv = Inventory()
        inv.add_item('BATTERY', 1)
        e.add_component(inv)
        
        # 5. Graphics
        e.add_component(Graphics())
        
        # 6. Physics
        e.add_component(Physics())
        
        # 7. Interaction
        e.add_component(Interaction())
        
        return e

    @staticmethod
    def create_npc(x, y, name="NPC", role="CITIZEN"):
        e = Entity(name)
        
        e.add_component(Transform(x, y))
        e.add_component(Stats(hp=100, ap=100))
        
        sub_role = None
        if role == "CITIZEN":
            sub_role = random.choice(["FARMER", "MINER", "FISHER"])
            
        skin = random.randint(0, len(CUSTOM_COLORS['SKIN'])-1)
        clothes = random.randint(0, len(CUSTOM_COLORS['CLOTHES'])-1)
        hat = random.randint(0, len(CUSTOM_COLORS['HAT'])-1)
        
        e.add_component(Role(main_role=role, sub_role=sub_role,
                             skin_idx=skin, clothes_idx=clothes, hat_idx=hat))
                             
        e.add_component(Graphics())
        e.add_component(Physics())
        e.add_component(AIBrain()) # NPC는 AI 두뇌 가짐
        e.add_component(Interaction()) # NPC도 문 열기 등 상호작용 가능
        
        return e
