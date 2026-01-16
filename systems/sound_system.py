import pygame
from .base_system import BaseSystem
from core.resource_manager import ResourceManager
from settings import TILE_SIZE

class SoundSystem(BaseSystem):
    def __init__(self):
        self.rm = ResourceManager.get_instance()
        self.visual_sounds = [] # (x, y, radius, max_radius, alpha, source_role)

    def play_sound(self, name, x=None, y=None, role="UNKNOWN"):
        sound_files = {
            "FOOTSTEP": "assets/sounds/step.wav", "GUNSHOT": "assets/sounds/gunshot.wav",
            "CLICK": "assets/sounds/click.wav", "CREAK": "assets/sounds/door_open.wav",
            "SLAM": "assets/sounds/door_close.wav", "KA-CHING": "assets/sounds/buy.wav",
            "CRUNCH": "assets/sounds/eat.wav", "GULP": "assets/sounds/drink.wav",
            "STAB": "assets/sounds/stab.wav", "SCREAM": "assets/sounds/scream.wav",
            "WORK": "assets/sounds/work.wav", "BEEP": "assets/sounds/beep.wav",
            "ZAP": "assets/sounds/zap.wav"
        }
        path = sound_files.get(name)
        if path:
            snd = self.rm.load_sound(path)
            if snd: snd.play()
            
        if x is not None and y is not None:
            self.add_visual_sound(x, y, name, role)

    def add_visual_sound(self, x, y, sound_type, source_role):
        max_radius = 50
        if sound_type == "GUNSHOT": max_radius = 300
        elif sound_type == "FOOTSTEP": max_radius = 30
        elif sound_type == "SCREAM": max_radius = 200
        elif sound_type == "ZAP": max_radius = 100
            
        self.visual_sounds.append({
            'x': x, 'y': y, 'r': 5, 'max_r': max_radius,
            'alpha': 255, 'role': source_role, 'type': sound_type
        })

    def update(self, dt):
        for vs in self.visual_sounds[:]:
            vs['r'] += dt * 0.2
            vs['alpha'] -= dt * 0.5
            if vs['alpha'] <= 0 or vs['r'] >= vs['max_r']:
                self.visual_sounds.remove(vs)

    def draw(self, screen, camera, listener_role="CITIZEN"):
        # [복구] 청취자 직업에 따른 색상/중요도 로직
        cx, cy = camera.x, camera.y
        
        for vs in self.visual_sounds:
            if not (cx - vs['max_r'] < vs['x'] < cx + camera.width + vs['max_r'] and
                    cy - vs['max_r'] < vs['y'] < cy + camera.height + vs['max_r']):
                continue

            color = (200, 200, 200) # 기본 회색
            source_role = vs['role']
            
            # 1. 시민/의사 입장
            if listener_role in ["CITIZEN", "DOCTOR"]:
                if source_role == "MAFIA": color = (255, 50, 50) # 적색 경보
                elif source_role == "POLICE": color = (50, 150, 255) # 파란색 구조
            
            # 2. 마피아 입장
            elif listener_role == "MAFIA":
                if source_role == "POLICE": color = (200, 50, 255) # 보라색 경고
                elif source_role in ["CITIZEN", "DOCTOR"]: color = (255, 255, 100) # 노란색 먹잇감
                
            # 3. 경찰 입장
            elif listener_role == "POLICE":
                if source_role == "MAFIA": color = (255, 150, 0) # 주황색 타겟

            surf = pygame.Surface((int(vs['r']*2), int(vs['r']*2)), pygame.SRCALPHA)
            alpha = max(0, min(255, int(vs['alpha'])))
            pygame.draw.circle(surf, (*color, alpha), (int(vs['r']), int(vs['r'])), int(vs['r']), 2)
            screen.blit(surf, (vs['x'] - cx - vs['r'], vs['y'] - cy - vs['r']))