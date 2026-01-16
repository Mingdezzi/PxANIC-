import pygame
from .base_system import BaseSystem
from core.resource_manager import ResourceManager

class SoundSystem(BaseSystem):
    def __init__(self):
        self.rm = ResourceManager.get_instance()
        self.visual_sounds = [] # (x, y, radius, max_radius, alpha)

    def play_sound(self, name, x=None, y=None):
        # 사운드 파일 매핑 (경로 확인 필요)
        sound_files = {
            "FOOTSTEP": "assets/sounds/step.wav",
            "GUNSHOT": "assets/sounds/gunshot.wav",
            "CLICK": "assets/sounds/click.wav",
            "CREAK": "assets/sounds/door_open.wav",
            "SLAM": "assets/sounds/door_close.wav",
            "KA-CHING": "assets/sounds/buy.wav",
            "CRUNCH": "assets/sounds/eat.wav",
            "GULP": "assets/sounds/drink.wav",
            "STAB": "assets/sounds/stab.wav",
            "SCREAM": "assets/sounds/scream.wav",
            "WORK": "assets/sounds/work.wav",
            "BEEP": "assets/sounds/beep.wav"
        }
        
        path = sound_files.get(name)
        if path:
            # 리소스 매니저가 파일 존재 여부를 체크하므로 안전함
            snd = self.rm.load_sound(path)
            if snd: 
                # 거리 기반 볼륨 조절 로직 추가 가능
                snd.play()
            
        # 시각적 사운드 효과 추가
        if x is not None and y is not None:
            self.add_visual_sound(x, y, name)

    def add_visual_sound(self, x, y, sound_type):
        # 사운드 타입에 따른 파동 색상/크기 설정
        color = (200, 200, 200)
        max_radius = 50
        
        if sound_type == "GUNSHOT":
            color = (255, 50, 50)
            max_radius = 300
        elif sound_type == "FOOTSTEP":
            color = (150, 150, 150)
            max_radius = 30
        elif sound_type == "SCREAM":
            color = (255, 0, 0)
            max_radius = 200
            
        self.visual_sounds.append({
            'x': x, 'y': y,
            'r': 5, 'max_r': max_radius,
            'color': color,
            'alpha': 255
        })

    def update(self, dt):
        # 시각적 효과 업데이트
        for vs in self.visual_sounds[:]:
            vs['r'] += dt * 0.2 # 퍼지는 속도
            vs['alpha'] -= dt * 0.5 # 사라지는 속도
            
            if vs['alpha'] <= 0 or vs['r'] >= vs['max_r']:
                self.visual_sounds.remove(vs)

    def draw(self, screen, camera):
        # 시각적 사운드 그리기 (RenderSystem이 아닌 여기서 직접 그리기 지원)
        cx, cy = camera.x, camera.y
        
        for vs in self.visual_sounds:
            # 화면 밖 컬링
            if not (cx - vs['max_r'] < vs['x'] < cx + camera.width + vs['max_r'] and
                    cy - vs['max_r'] < vs['y'] < cy + camera.height + vs['max_r']):
                continue

            # 투명 원 그리기
            surf = pygame.Surface((vs['r']*2, vs['r']*2), pygame.SRCALPHA)
            alpha = max(0, min(255, int(vs['alpha'])))
            pygame.draw.circle(surf, (*vs['color'], alpha), (vs['r'], vs['r']), int(vs['r']), 2)
            
            screen.blit(surf, (vs['x'] - cx - vs['r'], vs['y'] - cy - vs['r']))
