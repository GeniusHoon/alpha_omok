# AI Self-Play Visualizer
import sys
import os
import time
import numpy as np

# Adjust path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from env import env_competition as game
import utils
import agents

def get_num_games():
    while True:
        try:
            val = input("진행할 대전 판 수를 입력하세요 (예: 3): ").strip()
            if not val:
                return 1
            num = int(val)
            if num >= 1:
                return num
            print("[에러] 1판 이상이어야 합니다.")
        except ValueError:
            print("[에러] 숫자를 입력해주세요.")

def get_delay_input():
    while True:
        try:
            val = input("착수 간 렌더링 대기 시간(초)을 입력하세요 (예: 0.5): ").strip()
            if not val:
                return 0.5
            delay = float(val)
            if delay >= 0.0:
                return delay
            print("[에러] 대기 시간은 0보다 크거나 같아야 합니다.")
        except ValueError:
            print("[에러] 실수를 입력해주세요.")

def get_obstacles_input():
    print("=" * 60)
    print(" 오목 AI 자가 대전 (Self-Play) 시뮬레이터")
    print("=" * 60)
    print("게임 시작 시 배치할 3개의 빨간색 장애물 돌의 좌표를 입력해주세요.")
    print("좌표는 1~19 범위의 X,Y 형식이며, 공백으로 구분합니다.")
    print("예: 3,5 12,17 15,9")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("장애물 좌표 3개 입력 (빈 입력 시 무작위 배치): ").strip()
            if not user_input:
                coords = []
                while len(coords) < 3:
                    rx = np.random.randint(1, 20)
                    ry = np.random.randint(1, 20)
                    if (rx, ry) != (10, 10) and (rx, ry) not in coords:
                        coords.append((rx, ry))
                print(f"장애물이 무작위로 설정되었습니다: {coords[0][0]},{coords[0][1]} {coords[1][0]},{coords[1][1]} {coords[2][0]},{coords[2][1]}")
                return coords
                
            parts = user_input.split()
            if len(parts) != 3:
                print("[에러] 반드시 3개의 좌표를 입력해야 합니다.")
                continue
                
            coords = []
            valid = True
            for part in parts:
                xy = part.split(',')
                if len(xy) != 2:
                    print(f"[에러] 좌표 형식이 잘못되었습니다: '{part}'. 'X,Y' 형식이어야 합니다.")
                    valid = False
                    break
                x, y = int(xy[0]), int(xy[1])
                if not (1 <= x <= 19 and 1 <= y <= 19):
                    print(f"[에러] 좌표 범위를 벗어났습니다: {x},{y} (1~19 범위여야 합니다.)")
                    valid = False
                    break
                if (x, y) == (10, 10):
                    print("[에러] 중앙점(10,10)은 첫 착수 자리이므로 장애물을 놓을 수 없습니다.")
                    valid = False
                    break
                coords.append((x, y))
                
            if valid:
                if len(set(coords)) < 3:
                    print("[에러] 중복된 좌표가 있습니다. 서로 다른 3곳을 지정하세요.")
                    continue
                return coords
        except ValueError:
            print("[에러] 숫자 형식이 올바르지 않습니다. 다시 입력해주세요.")

def main():
    # 1. Get configuration inputs
    obstacles_coords = get_obstacles_input()
    obstacles_actions = [game.coord_to_action(x, y) for x, y in obstacles_coords]
    
    num_games = get_num_games()
    delay = get_delay_input()
    
    stats = {'Black': 0, 'White': 0, 'Draw': 0}
    
    # Run games
    for g in range(num_games):
        print("\n" + "=" * 60)
        print(f" 대전 {g + 1} / {num_games} 판 시작")
        print("=" * 60)
        
        # Initialize GameState
        env = game.GameState(obstacles=obstacles_coords)
        
        # Initialize Black (First) and White (Second) agents
        # Pass obstacles to both agents. Uses C++ agent if available.
        if utils._cpp_lib is not None:
            black_agent = agents.CppHeuristicMCTS(board_size=19, num_mcts=2000, obstacles=obstacles_actions)
            white_agent = agents.CppHeuristicMCTS(board_size=19, num_mcts=2000, obstacles=obstacles_actions)
        else:
            black_agent = agents.HeuristicMCTS(board_size=19, num_mcts=800, obstacles=obstacles_actions)
            white_agent = agents.HeuristicMCTS(board_size=19, num_mcts=800, obstacles=obstacles_actions)
        
        # Game starts with center stone placed at (10, 10) -> action index 180
        root_id = (0, 180)
        action_index = 180
        
        board = env.gameboard
        turn = env.turn # Turn starts at 1 (White's turn)
        win_index = 0
        
        # Game loop
        while win_index == 0:
            # 1. Render board
            env.render_console(last_action_index=action_index)
            
            # Print current turn
            curr_player_name = "Black (AI)" if turn == 0 else "White (AI)"
            print(f"[{curr_player_name} 가 수읽기 및 착수 중...]")
            
            # 2. Get move from appropriate agent
            if turn == 0:
                pi = black_agent.get_pi(root_id, board, turn, tau=0)
            else:
                pi = white_agent.get_pi(root_id, board, turn, tau=0)
                
            action_index = int(np.argmax(pi))
            
            # Print action details
            x, y = game.action_to_coord(action_index)
            print(f"-> 착수 좌표: {x},{y} (Action Index: {action_index})")
            
            # 3. Apply move to environment
            board, _, win_index, turn, _ = env.step(action_index)
            root_id += (action_index,)
            
            # 4. Clean search trees to optimize memory
            black_agent.del_parents(root_id)
            white_agent.del_parents(root_id)
            
            # Render delay so the user can watch
            if delay > 0:
                time.sleep(delay)
                
        # Game ended
        env.render_console(last_action_index=action_index)
        print("-" * 60)
        print(f" 대전 {g + 1} 결과:")
        if win_index == 1:
            print("★ 흑돌 (선수) AI 승리!")
            stats['Black'] += 1
        elif win_index == 2:
            print("★ 백돌 (후수) AI 승리!")
            stats['White'] += 1
        else:
            print("★ 무승부!")
            stats['Draw'] += 1
        print("-" * 60)
        
    # Print overall stats
    print("\n" + "=" * 60)
    print(" 전체 자가 대전 시뮬레이션 종료")
    print("=" * 60)
    print(f"총 대전 수: {num_games}판")
    print(f" - 흑돌 승리: {stats['Black']}회")
    print(f" - 백돌 승리: {stats['White']}회")
    print(f" - 무승부: {stats['Draw']}회")
    
    total_completed = stats['Black'] + stats['White'] + stats['Draw']
    if total_completed > 0:
        black_win_rate = (stats['Black'] + 0.5 * stats['Draw']) / total_completed * 100
        print(f" - 흑돌 승률 (무승부는 0.5승 처리): {black_win_rate:.2f}%")
    print("=" * 60)

if __name__ == '__main__':
    if os.name == 'nt':
        os.system('color')
    main()
