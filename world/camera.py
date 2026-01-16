from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.x = 0
        self.y = 0
        self.zoom_level = 1.0

    def update(self, target):
        if not target: return
        
        # 타겟 중심으로 이동
        # target은 Entity 또는 Transform 컴포넌트
        if hasattr(target, 'transform'):
            tx = target.transform.x
            ty = target.transform.y
        else: # Rect 등을 가진 객체일 경우 (하위 호환)
            tx = target.rect.centerx
            ty = target.rect.centery

        # 화면 중앙에 오도록 오프셋 계산
        self.x = tx - (self.width / 2)
        self.y = ty - (self.height / 2)

        # 맵 경계 제한 (선택 사항)
        # self.x = max(0, min(self.x, map_width - self.width))
        # self.y = max(0, min(self.y, map_height - self.height))
