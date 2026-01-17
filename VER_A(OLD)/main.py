import sys
import os
import subprocess
from core.engine import GameEngine

# 현재 디렉토리를 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def start_server():
    """게임 서버를 백그라운드 프로세스로 실행합니다."""
    python_exe = sys.executable
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    
    try:
        # Windows의 경우 새로운 콘솔 창에서 서버를 실행하여 로그를 볼 수 있게 하거나,
        # CREATE_NO_WINDOW를 사용하여 완전히 숨길 수 있습니다.
        # 여기서는 개발 편의를 위해 새로운 창(CREATE_NEW_CONSOLE)에서 실행하도록 설정합니다.
        if os.name == 'nt':
            subprocess.Popen([python_exe, server_script], 
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            # 리눅스/맥 환경
            subprocess.Popen([python_exe, server_script], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        print("[SYSTEM] Background Server starting...")
    except Exception as e:
        print(f"[SYSTEM] Failed to start server: {e}")

if __name__ == "__main__":
    # 1. 서버 자동 실행
    start_server()
    
    # 2. 게임 엔진 실행
    try:
        game = GameEngine()
        game.run()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Error occurred. Press Enter to exit...")