import pygame
import json
import os
from core.base_state import BaseState
from managers.resource_manager import ResourceManager
from systems.network import NetworkManager
from colors import COLORS
from settings import MAX_PLAYERS, MAX_SPECTATORS, DEFAULT_PHASE_DURATIONS, MAX_TOTAL_USERS

class LobbyState(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.resource_manager = ResourceManager.get_instance()
        self.font = self.resource_manager.get_font('default')
        self.bold_font = self.resource_manager.get_font('bold')
        self.large_font = self.resource_manager.get_font('large')
        self.lobby_buttons = {}
        if not hasattr(self.game, 'network'):
            self.game.network = NetworkManager()
        self.participants = [] 
        self.my_id = -1
        self.time_scale = 100
        self.map_size_str = "Unknown"
        self._load_map_info()
        
        # Panel sizes
        self.lw, self.lh = 500, 500 # Left panel (Players)
        self.rw, self.rh = 400, 240 # Right panels (Specs, Settings)
        self.gap = 20
        
        self.panel_players = self._create_panel_bg(self.lw, self.lh)
        self.panel_specs = self._create_panel_bg(self.rw, self.rh)
        self.panel_settings = self._create_panel_bg(self.rw, self.rh)

    def _load_map_info(self):
        try:
            if os.path.exists("map.json"):
                with open("map.json", "r", encoding='utf-8') as f:
                    data = json.load(f); self.map_size_str = f"{data.get('width', 50)}x{data.get('height', 50)}"
            else: self.map_size_str = "50x50 (Default)"
        except: self.map_size_str = "Error"

    def _create_panel_bg(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 20, 25, 220), (0, 0, w, h), border_radius=15)
        pygame.draw.rect(s, (80, 80, 100, 255), (0, 0, w, h), 2, border_radius=15)
        return s

    def enter(self, params=None):
        if not self.game.network.connected:
            if not self.game.network.connect():
                self.participants = [{'id': 0, 'name': 'Player 1', 'role': 'CITIZEN', 'type': 'PLAYER', 'group': 'PLAYER'}]
                self.game.shared_data['participants'] = self.participants

    def update(self, dt):
        if not self.game.network.connected: return
        for e in self.game.network.get_events():
            if e.get('type') == 'WELCOME': self.my_id = e.get('my_id'); self.game.network.my_id = self.my_id
            elif e.get('type') == 'PLAYER_LIST':
                self.participants = e.get('participants', [])
                self.game.shared_data['participants'] = self.participants
            elif e.get('type') == 'GAME_START':
                from states.play_state import PlayState
                self.game.state_machine.change(PlayState(self.game))

    def draw(self, screen):
        w, h = screen.get_size()
        screen.fill((10, 10, 15))
        self._draw_grid_bg(screen, w, h)
        
        mx, my = pygame.mouse.get_pos(); self.lobby_buttons = {}
        
        # Calculate Center Layout
        total_w = self.lw + self.gap + self.rw
        start_x = (w - total_w) // 2
        start_y = (h - self.lh) // 2
        
        player_group = [p for p in self.participants if p.get('group') == 'PLAYER']
        spectator_group = [p for p in self.participants if p.get('group') == 'SPECTATOR']

        # --- LEFT PANEL: PLAYERS ---
        screen.blit(self.panel_players, (start_x, start_y))
        title_txt = self.bold_font.render(f"PLAYERS ({len(player_group)}/{MAX_PLAYERS})", True, (150, 255, 150))
        screen.blit(title_txt, (start_x + 20, start_y + 20))
        
        for i, p in enumerate(player_group):
            if i >= 8: break
            rect = pygame.Rect(start_x + 20, start_y + 60 + i*50, 460, 40); is_me = (p.get('id') == self.my_id)
            pygame.draw.rect(screen, (50, 50, 70) if is_me else (30, 30, 40), rect, border_radius=5)
            pygame.draw.rect(screen, (100, 200, 255) if is_me else (60, 60, 70), rect, 1, border_radius=5)
            screen.blit(self.font.render(f"{p['name']} (ID: {p['id']})", True, (255, 255, 255)), (rect.x + 15, rect.y + 10))
            
            r_col = {'CITIZEN': (150, 200, 150), 'MAFIA': (255, 100, 100), 'POLICE': (100, 100, 255), 'DOCTOR': (200, 200, 100)}.get(p.get('role'), (200, 200, 200))
            role_rect = pygame.Rect(rect.right - 150, rect.y + 5, 100, 30)
            if is_me:
                pygame.draw.rect(screen, (80, 80, 100) if role_rect.collidepoint(mx, my) else (60, 60, 80), role_rect, border_radius=5)
                pygame.draw.rect(screen, r_col, role_rect, 1, border_radius=5)
                self.lobby_buttons['MY_ROLE'] = role_rect
            role_txt_img = self.font.render(p.get('role'), True, r_col)
            screen.blit(role_txt_img, role_txt_img.get_rect(center=role_rect.center))
            
            if self.my_id == 0 or not self.game.network.connected:
                m_rect = pygame.Rect(rect.right - 40, rect.y + 5, 30, 30)
                pygame.draw.rect(screen, (80, 80, 80) if m_rect.collidepoint(mx, my) else (60, 60, 60), m_rect, border_radius=4)
                arrow_img = self.bold_font.render("->", True, (200, 200, 200))
                screen.blit(arrow_img, arrow_img.get_rect(center=m_rect.center))
                self.lobby_buttons[f"TO_SPEC_{p['id']}"] = m_rect

        if (not self.game.network.connected or self.my_id == 0) and len(self.participants) < MAX_TOTAL_USERS:
            btn = pygame.Rect(start_x + 20, start_y + 440, 150, 40)
            pygame.draw.rect(screen, (70, 70, 80) if btn.collidepoint(mx, my) else (50, 50, 60), btn, border_radius=5)
            pygame.draw.rect(screen, (150, 150, 150), btn, 1, border_radius=5)
            txt_img = self.font.render("+ P-BOT", True, (200, 200, 200))
            screen.blit(txt_img, txt_img.get_rect(center=btn.center)); self.lobby_buttons['ADD_BOT_PLAYER'] = btn

        # --- RIGHT TOP PANEL: SPECTATORS ---
        rx, ry = start_x + self.lw + self.gap, start_y
        screen.blit(self.panel_specs, (rx, ry))
        screen.blit(self.bold_font.render(f"SPECTATORS ({len(spectator_group)}/{MAX_SPECTATORS})", True, (150, 150, 255)), (rx + 20, ry + 20))
        for i, p in enumerate(spectator_group):
            if i >= 3: break
            rect = pygame.Rect(rx + 20, ry + 60 + i*50, 360, 40)
            pygame.draw.rect(screen, (30, 30, 40), rect, border_radius=5)
            screen.blit(self.font.render(p['name'], True, (180, 180, 180)), (rect.x + 50, rect.y + 10))
            if self.my_id == 0 or not self.game.network.connected:
                m_rect = pygame.Rect(rect.x + 5, rect.y + 5, 30, 30)
                pygame.draw.rect(screen, (80, 80, 80) if m_rect.collidepoint(mx, my) else (60, 60, 60), m_rect, border_radius=4)
                arrow_img = self.bold_font.render("<-", True, (200, 200, 200))
                screen.blit(arrow_img, arrow_img.get_rect(center=m_rect.center))
                self.lobby_buttons[f"TO_PLAYER_{p['id']}"] = m_rect

        if (not self.game.network.connected or self.my_id == 0) and len(self.participants) < MAX_TOTAL_USERS:
            btn_s = pygame.Rect(rx + 20, ry + 190, 120, 35)
            pygame.draw.rect(screen, (70, 70, 80) if btn_s.collidepoint(mx, my) else (50, 50, 60), btn_s, border_radius=5)
            txt_s_img = self.font.render("+ S-BOT", True, (200, 200, 200))
            screen.blit(txt_s_img, txt_s_img.get_rect(center=btn_s.center)); self.lobby_buttons['ADD_BOT_SPEC'] = btn_s

        # --- RIGHT BOTTOM PANEL: SETTINGS ---
        sx, sy = rx, ry + self.rh + self.gap
        screen.blit(self.panel_settings, (sx, sy))
        screen.blit(self.bold_font.render("GAME SETTINGS", True, (255, 255, 100)), (sx + 20, sy + 20))
        m_r = pygame.Rect(sx + 130, sy + 55, 30, 30); p_r = pygame.Rect(sx + 230, sy + 55, 30, 30)
        pygame.draw.rect(screen, COLORS['BUTTON'], m_r, border_radius=4); pygame.draw.rect(screen, COLORS['BUTTON'], p_r, border_radius=4)
        minus_img = self.bold_font.render("-", True, (255, 255, 255))
        screen.blit(minus_img, minus_img.get_rect(center=m_r.center))
        plus_img = self.bold_font.render("+", True, (255, 255, 255))
        screen.blit(plus_img, plus_img.get_rect(center=p_r.center))
        self.lobby_buttons['SCALE_MINUS'] = m_r; self.lobby_buttons['SCALE_PLUS'] = p_r
        screen.blit(self.font.render(f"Time Speed: {self.time_scale}%", True, (100, 255, 100)), (sx + 20, sy + 100))
        screen.blit(self.font.render(f"Map Size: {self.map_size_str}", True, (160, 160, 180)), (sx + 20, sy + 130))

        if self.my_id == 0 or not self.game.network.connected:
            s_r = pygame.Rect(sx + 20, sy + 160, 360, 60)
            pygame.draw.rect(screen, (0, 150, 0) if s_r.collidepoint(mx, my) else (0, 100, 0), s_r, border_radius=8)
            pygame.draw.rect(screen, (100, 255, 100), s_r, 2, border_radius=8)
            start_txt_img = self.large_font.render("START GAME", True, (255, 255, 255))
            screen.blit(start_txt_img, start_txt_img.get_rect(center=s_r.center))
            self.lobby_buttons['START'] = s_r
        else: screen.blit(self.font.render("Waiting for Host...", True, (150, 150, 150)), (sx + 100, sy + 180))

    def _draw_grid_bg(self, screen, w, h):
        for x in range(0, w, 40): pygame.draw.line(screen, (20, 20, 30), (x, 0), (x, h))
        for y in range(0, h, 40): pygame.draw.line(screen, (20, 20, 30), (0, y), (w, y))

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1: return
        mx, my = event.pos
        if 'START' in self.lobby_buttons and self.lobby_buttons['START'].collidepoint(mx, my):
            scale = self.time_scale / 100.0
            self.game.shared_data['custom_durations'] = {k: int(v * scale) for k, v in DEFAULT_PHASE_DURATIONS.items()}
            if self.game.network.connected: self.game.network.send_start_game()
            else:
                from states.play_state import PlayState
                self.game.state_machine.change(PlayState(self.game))
        if 'ADD_BOT_PLAYER' in self.lobby_buttons and self.lobby_buttons['ADD_BOT_PLAYER'].collidepoint(mx, my):
            if self.game.network.connected: self.game.network.send_add_bot(f"Bot {len(self.participants)}", "PLAYER")
            else: self.participants.append({'id': len(self.participants), 'name': f'Bot {len(self.participants)}', 'role': 'RANDOM', 'type': 'BOT', 'group': 'PLAYER'})
        if 'ADD_BOT_SPEC' in self.lobby_buttons and self.lobby_buttons['ADD_BOT_SPEC'].collidepoint(mx, my):
            if self.game.network.connected: self.game.network.send_add_bot(f"SpecBot {len(self.participants)}", "SPECTATOR")
            else: self.participants.append({'id': len(self.participants), 'name': f'SpecBot {len(self.participants)}', 'role': 'RANDOM', 'type': 'BOT', 'group': 'SPECTATOR'})
        for k, v in self.lobby_buttons.items():
            if k.startswith("TO_SPEC_") and v.collidepoint(mx, my):
                tid = int(k.replace("TO_SPEC_", ""))
                if self.game.network.connected: self.game.network.send_change_group(tid, "SPECTATOR")
                else: 
                    for p in self.participants:
                        if p['id'] == tid: p['group'] = 'SPECTATOR'
            elif k.startswith("TO_PLAYER_") and v.collidepoint(mx, my):
                tid = int(k.replace("TO_PLAYER_", ""))
                if self.game.network.connected: self.game.network.send_change_group(tid, "PLAYER")
                else:
                    for p in self.participants:
                        if p['id'] == tid: p['group'] = 'PLAYER'
        if 'SCALE_MINUS' in self.lobby_buttons and self.lobby_buttons['SCALE_MINUS'].collidepoint(mx, my): self.time_scale = max(10, self.time_scale - 10)
        if 'SCALE_PLUS' in self.lobby_buttons and self.lobby_buttons['SCALE_PLUS'].collidepoint(mx, my): self.time_scale = min(500, self.time_scale + 10)
        if 'MY_ROLE' in self.lobby_buttons and self.lobby_buttons['MY_ROLE'].collidepoint(mx, my):
            roles = ["CITIZEN", "MAFIA", "POLICE", "DOCTOR"]
            curr_role = "CITIZEN"
            for p in self.participants:
                if p['id'] == self.my_id: curr_role = p.get('role', 'CITIZEN'); break
            new_role = roles[(roles.index(curr_role) + 1) % len(roles)]
            if self.game.network.connected: self.game.network.send_role_change(new_role)
            else: 
                for p in self.participants:
                    if p['id'] == self.my_id: p['role'] = new_role
