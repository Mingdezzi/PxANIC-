import pygame
from .event_bus import EventBus
from .resource_manager import ResourceManager
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS

class GameEngine:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("PIXELNIGHT")
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Core Modules
        self.event_bus = EventBus()
        self.resource_manager = ResourceManager.get_instance()
        
        # State Machine (추후 구현될 states 패키지에서 주입)
        self.state_machine = None 

    def set_state_machine(self, state_machine):
        self.state_machine = state_machine

    def run(self):
        if not self.state_machine:
            raise Exception("State Machine not initialized!")

        while self.running:
            dt = self.clock.tick(FPS)
            self._handle_events()
            self._update(dt)
            self._draw()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # UI Manager 등으로 이벤트 전달
            if self.state_machine and self.state_machine.current_state:
                self.state_machine.current_state.handle_event(event)

    def _update(self, dt):
        if self.state_machine:
            self.state_machine.update(dt)

    def _draw(self):
        self.screen.fill((0, 0, 0)) # Default Clear Color
        
        if self.state_machine:
            self.state_machine.draw(self.screen)
            
        pygame.display.flip()