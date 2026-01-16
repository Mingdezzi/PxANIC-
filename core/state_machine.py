class StateMachine:
    def __init__(self):
        self.states = {}
        self.current_state = None

    def add_state(self, name, state):
        self.states[name] = state

    def change_state(self, name, **kwargs):
        if self.current_state:
            self.current_state.exit()
        
        self.current_state = self.states.get(name)
        
        if self.current_state:
            self.current_state.enter(**kwargs)

    def update(self, dt):
        if self.current_state:
            self.current_state.update(dt)

    def draw(self, screen):
        if self.current_state:
            self.current_state.draw(screen)