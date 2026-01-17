class ECSManager:
    """
    Entity-Component-System 관리자
    엔티티 생성/삭제, 컴포넌트 관리, 시스템 업데이트를 담당합니다.
    """
    def __init__(self):
        self.next_entity_id = 0
        self.entities = set()
        self.components = {} # {component_type: {entity_id: component_instance}}
        self.systems = []
        self.entities_to_destroy = []

    def create_entity(self):
        entity_id = self.next_entity_id
        self.next_entity_id += 1
        self.entities.add(entity_id)
        return entity_id

    def destroy_entity(self, entity_id):
        if entity_id in self.entities:
            self.entities_to_destroy.append(entity_id)

    def add_component(self, entity_id, component):
        comp_type = type(component)
        if comp_type not in self.components:
            self.components[comp_type] = {}
        self.components[comp_type][entity_id] = component

    def get_component(self, entity_id, component_type):
        if component_type in self.components:
            return self.components[component_type].get(entity_id)
        return None
    
    def has_component(self, entity_id, component_type):
        if component_type in self.components:
            return entity_id in self.components[component_type]
        return False

    def remove_component(self, entity_id, component_type):
        if component_type in self.components:
            if entity_id in self.components[component_type]:
                del self.components[component_type][entity_id]

    def get_entities_with(self, *component_types):
        """
        주어진 컴포넌트 타입들을 모두 가진 엔티티 ID 리스트를 반환합니다.
        """
        if not component_types:
            return []
        
        first_type = component_types[0]
        if first_type not in self.components:
            return []
            
        # 첫 번째 컴포넌트를 가진 엔티티 집합으로 시작
        candidates = set(self.components[first_type].keys())
        
        # 나머지 컴포넌트들과 교집합 연산
        for c_type in component_types[1:]:
            if c_type not in self.components:
                return []
            candidates &= set(self.components[c_type].keys())
            
        return list(candidates)

    def add_system(self, system):
        self.systems.append(system)

    def update(self, dt):
        # 삭제 예정 엔티티 처리
        if self.entities_to_destroy:
            for entity_id in self.entities_to_destroy:
                self._actually_destroy_entity(entity_id)
            self.entities_to_destroy.clear()

        # 시스템 업데이트
        for system in self.systems:
            system.update(dt)

    def _actually_destroy_entity(self, entity_id):
        if entity_id in self.entities:
            self.entities.remove(entity_id)
            # 모든 컴포넌트 저장소에서 해당 엔티티 데이터 삭제
            for comp_type in self.components:
                if entity_id in self.components[comp_type]:
                    del self.components[comp_type][entity_id]
