import pygame
import os

class ResourceManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ResourceManager()
        return cls._instance

    def __init__(self):
        if ResourceManager._instance is not None:
            raise Exception("This class is a singleton!")
        ResourceManager._instance = self

        self.fonts = {}
        self.sounds = {}
        self.images = {}
        
        # 시스템 폰트 미리 로드
        self._load_system_fonts()

    def _load_system_fonts(self):
        font_names = ["malgungothic", "arial", "sans-serif"]
        selected_font = None
        system_fonts = pygame.font.get_fonts()
        
        for fn in font_names:
            if fn in system_fonts:
                selected_font = fn
                break
        
        try:
            self.fonts['default'] = pygame.font.SysFont(selected_font, 18)
            self.fonts['bold'] = pygame.font.SysFont(selected_font, 20, bold=True)
            self.fonts['large'] = pygame.font.SysFont(selected_font, 28)
            self.fonts['title'] = pygame.font.SysFont(selected_font, 60)
            self.fonts['small'] = pygame.font.SysFont(selected_font, 12)
        except:
            print("[ResourceManager] Failed to load system fonts, using pygame default")
            self.fonts['default'] = pygame.font.Font(None, 24)
            self.fonts['bold'] = pygame.font.Font(None, 26)
            self.fonts['large'] = pygame.font.Font(None, 36)
            self.fonts['title'] = pygame.font.Font(None, 70)
            self.fonts['small'] = pygame.font.Font(None, 16)

    def load_image(self, path: str, alpha: bool = True):
        if path in self.images:
            return self.images[path]
        
        if not os.path.exists(path):
            # 파일이 없으면 빈 Surface 반환 (에러 방지용)
            print(f"[ResourceManager] Image not found: {path}")
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 255)) # 마젠타 색상 (누락됨 표시)
            self.images[path] = surf
            return surf

        try:
            img = pygame.image.load(path)
            if alpha:
                img = img.convert_alpha()
            else:
                img = img.convert()
            self.images[path] = img
            return img
        except Exception as e:
            print(f"[ResourceManager] Failed to load image {path}: {e}")
            return None

    def load_sound(self, path: str):
        if path in self.sounds:
            return self.sounds[path]

        if not os.path.exists(path):
            return None

        try:
            snd = pygame.mixer.Sound(path)
            self.sounds[path] = snd
            return snd
        except Exception as e:
            print(f"[ResourceManager] Failed to load sound {path}: {e}")
            return None

    def get_font(self, name: str, size: int = 20):
        # 폰트 캐싱 키: "name_size"
        key = f"{name}_{size}"
        if key in self.fonts:
            return self.fonts[key]
        
        # 시스템 폰트 로드 시도
        try:
            font = pygame.font.SysFont(name, size)
            self.fonts[key] = font
            return font
        except:
            return self.fonts['default']

    def create_gradient_surface(self, radius: int, color: tuple):
        """조명 효과 등을 위한 원형 그라데이션 서피스 생성"""
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            alpha = int(255 * (1 - (r / radius)))
            pygame.draw.circle(surf, (*color, alpha), (radius, radius), r)
        return surf
