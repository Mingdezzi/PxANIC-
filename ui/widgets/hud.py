import pygame
import math
from core.resource_manager import ResourceManager
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, DEFAULT_PHASE_DURATIONS

class HUD:
    def __init__(self, ui_manager):
        self.ui_manager = ui_manager
        self.rm = ResourceManager.get_instance()
        
        # 폰트 로드
        self.font_main = self.rm.get_font("malgungothic", 20)
        self.font_small = self.rm.get_font("malgungothic", 14)
        self.font_big = self.rm.get_font("malgungothic", 30)
        self.font_digit = self.rm.get_font("consolas", 18)
        
        # 패널 배경 캐시
        self.panel_bg_status = self._create_panel_bg(360, 110)
        self.panel_bg_env = self._create_panel_bg(160, 80)
        self.panel_bg_emotion = self._create_panel_bg(220, 140)
        self.panel_bg_police = self._create_panel_bg(200, 120)

        # Motion Tracker
        self.scan_angle = 0
        self.scan_dir = 1
        self.scan_speed = 2

    def _create_panel_bg(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 20, 25, 200), (0, 0, w, h), border_radius=10)
        pygame.draw.rect(s, (80, 80, 90, 255), (0, 0, w, h), 2, border_radius=10)
        return s

    def draw(self, screen, player, game_state):
        w, h = screen.get_size()
        self._draw_player_status(screen, player)
        self._draw_env_status(screen, w, game_state)
        
        if player.role.main_role != "SPECTATOR":
            self._draw_emotion_panel(screen, w, h, player)

        if player.graphics.device_on:
            if player.role.main_role in ["CITIZEN", "DOCTOR"]:
                self._draw_motion_tracker(screen, w, h, player, game_state)
            elif player.role.main_role == "POLICE":
                self._draw_police_hud(screen, w, h, player)
                
        self._draw_stamina_bar(screen, player)
        self._draw_interaction_bar(screen, player)

    def _draw_player_status(self, screen, player):
        x, y = 20, 20
        screen.blit(self.panel_bg_status, (x, y))

        role_cols = {'CITIZEN': (100, 200, 100), 'POLICE': (50, 50, 255), 
                     'MAFIA': (200, 50, 50), 'DOCTOR': (200, 200, 255), 'SPECTATOR':(100,100,100)}
        c = role_cols.get(player.role.main_role, (200, 200, 200))
        
        # 아바타
        avatar_rect = pygame.Rect(x + 15, y + 15, 60, 60)
        pygame.draw.rect(screen, (40, 40, 40), avatar_rect, border_radius=8)
        pygame.draw.rect(screen, c, avatar_rect, 3, border_radius=8)
        
        role_char = player.role.main_role[0] 
        txt = self.font_big.render(role_char, True, c)
        screen.blit(txt, (avatar_rect.centerx - txt.get_width()//2, avatar_rect.centery - txt.get_height()//2))
        
        role_name = self.font_small.render(player.role.main_role, True, (200, 200, 200))
        screen.blit(role_name, (avatar_rect.centerx - role_name.get_width()//2, avatar_rect.bottom + 8))

        bar_x = x + 130  
        bar_w = 200

        hp_ratio = max(0, player.stats.hp / player.stats.max_hp)
        self._draw_bar(screen, bar_x, y + 25, bar_w, 12, hp_ratio, (220, 60, 60), "HP")
        
        ap_ratio = max(0, player.stats.ap / player.stats.max_ap)
        self._draw_bar(screen, bar_x, y + 50, bar_w, 12, ap_ratio, (60, 150, 220), "AP")
        
        coin_txt = self.font_digit.render(f"{player.inventory.coins:03d} $", True, (255, 215, 0))
        screen.blit(coin_txt, (bar_x, y + 75))

    def _draw_env_status(self, screen, screen_w, game_state):
        w, h = 160, 80
        x = screen_w - w - 20
        y = 20
        screen.blit(self.panel_bg_env, (x, y))

        time_str = self._calculate_game_time(game_state)
        time_col = (100, 255, 100) if game_state['phase'] in ["MORNING", "DAY", "NOON", "AFTERNOON"] else (255, 100, 100)
        
        time_surf = self.font_big.render(time_str, True, time_col)
        screen.blit(time_surf, (x + w//2 - time_surf.get_width()//2, y + 10))
        
        weather_str = game_state.get('weather', 'CLEAR')
        info_str = f"Day {game_state.get('day_count', 1)} | {weather_str}"
        info_surf = self.font_small.render(info_str, True, (200, 200, 200))
        screen.blit(info_surf, (x + w//2 - info_surf.get_width()//2, y + 50))

    def _draw_emotion_panel(self, screen, w, h, player):
        panel_w, panel_h = 220, 140
        x = w - panel_w - 20
        y = h - panel_h - 20
        screen.blit(self.panel_bg_emotion, (x, y))

        # Speed (여기서는 단순 표시만, 실제 로직은 MovementSystem 참조)
        # speed = player.physics.speed * multiplier... 복잡하므로 대략적 표시
        speed_txt = self.font_main.render(f"Move State: {player.physics.move_state}", True, (200, 255, 200))
        screen.blit(speed_txt, (x + 15, y + 15))

        pygame.draw.line(screen, (80, 80, 90), (x+15, y+40), (x+panel_w-15, y+40), 1)

        y_offset = 50
        active_statuses = []
        
        for emo, val in player.stats.emotions.items():
            if val:
                active_statuses.append((emo[:4], f'Lv.{val}', (255, 100, 100)))
        
        for k, v in player.stats.status_effects.items():
            if v:
                active_statuses.append((k[:4], 'Active', (150, 150, 255)))

        if not active_statuses:
            text = self.font_small.render("- Normal State -", True, (150, 150, 150))
            screen.blit(text, (x + 15, y + y_offset))
        else:
            for title, desc, color in active_statuses[:4]:
                text = self.font_small.render(f"■ {title}: {desc}", True, color)
                screen.blit(text, (x + 15, y + y_offset))
                y_offset += 20

    def _draw_motion_tracker(self, screen, w, h, player, game_state):
        cx, cy = 340, h - 150 
        radius = 90
        
        # 프레임
        frame_rect = pygame.Rect(cx - 100, cy - 110, 200, 240)
        pygame.draw.rect(screen, (30, 35, 30), frame_rect, border_radius=15)
        pygame.draw.rect(screen, (60, 70, 60), frame_rect, 3, border_radius=15)
        
        # 스캔 라인
        self.scan_angle += self.scan_dir * self.scan_speed
        if self.scan_angle > 45 or self.scan_angle < -45: self.scan_dir *= -1
        
        scan_rad = math.radians(self.scan_angle - 90)
        ex = cx + math.cos(scan_rad) * radius
        ey = (cy + 60) + math.sin(scan_rad) * radius
        pygame.draw.line(screen, (50, 200, 50), (cx, cy + 60), (ex, ey), 2)
        
        # 타겟 점 (게임 상태에서 NPCs 정보를 받아와야 함)
        npcs = game_state.get('npcs', [])
        detect_range = 400
        
        for npc in npcs:
            if not npc.components['stats'].alive: continue
            dist_sq = (player.transform.x - npc.transform.x)**2 + (player.transform.y - npc.transform.y)**2
            if dist_sq > detect_range**2: continue
            
            dx = (npc.transform.x - player.transform.x) / detect_range
            dy = (npc.transform.y - player.transform.y) / detect_range
            tx = cx + dx * radius
            ty = (cy + 60) + dy * radius
            
            pygame.draw.circle(screen, (150, 255, 150), (int(tx), int(ty)), 4)

    def _draw_police_hud(self, screen, w, h, player):
        x, y = 240, h - 200
        screen.blit(self.panel_bg_police, (x, y))
        t = self.font_main.render("POLICE TERMINAL", True, (100, 200, 255))
        screen.blit(t, (x + 100 - t.get_width()//2, y + 10))
        
        bullets = player.role.bullets_fired_today
        t2 = self.font_small.render(f"Shots Fired: {bullets}/1", True, (200, 200, 200))
        screen.blit(t2, (x + 20, y + 50))

    def _draw_stamina_bar(self, screen, player):
        # 플레이어 머리 위 표시 (좌표 변환 필요: ui_manager에서 camera 정보 받아야 함)
        pass # UI Manager에서 Camera 좌표 받아서 그리는 로직이 필요하므로, HUD보다는 별도 메서드가 나음
             # 혹은 draw 호출 시 camera 정보를 인자로 받도록 수정

    def _draw_interaction_bar(self, screen, player):
        pass

    def _draw_bar(self, screen, x, y, w, h, ratio, color, label):
        pygame.draw.rect(screen, (40, 40, 40), (x, y, w, h), border_radius=4)
        fill_w = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=4)
        for i in range(x, x+w, 10):
            pygame.draw.line(screen, (0,0,0,50), (i, y), (i+5, y+h), 1)
        l_surf = self.font_small.render(label, True, (200, 200, 200))
        screen.blit(l_surf, (x - 25, y - 2))

    def _calculate_game_time(self, game_state):
        phase = game_state.get('phase', 'MORNING')
        timer = game_state.get('state_timer', 0)
        
        start_times = {'DAWN': (4, 0), 'MORNING': (6, 0), 'NOON': (8, 0), 'AFTERNOON': (16, 0), 'EVENING': (17, 0), 'NIGHT': (19, 0)}
        phase_lengths = {'DAWN': 120, 'MORNING': 120, 'NOON': 480, 'AFTERNOON': 60, 'EVENING': 120, 'NIGHT': 540}
        
        total_duration = DEFAULT_PHASE_DURATIONS.get(phase, 60)
        
        # [Fix] timer는 0에서 total_duration까지 증가함
        # elapsed를 timer 그 자체로 사용해야 시간이 흐름
        elapsed = min(total_duration, timer)
        ratio = elapsed / total_duration if total_duration > 0 else 0
        
        start_h, start_m = start_times.get(phase, (0, 0))
        add_minutes = int(phase_lengths.get(phase, 60) * ratio)
        current_minutes = start_m + add_minutes
        current_h = (start_h + current_minutes // 60) % 24
        current_m = current_minutes % 60
        return f"{current_h:02d}:{current_m:02d}"
