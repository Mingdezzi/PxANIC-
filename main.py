from core.engine import GameEngine
from core.state_machine import StateMachine
from states.lobby_state import LobbyState
from states.play_state import PlayState

def main():
    # 1. 엔진 초기화
    engine = GameEngine()
    
    # 2. 상태 머신 초기화
    sm = StateMachine()
    
    lobby_state = LobbyState(engine)
    play_state = PlayState(engine)
    
    sm.add_state("LOBBY", lobby_state)
    sm.add_state("PLAY", play_state)
    
    sm.change_state("LOBBY")
    
    # 3. 엔진에 상태 머신 주입
    engine.set_state_machine(sm)
    
    # 4. 게임 실행
    engine.run()

if __name__ == "__main__":
    main()