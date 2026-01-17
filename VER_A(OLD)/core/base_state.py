class BaseState:
    def __init__(self, game):
        self.game = game

    def enter(self, params=None):
        pass

    def exit(self):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass

    def handle_event(self, event):
        pass
