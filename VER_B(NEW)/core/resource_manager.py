import pygame
import os
import sys

# [수정] 순환 참조 방지를 위해 로거는 필요할 때 import하거나 간단히 처리
# 여기서는 시스템 로거를 사용하거나 print로 대체할 수 있으나, 기존 구조 유지를 위해 systems.logger 시도
try:
    from systems.logger import GameLogger
except ImportError:
    GameLogger = None

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

        self.logger = GameLogger.get_instance() if GameLogger else None
        self.fonts = {}
        self.sounds = {}
        self.images = {} # 이미지 캐시

        self._load_system_fonts()

    def _log(self, level, msg):
        if self.logger:
            if level == "ERROR": self.logger.error("RESOURCE", msg)
            elif level == "WARNING": self.logger.warning("RESOURCE", msg)
            else: self.logger.info("RESOURCE", msg)
        else:
            print(f"[RESOURCE] {msg}")

    def _load_system_fonts(self):
        font_name = "malgungothic"
        if font_name not in pygame.font.get_fonts():
            font_name = "arial"

        try:
            self.fonts['default'] = pygame.font.SysFont(font_name, 18)
            self.fonts['bold'] = pygame.font.SysFont(font_name, 20, bold=True)
            self.fonts['large'] = pygame.font.SysFont(font_name, 28)
            self.fonts['title'] = pygame.font.SysFont(font_name, 60)
            self.fonts['small'] = pygame.font.SysFont(font_name, 12)
        except:
            self._log("WARNING", "Failed to load system fonts, using default")
            self.fonts['default'] = pygame.font.Font(None, 24)
            self.fonts['bold'] = pygame.font.Font(None, 26)
            self.fonts['large'] = pygame.font.Font(None, 36)
            self.fonts['title'] = pygame.font.Font(None, 70)
            self.fonts['small'] = pygame.font.Font(None, 16)

    def get_font(self, name):
        return self.fonts.get(name, self.fonts['default'])

    def get_image(self, path, use_alpha=True):
        """이미지를 로드하고 디스플레이 포맷에 맞춰 최적화(convert)하여 반환"""
        if path in self.images:
            return self.images[path]
        
        try:
            if not os.path.exists(path):
                self._log("ERROR", f"Image not found: {path}")
                return None
                
            img = pygame.image.load(path)
            # 로드 직후 포맷 변환 (블리팅 속도 5~10배 향상)
            if pygame.display.get_surface(): # 디스플레이가 초기화된 경우에만 convert 가능
                if use_alpha:
                    img = img.convert_alpha()
                else:
                    img = img.convert()
                
            self.images[path] = img
            return img
        except Exception as e:
            self._log("ERROR", f"Failed to load image: {path} / {e}")
            return None
            
    def clear_cache(self):
        self.images.clear()
        # 폰트는 유지
