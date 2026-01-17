from core.engine import GameEngine
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        game = GameEngine()
        game.run()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Error occurred. Press Enter to exit...")
