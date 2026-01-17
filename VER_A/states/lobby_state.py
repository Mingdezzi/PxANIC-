import pygame
import random
from core.base_state import BaseState
from managers.resource_manager import ResourceManager
from colors import COLORS
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, MAX_PLAYERS, MAX_SPECTATORS, MAX_TOTAL_USERS, DEFAULT_PHASE_DURATIONS

class LobbyState(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.resource_manager = ResourceManager.get_instance()
        self.font = self.resource_manager.get_font('default')
        self.bold_font = self.resource_manager.get_font('bold')
        self.large_font = self.resource_manager.get_font('large')

        self.lobby_buttons = {}

        if 'participants' not in self.game.shared_data:
            self.game.shared_data['participants'] = [{'name': 'Player 1', 'type': 'PLAYER', 'role': 'RANDOM', 'group': 'PLAYER'}]
        self.participants = self.game.shared_data['participants']

        self.time_scale = 100  # Percentage (100 means 100% of DEFAULT_PHASE_DURATIONS)

    def enter(self, params=None):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        self.lobby_buttons = {}
        screen.fill(COLORS['MENU_BG'])
        w, h = screen.get_width(), screen.get_height()
        mx, my = pygame.mouse.get_pos()

        player_group = [p for p in self.participants if p['group'] == 'PLAYER']
        spectator_group = [p for p in self.participants if p['group'] == 'SPECTATOR']

        left_area_x = 50
        left_area_w = 600
        start_y = 100

        title = self.large_font.render(f"PLAYERS ({len(player_group)}/{MAX_PLAYERS})", True, (100, 255, 100))
        screen.blit(title, (left_area_x, 40))

        for i, p in enumerate(player_group):
            pidx = self.participants.index(p)
            rect_obj = pygame.Rect(left_area_x, start_y + i*55, left_area_w, 45)
            pygame.draw.rect(screen, COLORS['SLOT_BG'], rect_obj)
            pygame.draw.rect(screen, (100, 100, 120), rect_obj, 1)

            p_txt = self.font.render(f"{p['name']} [{p['type']}]", True, (255, 255, 255))
            screen.blit(p_txt, (rect_obj.x + 15, rect_obj.y + 10))

            role_rect = pygame.Rect(rect_obj.right - 180, rect_obj.y + 7, 100, 30)
            r_col = COLORS['BUTTON_HOVER'] if role_rect.collidepoint(mx, my) else COLORS['ROLE_BTN']
            pygame.draw.rect(screen, r_col, role_rect)
            role_txt = self.font.render(p['role'], True, (255, 255, 0))
            screen.blit(role_txt, role_txt.get_rect(center=role_rect.center))
            self.lobby_buttons[f"ROLE_{pidx}"] = (role_rect, pidx)

            if len(spectator_group) < MAX_SPECTATORS:
                move_rect = pygame.Rect(rect_obj.right - 50, rect_obj.y + 7, 40, 30)
                m_col = (100, 100, 100) if move_rect.collidepoint(mx, my) else (60, 60, 60)
                pygame.draw.rect(screen, m_col, move_rect)
                m_txt = self.bold_font.render("->", True, (200, 200, 200))
                screen.blit(m_txt, m_txt.get_rect(center=move_rect.center))
                self.lobby_buttons[f"TO_SPEC_{pidx}"] = move_rect

        if len(player_group) < MAX_PLAYERS:
            add_rect = pygame.Rect(left_area_x, start_y + len(player_group)*55, 180, 40)
            a_col = COLORS['BUTTON_HOVER'] if add_rect.collidepoint(mx, my) else COLORS['BUTTON']
            pygame.draw.rect(screen, a_col, add_rect)
            screen.blit(self.font.render("+ ADD PLAYER BOT", True, (255, 255, 255)), (add_rect.x+20, add_rect.y+8))
            self.lobby_buttons['ADD_BOT_PLAYER'] = add_rect

        right_area_x = left_area_x + left_area_w + 50
        right_area_w = 400

        title_spec = self.large_font.render(f"SPECTATORS ({len(spectator_group)}/{MAX_SPECTATORS})", True, (150, 150, 255))
        screen.blit(title_spec, (right_area_x, 40))

        for i, p in enumerate(spectator_group):
            pidx = self.participants.index(p)
            rect_obj = pygame.Rect(right_area_x, start_y + i*55, right_area_w, 45)
            pygame.draw.rect(screen, (30, 30, 40), rect_obj)
            pygame.draw.rect(screen, (100, 100, 120), rect_obj, 1)

            if len(player_group) < MAX_PLAYERS:
                move_rect = pygame.Rect(rect_obj.x + 10, rect_obj.y + 7, 40, 30)
                m_col = (100, 100, 100) if move_rect.collidepoint(mx, my) else (60, 60, 60)
                pygame.draw.rect(screen, m_col, move_rect)
                m_txt = self.bold_font.render("<-", True, (200, 200, 200))
                screen.blit(m_txt, m_txt.get_rect(center=move_rect.center))
                self.lobby_buttons[f"TO_PLAYER_{pidx}"] = move_rect

            p_txt = self.font.render(f"{p['name']} [{p['type']}]", True, (200, 200, 200))
            screen.blit(p_txt, (rect_obj.x + 60, rect_obj.y + 10))

        if len(spectator_group) < MAX_SPECTATORS:
            add_rect = pygame.Rect(right_area_x, start_y + len(spectator_group)*55, 180, 40)
            a_col = COLORS['BUTTON_HOVER'] if add_rect.collidepoint(mx, my) else COLORS['BUTTON']
            pygame.draw.rect(screen, a_col, add_rect)
            screen.blit(self.font.render("+ ADD SPEC BOT", True, (255, 255, 255)), (add_rect.x+20, add_rect.y+8))
            self.lobby_buttons['ADD_BOT_SPEC'] = add_rect

        # Time Scale UI
        sx, sy = w - 450, h - 250
        pygame.draw.rect(screen, (30, 30, 40), (sx - 20, sy - 40, 420, 120))
        pygame.draw.rect(screen, (100, 100, 120), (sx - 20, sy - 40, 420, 120), 2)
        screen.blit(self.bold_font.render("TIME SETTINGS", True, (200, 200, 200)), (sx, sy - 30))

        screen.blit(self.font.render("TIME SCALE:", True, (255, 255, 255)), (sx, sy + 30))
        
        # Minus Button
        m_rect = pygame.Rect(sx + 150, sy + 25, 30, 30)
        pygame.draw.rect(screen, COLORS['BUTTON'], m_rect)
        screen.blit(self.bold_font.render("-", True, (255,255,255)), (m_rect.x+10, m_rect.y+5))
        self.lobby_buttons["SCALE_MINUS"] = m_rect

        # Scale Value
        val_txt = self.large_font.render(f"{self.time_scale}%", True, (0, 255, 0))
        screen.blit(val_txt, (sx + 200, sy + 20))

        # Plus Button
        p_rect = pygame.Rect(sx + 300, sy + 25, 30, 30)
        pygame.draw.rect(screen, COLORS['BUTTON'], p_rect)
        screen.blit(self.bold_font.render("+", True, (255,255,255)), (p_rect.x+8, p_rect.y+5))
        self.lobby_buttons["SCALE_PLUS"] = p_rect

        start_rect = pygame.Rect(w - 250, h - 100, 200, 60)
        s_col = (0, 150, 0) if start_rect.collidepoint(mx, my) else (0, 100, 0)
        pygame.draw.rect(screen, s_col, start_rect)
        pygame.draw.rect(screen, (255, 255, 255), start_rect, 2)
        screen.blit(self.large_font.render("START", True, (255, 255, 255)), (start_rect.x+55, start_rect.y+15))
        self.lobby_buttons['START'] = start_rect

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                btns = self.lobby_buttons

                if 'START' in btns and btns['START'].collidepoint(mx, my):
                    # Calculate durations based on Time Scale
                    scale = self.time_scale / 100.0
                    custom = {}
                    for k, v in DEFAULT_PHASE_DURATIONS.items():
                        custom[k] = int(v * scale)
                    
                    self.game.shared_data['custom_durations'] = custom

                    from states.play_state import PlayState
                    self.game.state_machine.change(PlayState(self.game))

                if 'ADD_BOT_PLAYER' in btns and btns['ADD_BOT_PLAYER'].collidepoint(mx, my):
                    if len(self.participants) < MAX_TOTAL_USERS:
                        self.participants.append({'name': f'Bot {len(self.participants)}', 'type': 'BOT', 'role': 'RANDOM', 'group': 'PLAYER'})

                if 'ADD_BOT_SPEC' in btns and btns['ADD_BOT_SPEC'].collidepoint(mx, my):
                    if len(self.participants) < MAX_TOTAL_USERS:
                        self.participants.append({'name': f'SpecBot {len(self.participants)}', 'type': 'BOT', 'role': 'RANDOM', 'group': 'SPECTATOR'})
                
                if 'SCALE_MINUS' in btns and btns['SCALE_MINUS'].collidepoint(mx, my):
                    self.time_scale = max(50, self.time_scale - 10)
                
                if 'SCALE_PLUS' in btns and btns['SCALE_PLUS'].collidepoint(mx, my):
                    self.time_scale = min(200, self.time_scale + 10)

                for k, v in btns.items():
                    if k.startswith("ROLE_") and v[0].collidepoint(mx, my):
                        roles = ["RANDOM", "FARMER", "MINER", "FISHER", "POLICE", "DOCTOR", "MAFIA"]
                        p = self.participants[v[1]]
                        if p['group'] == 'PLAYER':
                            curr_idx = roles.index(p['role']) if p['role'] in roles else 0
                            p['role'] = roles[(curr_idx+1)%len(roles)]

                    elif k.startswith("TO_SPEC_") and v.collidepoint(mx, my):
                        idx = int(k.replace("TO_SPEC_", ""))
                        self.participants[idx]['group'] = 'SPECTATOR'

                    elif k.startswith("TO_PLAYER_") and v.collidepoint(mx, my):
                        idx = int(k.replace("TO_PLAYER_", ""))
                        self.participants[idx]['group'] = 'PLAYER'