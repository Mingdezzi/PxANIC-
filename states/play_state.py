import pygame
import random
from .base_state import BaseState
from settings import SCREEN_WIDTH, SCREEN_HEIGHT
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
        
        self.map_manager = MapManager()
        self.map_manager.load_map("map.json")
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        self.entities = []
        self.player = None
        
        # [복구] 채팅 및 뉴스 시스템 변수
        self.is_chatting = False
        self.chat_text = ""
        self.daily_news_log = []
        
        # Systems
        self.input_system = InputSystem(engine.event_bus)
        self.movement_system = MovementSystem()
        self.render_system = RenderSystem(self.map_manager) # [Fix] map_manager 전달
        self.ai_system = AISystem(self.map_manager)
        self.time_system = TimeSystem(engine.event_bus)
        self.interaction_system = InteractionSystem(engine.event_bus, self.map_manager, None)
        self.interaction_system.time_system = self.time_system # [Fix] Inject TimeSystem
        self.combat_system = CombatSystem(engine.event_bus, self.map_manager)
        self.sound_system = SoundSystem()
        self.stats_system = StatsSystem(engine.event_bus) # [New]
        self.weather_system = WeatherSystem()
        self.minigame_system = MiniGameSystem(engine.event_bus)
        
        self.ui_manager = UIManager(engine.event_bus, None, self.map_manager)
        self.interaction_system.ui_manager = self.ui_manager

        # Event Binding
        engine.event_bus.subscribe("PLAY_SOUND", self._on_play_sound)
        engine.event_bus.subscribe("PHASE_CHANGED", self._on_phase_changed)
        engine.event_bus.subscribe("VOTE_CAST", self._on_vote_cast)
        engine.event_bus.subscribe("SHOW_ALERT", lambda d: self.ui_manager.popup.show_alert(d['text'], d.get('color')))

    def enter(self, participants=None):
        # ... (엔티티 생성 로직은 기존 코드 유지)
        self.entities.clear()
        
        # 1. Spawn Points
        spawn_points = self.map_manager.get_spawn_points()
        
        # 2. Create Entities from Participants
        if not participants:
            # Fallback for testing
            participants = [{'name': 'Player 1', 'type': 'PLAYER', 'role': 'CITIZEN', 'group': 'PLAYER'}]
            for i in range(5):
                participants.append({'name': f'NPC_{i}', 'type': 'BOT', 'role': 'CITIZEN', 'group': 'PLAYER'})
        
        random.shuffle(spawn_points)
        spawn_idx = 0
        
        for p in participants:
            if p['group'] == 'SPECTATOR':
                sx, sy = 0, 0
                player = EntityFactory.create_player(sx, sy, role="SPECTATOR")
                player.name = p['name']
                player.physics.no_clip = True
                self.entities.append(player)
                if p['type'] == 'PLAYER': self.player = player
                continue

            if spawn_idx < len(spawn_points):
                sx, sy = spawn_points[spawn_idx]
                spawn_idx += 1
            else:
                sx, sy = self.map_manager.spawn_x, self.map_manager.spawn_y

            role = p['role']
            if role == 'RANDOM':
                role = random.choice(['CITIZEN', 'DOCTOR', 'POLICE', 'MAFIA'])
            
            if p['type'] == 'PLAYER':
                self.player = EntityFactory.create_player(sx, sy, role=role)
                self.player.name = p['name']
                self.entities.append(self.player)
            else:
                npc = EntityFactory.create_npc(sx, sy, name=p['name'], role=role)
                self.entities.append(npc)
        
        # [복구] 테스트용 플레이어 생성 (참가자 없으면)
        if not self.player:
            self.player = EntityFactory.create_player(200, 200, role="CITIZEN")
            self.entities.append(self.player)

        self.ui_manager.player = self.player
        self.ui_manager.inventory_window.player = self.player
        self.ui_manager.shop_window.player = self.player

    def update(self, dt):
        if self.is_chatting: return # 채팅 중엔 게임 정지 (선택 사항)

        self.time_system.update(dt)
        self.input_system.process(self.player)
        
        keys = pygame.key.get_pressed()
        self.interaction_system.process(self.player, keys)
        
        # [복구] StatsSystem 호출 (Dead Code 부활)
        self.stats_system.update(dt, self.entities, self.player, self.time_system.is_blackout, self.time_system.current_phase)
        
        self.ai_system.update(dt, self.entities, self.player, self.time_system.get_state_data())
        
        self.weather_system.update(dt, 'RAIN' if self.time_system.day_count % 3 == 0 else 'CLEAR')
        current_weather = self.weather_system.current_weather
        
        self.movement_system.update(dt, self.entities, self.map_manager, weather_type=current_weather)
        self.combat_system.update(dt, self.entities)
        self.sound_system.update(dt)
        self.minigame_system.update(dt)
        self.ui_manager.update(dt)
        self.camera.update(self.player)
        
        active_rects = [e.transform.rect for e in self.entities if e.stats.alive]
        self.map_manager.update_doors(dt, active_rects)

    def draw(self, screen):
        self.render_system.draw(screen, self.camera, self.entities, self.map_manager, self.time_system.current_phase, self.player)
        self.weather_system.draw(screen)
        self.sound_system.draw(screen, self.camera, listener_role=self.player.role.main_role) # [Fix] listener_role 전달
        
        game_state = self.time_system.get_state_data()
        game_state['npcs'] = [e for e in self.entities if e != self.player]
        self.ui_manager.draw(screen, game_state)
        self.minigame_system.draw(screen, self.player)

        # [복구] 채팅 UI 렌더링
        if self.is_chatting:
            chat_bg = pygame.Surface((SCREEN_WIDTH, 40))
            chat_bg.fill((0, 0, 0))
            chat_bg.set_alpha(200)
            screen.blit(chat_bg, (0, SCREEN_HEIGHT - 40))
            
            font = pygame.font.SysFont("arial", 24)
            txt_surf = font.render(f"Chat: {self.chat_text}", True, (255, 255, 255))
            screen.blit(txt_surf, (10, SCREEN_HEIGHT - 35))

    def handle_event(self, event):
        # [복구] 채팅 입력 처리
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.is_chatting = not self.is_chatting
            if not self.is_chatting and self.chat_text.strip():
                self.ui_manager.popup.show_alert(f"Chat: {self.chat_text}")
                self.chat_text = ""
            return

        if self.is_chatting:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE: self.chat_text = self.chat_text[:-1]
                else: self.chat_text += event.unicode
            return

        if self.minigame_system.handle_event(event): return
        
        game_state = self.time_system.get_state_data()
        game_state['npcs'] = [e for e in self.entities if e != self.player]
        if self.ui_manager.handle_event(event, game_state): return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: # 특수 스킬 (R)
                 self.interaction_system.handle_special_key(self.player, pygame.K_r)
            elif event.key == pygame.K_v: # 특수 액션 (V) - 힐/스턴
                 self.combat_system.handle_heal(self.player, self.interaction_system.get_nearest_target(self.player, self.entities))

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # 마우스 공격 (거리 기반 자동 타겟팅)
                target = self.interaction_system.get_nearest_target(self.player, self.entities)
                self.combat_system.handle_attack(self.player, target)

    def _on_play_sound(self, data):
        self.sound_system.play_sound(data['name'], data.get('x'), data.get('y'), data.get('role', 'UNKNOWN'))

    def _on_phase_changed(self, data):
        self.ui_manager.popup.show_alert(f"Phase: {data['new_phase']}")
        
        # [복구] MORNING 페이즈 진입 시 정산 (Morning Process)
        if data['new_phase'] == 'MORNING':
            self._handle_morning_process()
        
        # [복구] 투표 결과 처리 (AFTERNOON -> EVENING 전환 시)
        if data['old_phase'] == 'AFTERNOON':
            self._process_voting_results()

    def _handle_morning_process(self):
        # 1. 플레이어 정산
        if self.player and self.player.stats.alive:
            # 구버전: 집 안인지 확인 (여기서는 간단히 HP 회복으로 대체하거나 Zone 체크 필요)
            self.player.stats.hp = min(self.player.stats.max_hp, self.player.stats.hp + 10)
            self.player.stats.ap = self.player.stats.max_ap
            
            # 작업량 체크 및 페널티
            if self.player.role.daily_work_count < 3: # 기준값
                self.player.stats.hp -= 10
                self.ui_manager.popup.show_alert("Work Quota Failed! (-10 HP)", (255, 50, 50))
            
            self.player.role.daily_work_count = 0
            
        # 2. 뉴스 생성 (CombatSystem 등에서 모은 로그 활용)
        # (EventBus를 통해 뉴스 로그를 모으는 별도 시스템이 없다면 여기서 임시 생성)
        news_logs = []
        if hasattr(self, 'daily_news_log'): # daily_news_buffer -> daily_news_log (일관성 유지)
             news_logs.extend(self.daily_news_log)
             self.daily_news_log = []
        
        if news_logs:
            # UI 매니저에 show_news 메서드 필요 (없으면 팝업으로 대체)
            if hasattr(self.ui_manager, 'show_news'):
                self.ui_manager.show_news(news_logs)
            else:
                for log in news_logs:
                    self.ui_manager.popup.show_alert(f"NEWS: {log}")

    def _on_vote_cast(self, data):
        target = data.get('target')
        if target:
            if not hasattr(target, 'vote_count'): target.vote_count = 0
            target.vote_count += 1
            self.ui_manager.popup.show_alert(f"Voted for {target.name}")

    def _process_voting_results(self):
        # [복구] 투표 집계 및 처형 로직
        candidates = [e for e in self.entities if e.stats.alive]
        # vote_count 속성이 없는 경우 대비
        for c in candidates: 
            if not hasattr(c, 'vote_count'): c.vote_count = 0
            
        candidates.sort(key=lambda x: x.vote_count, reverse=True)
        
        if candidates and candidates[0].vote_count >= 2:
            victim = candidates[0]
            victim.stats.alive = False # 처형
            
            msg = f"EXECUTION: {victim.name} ({victim.role.main_role})"
            self.daily_news_log.append(msg)
            self.ui_manager.popup.show_alert(msg, (255, 0, 0))
            self.sound_system.play_sound("EXECUTION!", victim.transform.x, victim.transform.y, "SYSTEM")
            
        # 초기화
        for c in candidates: c.vote_count = 0