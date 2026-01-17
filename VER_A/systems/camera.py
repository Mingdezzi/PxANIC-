import pygame
from settings import TILE_SIZE

class Camera:
    def __init__(self, screen_width, screen_height, map_width=0, map_height=0):
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.width = screen_width
        self.height = screen_height
        
        self.map_width = map_width
        self.map_height = map_height
        self.zoom_level = 1.0

        self.map_width_px = map_width * TILE_SIZE
        self.map_height_px = map_height * TILE_SIZE
        
        # [수정] 초기화 시 뷰포트 크기 계산 (__init__ 마지막에 호출)
        self._update_viewport_size()

    @property
    def x(self):
        return self.camera_x

    @x.setter
    def x(self, value):
        self.camera_x = value

    @property
    def y(self):
        return self.camera_y

    @y.setter
    def y(self, value):
        self.camera_y = value

    def resize(self, w, h):
        self.width = w
        self.height = h
        self._update_viewport_size()

    def set_zoom(self, zoom):
        self.zoom_level = zoom
        self._update_viewport_size()
        
    def set_bounds(self, width_px, height_px):
        self.map_width_px = width_px
        self.map_height_px = height_px

    def _update_viewport_size(self):
        """줌이나 해상도 변경 시 1회만 호출"""
        if self.zoom_level > 0:
            self.view_w = self.width / self.zoom_level
            self.view_h = self.height / self.zoom_level
        else:
            self.view_w = self.width
            self.view_h = self.height

    def move(self, dx, dy):
        self.camera_x += dx
        self.camera_y += dy

    def update(self, target_x, target_y):
        # 타겟을 화면 중앙에 위치시키기 위한 카메라의 좌상단 좌표 계산
        x = target_x - self.view_w / 2
        y = target_y - self.view_h / 2

        # 맵 경계 제한 (Clamp)
        # 가로축
        if self.map_width_px > self.view_w:
            x = max(0, min(x, self.map_width_px - self.view_w))
        else:
            # 맵이 화면보다 작으면 중앙 정렬
            x = -(self.view_w - self.map_width_px) / 2

        # 세로축
        if self.map_height_px > self.view_h:
            y = max(0, min(y, self.map_height_px - self.view_h))
        else:
            # 맵이 화면보다 작으면 중앙 정렬
            y = -(self.view_h - self.map_height_px) / 2

        self.camera_x = x
        self.camera_y = y
