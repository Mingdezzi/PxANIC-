from typing import Callable, Dict, List, Any

class EventBus:
    def __init__(self):
        self.listeners: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """이벤트 리스너 등록"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        if callback not in self.listeners[event_type]:
            self.listeners[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """이벤트 리스너 제거"""
        if event_type in self.listeners:
            if callback in self.listeners[event_type]:
                self.listeners[event_type].remove(callback)

    def publish(self, event_type: str, data: Dict[str, Any] = None):
        """이벤트 발생 및 전파"""
        if data is None:
            data = {}
        
        # data에 event_type 정보도 포함
        if 'event_type' not in data:
            data['event_type'] = event_type

        if event_type in self.listeners:
            # 리스트 복사본으로 순회 (콜백 실행 중 리스트 변경 방지)
            for callback in self.listeners[event_type][:]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"[EventBus] Error in listener for {event_type}: {e}")
