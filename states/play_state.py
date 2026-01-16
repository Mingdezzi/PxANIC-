import pygame
from core.base_state import BaseState
from core.ecs_manager import ECSManager
from core.event_bus import EventBus
from core.game_state_manager import GameStateManager
from world.map_manager import MapManager
from systems import (
    InputSystem, MovementSystem, TimeSystem, AISystem, 
    InteractionSystem, SoundSystem, RenderSystem, MiniGameSystem
)
from entities.factory import EntityFactory
from ui.ui_manager import UIManager
from systems.camera import Camera
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

class PlayState(BaseState):
    def __init__(self, game):
        super().__init__(game)
        
        # 1. Core Modules
        self.event_bus = EventBus()
        self.game_state = GameStateManager.get_instance()
        self.game_state.reset() # State reset
        self.ecs = ECSManager()
        self.map_manager = MapManager()
        
        # 2. Map Load
        self.map_manager.load_map("map.json")
        
        # 3. Camera
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, self.map_manager.width, self.map_manager.height)
        self.camera.set_zoom(1.5)
        
        # 4. Systems Initialization
        self.time_system = TimeSystem(self.ecs, self.event_bus, self.map_manager)
        self.input_system = InputSystem(self.ecs, self.event_bus)
        self.movement_system = MovementSystem(self.ecs, self.map_manager)
        self.movement_system.event_bus = self.event_bus # Inject EventBus manually as __init__ changed
        self.ai_system = AISystem(self.ecs, self.event_bus, self.map_manager)
        self.interaction_system = InteractionSystem(self.ecs, self.event_bus, self.map_manager)
        self.sound_system = SoundSystem(self.ecs, self.event_bus)
        self.minigame_system = MiniGameSystem(self.ecs, self.event_bus)
        self.render_system = RenderSystem(self.ecs, self.map_manager, self.camera)
        
        self.ui_manager = UIManager(self.ecs, self.event_bus, self.map_manager)
        
        # Register Systems to ECS (Update Order Matters!)
        self.ecs.add_system(self.time_system)
        self.ecs.add_system(self.minigame_system) # 미니게임 로직
        self.ecs.add_system(self.input_system)
        self.ecs.add_system(self.ai_system)
        self.ecs.add_system(self.interaction_system)
        self.ecs.add_system(self.movement_system)
        self.ecs.add_system(self.sound_system)
        # Render & UI are drawn separately
        
        # 5. Entity Creation
        self.factory = EntityFactory(self.ecs)
        self._init_entities()

    def _init_entities(self):
        participants = self.game.shared_data.get('participants', [])
        spawn_points = self.map_manager.get_spawn_points()
        
        # Player
        my_data = next((p for p in participants if p['type'] == 'PLAYER'), None)
        if my_data:
            sx, sy = spawn_points[0] if spawn_points else (100, 100)
            self.factory.create_player(sx, sy, name=my_data['name'], role=my_data['role'])
            
        # NPCs
        for i, p in enumerate(participants):
            if p['type'] == 'BOT':
                sx, sy = spawn_points[(i+1) % len(spawn_points)] if spawn_points else (100+i*32, 100)
                self.factory.create_npc(sx, sy, name=p['name'], role=p['role'])

    def update(self, dt):
        # ECS Update Loop
        self.ecs.update(dt)
        self.ui_manager.update(dt)
        
        # Camera Update (Follow Player)
        # 단순화를 위해 RenderSystem 내부 혹은 여기서 직접 처리
        from components.identity import Identity
        from components.common import Transform
        
        players = [e for e in self.ecs.get_entities_with(Identity, Transform) 
                  if self.ecs.get_component(e, Identity).is_player]
        if players:
            p_trans = self.ecs.get_component(players[0], Transform)
            self.camera.update(p_trans.x + 16, p_trans.y + 16)

    def draw(self, screen):
        # 1. World & Entities & Lighting
        # TimeSystem에서 계산된 조명 값을 전달
        phase = self.time_system.current_phase
        is_blackout = self.game_state.is_blackout
        
        # Update RenderSystem state
        self.render_system.ambient_alpha = self.time_system.current_ambient_alpha
        self.render_system.vision_factor = self.time_system.current_vision_factor
        self.render_system.clarity = self.time_system.current_clarity
        
        self.render_system.draw(screen, phase, is_blackout)
        
        # 2. Sound Visuals
        self.sound_system.draw(screen, self.camera)
        
        # 3. UI
        self.ui_manager.draw(screen)
        
        # 4. Minigame Overlay
        # 중앙 좌표 계산
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        self.minigame_system.draw(screen, cx, cy)

    def handle_event(self, event):
        # Minigame Input Priority
        if self.minigame_system.active:
            self.minigame_system.handle_event(event)
            return

        # UI Input Priority
        self.ui_manager.handle_input(event)
        
        # ECS Input (Event driven parts)
        # InputSystem handles polling in update(), but we can pass events if needed
        pass
