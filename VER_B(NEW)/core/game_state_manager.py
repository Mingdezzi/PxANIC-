class GameStateManager:
    """
    게임의 전역 상태(Global State)를 관리하는 싱글톤 클래스입니다.
    마피아 사보타주(정전), 경찰 사이렌, 일일 뉴스 로그 등을 관리합니다.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = GameStateManager()
        return cls._instance

    def __init__(self):
        if GameStateManager._instance is not None:
            raise Exception("This class is a singleton!")
        GameStateManager._instance = self
        
        self.reset()

    def reset(self):
        # Global States
        self.day_count = 1
        self.current_phase = "DAWN"
        self.current_weather = "CLEAR"
        
        # Sabotage (Blackout)
        self.is_blackout = False
        self.blackout_timer = 0
        
        # Siren (Freeze Mafia)
        self.is_mafia_frozen = False
        self.frozen_timer = 0
        
        # News & Logs
        self.daily_news_log = []
        self.mafia_last_seen_zone = None
        
        # Visual Effects State
        self.bloody_footsteps = [] # List of (x, y, timestamp, angle)

        # Interaction State
        self.is_minigame_active = False

    def add_news(self, message):
        self.daily_news_log.append(message)

    def trigger_blackout(self, duration_ms):
        self.is_blackout = True
        self.blackout_timer = duration_ms # System에서 현재 시간 + duration으로 설정 필요

    def trigger_siren(self, duration_ms):
        self.is_mafia_frozen = True
        self.frozen_timer = duration_ms # System에서 현재 시간 + duration으로 설정 필요
