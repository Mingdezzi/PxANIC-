import pygame
from colors import COLORS
from settings import SCREEN_WIDTH, SCREEN_HEIGHT

class UIWidget:
    def __init__(self, game):
        self.game = game
        self.font_main = None
        self.font_small = None
        self.font_big = None
        self.font_digit = None
        self._load_fonts()

    def _load_fonts(self):
        # 폰트 로딩 (전역 캐싱을 고려할 수도 있으나, 여기서는 개별 로드 후 인스턴스 변수로 보유)
        # 실제로는 ResourceManager를 쓰는 것이 더 좋지만, 기존 ui.py 로직을 따름
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

    def draw(self, screen):
        raise NotImplementedError

    def create_panel_bg(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 20, 25, 200), (0, 0, w, h), border_radius=10)
        pygame.draw.rect(s, (80, 80, 90, 255), (0, 0, w, h), 2, border_radius=10)
        return s
