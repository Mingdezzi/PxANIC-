class BaseState:
    def __init__(self, engine):
        self.engine = engine

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass

    def handle_event(self, event):
        pass
