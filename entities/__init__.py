import uuid
from typing import Dict, Type, TypeVar, Optional, Any

T = TypeVar('T')

class Entity:
    def __init__(self, name="Entity", uid=None):
        self.uid = uid if uid else str(uuid.uuid4())
        self.name = name
        self.components: Dict[Type, Any] = {}
    
    def add_component(self, component: Any):
        self.components[type(component)] = component
        # 편의를 위해 소문자 클래스명으로 속성 접근 가능하게 함 (예: entity.transform)
        # 단, 이미 존재하는 속성은 덮어쓰지 않음
        name = type(component).__name__.lower()
        if not hasattr(self, name):
            setattr(self, name, component)
            
    def get_component(self, component_type: Type[T]) -> Optional[T]:
        return self.components.get(component_type)
        
    def has_component(self, component_type: Type) -> bool:
        return component_type in self.components