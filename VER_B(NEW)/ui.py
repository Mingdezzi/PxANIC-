import pygame
import math
import random
from settings import *
from colors import *

# 미니맵에 표시할 타일 ID별 색상 정의 (R, G, B)
# 실제 사용하는 타일 ID에 맞춰서 색을 추가/수정해주세요.
MINIMAP_COLORS = {
    # [Floor]
    1110000: (100, 80, 50),    # Dirt (갈색)
    1110001: (34, 139, 34),    # Grass (초록색)
    1110002: (100, 100, 100),  # Stone (회색)
    
    # [Wall]
    3220000: (50, 50, 50),     # Wall (진한 회색)
    
    # [Object]
    5310000: (0, 0, 255),      # Water/Object (파랑)
    8321006: (255, 0, 0),      # Vending Machine (빨강)
}

# 기본 색상 (매핑되지 않은 타일용)
DEFAULT_COLORS = {
    'floor': (40, 40, 40),
    'wall': (100, 100, 100),
    'object': (200, 200, 100)
}

class UI:
    def __init__(self, game):
        self.game = game
        try:
            self.font_main = pygame.font.SysFont("malgungothic", 20)
            self.font_small = pygame.font.SysFont("malgungothic", 14)
            self.font_big = pygame.font.SysFont("malgungothic", 30, bold=True)
            self.font_digit = pygame.font.SysFont("consolas", 18, bold=True)
        except:
            self.font_main = pygame.font.Font(None, 24)
            self.font_small = pygame.font.Font(None, 18)
            self.font_big = pygame.font.Font(None, 40)
            self.font_digit = pygame.font.Font(None, 20)
            
        # [Fix] 참조 편의를 위한 단축 속성 설정 및 미니맵 변수 초기화
        self.map_manager = game.map_manager
        self.player = game.player
        self.minimap_surface = None
        self.radar_timer = 0
        self.radar_blips = []
            
        self.show_news = False
        self.news_timer = 0
        self.news_text = []

        # Motion Tracker Variables
        self.scan_angle = 0
        self.scan_dir = 1
        self.scan_speed = 2
        
        self.dim_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.dim_surface.fill((0, 0, 0, 180))

        # [Compatibility]
        self.custom_durations = DEFAULT_PHASE_DURATIONS.copy()

        # [State Variables]
        self.show_vending = False
        self.show_inventory = False
        self.show_voting = False
        self.sel_idx = 0
        
        # Alert System
        self.alert_text = ""
        self.alert_timer = 0
        self.alert_color = (255, 255, 255)

        # Spectator System
        self.spectator_follow_target = None
        self.spectator_scroll_y = 0
        self.entity_rects = []
        self.skip_btn_rect = None

        # [최적화] UI 패널 배경 미리 생성 (매 프레임 생성 방지)
        self.panel_bg_status = self._create_panel_bg(360, 110)
        self.panel_bg_env = self._create_panel_bg(160, 80)
        self.panel_bg_emotion = self._create_panel_bg(220, 140)
        self.panel_bg_police = self._create_panel_bg(200, 120)
        
    # [최적화] 배경 생성 헬퍼 함수
    def _create_panel_bg(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 20, 25, 200), (0, 0, w, h), border_radius=10)
        pygame.draw.rect(s, (80, 80, 90, 255), (0, 0, w, h), 2, border_radius=10)
        return s

    # [Fix] 미니맵 생성 함수 추가
    def generate_minimap_surface(self):
        w = self.map_manager.width
        h = self.map_manager.height
        surf = pygame.Surface((w, h))
        surf.fill((20, 20, 25)) # 전체 배경 (아주 어두운 남색)

        # 맵 데이터 가져오기
        floors = self.map_manager.map_data['floor']
        walls = self.map_manager.map_data['wall']
        objects = self.map_manager.map_data['object']
        
        # 픽셀 단위로 접근하기 위해 PixelArray 사용 (속도 향상)
        pixels = pygame.PixelArray(surf)

        for y in range(h):
            for x in range(w):
                # 1. 바닥 (Floor) 그리기
                f_val = floors[y][x]
                f_tid = f_val[0] if isinstance(f_val, (tuple, list)) else f_val
                if f_tid != 0:
                    col = MINIMAP_COLORS.get(f_tid, DEFAULT_COLORS['floor'])
                    pixels[x, y] = col
                
                # 2. 벽 (Wall) 덮어쓰기
                w_val = walls[y][x]
                w_tid = w_val[0] if isinstance(w_val, (tuple, list)) else w_val
                if w_tid != 0:
                    col = MINIMAP_COLORS.get(w_tid, DEFAULT_COLORS['wall'])
                    pixels[x, y] = col
                
                # 3. 사물 (Object) 덮어쓰기
                o_val = objects[y][x]
                o_tid = o_val[0] if isinstance(o_val, (tuple, list)) else o_val
                if o_tid != 0:
                    col = MINIMAP_COLORS.get(o_tid, DEFAULT_COLORS['object'])
                    pixels[x, y] = col
        
        pixels.close() # PixelArray 사용 종료
        self.cached_minimap = None # 캐시 무효화
        return surf

    def show_alert(self, text, color=(255, 255, 255)):
        self.alert_text = text
        self.alert_color = color
        self.alert_timer = pygame.time.get_ticks() + 3000

    def toggle_vending_machine(self):
        self.show_vending = not self.show_vending
        if self.show_vending: self.show_inventory = False; self.show_voting = False; self.sel_idx = 0

    def toggle_inventory(self):
        self.show_inventory = not self.show_inventory
        if self.show_inventory: self.show_vending = False; self.show_voting = False; self.sel_idx = 0

    def show_daily_news(self, news_log):
        self.show_news = True
        self.news_text = news_log if news_log else ["No special news today."]

    def calculate_game_time(self):
        phase = self.game.current_phase
        timer = self.game.state_timer
        
        start_times = {'DAWN': (4, 0), 'MORNING': (6, 0), 'NOON': (8, 0), 'AFTERNOON': (16, 0), 'EVENING': (17, 0), 'NIGHT': (19, 0)}
        phase_lengths = {'DAWN': 120, 'MORNING': 120, 'NOON': 480, 'AFTERNOON': 60, 'EVENING': 120, 'NIGHT': 540}
        
        durations = self.game.game.shared_data.get('custom_durations', DEFAULT_PHASE_DURATIONS)
        total_duration = durations.get(phase, 60)
        elapsed = max(0, total_duration - timer)
        ratio = elapsed / total_duration if total_duration > 0 else 0
        
        start_h, start_m = start_times.get(phase, (0, 0))
        add_minutes = int(phase_lengths.get(phase, 60) * ratio)
        current_minutes = start_m + add_minutes
        current_h = (start_h + current_minutes // 60) % 24
        current_m = current_minutes % 60
        return f"{current_h:02d}:{current_m:02d}"

    def draw_emotion_panel(self, screen, w, h):
        """플레이어의 감정 상태 및 이동 속도 상세 표시 패널 (우측 하단)"""
        player = self.game.player
        if not player or player.role == "SPECTATOR": return
        
        # 속도 계산 (PPS: Pixels Per Second)
        current_speed_frame = player.get_current_speed(getattr(player, 'weather', 'CLEAR'))
        current_speed_px = current_speed_frame * FPS 
        base_speed = 192 # settings.BASE_SPEED_PPS (초당 6타일 기준)
        ratio = (current_speed_px / base_speed) * 100
        
        # 1. 패널 배경 (화면 우측 하단)
        panel_w, panel_h = 220, 140
        x = w - panel_w - 20
        y = h - panel_h - 20
        
        # [최적화] 캐시된 배경 사용
        screen.blit(self.panel_bg_emotion, (x, y))

        # 2. 속도 모니터링
        speed_col = (200, 255, 200) if ratio >= 100 else (255, 100, 100)
        speed_text = self.font_main.render(f"SPEED: {int(current_speed_px)} px/s ({int(ratio)}%)", True, speed_col)
        screen.blit(speed_text, (x + 15, y + 15))

        # 구분선
        pygame.draw.line(screen, (80, 80, 90), (x+15, y+40), (x+panel_w-15, y+40), 1)

        # 3. 감정 및 상태 리스트 출력
        y_offset = 50
        active_statuses = []
        
        # Emotions
        for emo, val in player.emotions.items():
            if val:
                if emo == 'FEAR': active_statuses.append(('FEAR', 'Speed -30%', (100, 100, 255)))
                elif emo == 'RAGE': active_statuses.append(('RAGE', 'Stamina ∞', (255, 50, 50)))
                elif emo == 'PAIN': active_statuses.append(('PAIN', f'Lv.{val} Slow', (255, 100, 100)))
                elif emo == 'HAPPINESS': active_statuses.append(('HAPPY', 'Speed +10%', (255, 255, 100)))
                elif emo == 'ANXIETY': active_statuses.append(('ANXTY', 'Heartbeat', (255, 150, 50)))
            
        # Status Effects
        if player.status_effects.get('FATIGUE'): active_statuses.append(('FATIGUE', 'Speed -30%', (150, 150, 150)))
        if player.status_effects.get('DOPAMINE'): active_statuses.append(('DOPA', 'Speed +20%', (255, 0, 255)))
        
        if not active_statuses:
            text = self.font_small.render("- Normal State -", True, (150, 150, 150))
            screen.blit(text, (x + 15, y + y_offset))
        else:
            for title, desc, color in active_statuses[:4]: # Max 4 items
                text = self.font_small.render(f"■ {title}: {desc}", True, color)
                screen.blit(text, (x + 15, y + y_offset))
                y_offset += 20

    def draw_minimap(self, screen, w, h, npcs, is_blackout):
        """우측 하단, 감정 패널 바로 위에 미니맵 표시"""
        mm_w, mm_h = 200, 150
        x = w - mm_w - 20
        # Y위치: 전체높이 - 감정패널높이(140) - 여백(20) - 미니맵높이(150) - 간격(10)
        y = h - 140 - 20 - mm_h - 10
        
        mm_rect = pygame.Rect(x, y, mm_w, mm_h)
        
        # [수정] 투명도를 지원하는 임시 서피스 생성 및 그리기
        s = pygame.Surface((mm_rect.width, mm_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        screen.blit(s, mm_rect.topleft)
        
        pygame.draw.rect(screen, (100, 100, 120), mm_rect, 2)
        
        if not hasattr(self, 'minimap_surface') or not self.minimap_surface: 
            self.minimap_surface = self.generate_minimap_surface()
            
        if self.minimap_surface:
            # [Optimization] 캐싱된 스케일 이미지가 없으면 생성
            if not hasattr(self, 'cached_minimap') or self.cached_minimap is None:
                 self.cached_minimap = pygame.transform.scale(self.minimap_surface, (mm_w - 4, mm_h - 4))
            
            # 저장된 이미지 그리기
            screen.blit(self.cached_minimap, (mm_rect.x + 2, mm_rect.y + 2))
        
        # 플레이어 점
        map_w_px = self.map_manager.width * TILE_SIZE
        map_h_px = self.map_manager.height * TILE_SIZE
        if map_w_px > 0:
            dot_x = mm_rect.x + 2 + (self.player.rect.centerx / map_w_px) * (mm_w - 4)
            dot_y = mm_rect.y + 2 + (self.player.rect.centery / map_h_px) * (mm_h - 4)
            pygame.draw.circle(screen, (0, 255, 0), (int(dot_x), int(dot_y)), 3)

        # 특수 감지 (마피아 레이더, 경찰 CCTV 등)
        if self.player.role == "MAFIA" and is_blackout:
            current_time = pygame.time.get_ticks()
            if current_time > self.radar_timer:
                self.radar_timer = current_time + 2000
                self.radar_blips = []
                for n in npcs:
                    if not n.alive: continue
                    color = (0, 255, 0)
                    if n.role == "POLICE": color = (0, 100, 255)
                    elif n.role == "MAFIA": color = (255, 0, 0)
                    nx = mm_rect.x + 2 + (n.rect.centerx / map_w_px) * (mm_w - 4)
                    ny = mm_rect.y + 2 + (n.rect.centery / map_h_px) * (mm_h - 4)
                    self.radar_blips.append(((int(nx), int(ny)), color))
            for pos, col in self.radar_blips: pygame.draw.circle(screen, col, pos, 4)
        
        elif self.player.device_on:
            if self.player.role == "POLICE" and getattr(self, 'mafia_detected_by_cctv', False):
                for n in npcs:
                    if n.role == "MAFIA" and n.alive:
                        nx = mm_rect.x + 2 + (n.rect.centerx / map_w_px) * (mm_w - 4)
                        ny = mm_rect.y + 2 + (n.rect.centery / map_h_px) * (mm_h - 4)
                        if (pygame.time.get_ticks() // 200) % 2 == 0: pygame.draw.circle(screen, (255, 0, 0), (int(nx), int(ny)), 5)
            elif self.player.role in ["CITIZEN", "DOCTOR"]:
                 for n in npcs:
                    if not n.alive: continue
                    if math.sqrt((self.player.rect.centerx - n.rect.centerx)**2 + (self.player.rect.centery - n.rect.centery)**2) < 400 and getattr(n, 'is_moving', False):
                         nx = mm_rect.x + 2 + (n.rect.centerx / map_w_px) * (mm_w - 4)
                         ny = mm_rect.y + 2 + (n.rect.centery / map_h_px) * (mm_h - 4)
                         pygame.draw.circle(screen, (0, 255, 0), (int(nx), int(ny)), 3)

    def draw(self, screen):
        w, h = screen.get_size()
        
        self.draw_top_hud(screen, w, h)
        self.draw_controls(screen, w, h)
        
        if self.game.player.device_on:
            if self.game.player.role in ["CITIZEN", "DOCTOR"]:
                self.draw_motion_tracker(screen, w, h)
            elif self.game.player.role == "POLICE":
                self.draw_police_hud(screen, w, h)

        # [수정] 우측 하단 정보 패널 (미니맵이 감정 패널 위로)
        if self.game.player.role != "SPECTATOR":
            self.draw_minimap(screen, w, h, self.game.npcs, getattr(self.game, 'is_blackout', False))
            self.draw_emotion_panel(screen, w, h)

        # [추가] 스테미나 바 및 상호작용 바 그리기
        self.draw_stamina_bar(screen)
        self.draw_interaction(screen)
        
        self.draw_vote_ui(screen, w, h)
        
        if self.show_inventory: self.draw_inventory(screen, w, h)
        if self.show_vending: self.draw_vending_machine(screen, w, h)
        
        # Alert Drawing
        if pygame.time.get_ticks() < self.alert_timer:
            font = self.font_big
            txt_surf = font.render(self.alert_text, True, self.alert_color)
            bg_rect = txt_surf.get_rect(center=(w // 2, 150))
            bg_rect.inflate_ip(40, 20)
            
            s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            screen.blit(s, bg_rect.topleft)
            screen.blit(txt_surf, txt_surf.get_rect(center=bg_rect.center))

        if self.game.player.role == "SPECTATOR":
            self._draw_spectator_ui(screen, w, h)

        self.draw_daily_news(screen, w, h)

    def draw_top_hud(self, screen, w, h):
        self._draw_player_status(screen)
        self._draw_env_status(screen, w)

    def _draw_player_status(self, screen):
        """좌측 상단: 플레이어 상태 (HP, AP, Coin, Role)"""
        p = self.game.player
        x, y = 20, 20
        # [수정] 너비(w)와 높이(h)를 늘려 여유 공간 확보
        w, h = 360, 110  
        
        # [최적화] 캐시된 배경 사용
        screen.blit(self.panel_bg_status, (x, y))

        role_cols = {'CITIZEN': (100, 200, 100), 'POLICE': (50, 50, 255), 
                     'MAFIA': (200, 50, 50), 'DOCTOR': (200, 200, 255), 'SPECTATOR':(100,100,100)}
        c = role_cols.get(p.role, (200, 200, 200))
        
        # 아바타 영역
        avatar_rect = pygame.Rect(x + 15, y + 15, 60, 60)
        pygame.draw.rect(screen, (40, 40, 40), avatar_rect, border_radius=8)
        pygame.draw.rect(screen, c, avatar_rect, 3, border_radius=8)
        
        # 역할 이니셜
        role_char = p.role[0] 
        txt = self.font_big.render(role_char, True, c)
        screen.blit(txt, (avatar_rect.centerx - txt.get_width()//2, avatar_rect.centery - txt.get_height()//2))
        
        # 역할 이름 (아바타 하단)
        role_name = self.font_small.render(p.role, True, (200, 200, 200))
        screen.blit(role_name, (avatar_rect.centerx - role_name.get_width()//2, avatar_rect.bottom + 8))

        # [수정] 바 위치(bar_x)를 오른쪽으로 더 밀어서 'HP', 'AP' 글씨가 아바타와 겹치지 않게 함
        bar_x = x + 130  
        bar_w = 200      # 바 길이도 이에 맞춰 조정

        hp_ratio = max(0, p.hp / p.max_hp)
        self._draw_bar(screen, bar_x, y + 25, bar_w, 12, hp_ratio, (220, 60, 60), "HP")
        
        ap_ratio = max(0, p.ap / p.max_ap)
        self._draw_bar(screen, bar_x, y + 50, bar_w, 12, ap_ratio, (60, 150, 220), "AP")
        
        # 소지금 표시
        coin_txt = self.font_digit.render(f"{p.coins:03d} $", True, (255, 215, 0))
        screen.blit(coin_txt, (bar_x, y + 75))

    def _draw_env_status(self, screen, screen_w):
        game = self.game
        w, h = 160, 80
        x = screen_w - w - 20
        y = 20
        
        # [최적화] 캐시된 배경 사용
        screen.blit(self.panel_bg_env, (x, y))

        time_str = self.calculate_game_time()
        time_col = (100, 255, 100) if game.current_phase in ["MORNING", "DAY", "NOON", "AFTERNOON"] else (255, 100, 100)
        
        time_surf = self.font_big.render(time_str, True, time_col)
        screen.blit(time_surf, (x + w//2 - time_surf.get_width()//2, y + 10))
        
        weather_str = getattr(game, 'weather', 'CLEAR')
        info_str = f"Day {game.day_count} | {weather_str}"
        info_surf = self.font_small.render(info_str, True, (200, 200, 200))
        screen.blit(info_surf, (x + w//2 - info_surf.get_width()//2, y + 50))

    def _draw_bar(self, screen, x, y, w, h, ratio, color, label):
        pygame.draw.rect(screen, (40, 40, 40), (x, y, w, h), border_radius=4)
        fill_w = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=4)
        for i in range(x, x+w, 10):
            pygame.draw.line(screen, (0,0,0,50), (i, y), (i+5, y+h), 1)
        l_surf = self.font_small.render(label, True, (200, 200, 200))
        screen.blit(l_surf, (x - 25, y - 2))

    def draw_controls(self, screen, w, h):
        icon_size = 50
        gap = 10
        start_x = 20
        start_y = h - (icon_size * 2 + gap) - 20 
        
        def get_pos(col, row):
            return start_x + col * (icon_size + gap), start_y + row * (icon_size + gap)

        self.draw_key_icon(screen, *get_pos(0, 0), "I", "인벤토리")
        self.draw_key_icon(screen, *get_pos(1, 0), "Z", "투표")
        self.draw_key_icon(screen, *get_pos(2, 0), "E", "상호작용")
        
        role = self.game.player.role
        if role in ["CITIZEN", "DOCTOR"]:
            q_label = "동체탐지"
        elif role == "POLICE":
            q_label = "사이렌"
        else:
            q_label = "특수스킬"
        
        self.draw_key_icon(screen, *get_pos(0, 1), "Q", q_label)
        self.draw_key_icon(screen, *get_pos(1, 1), "R", "재장전")
        self.draw_key_icon(screen, *get_pos(2, 1), "V", "행동")

    def draw_key_icon(self, screen, x, y, key, label):
        rect = pygame.Rect(x, y, 50, 50)
        # 버튼 배경
        pygame.draw.rect(screen, (40, 40, 50), rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 120), rect, 2, border_radius=8)
        
        # 1. 키 텍스트 (상단 배치, 크기 조정)
        text_surf = self.font_main.render(key, True, (255, 255, 255))
        screen.blit(text_surf, (x + 25 - text_surf.get_width()//2, y + 4))
        
        # 2. 라벨 텍스트 (박스 내부 하단 배치)
        lbl_surf = self.font_small.render(label, True, (200, 200, 200))
        # 폰트가 너무 길면 축소 시도 (한글 4글자 대응 등)
        if lbl_surf.get_width() > 46:
            lbl_surf = pygame.transform.smoothscale(lbl_surf, (44, int(lbl_surf.get_height() * (44/lbl_surf.get_width()))))
        screen.blit(lbl_surf, (x + 25 - lbl_surf.get_width()//2, y + 28))

    def draw_motion_tracker(self, screen, w, h):
        player = self.game.player
        if player.role == "SPECTATOR": return
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

        detect_range = 400
        detect_range_sq = detect_range * detect_range # [최적화] 거리 제곱값 미리 계산
        
        targets = []
        for npc in self.game.npcs:
            if not npc.alive: continue
            
            # [최적화] 제곱 거리 사용으로 math.sqrt 호출 제거
            dist_sq = (player.rect.centerx - npc.rect.centerx)**2 + (player.rect.centery - npc.rect.centery)**2
            if dist_sq > detect_range_sq: continue
            
            dx = (npc.rect.centerx - player.rect.centerx) / detect_range
            dy = (npc.rect.centery - player.rect.centery) / detect_range
            tx = cx + dx * radius
            ty = (cy + 60) + dy * radius
            
            if screen_rect.collidepoint(tx, ty):
                targets.append((tx, ty))

        for tx, ty in targets:
            pygame.draw.circle(screen, (150, 255, 150), (int(tx), int(ty)), 4)
            s = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(s, (50, 200, 50, 100), (10, 10), 8)
            screen.blit(s, (tx-10, ty-10))

        for i in range(screen_rect.top, screen_rect.bottom, 4):
            pygame.draw.line(screen, (0, 20, 0), (screen_rect.left, i), (screen_rect.right, i), 1)
            
        dist_val = f"{int(detect_range/32)}m"
        lbl = self.font_digit.render(f"RNG: {dist_val}", True, (50, 180, 50))
        screen.blit(lbl, (cx - 30, cy + 90))
        title = self.font_small.render("MOTION TRACKER", True, (150, 150, 150))
        screen.blit(title, (cx - title.get_width()//2, frame_rect.top + 10))

    def draw_police_hud(self, screen, w, h):
        x, y = 240, h - 200
        
        # [최적화] 캐시된 배경 사용
        screen.blit(self.panel_bg_police, (x, y))
        
        t = self.font_main.render("POLICE TERMINAL", True, (100, 200, 255))
        screen.blit(t, (x + 100 - t.get_width()//2, y + 10))
        bullets = getattr(self.game.player, 'bullets_fired_today', 0)
        t2 = self.font_small.render(f"Shots Fired: {bullets}/1", True, (200, 200, 200))
        screen.blit(t2, (x + 20, y + 50))

    def draw_interaction(self, screen):
        player = self.game.player
        if player.e_key_pressed:
            now = pygame.time.get_ticks()
            hold_time = now - player.interaction_hold_timer
            ratio = min(1.0, hold_time / 1000.0)
            
            # [수정] 카메라 오프셋과 줌을 적용한 화면 좌표 계산
            cam_x, cam_y = self.game.camera.x, self.game.camera.y
            zoom = self.game.zoom_level
            
            screen_x = (player.rect.centerx - cam_x) * zoom
            screen_y = (player.rect.centery - cam_y) * zoom
            
            # 캐릭터 머리 위 (약 50px 위)
            draw_x = screen_x
            draw_y = screen_y - (50 * zoom)
            
            w, h = 40, 6
            # 바 배경
            pygame.draw.rect(screen, (50, 50, 50), (draw_x - w//2, draw_y, w, h))
            # 노란색 게이지
            pygame.draw.rect(screen, (255, 255, 0), (draw_x - w//2, draw_y, w * ratio, h))

    def draw_stamina_bar(self, screen):
        # [신규] 스테미나(기력) 표시 함수
        player = self.game.player
        if player.breath_gauge >= 100: return # 기력이 가득 차 있으면 표시 안 함
        
        cam_x, cam_y = self.game.camera.x, self.game.camera.y
        zoom = self.game.zoom_level
        
        screen_x = (player.rect.centerx - cam_x) * zoom
        screen_y = (player.rect.centery - cam_y) * zoom
        
        # 상호작용 바보다 조금 더 위에 표시 (겹치지 않게 -60px)
        draw_x = screen_x
        draw_y = screen_y - (60 * zoom)
        
        w, h = 40, 5
        ratio = max(0, player.breath_gauge / 100.0)
        
        # 배경
        pygame.draw.rect(screen, (30, 30, 30), (draw_x - w//2, draw_y, w, h))
        # 파란색 게이지 (기력)
        pygame.draw.rect(screen, (100, 200, 255), (draw_x - w//2, draw_y, w * ratio, h))
    
    def draw_vote_ui(self, screen, w, h):
        if self.game.current_phase != "VOTE": return
        center_x = w // 2
        msg = self.font_big.render("VOTING SESSION", True, (255, 50, 50))
        screen.blit(msg, (center_x - msg.get_width()//2, 100))
        desc = self.font_main.render("Press 'Z' to Vote", True, (200, 200, 200))
        screen.blit(desc, (center_x - desc.get_width()//2, 140))

    # [Removed] draw_vote_button deleted

    def draw_vote_popup(self, screen, sw, sh, npcs, player, current_target):
        w, h = 400, 500
        cx, cy = sw // 2, sh // 2
        panel_rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        
        # [최적화] 기존 self.dim_surface 재사용 (매 프레임 Surface 생성 방지)
        if self.dim_surface.get_size() != (sw, sh):
             self.dim_surface = pygame.Surface((sw, sh), pygame.SRCALPHA)
             self.dim_surface.fill((0, 0, 0, 150))
        screen.blit(self.dim_surface, (0, 0))
        
        pygame.draw.rect(screen, (40, 40, 45), panel_rect, border_radius=12)
        pygame.draw.rect(screen, (100, 100, 120), panel_rect, 2, border_radius=12)
        title = self.font_big.render("VOTE TARGET", True, (255, 255, 255))
        screen.blit(title, (cx - title.get_width()//2, panel_rect.top + 20))
        candidates = [player] + [n for n in npcs if n.alive]
        candidate_rects = []
        start_y = panel_rect.top + 80
        for c in candidates:
            row_rect = pygame.Rect(panel_rect.left + 20, start_y, w - 40, 40)
            is_selected = (current_target == c)
            col = (50, 50, 150) if is_selected else (60, 60, 70)
            if row_rect.collidepoint(pygame.mouse.get_pos()):
                col = (80, 80, 100)
            pygame.draw.rect(screen, col, row_rect, border_radius=4)
            info = f"{c.name} ({c.role})"
            t = self.font_main.render(info, True, (220, 220, 220))
            screen.blit(t, (row_rect.left + 10, row_rect.centery - t.get_height()//2))
            candidate_rects.append((c, row_rect))
            start_y += 50
        return candidate_rects

    def draw_daily_news(self, screen, w, h):
        if not self.show_news: return
        screen.blit(self.dim_surface, (0, 0))
        center_x, center_y = w // 2, h // 2
        paper_w, paper_h = 500, 600
        paper_rect = pygame.Rect(center_x - paper_w//2, center_y - paper_h//2, paper_w, paper_h)
        pygame.draw.rect(screen, (240, 230, 200), paper_rect)
        pygame.draw.rect(screen, (100, 90, 80), paper_rect, 4)
        title = self.font_big.render("DAILY NEWS", True, (50, 40, 30))
        screen.blit(title, (center_x - title.get_width()//2, paper_rect.top + 30))
        line_y = paper_rect.top + 80
        pygame.draw.line(screen, (50, 40, 30), (paper_rect.left + 20, line_y), (paper_rect.right - 20, line_y), 2)
        y_offset = 110
        for line in self.news_text:
            t = self.font_main.render(line, True, (20, 20, 20))
            screen.blit(t, (center_x - t.get_width()//2, paper_rect.top + y_offset))
            y_offset += 35
        close_txt = self.font_small.render("Press SPACE to Close", True, (100, 100, 100))
        screen.blit(close_txt, (center_x - close_txt.get_width()//2, paper_rect.bottom - 40))

    def handle_keyboard(self, key, npcs=None):
        if self.show_news:
            if key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE]: self.show_news = False
            return True
        items_list = list(ITEMS.keys())
        if self.show_vending:
            if key == pygame.K_UP: self.sel_idx = (self.sel_idx - 1) % len(items_list)
            elif key == pygame.K_DOWN: self.sel_idx = (self.sel_idx + 1) % len(items_list)
            elif key == pygame.K_RETURN: return self.player.buy_item(items_list[self.sel_idx])
            elif key in [pygame.K_ESCAPE, pygame.K_e]: self.show_vending = False
            return True
        if self.show_inventory:
            if key == pygame.K_UP: self.sel_idx = (self.sel_idx - 1) % len(items_list)
            elif key == pygame.K_DOWN: self.sel_idx = (self.sel_idx + 1) % len(items_list)
            elif key == pygame.K_RETURN: return self.player.use_item(items_list[self.sel_idx])
            elif key in [pygame.K_ESCAPE, pygame.K_i]: self.show_inventory = False
            return True
        if self.show_voting:
            targets = [n for n in npcs if n.alive] + ([self.player] if self.player.alive else [])
            if not targets: return False
            if key == pygame.K_UP: self.sel_idx = (self.sel_idx - 1) % len(targets)
            elif key == pygame.K_DOWN: self.sel_idx = (self.sel_idx + 1) % len(targets)
            elif key == pygame.K_RETURN: targets[self.sel_idx].vote_count += 1; self.show_voting = False; return "VOTED"
            return True
        if key == pygame.K_ESCAPE:
            self.show_vending = False
            self.show_inventory = False
            self.show_voting = False
            self.show_news = False
            return True
        return False

    def draw_item_icon(self, screen, key, rect, is_sel):
        col = (60, 60, 80) if not is_sel else (100, 100, 150)
        pygame.draw.rect(screen, col, rect, border_radius=5)
        if is_sel: pygame.draw.rect(screen, (255, 255, 0), rect, 2, border_radius=5)
        c = rect.center
        if key == 'TANGERINE': pygame.draw.circle(screen, (255, 165, 0), c, 10)
        elif key == 'CHOCOBAR': pygame.draw.rect(screen, (139, 69, 19), (c[0]-8, c[1]-12, 16, 24))
        elif key == 'MEDKIT': 
            pygame.draw.rect(screen, (255, 255, 255), (c[0]-10, c[1]-8, 20, 16))
            pygame.draw.line(screen, (255, 0, 0), (c[0], c[1]-5), (c[0], c[1]+5), 2); pygame.draw.line(screen, (255, 0, 0), (c[0]-5, c[1]), (c[0]+5, c[1]), 2)
        elif key == 'KEY': pygame.draw.line(screen, (255, 215, 0), (c[0]-5, c[1]+5), (c[0]+5, c[1]-5), 3)
        elif key == 'BATTERY': pygame.draw.rect(screen, (0, 255, 0), (c[0]-6, c[1]-10, 12, 20))
        elif key == 'TASER': pygame.draw.rect(screen, (50, 50, 200), (c[0]-10, c[1]-5, 20, 10))
        else: pygame.draw.circle(screen, (200, 200, 200), c, 5)

    def draw_vending_machine(self, screen, w, h):
        vw, vh = 600, 500; rect_obj = pygame.Rect(w//2 - vw//2, h//2 - vh//2, vw, vh)
        pygame.draw.rect(screen, (20, 20, 30), rect_obj); pygame.draw.rect(screen, (0, 255, 255), rect_obj, 3)
        screen.blit(self.font_big.render("SHOP", True, (0, 255, 255)), (rect_obj.x + 20, rect_obj.y + 20))
        items_list = list(ITEMS.keys())
        grid_cols, slot_size, gap = 5, 60, 15; start_x, start_y = rect_obj.x + 30, rect_obj.y + 70
        for i, key in enumerate(items_list):
            row, col = i // grid_cols, i % grid_cols; x, y = start_x + col * (slot_size + gap), start_y + row * (slot_size + gap)
            self.draw_item_icon(screen, key, pygame.Rect(x, y, slot_size, slot_size), self.sel_idx == i)
        if 0 <= self.sel_idx < len(items_list):
            key = items_list[self.sel_idx]; data = ITEMS[key]; info_y = rect_obj.bottom - 120
            pygame.draw.line(screen, (100, 100, 100), (rect_obj.x, info_y), (rect_obj.right, info_y))
            screen.blit(self.font_main.render(data['name'], True, (255, 255, 255)), (rect_obj.x + 30, info_y + 15))
            screen.blit(self.font_small.render(f"Price: {data['price']}G", True, (255, 215, 0)), (rect_obj.x + 30, info_y + 45))
            screen.blit(self.font_small.render(data['desc'], True, (200, 200, 200)), (rect_obj.x + 30, info_y + 75))

    def draw_inventory(self, screen, w, h):
        iw, ih = 500, 400; rect_obj = pygame.Rect(w//2 - iw//2, h//2 - ih//2, iw, ih)
        pygame.draw.rect(screen, (30, 30, 40), rect_obj); pygame.draw.rect(screen, (255, 255, 0), rect_obj, 2)
        screen.blit(self.font_big.render("INVENTORY", True, (255, 255, 0)), (rect_obj.x + 20, rect_obj.y + 20))
        items_list = list(ITEMS.keys())
        grid_cols, slot_size, gap = 5, 60, 15; start_x, start_y = rect_obj.x + 30, rect_obj.y + 70
        for i, key in enumerate(items_list):
            row, col = i // grid_cols, i % grid_cols; x, y = start_x + col * (slot_size + gap), start_y + row * (slot_size + gap); r = pygame.Rect(x, y, slot_size, slot_size)
            count = self.player.inventory.get(key, 0); self.draw_item_icon(screen, key, r, self.sel_idx == i)
            if count > 0:
                cnt_txt = self.font_small.render(str(count), True, (255, 255, 255))
                screen.blit(cnt_txt, cnt_txt.get_rect(bottomright=(r.right-2, r.bottom-2)))
            else:
                s = pygame.Surface((slot_size, slot_size), pygame.SRCALPHA); s.fill((0, 0, 0, 150)); screen.blit(s, r)
        if 0 <= self.sel_idx < len(items_list):
            key = items_list[self.sel_idx]; data = ITEMS[key]; info_y = rect_obj.bottom - 100
            pygame.draw.line(screen, (100, 100, 100), (rect_obj.x, info_y), (rect_obj.right, info_y))
            screen.blit(self.font_main.render(data['name'], True, (255, 255, 255)), (rect_obj.x + 30, info_y + 15))
            screen.blit(self.font_small.render(f"Owned: {self.player.inventory.get(key,0)}", True, (200, 200, 200)), (rect_obj.x + 30, info_y + 45))
            screen.blit(self.font_small.render(data['desc'], True, (150, 150, 150)), (rect_obj.x + 30, info_y + 70))

    def _draw_spectator_ui(self, screen, w, h):
        # [수정] 버튼 위치 변경 (w - 120 -> w - 300)
        # 환경 정보창이 약 180px 차지하므로 더 왼쪽으로 이동
        self.skip_btn_rect = pygame.Rect(w - 300, 20, 100, 40)
        pygame.draw.rect(screen, (150, 50, 50), self.skip_btn_rect, border_radius=8)
        txt = self.font_small.render("SKIP PHASE", True, (255, 255, 255))
        screen.blit(txt, (self.skip_btn_rect.centerx - txt.get_width()//2, self.skip_btn_rect.centery - txt.get_height()//2))
        
        self.entity_rects = []
        start_y = 80 - self.spectator_scroll_y
        right_panel_x = w - 180
        
        for npc in self.game.npcs:
            if not npc.alive: continue
            
            r = pygame.Rect(right_panel_x, start_y, 160, 30)
            
            if 0 < start_y < h:
                col = (100, 255, 100) if npc.role == "CITIZEN" else ((255, 100, 100) if npc.role == "MAFIA" else (200, 200, 255))
                pygame.draw.rect(screen, (50, 50, 50), r, border_radius=4)
                pygame.draw.rect(screen, col, (r.left, r.top, 5, r.height), border_top_left_radius=4, border_bottom_left_radius=4)
                
                name_txt = self.font_small.render(f"{npc.name} ({npc.role})", True, (200, 200, 200))
                screen.blit(name_txt, (r.left + 10, r.centery - name_txt.get_height()//2))
                
                self.entity_rects.append((r, npc))
            
            start_y += 35