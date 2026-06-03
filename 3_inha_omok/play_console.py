# Play Omok on Console
import sys
import os
import numpy as np

# Adjust path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from env import env_competition as game
import utils
import agents

def get_obstacles_input():
    print("=" * 60)
    print(" 오목 AI 대전 - 장애물(빨간 돌) 설정")
    print("=" * 60)
    print("게임 시작 시 배치할 3개의 빨간색 장애물 돌의 좌표를 입력해주세요.")
    print("좌표는 1~19 범위의 X,Y 형식이며, 공백으로 구분합니다.")
    print("예: 3,5 12,17 15,9")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("장애물 좌표 3개 입력 (빈 입력 시 무작위 배치): ").strip()
            if not user_input:
                # Default random obstacles
                coords = []
                while len(coords) < 3:
                    rx = np.random.randint(1, 20)
                    ry = np.random.randint(1, 20)
                    # Don't place on center (10, 10)
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

def get_color_selection():
    print("-" * 60)
    print(" 돌 색상 선택")
    print("-" * 60)
    while True:
        choice = input("색상을 선택하세요 (1: 흑돌(선수), 2: 백돌(후수)): ").strip()
        if choice == '1':
            return 0  # Black
        elif choice == '2':
            return 1  # White
        else:
            print("[에러] 1 또는 2를 입력해주세요.")

def main():
    # 1. Get obstacles
    obstacles_coords = get_obstacles_input()
    
    # Convert obstacle coordinates to action indices
    obstacles_actions = [game.coord_to_action(x, y) for x, y in obstacles_coords]
    
    # 2. Get player color selection
    player_color = get_color_selection()
    
    # 3. Initialize GameState
    env = game.GameState(obstacles=obstacles_coords)
    
    # MCTS Agent setup
    if utils._cpp_lib is not None:
        # C++ version can search much faster; we use 2000 simulations as a solid standard
        ai_agent = agents.CppHeuristicMCTS(board_size=19, num_mcts=2000, obstacles=obstacles_actions)
        print("[알림] C++ 최적화 MCTS 에이전트를 사용합니다 (시뮬레이션: 2000회).")
    else:
        ai_agent = agents.HeuristicMCTS(board_size=19, num_mcts=800, obstacles=obstacles_actions)
        print("[알림] 파이썬 Heuristic MCTS 에이전트를 사용합니다 (시뮬레이션: 800회).")
    
    # Root node ID starts with (0, 180) because Black is forced to play at (10, 10)
    # Action index of (10,10) is 9*19 + 9 = 180
    root_id = (0, 180)
    action_index = 180
    
    board = env.gameboard
    turn = env.turn # Starts at 1 (White turn)
    win_index = 0
    
    print("\n" + "=" * 60)
    print(" 오목 게임 대전 시작!")
    print(" 흑돌의 첫 수는 (10,10)에 자동 배치되었습니다.")
    print("=" * 60)
    
    # Game Loop
    while win_index == 0:
        env.render_console(last_action_index=action_index)
        
        # Check current turn owner
        # Turn 0 is Black, Turn 1 is White
        is_player_turn = (turn == player_color)
        
        if is_player_turn:
            print(">>> 당신의 턴입니다.")
            player_symbol = "● (흑돌)" if player_color == 0 else "○ (백돌)"
            print(f"착수할 좌표 X,Y를 입력하세요 (예: 11,10 또는 undo).")
            
            while True:
                user_move = input("좌표 입력: ").strip().lower()
                
                # Undo option (optional but nice)
                if user_move == "undo":
                    if len(root_id) >= 3:
                        # Pop last two moves (AI move and player move)
                        root_id = root_id[:-2]
                        # Reconstruct board
                        env.gameboard = utils.get_board(root_id, 19, obstacles_actions)
                        env.turn = player_color
                        env.num_stones = len(root_id) - 1
                        board = env.gameboard
                        turn = player_color
                        ai_agent.reset()
                        print("[알림] 한 수 무르고 이전 상태로 돌아갑니다.")
                        action_index = root_id[-1] if len(root_id) > 1 else 180
                        env.render_console(last_action_index=action_index)
                        continue
                    else:
                        print("[에러] 무를 수 있는 기보가 없습니다.")
                        continue
                
                # Parse coordinate
                try:
                    xy = user_move.split(',')
                    if len(xy) != 2:
                        print("[에러] 'X,Y' 형식으로 입력해야 합니다 (예: 9,11).")
                        continue
                    x, y = int(xy[0]), int(xy[1])
                    if not (1 <= x <= 19 and 1 <= y <= 19):
                        print("[에러] 좌표는 1~19 범위여야 합니다.")
                        continue
                        
                    # Calculate action index
                    act_idx = game.coord_to_action(x, y)
                    r, c = game.coord_to_matrix(x, y)
                    
                    # Check occupied
                    if env.gameboard[r, c] != 0:
                        print("[에러] 이미 돌이나 장애물이 배치된 위치입니다.")
                        continue
                        
                    # Check 3-3 restriction
                    player_val = 1 if player_color == 0 else -1
                    if utils.check_double_three(board, act_idx, player_val):
                        print("[에러] 안막힌 3,3(쌍삼)은 착수할 수 없습니다.")
                        continue
                        
                    action_index = act_idx
                    break
                except ValueError:
                    print("[에러] 입력 형식이 잘못되었습니다. 다시 시도하십시오.")
                    
            # Apply move
            board, _, win_index, turn, _ = env.step(action_index)
            root_id += (action_index,)
            
        else:
            print(">>> AI가 수읽기 중입니다 (최대 3초)...")
            # AI's turn
            # Heuristic MCTS search
            pi = ai_agent.get_pi(root_id, board, turn, tau=0)
            action_index = int(np.argmax(pi))
            
            # Print AI choice
            ai_x, ai_y = game.action_to_coord(action_index)
            print(f"AI 착수 위치: {ai_x},{ai_y}")
            
            # Apply move
            board, _, win_index, turn, _ = env.step(action_index)
            root_id += (action_index,)
            
            # Clean search tree for memory optimization
            ai_agent.del_parents(root_id)
            
    # Game Over
    env.render_console(last_action_index=action_index)
    print("=" * 60)
    print(" 게임 종료!")
    if win_index == 1:
        print("결과: 흑돌 (선수) 승리!")
    elif win_index == 2:
        print("결과: 백돌 (후수) 승리!")
    else:
        print("결과: 무승부!")
    print("=" * 60)

if __name__ == '__main__':
    # Force ANSI escape sequences on Windows Command Prompt if needed
    if os.name == 'nt':
        os.system('color')
    main()
