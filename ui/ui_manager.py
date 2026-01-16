import pygame
import math
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, ITEMS
from colors import COLORS
from core.ecs_manager import ECSManager
from core.event_bus import EventBus
from core.game_state_manager import GameStateManager
from core.resource_manager import ResourceManager
from components.status import Stats, StatusEffects
from components.identity import Identity
from components.interaction import Inventory, InteractionState
from components.common import Transform, Velocity
from world.map_manager import MapManager

# 미니맵 색상 정의 (기존 ui.py에서 가져옴)
MINIMAP_COLORS = {
    1110000: (100, 80, 50),    # Dirt
    1110001: (34, 139, 34),    # Grass
    1110002: (100, 100, 100),  # Stone
    3220000: (50, 50, 50),     # Wall
    5310000: (0, 0, 255),      # Water/Object
    8321006: (255, 0, 0),      # Vending Machine
}
DEFAULT_COLORS = {
    'floor': (40, 40, 40),
    'wall': (100, 100, 100),
    'object': (200, 200, 100)
}

class UIManager:
    def __init__(self, ecs: ECSManager, event_bus: EventBus, map_manager: MapManager):
        self.ecs = ecs
        self.event_bus = event_bus
        self.map_manager = map_manager
        self.game_state = GameStateManager.get_instance()
        self.resource_manager = ResourceManager.get_instance()
        
        self.font_main = self.resource_manager.get_font('default')
        self.font_small = self.resource_manager.get_font('small')
        self.font_big = self.resource_manager.get_font('large')
        self.font_digit = pygame.font.SysFont("consolas", 18, bold=True)
        
        # UI Resources
        self.panel_bg_status = self._create_panel_bg(360, 110)
        self.panel_bg_env = self._create_panel_bg(160, 80)
        self.panel_bg_emotion = self._create_panel_bg(220, 140)
        self.panel_bg_police = self._create_panel_bg(200, 120)
        
        # State
        self.show_inventory = False
        self.show_vending = False
        self.show_vote_ui = False
        self.show_news = False
        self.sel_idx = 0
        
        # Minimap
        self.minimap_surface = None
        self.cached_minimap = None
        self.radar_timer = 0
        self.radar_blips = []
        
        # Motion Tracker
        self.scan_angle = 0
        self.scan_dir = 1
        self.scan_speed = 2
        
        # Alert
        self.alert_text = ""
        self.alert_timer = 0
        self.alert_color = (255, 255, 255)
        
        # Event Sub
        self.event_bus.subscribe("TOGGLE_UI", self.toggle_ui)
        self.event_bus.subscribe("SHOW_POPUP", self.show_alert)

    def _create_panel_bg(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 20, 25, 200), (0, 0, w, h), border_radius=10)
        pygame.draw.rect(s, (80, 80, 90, 255), (0, 0, w, h), 2, border_radius=10)
        return s

    def toggle_ui(self, ui_type):
        if ui_type == "INVENTORY":
            self.show_inventory = not self.show_inventory
            self.show_vending = False; self.show_vote_ui = False
        elif ui_type == "VENDING":
            self.show_vending = not self.show_vending
            self.show_inventory = False; self.show_vote_ui = False
        elif ui_type == "VOTE":
            self.show_vote_ui = not self.show_vote_ui
            self.show_inventory = False; self.show_vending = False
        self.sel_idx = 0

    def show_alert(self, text, color=(255, 255, 255)):
        self.alert_text = text
        self.alert_color = color
        self.alert_timer = pygame.time.get_ticks() + 3000

    def update(self, dt):
        pass

    def draw(self, screen):
        w, h = screen.get_size()
        
        # Player Data Fetch
        player_ent = [e for e in self.ecs.get_entities_with(Identity) if self.ecs.get_component(e, Identity).is_player]
        if not player_ent: return
        pid = player_ent[0]
        
        stats = self.ecs.get_component(pid, Stats)
        ident = self.ecs.get_component(pid, Identity)
        inv = self.ecs.get_component(pid, Inventory)
        effects = self.ecs.get_component(pid, StatusEffects)
        inter = self.ecs.get_component(pid, InteractionState)
        trans = self.ecs.get_component(pid, Transform)
        
        if ident.role == "SPECTATOR":
            self._draw_spectator_ui(screen, w, h)
            return

        # HUDs
        self._draw_status_panel(screen, stats, ident)
        self._draw_env_panel(screen, w)
        self._draw_controls(screen, w, h, ident, inv, inter) # Pass inv, inter
        
        # Gadgets
        if inv.device_on:
            if ident.role in ["CITIZEN", "DOCTOR"]:
                self._draw_motion_tracker(screen, w, h, trans)
            elif ident.role == "POLICE":
                self._draw_police_hud(screen, w, h, inter)

        # Bottom Right Panels
        if ident.role != "SPECTATOR":
            is_blackout = self.game_state.is_blackout
            self._draw_minimap(screen, w, h, trans, ident, is_blackout)
            self._draw_emotion_panel(screen, w, h, effects)

        # Stamina & Interaction Bar
        self._draw_stamina_bar(screen, trans, effects)
        self._draw_interaction_bar(screen, trans, inter)
        
        # Popups
        if self.show_vote_ui: self._draw_vote_ui(screen, w, h)
        if self.show_inventory: self._draw_inventory(screen, w, h, inv)
        if self.show_vending: self._draw_vending(screen, w, h, stats)
        
        # Alert
        if pygame.time.get_ticks() < self.alert_timer:
            txt = self.font_big.render(self.alert_text, True, self.alert_color)
            bg_rect = txt.get_rect(center=(w // 2, 150))
            bg_rect.inflate_ip(40, 20)
            s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            screen.blit(s, bg_rect.topleft)
            screen.blit(txt, txt.get_rect(center=bg_rect.center))

    def _draw_status_panel(self, screen, stats, ident):
        x, y = 20, 20
        screen.blit(self.panel_bg_status, (x, y))
        
        # Role
        c = (200, 200, 200)
        if ident.role == 'MAFIA': c = (200, 50, 50)
        elif ident.role == 'POLICE': c = (50, 50, 255)
        
        # Avatar Box
        avatar_rect = pygame.Rect(x + 15, y + 15, 60, 60)
        pygame.draw.rect(screen, (40, 40, 40), avatar_rect, border_radius=8)
        pygame.draw.rect(screen, c, avatar_rect, 3, border_radius=8)
        
        role_char = ident.role[0]
        txt = self.font_big.render(role_char, True, c)
        screen.blit(txt, (avatar_rect.centerx - txt.get_width()//2, avatar_rect.centery - txt.get_height()//2))
        
        role_name = self.font_small.render(ident.role, True, (200, 200, 200))
        screen.blit(role_name, (avatar_rect.centerx - role_name.get_width()//2, avatar_rect.bottom + 8))

        bar_x = x + 130
        bar_w = 200
        
        # HP
        hp_ratio = max(0, stats.hp / stats.max_hp)
        self._draw_bar(screen, bar_x, y + 25, bar_w, 12, hp_ratio, (220, 60, 60), "HP")
        
        # AP
        ap_ratio = max(0, stats.ap / stats.max_ap)
        self._draw_bar(screen, bar_x, y + 50, bar_w, 12, ap_ratio, (60, 150, 220), "AP")
        
        # Coin
        coin_txt = self.font_digit.render(f"{stats.coins:03d} $", True, (255, 215, 0))
        screen.blit(coin_txt, (bar_x, y + 75))

    def _draw_bar(self, screen, x, y, w, h, ratio, color, label):
        pygame.draw.rect(screen, (40, 40, 40), (x, y, w, h), border_radius=4)
        fill_w = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=4)
        for i in range(x, x+w, 10):
            pygame.draw.line(screen, (0,0,0,50), (i, y), (i+5, y+h), 1)
        l_surf = self.font_small.render(label, True, (200, 200, 200))
        screen.blit(l_surf, (x - 25, y - 2))

    def _draw_env_panel(self, screen, sw):
        w, h = 160, 80
        x, y = sw - w - 20, 20
        screen.blit(self.panel_bg_env, (x, y))
        
        day_txt = self.font_big.render(f"Day {self.game_state.day_count}", True, (200, 200, 200))
        screen.blit(day_txt, (x + w//2 - day_txt.get_width()//2, y + 20))

    def _draw_controls(self, screen, w, h, ident, inv, inter):
        icon_size = 50
        gap = 10
        start_x = 20
        start_y = h - (icon_size * 2 + gap) - 20 
        
        def get_pos(col, row):
            return start_x + col * (icon_size + gap), start_y + row * (icon_size + gap)

        self._draw_key_icon(screen, *get_pos(0, 0), "I", "인벤토리", True)
        self._draw_key_icon(screen, *get_pos(1, 0), "Z", "투표", True)
        self._draw_key_icon(screen, *get_pos(2, 0), "E", "상호작용", True)
        
        q_label = "특수스킬"
        if ident.role in ["CITIZEN", "DOCTOR"]: q_label = "동체탐지"
        elif ident.role == "POLICE": q_label = "사이렌"
        
        q_active = inv.device_on if ident.role in ["CITIZEN", "DOCTOR"] else not inter.ability_used
        r_active = not inter.ability_used # Simply check used
        
        self._draw_key_icon(screen, *get_pos(0, 1), "Q", q_label, q_active)
        self._draw_key_icon(screen, *get_pos(1, 1), "R", "스킬", r_active)
        self._draw_key_icon(screen, *get_pos(2, 1), "V", "행동", True)

    def _draw_key_icon(self, screen, x, y, key, label, active=True):
        rect = pygame.Rect(x, y, 50, 50)
        bg_col = (40, 40, 50) if active else (30, 30, 30)
        border_col = (100, 100, 120) if active else (60, 60, 60)
        text_col = (255, 255, 255) if active else (100, 100, 100)
        
        pygame.draw.rect(screen, bg_col, rect, border_radius=8)
        pygame.draw.rect(screen, border_col, rect, 2, border_radius=8)
        
        text_surf = self.font_main.render(key, True, text_col)
        screen.blit(text_surf, (x + 25 - text_surf.get_width()//2, y + 4))
        
        lbl_surf = self.font_small.render(label, True, (200, 200, 200))
        if lbl_surf.get_width() > 46:
            lbl_surf = pygame.transform.smoothscale(lbl_surf, (44, int(lbl_surf.get_height() * (44/lbl_surf.get_width()))))
        screen.blit(lbl_surf, (x + 25 - lbl_surf.get_width()//2, y + 28))

    def _draw_motion_tracker(self, screen, w, h, player_trans):
        cx, cy = 340, h - 150
        radius = 90
        
        frame_rect = pygame.Rect(cx - 100, cy - 110, 200, 240)
        pygame.draw.rect(screen, (30, 35, 30), frame_rect, border_radius=15)
        pygame.draw.rect(screen, (60, 70, 60), frame_rect, 3, border_radius=15)
        screen_rect = pygame.Rect(cx - 85, cy - 90, 170, 170)
        pygame.draw.rect(screen, (10, 25, 15), screen_rect)
        pygame.draw.rect(screen, (40, 60, 40), screen_rect, 2)

        for r in [30, 60, 90]:
            pygame.draw.circle(screen, (30, 80, 30), (cx, cy + 60), r, 1)

        self.scan_angle += self.scan_dir * self.scan_speed
        if self.scan_angle > 45 or self.scan_angle < -45: self.scan_dir *= -1
            
        scan_rad = math.radians(self.scan_angle - 90)
        ex = cx + math.cos(scan_rad) * radius
        ey = (cy + 60) + math.sin(scan_rad) * radius
        pygame.draw.line(screen, (50, 200, 50), (cx, cy + 60), (ex, ey), 2)

        # NPCs Scan
        npcs = self.ecs.get_entities_with(Transform, Identity, Stats)
        detect_range = 400
        detect_range_sq = detect_range**2
        
        targets = []
        for n in npcs:
            nid = self.ecs.get_component(n, Identity)
            if nid.is_player: continue
            
            nstats = self.ecs.get_component(n, Stats)
            if not nstats.alive: continue
            
            ntrans = self.ecs.get_component(n, Transform)
            nvel = self.ecs.get_component(n, Velocity)
            
            # Check movement (velocity > 0)
            is_moving = (nvel.dx != 0 or nvel.dy != 0) if nvel else False
            if not is_moving: continue
            
            dist_sq = (player_trans.x - ntrans.x)**2 + (player_trans.y - ntrans.y)**2
            if dist_sq > detect_range_sq: continue
            
            dx = (ntrans.x - player_trans.x) / detect_range
            dy = (ntrans.y - player_trans.y) / detect_range
            tx = cx + dx * radius
            ty = (cy + 60) + dy * radius
            
            if screen_rect.collidepoint(tx, ty):
                targets.append((tx, ty))

        for tx, ty in targets:
            pygame.draw.circle(screen, (150, 255, 150), (int(tx), int(ty)), 4)
            s = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(s, (50, 200, 50, 100), (10, 10), 8)
            screen.blit(s, (tx-10, ty-10))

        title = self.font_small.render("MOTION TRACKER", True, (150, 150, 150))
        screen.blit(title, (cx - title.get_width()//2, frame_rect.top + 10))

    def _draw_police_hud(self, screen, w, h, inter):
        x, y = 240, h - 200
        screen.blit(self.panel_bg_police, (x, y))
        
        t = self.font_main.render("POLICE TERMINAL", True, (100, 200, 255))
        screen.blit(t, (x + 100 - t.get_width()//2, y + 10))
        
        t2 = self.font_small.render(f"Shots Fired: {inter.bullets_fired_today}/1", True, (200, 200, 200))
        screen.blit(t2, (x + 20, y + 50))

    def _draw_minimap(self, screen, w, h, player_trans, ident, is_blackout):
        mm_w, mm_h = 200, 150
        x = w - mm_w - 20
        y = h - 140 - 20 - mm_h - 10
        mm_rect = pygame.Rect(x, y, mm_w, mm_h)
        
        s = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        screen.blit(s, mm_rect.topleft)
        pygame.draw.rect(screen, (100, 100, 120), mm_rect, 2)
        
        if not hasattr(self, 'cached_minimap') or self.cached_minimap is None:
            self._generate_minimap_cache(mm_w-4, mm_h-4)
            
        if self.cached_minimap:
            screen.blit(self.cached_minimap, (mm_rect.x + 2, mm_rect.y + 2))
            
        map_w_px = self.map_manager.width * TILE_SIZE
        map_h_px = self.map_manager.height * TILE_SIZE
        
        if map_w_px > 0:
            dot_x = mm_rect.x + 2 + (player_trans.x / map_w_px) * (mm_w - 4)
            dot_y = mm_rect.y + 2 + (player_trans.y / map_h_px) * (mm_h - 4)
            pygame.draw.circle(screen, (0, 255, 0), (int(dot_x), int(dot_y)), 3)

        # Radar / Special Vision
        if ident.role == "MAFIA" and is_blackout:
            now = pygame.time.get_ticks()
            if now > self.radar_timer:
                self.radar_timer = now + 2000
                self.radar_blips = []
                npcs = self.ecs.get_entities_with(Transform, Identity, Stats)
                for n in npcs:
                    nid = self.ecs.get_component(n, Identity)
                    if nid.is_player: continue
                    ns = self.ecs.get_component(n, Stats)
                    if not ns.alive: continue
                    nt = self.ecs.get_component(n, Transform)
                    
                    color = (0, 255, 0)
                    if nid.role == "POLICE": color = (0, 100, 255)
                    elif nid.role == "MAFIA": color = (255, 0, 0)
                    
                    nx = mm_rect.x + 2 + (nt.x / map_w_px) * (mm_w - 4)
                    ny = mm_rect.y + 2 + (nt.y / map_h_px) * (mm_h - 4)
                    self.radar_blips.append(((int(nx), int(ny)), color))
            
            for pos, col in self.radar_blips:
                pygame.draw.circle(screen, col, pos, 4)

    def _generate_minimap_cache(self, w, h):
        surf = pygame.Surface((self.map_manager.width, self.map_manager.height))
        surf.fill((20, 20, 25))
        
        floors = self.map_manager.map_data['floor']
        walls = self.map_manager.map_data['wall']
        objects = self.map_manager.map_data['object']
        
        px = pygame.PixelArray(surf)
        for r in range(self.map_manager.height):
            for c in range(self.map_manager.width):
                # Floor
                tid = floors[r][c][0]
                if tid != 0: px[c, r] = MINIMAP_COLORS.get(tid, DEFAULT_COLORS['floor'])
                # Wall
                tid = walls[r][c][0]
                if tid != 0: px[c, r] = MINIMAP_COLORS.get(tid, DEFAULT_COLORS['wall'])
                # Object
                tid = objects[r][c][0]
                if tid != 0: px[c, r] = MINIMAP_COLORS.get(tid, DEFAULT_COLORS['object'])
        px.close()
        self.cached_minimap = pygame.transform.scale(surf, (w, h))

    def _draw_emotion_panel(self, screen, w, h, effects):
        panel_w, panel_h = 220, 140
        x = w - panel_w - 20
        y = h - panel_h - 20
        
        screen.blit(self.panel_bg_emotion, (x, y))
        
        y_offset = 50
        for emo, val in effects.emotions.items():
            if val > 0:
                color = (255, 255, 255)
                if emo == 'FEAR': color = (100, 100, 255)
                elif emo == 'PAIN': color = (255, 100, 100)
                elif emo == 'ANXIETY': color = (255, 150, 50)
                
                txt = self.font_small.render(f"{emo}: {val}", True, color)
                screen.blit(txt, (x + 15, y + y_offset))
                y_offset += 20

    def _draw_stamina_bar(self, screen, trans, effects):
        if effects.breath_gauge >= 100: return
        draw_x = SCREEN_WIDTH // 2
        draw_y = SCREEN_HEIGHT // 2 - 60
        w, h = 40, 5
        ratio = max(0, effects.breath_gauge / 100.0)
        pygame.draw.rect(screen, (30, 30, 30), (draw_x - w//2, draw_y, w, h))
        pygame.draw.rect(screen, (100, 200, 255), (draw_x - w//2, draw_y, w*ratio, h))

    def _draw_interaction_bar(self, screen, trans, inter):
        if inter.e_key_pressed:
            now = pygame.time.get_ticks()
            hold_time = now - inter.e_hold_start_time
            ratio = min(1.0, hold_time / 1000.0)
            draw_x = SCREEN_WIDTH // 2
            draw_y = SCREEN_HEIGHT // 2 - 50
            w, h = 40, 6
            pygame.draw.rect(screen, (50, 50, 50), (draw_x - w//2, draw_y, w, h))
            pygame.draw.rect(screen, (255, 255, 0), (draw_x - w//2, draw_y, w*ratio, h))

    def _draw_vote_ui(self, screen, w, h):
        center_x = w // 2
        msg = self.font_big.render("VOTING SESSION", True, (255, 50, 50))
        screen.blit(msg, (center_x - msg.get_width()//2, 100))
        panel_w, panel_h = 400, 500
        panel_rect = pygame.Rect(center_x - panel_w//2, h//2 - panel_h//2, panel_w, panel_h)
        s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        screen.blit(s, panel_rect.topleft)
        pygame.draw.rect(screen, (100, 100, 120), panel_rect, 2)
        npcs = self.ecs.get_entities_with(Identity, Stats)
        candidates = []
        for n in npcs:
            ns = self.ecs.get_component(n, Stats)
            if ns.alive: candidates.append(self.ecs.get_component(n, Identity))
        start_y = panel_rect.top + 50
        for i, c in enumerate(candidates):
            col = (255, 255, 255)
            if i == self.sel_idx: col = (255, 255, 0)
            txt = self.font_main.render(f"{c.name} ({c.role})", True, col)
            screen.blit(txt, (panel_rect.left + 30, start_y + i * 40))

    def _draw_item_icon(self, screen, key, rect, is_sel):
        col = (60, 60, 80) if not is_sel else (100, 100, 150)
        pygame.draw.rect(screen, col, rect, border_radius=5)
        if is_sel: pygame.draw.rect(screen, (255, 255, 0), rect, 2, border_radius=5)
        c = rect.center
        if key == 'TANGERINE': pygame.draw.circle(screen, (255, 165, 0), c, 10)
        elif key == 'CHOCOBAR': pygame.draw.rect(screen, (139, 69, 19), (c[0]-8, c[1]-12, 16, 24))
        elif key == 'MEDKIT': 
            pygame.draw.rect(screen, (255, 255, 255), (c[0]-10, c[1]-8, 20, 16))
            pygame.draw.line(screen, (255, 0, 0), (c[0], c[1]-5), (c[0], c[1]+5), 2)
            pygame.draw.line(screen, (255, 0, 0), (c[0]-5, c[1]), (c[0]+5, c[1]), 2)
        elif key == 'KEY': pygame.draw.line(screen, (255, 215, 0), (c[0]-5, c[1]+5), (c[0]+5, c[1]-5), 3)
        elif key == 'BATTERY': pygame.draw.rect(screen, (0, 255, 0), (c[0]-6, c[1]-10, 12, 20))
        elif key == 'TASER': pygame.draw.rect(screen, (50, 50, 200), (c[0]-10, c[1]-5, 20, 10))
        else: pygame.draw.circle(screen, (200, 200, 200), c, 5)

    def _draw_vending(self, screen, w, h, stats):
        vw, vh = 600, 500; rect = pygame.Rect(w//2 - vw//2, h//2 - vh//2, vw, vh)
        pygame.draw.rect(screen, (20, 20, 30), rect); pygame.draw.rect(screen, (0, 255, 255), rect, 3)
        screen.blit(self.font_big.render("SHOP", True, (0, 255, 255)), (rect.x + 20, rect.y + 20))
        items_list = list(ITEMS.keys())
        grid_cols, slot_size, gap = 5, 60, 15; start_x, start_y = rect.x + 30, rect.y + 70
        for i, key in enumerate(items_list):
            row, col = i // grid_cols, i % grid_cols; x, y = start_x + col * (slot_size + gap), start_y + row * (slot_size + gap)
            self._draw_item_icon(screen, key, pygame.Rect(x, y, slot_size, slot_size), self.sel_idx == i)
        if 0 <= self.sel_idx < len(items_list):
            key = items_list[self.sel_idx]; data = ITEMS[key]; info_y = rect.bottom - 120
            pygame.draw.line(screen, (100, 100, 100), (rect.x, info_y), (rect.right, info_y))
            screen.blit(self.font_main.render(data['name'], True, (255, 255, 255)), (rect.x + 30, info_y + 15))
            screen.blit(self.font_small.render(f"Price: {data['price']}G | {data['desc']}", True, (255, 215, 0)), (rect.x + 30, info_y + 45))

    def _draw_inventory(self, screen, w, h, inv):
        iw, ih = 500, 400; rect = pygame.Rect(w//2 - iw//2, h//2 - ih//2, iw, ih)
        pygame.draw.rect(screen, (30, 30, 40), rect); pygame.draw.rect(screen, (255, 255, 0), rect, 2)
        screen.blit(self.font_big.render("INVENTORY", True, (255, 255, 0)), (rect.x + 20, rect.y + 20))
        items_list = list(ITEMS.keys())
        grid_cols, slot_size, gap = 5, 60, 15; start_x, start_y = rect.x + 30, rect.y + 70
        for i, key in enumerate(items_list):
            row, col = i // grid_cols, i % grid_cols; x, y = start_x + col * (slot_size + gap), start_y + row * (slot_size + gap); r = pygame.Rect(x, y, slot_size, slot_size)
            count = inv.items.get(key, 0); self._draw_item_icon(screen, key, r, self.sel_idx == i)
            if count > 0:
                cnt_txt = self.font_small.render(str(count), True, (255, 255, 255))
                screen.blit(cnt_txt, cnt_txt.get_rect(bottomright=(r.right-2, r.bottom-2)))
            else:
                s = pygame.Surface((slot_size, slot_size), pygame.SRCALPHA); s.fill((0, 0, 0, 150)); screen.blit(s, r)
        if 0 <= self.sel_idx < len(items_list):
            key = items_list[self.sel_idx]; data = ITEMS[key]; info_y = rect.bottom - 100
            pygame.draw.line(screen, (100, 100, 100), (rect.x, info_y), (rect.right, info_y))
            screen.blit(self.font_main.render(data['name'], True, (255, 255, 255)), (rect.x + 30, info_y + 15))
            screen.blit(self.font_small.render(f"Owned: {inv.items.get(key,0)} | {data['desc']}", True, (200, 200, 200)), (rect.x + 30, info_y + 45))

    def _draw_spectator_ui(self, screen, sw, sh):
        txt = self.font_big.render("SPECTATOR MODE", True, (150, 150, 255))
        screen.blit(txt, (sw//2 - txt.get_width()//2, 50))

    def handle_input(self, event):
        if event.type != pygame.KEYDOWN: return
        key = event.key
        items_list = list(ITEMS.keys())
        if self.show_vending:
            if key == pygame.K_UP: self.sel_idx = (self.sel_idx - 1) % len(items_list)
            elif key == pygame.K_DOWN: self.sel_idx = (self.sel_idx + 1) % len(items_list)
            elif key == pygame.K_RETURN: 
                item_key = items_list[self.sel_idx]; price = ITEMS[item_key]['price']
                players = [e for e in self.ecs.get_entities_with(Identity) if self.ecs.get_component(e, Identity).is_player]
                if players:
                    pid = players[0]; stats = self.ecs.get_component(pid, Stats); inv = self.ecs.get_component(pid, Inventory)
                    if stats.coins >= price:
                        stats.coins -= price; inv.items[item_key] = inv.items.get(item_key, 0) + 1
                        self.show_alert(f"Bought {ITEMS[item_key]['name']}", (100, 255, 100))
                    else: self.show_alert("Not enough coins!", (255, 100, 100))
            elif key in [pygame.K_ESCAPE, pygame.K_e]: self.show_vending = False
        elif self.show_inventory:
            if key == pygame.K_UP: self.sel_idx = (self.sel_idx - 1) % len(items_list)
            elif key == pygame.K_DOWN: self.sel_idx = (self.sel_idx + 1) % len(items_list)
            elif key == pygame.K_RETURN:
                item_key = items_list[self.sel_idx]
                # Use Item Event or Direct Call
                self.event_bus.publish("USE_ITEM", {'entity_id': None, 'item_key': item_key}) # None means local player
            elif key in [pygame.K_ESCAPE, pygame.K_i]: self.show_inventory = False