from enum import Enum, auto

class BTState(Enum):
    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()

class BTNode:
    def tick(self, entity, blackboard): return BTState.FAILURE

class Composite(BTNode):
    def __init__(self, children=None): self.children = children or []

class Selector(Composite):
    def tick(self, entity, blackboard):
        for child in self.children:
            status = child.tick(entity, blackboard)
            if status != BTState.FAILURE: return status
        return BTState.FAILURE

class Sequence(Composite):
    def tick(self, entity, blackboard):
        for child in self.children:
            status = child.tick(entity, blackboard)
            if status == BTState.FAILURE: return BTState.FAILURE
            if status == BTState.RUNNING: return BTState.RUNNING
        return BTState.SUCCESS

class Action(BTNode):
    def __init__(self, action_func): self.action_func = action_func
    def tick(self, entity, blackboard): return self.action_func(entity, blackboard)

class Condition(BTNode):
    def __init__(self, condition_func): self.condition_func = condition_func
    def tick(self, entity, blackboard): return BTState.SUCCESS if self.condition_func(entity, blackboard) else BTState.FAILURE
