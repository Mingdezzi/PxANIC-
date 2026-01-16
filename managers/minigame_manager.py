# 기존 MiniGameManager 코드를 그대로 가져오되, 일부 의존성 수정
import pygame
import random
import math
from colors import *

class MiniGameManager:
    def __init__(self):
        self.active = False
        self.game_type = None
        self.difficulty = 1
        self.on_success = None
        self.on_fail = None

        self.width = 240
        self.height = 160
        self.bg_color = (25, 25, 35)
        self.border_color = (180, 180, 190)

        # 폰트 로드
        try:
            self.font_title = pygame.font.SysFont("arial", 20, bold=True)
            self.font_ui = pygame.font.SysFont("arial", 14)
            self.font_big = pygame.font.SysFont("arial", 30, bold=True)
        except:
            self.font_title = pygame.font.Font(None, 26)
            self.font_ui = pygame.font.Font(None, 20)
            self.font_big = pygame.font.Font(None, 34)

        self.start_time = 0
        self.duration = 10000

        # 게임별 상태 변수들
        self.mash_progress = 0; self.mash_decay = 0.35
        self.timing_cursor = 0; self.timing_dir = 1; self.timing_speed = 3; self.timing_target = (0, 0)
        self.cmd_seq = []; self.cmd_idx = 0
        self.circle_angle = 0; self.circle_speed = 2; self.circle_target_angle = 0; self.circle_tolerance = 35

        self.wires_left = []; self.wires_right = []; self.wire_connections = {}
        self.wire_l_idx = 0; self.wire_r_idx = 0; self.wire_selected_l = -1
        self.wire_state = 0

        self.memory_grid = []; self.memory_seq = []; self.memory_next = 1
        self.mem_cursor = [0, 0]
        
        self.lock_pins = []
        self.lock_targets = []
        self.lock_current_pin = 0
        self.lock_cursor = 0.0
        self.lock_dir = 1.0
        self.lock_speed = 0.02

    def start(self, game_type, difficulty, on_success, on_fail):
        self.active = True
        self.game_type = game_type
        self.difficulty = difficulty
        self.on_success = on_success
        self.on_fail = on_fail
        self.start_time = pygame.time.get_ticks()

        base_time = 10000
        if game_type in ['WIRING', 'MEMORY', 'LOCKPICK']: base_time = 15000
        self.duration = base_time

        self.init_specific_game()

    def init_specific_game(self):
        if self.game_type == 'MASHING':
            self.mash_progress = 20
        elif self.game_type == 'TIMING':
            self.timing_cursor = 0; self.timing_dir = 1; self.timing_speed = 3 + self.difficulty
            w = 60 - (self.difficulty*4); c = self.width//2; self.timing_target = (c-w//2 - 20, c+w//2 - 20)
        elif self.game_type == 'COMMAND':
            self.cmd_seq = [random.choice(['UP','DOWN','LEFT','RIGHT']) for _ in range(3+self.difficulty)]; self.cmd_idx = 0
        elif self.game_type == 'CIRCLE':
            self.circle_angle = 0; self.circle_speed = 2 + self.difficulty*0.5; self.circle_target_angle = random.randint(45, 315)
        elif self.game_type == 'WIRING':
            safe_colors = [(255, 50, 50), (50, 100, 255), (255, 200, 50), (50, 200, 50)]
            random.shuffle(safe_colors)
            self.wires_left = [{'color': c, 'id': i} for i, c in enumerate(safe_colors)]
            indices = list(range(4)); random.shuffle(indices)
            self.wires_right = [{'color': safe_colors[i], 'id': i} for i in indices]
            self.wire_connections = {}; self.wire_l_idx = 0; self.wire_r_idx = 0; self.wire_selected_l = -1; self.wire_state = 0
        elif self.game_type == 'MEMORY':
            count = min(9, 3 + self.difficulty)
            cells = []
            for y in range(3):
                for x in range(3): cells.append((x,y))
            random.shuffle(cells)
            self.memory_grid = [[None]*3 for _ in range(3)]
            for i in range(count):
                x, y = cells[i]
                self.memory_grid[y][x] = {'num': i+1, 'clicked': False}
            self.memory_next = 1; self.mem_cursor = [1, 1]
        elif self.game_type == 'LOCKPICK':
            num_pins = 3 + self.difficulty
            self.lock_pins = [0.0] * num_pins
            self.lock_targets = []
            self.lock_current_pin = 0
            self.lock_cursor = 0.0
            self.lock_dir = 1.0
            self.lock_speed = 0.03 + (self.difficulty * 0.005)
            for _ in range(num_pins):
                center = random.uniform(0.7, 0.9)
                width = 0.15 - (self.difficulty * 0.02)
                self.lock_targets.append((center - width/2, center + width/2))

    def update(self):
        if not self.active: return
        if pygame.time.get_ticks() - self.start_time > self.duration: self.fail_game(); return

        if self.game_type == 'MASHING':
            self.mash_progress = max(0, self.mash_progress - self.mash_decay)
        elif self.game_type == 'TIMING':
            self.timing_cursor += self.timing_speed * self.timing_dir
            if self.timing_cursor < 0 or self.timing_cursor > self.width - 40: self.timing_dir *= -1
        elif self.game_type == 'CIRCLE':
            self.circle_angle = (self.circle_angle + self.circle_speed) % 360
        elif self.game_type == 'LOCKPICK':
            self.lock_cursor += self.lock_speed * self.lock_dir
            if self.lock_cursor >= 1.0:
                self.lock_cursor = 1.0; self.lock_dir = -1.0
            elif self.lock_cursor <= 0.0:
                self.lock_cursor = 0.0; self.lock_dir = 1.0
            self.lock_pins[self.lock_current_pin] = self.lock_cursor

    def handle_event(self, event):
        if not self.active or event.type != pygame.KEYDOWN: return

        if self.game_type == 'MASHING':
            if event.key == pygame.K_SPACE:
                self.mash_progress += 12
                if self.mash_progress >= 100: self.success_game()
        elif self.game_type == 'TIMING':
            if event.key == pygame.K_SPACE:
                if self.timing_target[0] <= self.timing_cursor <= self.timing_target[1]: self.success_game()
                else: self.fail_game()
        elif self.game_type == 'COMMAND':
            target = self.cmd_seq[self.cmd_idx]
            k = event.key
            valid = (target=='UP' and k==pygame.K_UP) or (target=='DOWN' and k==pygame.K_DOWN) or (target=='LEFT' and k==pygame.K_LEFT) or (target=='RIGHT' and k==pygame.K_RIGHT)
            if valid:
                self.cmd_idx += 1
                if self.cmd_idx >= len(self.cmd_seq): self.success_game()
            else: self.fail_game()
        elif self.game_type == 'CIRCLE':
            if event.key == pygame.K_SPACE:
                diff = abs(self.circle_angle - self.circle_target_angle)
                if diff > 180: diff = 360 - diff
                if diff <= self.circle_tolerance: self.success_game()
                else: self.fail_game()
        elif self.game_type == 'WIRING':
            if self.wire_state == 0:
                if event.key == pygame.K_UP: self.wire_l_idx = max(0, self.wire_l_idx - 1)
                elif event.key == pygame.K_DOWN: self.wire_l_idx = min(3, self.wire_l_idx + 1)
                elif event.key == pygame.K_SPACE:
                    if self.wires_left[self.wire_l_idx]['id'] not in self.wire_connections:
                        self.wire_selected_l = self.wire_l_idx; self.wire_state = 1
            elif self.wire_state == 1:
                if event.key == pygame.K_UP: self.wire_r_idx = max(0, self.wire_r_idx - 1)
                elif event.key == pygame.K_DOWN: self.wire_r_idx = min(3, self.wire_r_idx + 1)
                elif event.key == pygame.K_LEFT: self.wire_state = 0; self.wire_selected_l = -1
                elif event.key == pygame.K_SPACE:
                    l_id = self.wires_left[self.wire_selected_l]['id']
                    if self.wires_left[self.wire_selected_l]['color'] == self.wires_right[self.wire_r_idx]['color']:
                        self.wire_connections[l_id] = self.wires_right[self.wire_r_idx]['id']
                        self.wire_state = 0; self.wire_selected_l = -1
                        if len(self.wire_connections) == 4: self.success_game()
                    else: self.fail_game()
        elif self.game_type == 'MEMORY':
            if event.key == pygame.K_UP: self.mem_cursor[1] = max(0, self.mem_cursor[1] - 1)
            elif event.key == pygame.K_DOWN: self.mem_cursor[1] = min(2, self.mem_cursor[1] + 1)
            elif event.key == pygame.K_LEFT: self.mem_cursor[0] = max(0, self.mem_cursor[0] - 1)
            elif event.key == pygame.K_RIGHT: self.mem_cursor[0] = min(2, self.mem_cursor[0] + 1)
            elif event.key == pygame.K_SPACE:
                cx, cy = self.mem_cursor
                item = self.memory_grid[cy][cx]
                if item and not item['clicked']:
                    if item['num'] == self.memory_next:
                        item['clicked'] = True; self.memory_next += 1
                        count = sum(1 for row in self.memory_grid for x in row if x)
                        if self.memory_next > count: self.success_game()
                    else: self.fail_game()
        elif self.game_type == 'LOCKPICK':
            if event.key == pygame.K_SPACE:
                current_val = self.lock_cursor
                target_min, target_max = self.lock_targets[self.lock_current_pin]
                if target_min <= current_val <= target_max:
                    self.lock_pins[self.lock_current_pin] = 1.0
                    self.lock_current_pin += 1
                    self.lock_cursor = 0.0
                    if self.lock_current_pin >= len(self.lock_pins):
                        self.success_game()
                else:
                    self.lock_cursor = 0.0
                    self.start_time -= 1000

    def success_game(self): self.active = False; self.on_success() if self.on_success else None
    def fail_game(self): self.active = False; self.on_fail() if self.on_fail else None

    def draw(self, screen, x, y):
        # (기존 그리기 코드와 동일, 생략 없이 복사)
        # 위 원본 코드 참조
        if not self.active: return

        rect = pygame.Rect(x - self.width//2, y, self.width, self.height)
        pygame.draw.rect(screen, self.bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, self.border_color, rect, 2, border_radius=8)

        now = pygame.time.get_ticks()
        ratio = max(0, 1.0 - (now - self.start_time) / self.duration)
        pygame.draw.rect(screen, (0, 200, 0), (rect.x + 10, rect.y + 10, (self.width-20)*ratio, 4))

        title = self.font_title.render(self.game_type, True, (255, 255, 255))
        screen.blit(title, (rect.centerx - title.get_width()//2, rect.y + 20))
        cx, cy = rect.centerx, rect.centery + 10

        if self.game_type == 'MASHING':
            pygame.draw.rect(screen, (40, 40, 40), (cx-80, cy, 160, 25))
            pygame.draw.rect(screen, (0, 255, 100), (cx-80, cy, 160*(self.mash_progress/100), 25))
            t = self.font_ui.render("Mash SPACE!", True, (200, 200, 200))
            screen.blit(t, (cx - t.get_width()//2, cy + 30))
            
        elif self.game_type == 'TIMING':
            pygame.draw.rect(screen, (40, 40, 40), (cx-100, cy, 200, 25))
            tx, tx2 = self.timing_target
            pygame.draw.rect(screen, (255, 255, 0), (cx-100 + tx, cy, tx2-tx, 25))
            pygame.draw.rect(screen, (255, 255, 255), (cx-100 + self.timing_cursor, cy-2, 3, 29))
            
        elif self.game_type == 'COMMAND':
            start_x = cx - (len(self.cmd_seq)*35)//2
            for i, c in enumerate(self.cmd_seq):
                col = (0, 255, 0) if i < self.cmd_idx else (80, 80, 80)
                if i == self.cmd_idx: col = (255, 255, 0)
                txt = self.font_big.render({'UP':'▲','DOWN':'▼','LEFT':'◀','RIGHT':'▶'}[c], True, col)
                screen.blit(txt, (start_x + i*35, cy-15))
                
        elif self.game_type == 'CIRCLE':
            pygame.draw.circle(screen, (40, 40, 40), (cx, cy), 45, 3)
            tr = math.radians(self.circle_target_angle)
            pygame.draw.circle(screen, (255, 255, 0), (int(cx + math.cos(tr)*45), int(cy + math.sin(tr)*45)), 6)
            ar = math.radians(self.circle_angle)
            pygame.draw.line(screen, (255, 255, 255), (cx, cy), (int(cx + math.cos(ar)*45), int(cy + math.sin(ar)*45)), 2)
            
        elif self.game_type == 'WIRING':
            for i, w in enumerate(self.wires_left):
                wy = rect.y + 55 + i*25
                pygame.draw.rect(screen, w['color'], (rect.x + 20, wy, 15, 15))
                if self.wire_state == 0 and self.wire_l_idx == i: 
                    pygame.draw.rect(screen, (255, 255, 255), (rect.x + 18, wy-2, 19, 19), 2)
                elif self.wire_selected_l == i: 
                    pygame.draw.rect(screen, (255, 255, 0), (rect.x + 18, wy-2, 19, 19), 2)
                if w['id'] in self.wire_connections:
                    for j, rw in enumerate(self.wires_right):
                        if rw['id'] == self.wire_connections[w['id']]:
                            ry = rect.y + 55 + j*25
                            pygame.draw.line(screen, w['color'], (rect.x+35, wy+7), (rect.right-35, ry+7), 2)
            for i, w in enumerate(self.wires_right):
                wy = rect.y + 55 + i*25
                pygame.draw.rect(screen, w['color'], (rect.right - 35, wy, 15, 15))
                if self.wire_state == 1 and self.wire_r_idx == i: 
                    pygame.draw.rect(screen, (255, 255, 255), (rect.right - 37, wy-2, 19, 19), 2)
            msg = "Connect Matching Colors!"
            help_txt = self.font_ui.render(msg, True, (180, 180, 180))
            screen.blit(help_txt, (rect.centerx - help_txt.get_width()//2, rect.bottom - 16))

        elif self.game_type == 'MEMORY':
            sx = cx - 50; sy = cy - 45
            for y in range(3):
                for x in range(3):
                    bx, by = sx + x*35, sy + y*35; item = self.memory_grid[y][x]
                    if self.mem_cursor == [x, y]: pygame.draw.rect(screen, (255, 255, 0), (bx-2, by-2, 34, 34), 2)
                    if item:
                        pygame.draw.rect(screen, (0, 150, 0) if item['clicked'] else (50, 50, 60), (bx, by, 30, 30))
                        if not item['clicked']:
                            t = self.font_ui.render(str(item['num']), True, (255, 255, 255))
                            screen.blit(t, (bx + 15 - t.get_width()//2, by + 15 - t.get_height()//2))
                            
        elif self.game_type == 'LOCKPICK':
            num_pins = len(self.lock_pins)
            pin_w = 20; pin_gap = 10; total_w = num_pins * pin_w + (num_pins - 1) * pin_gap; start_x = cx - total_w // 2
            pygame.draw.line(screen, (100, 100, 100), (rect.left + 20, cy + 20), (rect.right - 20, cy + 20), 2)
            for i in range(num_pins):
                px = start_x + i * (pin_w + pin_gap); py_base = cy + 20
                t_min, t_max = self.lock_targets[i]; t_h = 40
                target_y_start = py_base - (t_max * t_h); target_height = (t_max - t_min) * t_h
                target_col = (50, 100, 50) 
                if i == self.lock_current_pin: target_col = (100, 200, 100)
                elif i < self.lock_current_pin: target_col = (0, 0, 0)
                if i >= self.lock_current_pin: pygame.draw.rect(screen, target_col, (px, target_y_start, pin_w, target_height))
                pin_val = self.lock_pins[i]; current_h = pin_val * t_h; pin_rect = pygame.Rect(px, py_base - current_h, pin_w, current_h)
                pin_col = (200, 200, 200)
                if i < self.lock_current_pin: pin_col = (50, 255, 50)
                elif i == self.lock_current_pin: pin_col = (255, 255, 0)
                pygame.draw.rect(screen, pin_col, pin_rect, border_radius=2)
            t = self.font_ui.render("Press SPACE in Green Zone", True, (150, 150, 150))
            screen.blit(t, (cx - t.get_width()//2, rect.bottom - 25))
