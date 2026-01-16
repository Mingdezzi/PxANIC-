import pygame
from .base_state import BaseState
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from world.map_manager import MapManager
from world.camera import Camera
from entities.factory import EntityFactory
from systems.input_system import InputSystem
from systems.movement_system import MovementSystem
from systems.render_system import RenderSystem
from systems.ai_system import AISystem
from systems.time_system import TimeSystem
from systems.interaction_system import InteractionSystem
from systems.combat_system import CombatSystem
from systems.sound_system import SoundSystem
from systems.stats_system import StatsSystem
from systems.weather_system import WeatherSystem
from systems.minigame_system import MiniGameSystem
from ui.ui_manager import UIManager

class PlayState(BaseState):
    def __init__(self, engine):
        super().__init__(engine)
        
        # 1. World & Camera
        self.map_manager = MapManager()
        self.map_manager.load_map("map.json")
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # 2. Entities
        self.entities = []
        self.player = None
        self._init_entities()
        
        # 3. Systems
        self.input_system = InputSystem(engine.event_bus)
        self.movement_system = MovementSystem()
        self.render_system = RenderSystem()
        self.ai_system = AISystem(self.map_manager)
        self.time_system = TimeSystem(engine.event_bus)
        self.interaction_system = InteractionSystem(engine.event_bus, self.map_manager, None) # UI Manager는 아래에서 주입
        self.combat_system = CombatSystem(engine.event_bus, self.map_manager)
        self.sound_system = SoundSystem()
        
        # [New Systems]
        self.stats_system = StatsSystem(engine.event_bus)
        self.weather_system = WeatherSystem()
        self.minigame_system = MiniGameSystem(engine.event_bus)
        
        # 4. UI
        self.ui_manager = UIManager(engine.event_bus, self.player, self.map_manager)
        self.interaction_system.ui_manager = self.ui_manager # 상호 참조 해결

        # 5. Event Binding
        engine.event_bus.subscribe("PLAY_SOUND", self._on_play_sound)
        engine.event_bus.subscribe("PHASE_CHANGED", self._on_phase_changed)
        engine.event_bus.subscribe("ENTITY_DIED", self._on_entity_died)
        engine.event_bus.subscribe("VOTE_CAST", self._on_vote_cast)

    def enter(self, participants=None):
        self.entities.clear()
        
        # 1. Spawn Points
        spawn_points = self.map_manager.get_spawn_points()
        
        # 2. Create Entities from Participants
        if not participants:
            # Fallback for testing
            participants = [{'name': 'Player 1', 'type': 'PLAYER', 'role': 'CITIZEN', 'group': 'PLAYER'}]
            for i in range(5):
                participants.append({'name': f'NPC_{i}', 'type': 'BOT', 'role': 'CITIZEN', 'group': 'PLAYER'})
        
        import random
        random.shuffle(spawn_points)
        spawn_idx = 0
        
        for p in participants:
            if p['group'] == 'SPECTATOR':
                # Create Spectator Entity
                sx, sy = 0, 0 # Spectator pos doesn't matter much
                player = EntityFactory.create_player(sx, sy, role="SPECTATOR")
                player.name = p['name']
                player.physics.no_clip = True
                self.entities.append(player)
                if p['type'] == 'PLAYER': self.player = player
                continue

            # Assign Spawn Point
            if spawn_idx < len(spawn_points):
                sx, sy = spawn_points[spawn_idx]
                spawn_idx += 1
            else:
                sx, sy = self.map_manager.spawn_x, self.map_manager.spawn_y

            # Determine Role
            role = p['role']
            if role == 'RANDOM':
                role = random.choice(['CITIZEN', 'DOCTOR', 'POLICE', 'MAFIA'])
            
            # Create Entity
            if p['type'] == 'PLAYER':
                self.player = EntityFactory.create_player(sx, sy, role=role)
                self.player.name = p['name']
                self.entities.append(self.player)
            else:
                npc = EntityFactory.create_npc(sx, sy, name=p['name'], role=role)
                self.entities.append(npc)

        # UI Manager Re-init with new player
        self.ui_manager.player = self.player
        self.ui_manager.inventory_window.player = self.player
        self.ui_manager.shop_window.player = self.player

    def _init_entities(self):
        pass # Moved to enter()

    def update(self, dt):
        # 1. System Updates
        self.time_system.update(dt)
        self.input_system.process(self.player)
        
        # 키 입력 상태를 매 프레임 전달 (E키 홀드, 이동 등)
        keys = pygame.key.get_pressed()
        self.interaction_system.process(self.player, keys)
        
        # [New] Stats Update (Emotion, Stamina)
        self.stats_system.update(dt, self.entities, self.player, self.time_system.is_blackout, self.time_system.current_phase)
        
        # AI Update (NPCs only)
        self.ai_system.update(dt, self.entities, self.player, self.time_system.get_state_data())
        
        # Physics Update
        # [New] Weather Update
        self.weather_system.update(dt, 'RAIN' if self.time_system.day_count % 3 == 0 else 'CLEAR')
        current_weather = self.weather_system.current_weather
        
        self.movement_system.update(dt, self.entities, self.map_manager, weather_type=current_weather)
        
        # Combat & Interaction & Minigame
        self.combat_system.update(dt, self.entities)
        self.sound_system.update(dt)
        self.minigame_system.update(dt)
        
        # UI Update
        self.ui_manager.update(dt)
        
        # Camera Update
        self.camera.update(self.player)
        
        # Map Logic (Doors auto close etc)
        # collidelist를 위해 rect 리스트 생성
        active_rects = [e.transform.rect for e in self.entities if e.stats.alive]
        self.map_manager.update_doors(dt, active_rects)

    def draw(self, screen):
        # 1. Render World & Entities
        self.render_system.draw(screen, self.camera, self.entities, self.map_manager, 
                                self.time_system.current_phase, self.player)
        
        # [New] Render Weather
        self.weather_system.draw(screen)
        
        # 2. Render Visual Sounds
        self.sound_system.draw(screen, self.camera)
        
        # 3. Render UI
        game_state = self.time_system.get_state_data()
        game_state['npcs'] = [e for e in self.entities if e != self.player]
        game_state['weather'] = self.weather_system.current_weather
        
        self.ui_manager.draw(screen, game_state)
        
        # [New] Render Minigame
        self.minigame_system.draw(screen, self.player)

    def handle_event(self, event):
        # [New] Minigame Input Priority
        if self.minigame_system.handle_event(event):
            return

        # UI 이벤트 우선 처리
        game_state = self.time_system.get_state_data()
        game_state['npcs'] = [e for e in self.entities if e != self.player]
        
        if self.ui_manager.handle_event(event, game_state):
            return

        # R키 (InteractionSystem으로 전달하거나 여기서 처리)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
             # 재장전 또는 특수 기능
             self.interaction_system.handle_special_key(self.player, pygame.K_r)

        # Player Interaction Keys (Moved to update loop)
        # self.interaction_system.process(self.player, pygame.key.get_pressed())
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left Click Attack
                # 마우스 좌표를 월드 좌표로 변환
                # mx, my = event.pos
                # wx = mx + self.camera.x
                # wy = my + self.camera.y
                # self.combat_system.handle_attack(self.player, target_at=(wx, wy))
                self.combat_system.handle_attack(self.player, None) # 근접/타겟팅 방식에 따라 수정 필요

    def _on_play_sound(self, data):
        self.sound_system.play_sound(data['name'], data.get('x'), data.get('y'))

    def _on_phase_changed(self, data):
        # 페이즈 변경 시 알림
        self.ui_manager.popup.show_alert(f"Phase Changed: {data['new_phase']}")

    def _on_entity_died(self, data):
        # 사망 처리 (필요시)
        pass

    def _on_vote_cast(self, data):
        target = data.get('target')
        if not target: return
        
        # 투표 수 증가 (Role 컴포넌트에 vote_count 필드 필요 -> 없으면 추가하거나 Stats에 임시 저장)
        # Role 데이터클래스는 수정하기 번거로우므로, 여기서는 동적 속성으로 처리
        if not hasattr(target, 'vote_count'):
            target.vote_count = 0
        target.vote_count += 1
        
        self.ui_manager.popup.show_alert(f"Voted for {target.name}", (255, 255, 0))
        
        # 투표 결과 처리 로직 (모두 투표했거나 시간이 다 되었을 때)
        # 여기서는 즉시 처형하지 않고, TimeSystem의 페이즈 종료 시 처리를 권장.
        # 일단 알림만 띄움.
