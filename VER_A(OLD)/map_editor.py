import pygame
import json
import sys
import os
import tkinter as tk
from tkinter import messagebox, filedialog
from settings import TILE_SIZE, FPS, ZONES
from colors import COLORS
from world.tiles import TILE_DATA, create_texture, get_tile_category, check_collision, get_tile_function, NEW_ID_MAP, get_tile_type, get_tile_interaction, get_tile_hiding

UI_WIDTH = 340
MINIMAP_SIZE_BASE = 250
CAMERA_PADDING = 50

class MapEditor:
    def __init__(self):
        pygame.init()
        self.root = tk.Tk(); self.root.withdraw()

        info = pygame.display.Info()
        self.screen_width = int(info.current_w * 0.9)
        self.screen_height = int(info.current_h * 0.9)

        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("Pixel Night Map Editor - V9.8 (Deep Copy & Group Rotate)")

        self.clock = pygame.time.Clock()

        font_name = "malgungothic"
        if font_name not in pygame.font.get_fonts(): font_name = "arial"
        try:
            self.font = pygame.font.SysFont(font_name, 14)
            self.small_font = pygame.font.SysFont(font_name, 11)
            self.title_font = pygame.font.SysFont(font_name, 40)
        except:
            self.font = pygame.font.Font(None, 18)
            self.small_font = pygame.font.Font(None, 14)
            self.title_font = pygame.font.Font(None, 50)


        self.textures = {tid: create_texture(tid) for tid in TILE_DATA}
        self.ui_textures = {tid: pygame.transform.scale(surf, (24, 24)) for tid, surf in self.textures.items()}


        self.state = 'MENU'


        self.init_empty_map(50, 50)
        self.active_layer = 'floor'


        self.input_width_str = "50"
        self.input_height_str = "50"
        self.input_active_field = 0
        self.input_error_msg = ""


        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 3.0


        self.tool_mode = 'BRUSH'
        self.clipboard = None
        self.mode = 'TILE'
        self.current_rotation = 0

        self.filters = {'A': None, 'B': None, 'C': None, 'D': None, 'E': None}
        self.filtered_tiles = []
        self.current_tile_idx = 0
        self.selected_zone_id = 1
        self.tile_list_scroll = 0

        self.update_filtered_tiles()


        self.is_dragging = False
        self.is_erasing = False
        self.drag_start_pos = (0, 0)
        self.drag_current_pos = (0, 0)


        self.ui_width = UI_WIDTH
        self.minimap_size = min(MINIMAP_SIZE_BASE, self.screen_height - 100, self.ui_width - 30)
        self.map_view_width = self.screen_width - self.ui_width
        self.mm_draw_rect = pygame.Rect(0, 0, 0, 0)
        self.ui_rects = {}

        self.running = True

    def init_empty_map(self, w, h):
        self.map_width, self.map_height = w, h
        self.layers = {
            'floor': [[(1110000, 0) for _ in range(w)] for _ in range(h)],
            'wall': [[(0, 0) for _ in range(w)] for _ in range(h)],
            'object': [[(0, 0) for _ in range(w)] for _ in range(h)]
        }
        self.zone_map = [[0 for _ in range(w)] for _ in range(h)]

    def update_filtered_tiles(self):
        results = []
        layer_cats = []
        if self.active_layer == 'floor': layer_cats = [1, 2]
        elif self.active_layer == 'wall': layer_cats = [3, 4]
        elif self.active_layer == 'object': layer_cats = [5, 6, 7, 8, 9]

        for tid in TILE_DATA.keys():
            cat = get_tile_category(tid)
            if cat not in layer_cats: continue
            if self.filters['A'] is not None and cat != self.filters['A']: continue
            if self.filters['B'] is not None and get_tile_type(tid) != self.filters['B']: continue
            c_val = 2 if check_collision(tid) else 1
            if self.filters['C'] is not None and c_val != self.filters['C']: continue
            if self.filters['D'] is not None and get_tile_interaction(tid) != self.filters['D']: continue
            if self.filters['E'] is not None and get_tile_hiding(tid) != self.filters['E']: continue
            results.append(tid)

        results.sort()
        self.filtered_tiles = results
        self.current_tile_idx = 0
        self.tile_list_scroll = 0

    def get_selected_tile_id(self):
        if not self.filtered_tiles: return 0
        if self.current_tile_idx >= len(self.filtered_tiles): self.current_tile_idx = 0
        return self.filtered_tiles[self.current_tile_idx]

    def grid_to_screen(self, gx, gy):
        return (gx * TILE_SIZE * self.zoom) - self.camera_x, (gy * TILE_SIZE * self.zoom) - self.camera_y

    def screen_to_grid(self, sx, sy):
        return int((sx + self.camera_x) / (TILE_SIZE * self.zoom)), int((sy + self.camera_y) / (TILE_SIZE * self.zoom))

    def get_selection_rect(self):
        x1, y1 = self.drag_start_pos; x2, y2 = self.drag_current_pos
        return min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)

    def apply_fill(self):
        if self.tool_mode == 'BRUSH':
            sx, ex, sy, ey = self.get_selection_rect()
            tid = self.get_selected_tile_id()
            for y in range(sy, ey + 1):
                for x in range(sx, ex + 1):
                    if 0 <= x < self.map_width and 0 <= y < self.map_height:
                        if self.mode == 'TILE':
                            target_grid = self.layers[self.active_layer]
                            if self.is_erasing:
                                if self.active_layer == 'floor': target_grid[y][x] = (1110000, 0)
                                else: target_grid[y][x] = (0, 0)
                            else:
                                if self.active_layer in ['wall', 'object']:
                                    floor_tid = self.layers['floor'][y][x][0]
                                    if floor_tid == 0: continue
                                if self.active_layer == 'object' and get_tile_category(tid) == 5:
                                    self.layers['wall'][y][x] = (0, 0)
                                target_grid[y][x] = (tid, self.current_rotation)
                        else:
                            self.zone_map[y][x] = 0 if self.is_erasing else self.selected_zone_id

        elif self.tool_mode == 'COPY':
            sx, ex, sy, ey = self.get_selection_rect()
            w, h = ex - sx + 1, ey - sy + 1


            clipboard_data = {'floor': [], 'wall': [], 'object': [], 'zones': []}
            for y in range(sy, ey + 1):
                f_row, w_row, o_row, z_row = [], [], [], []
                for x in range(sx, ex + 1):
                    if 0 <= x < self.map_width and 0 <= y < self.map_height:
                        f_row.append(self.layers['floor'][y][x])
                        w_row.append(self.layers['wall'][y][x])
                        o_row.append(self.layers['object'][y][x])
                        z_row.append(self.zone_map[y][x])
                    else:
                        f_row.append((0,0)); w_row.append((0,0)); o_row.append((0,0)); z_row.append(0)
                clipboard_data['floor'].append(f_row)
                clipboard_data['wall'].append(w_row)
                clipboard_data['object'].append(o_row)
                clipboard_data['zones'].append(z_row)
            self.clipboard = {'w': w, 'h': h, 'data': clipboard_data}

    def rotate_clipboard(self):
        """클립보드 내용을 90도 회전"""
        if not self.clipboard: return
        w, h = self.clipboard['w'], self.clipboard['h']
        new_w, new_h = h, w
        new_data = {'floor': [], 'wall': [], 'object': [], 'zones': []}

        def rotate_grid(grid, is_tile=True):
            new_grid = [[None for _ in range(new_w)] for _ in range(new_h)]
            for y in range(h):
                for x in range(w):
                    nx, ny = h - 1 - y, x
                    val = grid[y][x]
                    if is_tile:
                        tid, rot = val
                        if tid != 0: new_grid[ny][nx] = (tid, (rot + 90) % 360)
                        else: new_grid[ny][nx] = (0, 0)
                    else:
                        new_grid[ny][nx] = val
            return new_grid

        new_data['floor'] = rotate_grid(self.clipboard['data']['floor'])
        new_data['wall'] = rotate_grid(self.clipboard['data']['wall'])
        new_data['object'] = rotate_grid(self.clipboard['data']['object'])
        new_data['zones'] = rotate_grid(self.clipboard['data']['zones'], is_tile=False)

        self.clipboard = {'w': new_w, 'h': new_h, 'data': new_data}

    def apply_paste(self, gx, gy):
        if not self.clipboard: return
        w, h = self.clipboard['w'], self.clipboard['h']
        for y in range(h):
            for x in range(w):
                mx, my = gx + x, gy + y
                if 0 <= mx < self.map_width and 0 <= my < self.map_height:
                    for layer in ['floor', 'wall', 'object']:
                        val = self.clipboard['data'][layer][y][x]

                        if val[0] != 0 or (layer == 'floor' and val[0] == 0):
                            if val[0] != 0: self.layers[layer][my][mx] = val

                    z_val = self.clipboard['data']['zones'][y][x]
                    if z_val != 0: self.zone_map[my][mx] = z_val

    def clamp_camera(self):
        mw, mh = self.map_width * TILE_SIZE * self.zoom, self.map_height * TILE_SIZE * self.zoom
        if mw < self.map_view_width: self.camera_x = -(self.map_view_width - mw) / 2
        else: self.camera_x = max(-CAMERA_PADDING, min(self.camera_x, mw - self.map_view_width + CAMERA_PADDING))
        if mh < self.screen_height: self.camera_y = -(self.screen_height - mh) / 2
        else: self.camera_y = max(-CAMERA_PADDING, min(self.camera_y, mh - self.screen_height + CAMERA_PADDING))

    def save_map(self):
        data = {"width": self.map_width, "height": self.map_height, "layers": self.layers, "zones": self.zone_map}
        try:
            with open("map.json", "w", encoding='utf-8') as f: json.dump(data, f)
            print("Map Saved!")
        except Exception as e: print(f"Save Error: {e}")

    def load_map(self):
        try:
            filename = filedialog.askopenfilename(initialdir=os.getcwd(), title="Select Map File", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
            if not filename: return False
            with open(filename, "r", encoding='utf-8') as f: data = json.load(f)
            load_w = data.get("width", 50); load_h = data.get("height", 50)

            if 'layers' not in data and 'tiles' in data:
                res = messagebox.askyesno("구형 맵 감지", "구형 맵 데이터입니다.\n최신 형식으로 변환하시겠습니까?")
                if res:
                    self.init_empty_map(load_w, load_h)
                    old_tiles = data['tiles']
                    rows = min(len(old_tiles), load_h)
                    for y in range(rows):
                        cols = min(len(old_tiles[y]), load_w)
                        for x in range(cols):
                            old_id = old_tiles[y][x]; new_id = NEW_ID_MAP.get(old_id, old_id); cat = get_tile_category(new_id); val = (new_id, 0)
                            if 0 <= y < self.map_height and 0 <= x < self.map_width:
                                if cat in [1, 2]: self.layers['floor'][y][x] = val
                                elif cat in [3, 4]: self.layers['wall'][y][x] = val
                                else:
                                    if self.layers['floor'][y][x][0] == 0: self.layers['floor'][y][x] = (1110000, 0)
                                    self.layers['object'][y][x] = val
                    loaded_zones = data.get("zones", [])
                    for y in range(min(len(loaded_zones), self.map_height)):
                        for x in range(min(len(loaded_zones[y]), self.map_width)): self.zone_map[y][x] = loaded_zones[y][x]
                else: return False
            else:
                self.init_empty_map(load_w, load_h)
                loaded_layers = data.get('layers', {})
                for k in ['floor', 'wall', 'object']:
                    if k in loaded_layers:
                        grid = loaded_layers[k]; rows = min(len(grid), self.map_height)
                        for y in range(rows):
                            cols = min(len(grid[y]), self.map_width)
                            for x in range(cols):
                                v = grid[y][x]
                                if isinstance(v, int): self.layers[k][y][x] = (v, 0)
                                elif isinstance(v, list): self.layers[k][y][x] = tuple(v)
                loaded_zones = data.get("zones", [])
                for y in range(min(len(loaded_zones), self.map_height)):
                    for x in range(min(len(loaded_zones[y]), self.map_width)): self.zone_map[y][x] = loaded_zones[y][x]

            self.state = 'EDITOR'; self.camera_x, self.camera_y = 0, 0; self.clamp_camera()
            self.update_filtered_tiles()
            return True
        except Exception as e: print(f"Load Error: {e}"); import traceback; traceback.print_exc(); return False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.VIDEORESIZE:
                self.screen_width, self.screen_height = event.w, event.h
                self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
                self.map_view_width = self.screen_width - self.ui_width
                self.minimap_size = min(MINIMAP_SIZE_BASE, self.screen_height - 100, self.ui_width - 30)
                if self.state == 'EDITOR': self.clamp_camera()

            if self.state == 'MENU':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_n: self.state = 'INPUT_SIZE'; self.input_error_msg = ""
                    elif event.key == pygame.K_l: self.load_map()
                    elif event.key == pygame.K_ESCAPE: self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos(); cx, cy = self.screen_width // 2, self.screen_height // 2
                    if cx - 100 <= mx <= cx + 100:
                        if cy - 20 <= my <= cy + 30: self.state = 'INPUT_SIZE'; self.input_error_msg = ""
                        elif cy + 50 <= my <= cy + 100: self.load_map()

            elif self.state == 'INPUT_SIZE':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB: self.input_active_field = 1 - self.input_active_field
                    elif event.key == pygame.K_RETURN:
                        try:
                            w, h = int(self.input_width_str), int(self.input_height_str)
                            if 0 < w <= 500 and 0 < h <= 500: self.init_empty_map(w, h); self.state = 'EDITOR'; self.update_filtered_tiles()
                            else: self.input_error_msg = "1-500 Only"
                        except: self.input_error_msg = "Invalid Format"
                    elif event.key == pygame.K_ESCAPE: self.state = 'MENU'
                    elif event.key == pygame.K_BACKSPACE:
                        if self.input_active_field == 0: self.input_width_str = self.input_width_str[:-1]
                        else: self.input_height_str = self.input_height_str[:-1]
                    elif event.unicode.isdigit():
                        if self.input_active_field == 0: self.input_width_str += event.unicode
                        else: self.input_height_str += event.unicode

            elif self.state == 'EDITOR':
                mx, my = pygame.mouse.get_pos()
                if event.type == pygame.MOUSEWHEEL:
                    if mx < self.screen_width - self.ui_width:

                        world_mx = (mx + self.camera_x) / self.zoom
                        world_my = (my + self.camera_y) / self.zoom
                        new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom + (0.1 if event.y > 0 else -0.1)))
                        if new_zoom != self.zoom:
                            self.zoom = new_zoom
                            self.camera_x = (world_mx * self.zoom) - mx
                            self.camera_y = (world_my * self.zoom) - my
                        self.clamp_camera()
                    else:
                        self.tile_list_scroll = max(0, min(len(self.filtered_tiles) - 1, self.tile_list_scroll - event.y))
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.mm_draw_rect.collidepoint(mx, my):
                        if event.button == 1:
                            rx, ry = (mx - self.mm_draw_rect.x) / self.mm_draw_rect.width, (my - self.mm_draw_rect.y) / self.mm_draw_rect.height
                            self.camera_x, self.camera_y = rx * (self.map_width * TILE_SIZE * self.zoom) - (self.map_view_width / 2), ry * (self.map_height * TILE_SIZE * self.zoom) - (self.screen_height / 2); self.clamp_camera()
                    elif mx > self.screen_width - self.ui_width:
                        if event.button == 1: self.handle_ui_click(mx, my)
                    else:
                        if event.button in [1, 3]:
                            if self.tool_mode == 'PASTE':
                                if event.button == 1: gx, gy = self.screen_to_grid(mx, my); self.apply_paste(gx, gy)
                                elif event.button == 3: self.tool_mode = 'BRUSH'
                            else:
                                self.is_dragging = True; self.is_erasing = (event.button == 3); self.drag_start_pos = self.screen_to_grid(mx, my)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if self.is_dragging and event.button in [1, 3]: self.apply_fill(); self.is_dragging = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL): self.save_map()
                    elif event.key == pygame.K_ESCAPE: self.state = 'MENU'
                    elif event.key == pygame.K_b: self.tool_mode = 'BRUSH'
                    elif event.key == pygame.K_c: self.tool_mode = 'COPY'
                    elif event.key == pygame.K_v:
                        if self.clipboard: self.tool_mode = 'PASTE'
                    elif event.key == pygame.K_r:
                        if self.tool_mode == 'PASTE': self.rotate_clipboard()
                        else: self.current_rotation = (self.current_rotation + 90) % 360
                    elif event.key == pygame.K_TAB: self.mode = 'ZONE' if self.mode == 'TILE' else 'TILE'
                    elif event.key == pygame.K_1: self.active_layer = 'floor'; self.update_filtered_tiles()
                    elif event.key == pygame.K_2: self.active_layer = 'wall'; self.update_filtered_tiles()
                    elif event.key == pygame.K_3: self.active_layer = 'object'; self.update_filtered_tiles()

    def draw_button(self, text, rect, is_selected=False, hover_check=True):
        mx, my = pygame.mouse.get_pos()
        color = COLORS['BUTTON_HOVER'] if hover_check and rect.collidepoint(mx, my) else COLORS['BUTTON']
        if is_selected: color = COLORS['SELECTION']
        pygame.draw.rect(self.screen, color, rect); pygame.draw.rect(self.screen, (200, 200, 200), rect, 1)
        txt = self.small_font.render(text, True, COLORS['TEXT'])
        self.screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

    def draw_menu(self):
        cx, cy = self.screen_width // 2, self.screen_height // 2
        title = self.title_font.render("PIXEL NIGHT MAP EDITOR", True, COLORS['TEXT'])
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 150))
        self.draw_button("NEW MAP", pygame.Rect(cx - 100, cy - 20, 200, 50))
        self.draw_button("LOAD MAP", pygame.Rect(cx - 100, cy + 50, 200, 50))

    def draw_input_size(self):
        cx, cy = self.screen_width // 2, self.screen_height // 2
        for i, text in enumerate([f"W: {self.input_width_str}", f"H: {self.input_height_str}"]):
            rect = pygame.Rect(cx - 110 + i*120, cy - 20, 100, 40); color = COLORS['SELECTION'] if self.input_active_field == i else COLORS['BUTTON']
            pygame.draw.rect(self.screen, color, rect, 2); self.screen.blit(self.font.render(text, True, COLORS['TEXT']), (rect.x + 10, rect.y + 10))

    def draw_editor(self):
        keys = pygame.key.get_pressed(); ms = 25 / self.zoom
        if keys[pygame.K_w] or keys[pygame.K_UP]: self.camera_y -= ms
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            if not (pygame.key.get_mods() & pygame.KMOD_CTRL): self.camera_y += ms
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.camera_x -= ms
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.camera_x += ms
        self.clamp_camera(); self.draw_map_view()
        mx, my = pygame.mouse.get_pos()
        self.drag_current_pos = self.screen_to_grid(mx, my)
        if mx < self.screen_width - self.ui_width and not self.mm_draw_rect.collidepoint(mx, my):
            if self.tool_mode == 'PASTE': self.draw_paste_preview(mx, my)
            elif self.is_dragging: self.draw_preview()
        self.draw_ui_panel(); self.draw_minimap()

    def draw_map_view(self):
        tp = TILE_SIZE * self.zoom; sc, ec = int(max(0, self.camera_x // tp)), int(min(self.map_width, (self.camera_x + self.map_view_width) // tp + 1))
        sr, er = int(max(0, self.camera_y // tp)), int(min(self.map_height, (self.screen_height // tp) + 1 + (self.camera_y // tp)))
        pygame.draw.rect(self.screen, COLORS['MAP_BORDER'], pygame.Rect(-self.camera_x, -self.camera_y, self.map_width * tp, self.map_height * tp), 2)
        layer_order = ['floor', 'wall', 'object']
        for layer in layer_order:
            grid = self.layers[layer]; alpha = 255 if layer == self.active_layer else 180
            for y in range(max(0, sr-1), min(self.map_height, er+1)):
                for x in range(max(0, sc-1), min(self.map_width, ec+1)):
                    sx, sy = self.grid_to_screen(x, y); tid, rot = grid[y][x]
                    if tid != 0:
                        if tid not in self.textures: self.textures[tid] = create_texture(tid)
                        surf = self.textures[tid]
                        if rot != 0: surf = pygame.transform.rotate(surf, rot)
                        surf = pygame.transform.scale(surf, (int(tp) + 1, int(tp) + 1))
                        if alpha < 255: surf.set_alpha(alpha)
                        self.screen.blit(surf, (sx, sy))
                    if layer == 'floor':
                        zid = self.zone_map[y][x]
                        if zid != 0:
                            s = pygame.Surface((int(tp) + 1, int(tp) + 1), pygame.SRCALPHA); s.fill(ZONES[zid]['color']); self.screen.blit(s, (sx, sy))
        self.draw_grid_lines()

    def draw_grid_lines(self):
        tp = TILE_SIZE * self.zoom
        for x in range(0, self.map_width + 1):
            sx, _ = self.grid_to_screen(x, 0)
            if 0 <= sx <= self.map_view_width:
                col, width = COLORS['GRID_10'], 1
                if x % 10 == 0: col = COLORS['GRID_50']
                if x % 50 == 0: col, width = COLORS['GRID'], 2
                if x == self.map_width // 2: col, width = COLORS['GRID_CENTER'], 3
                pygame.draw.line(self.screen, col, (sx, 0), (sx, self.screen_height), width)
        for y in range(0, self.map_height + 1):
            _, sy = self.grid_to_screen(0, y)
            if 0 <= sy <= self.screen_height:
                col, width = COLORS['GRID_10'], 1
                if y % 10 == 0: col = COLORS['GRID_50']
                if y % 50 == 0: col, width = COLORS['GRID'], 2
                if y == self.map_height // 2: col, width = COLORS['GRID_CENTER'], 3
                pygame.draw.line(self.screen, col, (0, sy), (self.map_view_width, sy), width)

    def draw_preview(self):
        sx, ex, sy, ey = self.get_selection_rect(); tp = TILE_SIZE * self.zoom
        preview_surf = None
        if self.mode == 'TILE' and not self.is_erasing:
            tid = self.get_selected_tile_id()
            if tid in self.textures:
                tex = self.textures[tid]
                if self.current_rotation != 0: tex = pygame.transform.rotate(tex, self.current_rotation)
                preview_surf = pygame.transform.scale(tex, (int(tp), int(tp))); preview_surf.set_alpha(150)
        for y in range(sy, ey + 1):
            for x in range(sx, ex + 1):
                px, py = self.grid_to_screen(x, y); r = (px, py, tp, tp)
                if self.tool_mode == 'COPY': pygame.draw.rect(self.screen, COLORS['COPY_SELECT'], r, 2)
                else:
                    if self.is_erasing: pygame.draw.rect(self.screen, (200, 50, 50), r, 2)
                    else:
                        if self.mode == 'TILE' and preview_surf: self.screen.blit(preview_surf, (px, py))
                        elif self.mode == 'ZONE':
                            c = ZONES[self.selected_zone_id]['color']; s = pygame.Surface((int(tp), int(tp)), pygame.SRCALPHA); s.fill(c); self.screen.blit(s, (px, py))
                        pygame.draw.rect(self.screen, (200, 200, 200), r, 1)

    def draw_paste_preview(self, mx, my):
        if not self.clipboard: return
        gx, gy = self.screen_to_grid(mx, my); tp = TILE_SIZE * self.zoom
        w, h = self.clipboard['w'], self.clipboard['h']
        for y in range(h):
            for x in range(w):
                sx, sy = self.grid_to_screen(gx + x, gy + y)
                tid, rot = 0, 0
                for layer in ['object', 'wall', 'floor']:
                    val = self.clipboard['data'][layer][y][x]
                    if val[0] != 0:
                        tid, rot = val; break

                if tid != 0:
                    if tid not in self.textures: self.textures[tid] = create_texture(tid)
                    t = self.textures[tid]
                    if rot != 0: t = pygame.transform.rotate(t, rot)
                    t = t.copy(); t.set_alpha(150); self.screen.blit(pygame.transform.scale(t, (int(tp), int(tp))), (sx, sy))
                pygame.draw.rect(self.screen, (255, 255, 255), (sx, sy, tp, tp), 1)

    def draw_ui_panel(self):
        self.ui_rects = {}
        pr = (self.screen_width - self.ui_width, 0, self.ui_width, self.screen_height)
        pygame.draw.rect(self.screen, COLORS['UI_BG'], pr); pygame.draw.rect(self.screen, COLORS['UI_BORDER'], pr, 2)
        y_off = 10; self.screen.blit(self.font.render(f"MODE: {self.mode} (TAB)", True, COLORS['SELECTION']), (pr[0] + 10, y_off)); y_off += 30
        if self.mode == 'TILE':
            self.screen.blit(self.small_font.render("Active Layer (1-3)", True, (200, 200, 200)), (pr[0] + 10, y_off)); y_off += 20
            for i, layer in enumerate(['floor', 'wall', 'object']):
                rect = pygame.Rect(pr[0] + 10 + i*100, y_off, 95, 25)
                self.draw_button(layer.upper(), rect, is_selected=(self.active_layer == layer)); self.ui_rects[f"LAYER_{layer}"] = rect
            y_off += 35
            self.screen.blit(self.small_font.render(f"Rotation: {self.current_rotation}° (R)", True, COLORS['SELECTION']), (pr[0] + 10, y_off)); y_off += 20
            filter_opts = { 'A': [1,2,3,4,5,6,7,8,9], 'B': [1,2,3], 'C': [1,2], 'D': [0,1,2], 'E': [0,1,2] }
            labels = {'A':'Cat','B':'Type','C':'Col','D':'Act','E':'Hide'}
            for f_key in ['A', 'B', 'C', 'D', 'E']:
                lbl = f"{f_key}: {labels[f_key]}"; self.screen.blit(self.small_font.render(lbl, True, (180, 180, 180)), (pr[0] + 10, y_off))
                all_rect = pygame.Rect(pr[0] + 60, y_off-2, 30, 18); self.draw_button("ALL", all_rect, is_selected=(self.filters[f_key] is None)); self.ui_rects[f"FILTER_{f_key}_ALL"] = all_rect
                for i, val in enumerate(filter_opts[f_key]):
                    rect = pygame.Rect(pr[0] + 95 + i*22, y_off-2, 20, 18); self.draw_button(str(val), rect, is_selected=(self.filters[f_key] == val)); self.ui_rects[f"FILTER_{f_key}_{val}"] = rect
                y_off += 22
            y_off += 10
            self.screen.blit(self.small_font.render(f"Found: {len(self.filtered_tiles)}", True, COLORS['SELECTION']), (pr[0] + 10, y_off)); y_off += 20
            item_h = 28; max_items = (self.screen_height - self.minimap_size - y_off - 150) // item_h
            visible_tiles = self.filtered_tiles[self.tile_list_scroll : self.tile_list_scroll + max_items]
            for i, tid in enumerate(visible_tiles):
                abs_idx = self.tile_list_scroll + i; btn_rect = pygame.Rect(pr[0] + 10, y_off, self.ui_width - 20, item_h - 3)
                if abs_idx == self.current_tile_idx: pygame.draw.rect(self.screen, (60, 60, 60), btn_rect); pygame.draw.rect(self.screen, COLORS['SELECTION'], btn_rect, 1)
                tex = self.ui_textures[tid]
                if self.current_rotation != 0: tex = pygame.transform.rotate(tex, self.current_rotation)
                if tex.get_width() > 24 or tex.get_height() > 24: tex = pygame.transform.scale(tex, (24, 24))
                self.screen.blit(tex, (btn_rect.x + 5, btn_rect.y + 2)); self.screen.blit(self.small_font.render(f"{tid}: {TILE_DATA[tid]['name']}", True, COLORS['TEXT']), (btn_rect.x + 35, btn_rect.y + 6))
                self.ui_rects[f"TILE_ABS_{abs_idx}"] = btn_rect; y_off += item_h
        else:
            for zid, info in ZONES.items():
                rect = pygame.Rect(pr[0] + 10, y_off, self.ui_width - 20, 25)
                if zid == self.selected_zone_id: pygame.draw.rect(self.screen, (60, 60, 60), rect); pygame.draw.rect(self.screen, COLORS['SELECTION'], rect, 1)
                pygame.draw.rect(self.screen, info['color'][:3], (rect.x + 5, rect.y + 5, 15, 15)); self.screen.blit(self.font.render(info['name'], True, COLORS['TEXT']), (rect.x + 30, rect.y + 2))
                self.ui_rects[f"ZONE_ID_{zid}"] = rect; y_off += 28
        gy = self.screen_height - self.minimap_size - 140
        for t in ["WASD: Cam | Wheel: Zoom", "L-Drag: Place | R-Drag: Erase", "B: Brush | C: Copy | V: Paste", "R: Rotate | 1/2/3: Layer", "Ctrl+S: Save | ESC: Menu"]: self.screen.blit(self.small_font.render(t, True, (180, 180, 180)), (pr[0] + 10, gy)); gy += 16

    def draw_minimap(self):
        mm_x, mm_y = self.screen_width - self.minimap_size - 20, self.screen_height - self.minimap_size - 20
        scale = min(self.minimap_size / self.map_width, self.minimap_size / self.map_height)
        self.mm_draw_rect = pygame.Rect(mm_x, mm_y, int(self.map_width * scale), int(self.map_height * scale))
        pygame.draw.rect(self.screen, (0, 0, 0), self.mm_draw_rect); pygame.draw.rect(self.screen, COLORS['UI_BORDER'], self.mm_draw_rect, 1)
        for y in range(self.map_height):
            for x in range(self.map_width):
                tid = self.layers['wall'][y][x][0]
                if tid == 0: tid = self.layers['floor'][y][x][0]
                if tid != 0 and tid in TILE_DATA: pygame.draw.rect(self.screen, TILE_DATA[tid]['color'], (int(mm_x + x * scale), int(mm_y + y * scale), max(1, int(scale)), max(1, int(scale))))
        vw, vh = self.screen_width / self.zoom, self.screen_height / self.zoom; clipped = pygame.Rect(int(mm_x + (self.camera_x / TILE_SIZE) * scale), int(mm_y + (self.camera_y / TILE_SIZE) * scale), int(vw / TILE_SIZE * scale), int(vh / TILE_SIZE * scale)).clip(self.mm_draw_rect)
        if clipped.width > 0: pygame.draw.rect(self.screen, (255, 255, 255), clipped, 1)

    def handle_ui_click(self, mx, my):
        for key, rect in self.ui_rects.items():
            if rect.collidepoint(mx, my):
                if key.startswith("LAYER_"): self.active_layer = key.replace("LAYER_", "").lower(); self.update_filtered_tiles()
                elif key.startswith("FILTER_"):
                    parts = key.split('_'); f_key = parts[1]; val = parts[2]
                    self.filters[f_key] = None if val == "ALL" else int(val); self.update_filtered_tiles()
                elif key.startswith("TILE_ABS_"): self.current_tile_idx = int(key.replace("TILE_ABS_", ""))
                elif key.startswith("ZONE_ID_"): self.selected_zone_id = int(key.replace("ZONE_ID_", ""))
                return

    def run(self):
        while self.running:
            self.handle_events(); self.screen.fill(COLORS['BG'])
            if self.state == 'MENU': self.draw_menu()
            elif self.state == 'INPUT_SIZE': self.draw_input_size()
            elif self.state == 'EDITOR': self.draw_editor()
            pygame.display.flip(); self.clock.tick(FPS)
        pygame.quit(); sys.exit()

if __name__ == "__main__": MapEditor().run()
