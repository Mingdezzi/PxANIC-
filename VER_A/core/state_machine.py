class StateMachine:
    def __init__(self, game):
        self.game = game
        self.stack = []

    def push(self, state):
        if self.stack:
            self.stack[-1].exit()
        self.stack.append(state)
        state.enter()

    def pop(self):
        if self.stack:
            state = self.stack.pop()
            state.exit()
            if self.stack:
                self.stack[-1].enter()
            return state
        return None

    def change(self, state, params=None):
        while self.stack:
            self.stack.pop().exit()
        self.stack.append(state)
        state.enter(params)

    def update(self, dt):
        if self.stack:
            self.stack[-1].update(dt)

    def draw(self, screen):
        if self.stack:
            self.stack[-1].draw(screen)

    def handle_event(self, event):
        if self.stack:
            self.stack[-1].handle_event(event)
