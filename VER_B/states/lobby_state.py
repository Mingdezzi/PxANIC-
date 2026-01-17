import pygame
from core.base_state import BaseState
from managers.resource_manager import ResourceManager
from systems.network import NetworkManager
from colors import COLORS
from settings import MAX_PLAYERS, MAX_SPECTATORS, MAX_TOTAL_USERS, NETWORK_PORT, DEFAULT_PHASE_DURATIONS

class LobbyState(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.resource_manager = ResourceManager.get_instance()
        self.font = self.resource_manager.get_font('default')
        self.bold_font = self.resource_manager.get_font('bold')
        self.large_font = self.resource_manager.get_font('large')
        self.lobby_buttons = {}
        
        # Network Instance (Create if not exists)
        if not hasattr(self.game, 'network'):
            self.game.network = NetworkManager()

        self.participants = [] # Synced from Server
        self.my_id = -1
        self.time_scale = 100 # Percentage

    def enter(self, params=None):
        print("[LOBBY] Connecting to server...")
        if not self.game.network.connected:
            if self.game.network.connect():
                print("[LOBBY] Success!")
            else:
                print("[LOBBY] Failed. Playing Offline.")
                # Fallback to local (Add local player)
                self.participants = [{'id': 0, 'name': 'Player 1', 'role': 'CITIZEN', 'group': 'PLAYER', 'type': 'PLAYER'}]
                self.game.shared_data['participants'] = self.participants
                return

    def update(self, dt):
        if not self.game.network.connected: return

        events = self.game.network.get_events()
        for e in events:
            ptype = e.get('type')
            
            if ptype == 'WELCOME':
                self.my_id = e.get('my_id')
                self.game.network.my_id = self.my_id
                print(f"[LOBBY] My ID is {self.my_id}")

            elif ptype == 'PLAYER_LIST':
                self.participants = e.get('participants', [])
                self.game.shared_data['participants'] = self.participants

            elif ptype == 'GAME_START':
                print("[LOBBY] Game Starting!")
                # Apply Time Scale (Server should actually handle this, but for now we trust host config)
                scale = self.time_scale / 100.0
                custom = {}
                for k, v in DEFAULT_PHASE_DURATIONS.items():
                    custom[k] = int(v * scale)
                self.game.shared_data['custom_durations'] = custom
                
                from states.play_state import PlayState
                self.game.state_machine.change(PlayState(self.game))

    def draw(self, screen):
        screen.fill(COLORS['MENU_BG'])
        w, h = screen.get_width(), screen.get_height()
        mx, my = pygame.mouse.get_pos()
        self.lobby_buttons = {}

        # Title
        title = self.large_font.render(f"LOBBY - Connected: {len(self.participants)}", True, (100, 255, 100))
        screen.blit(title, (50, 40))

        # --- [Player List] ---
        start_y = 100
        # Filter participants by group if we had groups, but current server impl sends flat list. 
        # For full restore, we need server to support groups/types. 
        # Assuming server logic is basic, we just list them.
        
        # But wait, we need to restore the UI layout (Left: Players, Right: Spectators)
        # We will split local list for display
        player_group = [p for p in self.participants if p.get('group', 'PLAYER') == 'PLAYER']
        spectator_group = [p for p in self.participants if p.get('group') == 'SPECTATOR']

        # Left Area (Players)
        left_area_x = 50
        for i, p in enumerate(player_group):
            rect = pygame.Rect(left_area_x, start_y + i*60, 500, 50)
            is_me = (p.get('id') == self.my_id)
            color = (50, 50, 70) if is_me else COLORS['SLOT_BG']
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (100, 100, 120), rect, 1)

            p_str = f"{p['name']} (ID: {p.get('id', '?')})"
            txt = self.font.render(p_str, True, (255, 255, 255))
            screen.blit(txt, (rect.x + 20, rect.y + 15))

            if is_me:
                role_rect = pygame.Rect(rect.right - 120, rect.y + 10, 100, 30)
                pygame.draw.rect(screen, COLORS['ROLE_BTN'], role_rect)
                role_txt = self.font.render(p.get('role', 'CITIZEN'), True, (255, 255, 0))
                screen.blit(role_txt, (role_rect.x + 10, role_rect.y + 5))
                self.lobby_buttons['MY_ROLE'] = role_rect
            else:
                role_txt = self.font.render(p.get('role', 'CITIZEN'), True, (200, 200, 200))
                screen.blit(role_txt, (rect.right - 110, rect.y + 15))

        # Add Bot Button (Host Only)
        if self.my_id == 0: # Host
            add_rect = pygame.Rect(left_area_x, start_y + len(player_group)*60, 180, 40)
            pygame.draw.rect(screen, COLORS['BUTTON'], add_rect)
            screen.blit(self.font.render("+ ADD BOT", True, (255, 255, 255)), (add_rect.x+20, add_rect.y+10))
            self.lobby_buttons['ADD_BOT_PLAYER'] = add_rect

        # Time Scale UI (Bottom Right)
        sx, sy = w - 450, h - 250
        pygame.draw.rect(screen, (30, 30, 40), (sx - 20, sy - 40, 420, 120))
        pygame.draw.rect(screen, (100, 100, 120), (sx - 20, sy - 40, 420, 120), 2)
        screen.blit(self.bold_font.render("TIME SETTINGS", True, (200, 200, 200)), (sx, sy - 30))
        screen.blit(self.font.render("TIME SCALE:", True, (255, 255, 255)), (sx, sy + 30))
        
        m_rect = pygame.Rect(sx + 150, sy + 25, 30, 30)
        pygame.draw.rect(screen, COLORS['BUTTON'], m_rect)
        screen.blit(self.bold_font.render("-", True, (255,255,255)), (m_rect.x+10, m_rect.y+5))
        self.lobby_buttons["SCALE_MINUS"] = m_rect

        val_txt = self.large_font.render(f"{self.time_scale}%", True, (0, 255, 0))
        screen.blit(val_txt, (sx + 200, sy + 20))

        p_rect = pygame.Rect(sx + 300, sy + 25, 30, 30)
        pygame.draw.rect(screen, COLORS['BUTTON'], p_rect)
        screen.blit(self.bold_font.render("+", True, (255,255,255)), (p_rect.x+8, p_rect.y+5))
        self.lobby_buttons["SCALE_PLUS"] = p_rect

        # Start Button
        if self.my_id == 0 or not self.game.network.connected:
            start_rect = pygame.Rect(w - 250, h - 100, 200, 60)
            pygame.draw.rect(screen, (0, 150, 0), start_rect)
            st_txt = self.large_font.render("START GAME", True, (255, 255, 255))
            screen.blit(st_txt, (start_rect.x + 20, start_rect.y + 10))
            self.lobby_buttons['START'] = start_rect
        else:
            msg = self.font.render("Waiting for Host...", True, (150, 150, 150))
            screen.blit(msg, (w - 250, h - 80))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                
                if 'START' in self.lobby_buttons and self.lobby_buttons['START'].collidepoint(mx, my):
                    # Save Time Scale locally first
                    scale = self.time_scale / 100.0
                    custom = {}
                    for k, v in DEFAULT_PHASE_DURATIONS.items():
                        custom[k] = int(v * scale)
                    self.game.shared_data['custom_durations'] = custom

                    if self.game.network.connected:
                        self.game.network.send_start_game()
                    else:
                        from states.play_state import PlayState
                        self.game.state_machine.change(PlayState(self.game))

                if 'MY_ROLE' in self.lobby_buttons and self.lobby_buttons['MY_ROLE'].collidepoint(mx, my):
                    roles = ["CITIZEN", "MAFIA", "POLICE", "DOCTOR"]
                    curr_role = "CITIZEN"
                    for p in self.participants:
                        if p.get('id') == self.my_id:
                            curr_role = p.get('role', 'CITIZEN')
                            break
                    try:
                        next_idx = (roles.index(curr_role) + 1) % len(roles)
                        new_role = roles[next_idx]
                        if self.game.network.connected:
                            self.game.network.send_role_change(new_role)
                        else:
                            # Offline
                            self.participants[0]['role'] = new_role
                    except: pass

                if 'SCALE_MINUS' in self.lobby_buttons and self.lobby_buttons['SCALE_MINUS'].collidepoint(mx, my):
                    self.time_scale = max(10, self.time_scale - 10)
                
                if 'SCALE_PLUS' in self.lobby_buttons and self.lobby_buttons['SCALE_PLUS'].collidepoint(mx, my):
                    self.time_scale = min(500, self.time_scale + 10)

                # Add Bot (Offline/Online handling)
                if 'ADD_BOT_PLAYER' in self.lobby_buttons and self.lobby_buttons['ADD_BOT_PLAYER'].collidepoint(mx, my):
                    if not self.game.network.connected:
                        if len(self.participants) < MAX_TOTAL_USERS:
                            self.participants.append({'id': len(self.participants), 'name': f'Bot {len(self.participants)}', 'role': 'RANDOM', 'group': 'PLAYER', 'type': 'BOT'})
                    else:
                        # Request Server to add a bot
                        self.game.network.send_add_bot()