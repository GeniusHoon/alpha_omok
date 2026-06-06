# Grid Search Hyperparameter Tuner
import sys
import os
import time
import numpy as np
import multiprocessing

# Adjust path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from env import env_competition as game
import utils
import agents

# Prevent Flask or other libraries from printing logs during search
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

def play_match(params_black, params_white, obstacles_coords, obstacles_actions):
    """
    Plays a single fast game between two configurations without console rendering.
    """
    env = game.GameState(obstacles=obstacles_coords)
    
    # 0: Black, 1: White
    # We use C++ optimized agent (CppHeuristicMCTS) for high speed
    black_agent = agents.CppHeuristicMCTS(board_size=19, num_mcts=400, obstacles=obstacles_actions, score_table=params_black.get('score_table', None))
    black_agent.c_puct = params_black['c_puct']
    black_agent.defense_weight = params_black['defense_weight']
    
    white_agent = agents.CppHeuristicMCTS(board_size=19, num_mcts=400, obstacles=obstacles_actions, score_table=params_white.get('score_table', None))
    white_agent.c_puct = params_white['c_puct']
    white_agent.defense_weight = params_white['defense_weight']
    
    root_id = (0, 180)
    action_index = 180
    
    board = env.gameboard
    turn = env.turn  # turn 1 (White starts since Black automatically played at center)
    win_index = 0
    
    while win_index == 0:
        if turn == 0:
            pi = black_agent.get_pi(root_id, board, turn, tau=0)
        else:
            pi = white_agent.get_pi(root_id, board, turn, tau=0)
            
        action_index = int(np.argmax(pi))
        board, _, win_index, turn, _ = env.step(action_index)
        root_id += (action_index,)
        
    return win_index  # 1: Black wins, 2: White wins, 3: Draw

def match_runner(task):
    """
    Worker task: plays symmetric matches between config A and config B
    using a unique set of random obstacles.
    """
    id_a, params_a, id_b, params_b = task
    
    # Generate unique random obstacles for this matchup
    obstacles_coords = []
    while len(obstacles_coords) < 3:
        rx = np.random.randint(1, 20)
        ry = np.random.randint(1, 20)
        if (rx, ry) != (10, 10) and (rx, ry) not in obstacles_coords:
            obstacles_coords.append((rx, ry))
            
    obstacles_actions = [game.coord_to_action(x, y) for x, y in obstacles_coords]
    
    # Game 1: A is Black (First), B is White (Second)
    res1 = play_match(params_a, params_b, obstacles_coords, obstacles_actions)
    
    # Game 2: B is Black (First), A is White (Second)
    res2 = play_match(params_b, params_a, obstacles_coords, obstacles_actions)
    
    return id_a, id_b, res1, res2

def main():
    print("=" * 60)
    print(" 오목 AI 파라미터 그리드 서치 (Grid Search) 시작")
    print("=" * 60)
    
    if utils._cpp_lib is None:
        print("[오류] C++ 최적화 DLL이 로드되지 않았습니다.")
        print("파이썬 MCTS는 그리드 서치를 수행하기에 너무 느립니다.")
        print("먼저 C++ 코드를 컴파일하고 dll 파일이 존재하는지 확인하십시오.")
        sys.exit(1)
        
    # Define Parameter Grid
    c_puct_grid = [1.0, 3.0, 5.0, 7.0]
    defense_weight_grid = [1.0, 1.2, 1.5]
    
    # Generate configurations
    configs = []
    config_id = 0
    for c_puct in c_puct_grid:
        for def_weight in defense_weight_grid:
            configs.append({
                'id': config_id,
                'c_puct': c_puct,
                'defense_weight': def_weight
            })
            config_id += 1
            
    num_configs = len(configs)
    print(f"생성된 총 하이퍼파라미터 조합 수: {num_configs}개")
    for cfg in configs:
        print(f" - ID {cfg['id']:2d}: C_puct={cfg['c_puct']:.1f}, Defense_Weight={cfg['defense_weight']:.1f}")
        
    # Number of symmetric matches per pair
    # Each pair plays symmetric games multiple times
    MATCHES_PER_PAIR = 2  # Total 4 games per matchup
    
    # Generate tasks
    tasks = []
    for i in range(num_configs):
        for j in range(i + 1, num_configs):
            for _ in range(MATCHES_PER_PAIR):
                tasks.append((i, configs[i], j, configs[j]))
                
    num_tasks = len(tasks)
    print(f"총 매치 매칭 게임 수: {num_tasks * 2}판 (라운드 로빈 대칭 대국)")
    print("-" * 60)
    
    # Run in parallel using Multiprocessing Pool
    num_cores = multiprocessing.cpu_count()
    print(f"멀티프로세싱 병렬화 활성화 (사용 가능한 코어 수: {num_cores}개)")
    
    start_time = time.time()
    
    # Initialize score tallies
    # Each win = 1.0, draw = 0.5, loss = 0.0
    wins = np.zeros(num_configs)
    losses = np.zeros(num_configs)
    draws = np.zeros(num_configs)
    points = np.zeros(num_configs)
    games_played = np.zeros(num_configs)
    
    # Use pool to execute
    pool = multiprocessing.Pool(processes=num_cores)
    
    completed = 0
    try:
        for id_a, id_b, res1, res2 in pool.imap_unordered(match_runner, tasks):
            completed += 1
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (num_tasks - completed) / rate if rate > 0 else 0
            
            # Print real-time progress on every single matchup completion
            sys.stdout.write(
                f"\r대국 시뮬레이션 진행 상황: {completed * 2}/{num_tasks * 2} 판 완료 ({completed * 100.0 / num_tasks:.1f}%) "
                f"| 경과 시간: {elapsed:.1f}초 | 남은 시간: {eta:.1f}초 | 최근 완료 매치: ID {id_a} vs ID {id_b}      "
            )
            sys.stdout.flush()
                
            # Game 1: A is Black, B is White
            games_played[id_a] += 1
            games_played[id_b] += 1
            if res1 == 1: # Black wins (A wins)
                wins[id_a] += 1
                losses[id_b] += 1
                points[id_a] += 1.0
            elif res1 == 2: # White wins (B wins)
                wins[id_b] += 1
                losses[id_a] += 1
                points[id_b] += 1.0
            else: # Draw
                draws[id_a] += 1
                draws[id_b] += 1
                points[id_a] += 0.5
                points[id_b] += 0.5
                
            # Game 2: B is Black, A is White
            games_played[id_a] += 1
            games_played[id_b] += 1
            if res2 == 1: # Black wins (B wins)
                wins[id_b] += 1
                losses[id_a] += 1
                points[id_b] += 1.0
            elif res2 == 2: # White wins (A wins)
                wins[id_a] += 1
                losses[id_b] += 1
                points[id_a] += 1.0
            else: # Draw
                draws[id_a] += 1
                draws[id_b] += 1
                points[id_a] += 0.5
                points[id_b] += 0.5
    except KeyboardInterrupt:
        print("\n[알림] 시뮬레이션이 사용자에 의해 중단되었습니다.")
        pool.terminate()
        sys.exit(1)
    finally:
        pool.close()
        pool.join()
        
    duration = time.time() - start_time
    print(f"\n\n시뮬레이션 완료! 소요 시간: {duration:.1f}초 (평균 판당 {duration/(num_tasks*2):.3f}초)")
    
    # 4. Process Results and Print Leaderboard
    leaderboard = []
    for i in range(num_configs):
        win_rate = (points[i] / games_played[i]) * 100 if games_played[i] > 0 else 0
        leaderboard.append({
            'id': i,
            'c_puct': configs[i]['c_puct'],
            'defense_weight': configs[i]['defense_weight'],
            'wins': wins[i],
            'losses': losses[i],
            'draws': draws[i],
            'games': games_played[i],
            'points': points[i],
            'win_rate': win_rate
        })
        
    # Sort by win rate descending
    leaderboard.sort(key=lambda x: x['win_rate'], reverse=True)
    
    print("\n" + "=" * 80)
    print(" 오목 하이퍼파라미터 토너먼트 리더보드 (Grid Search Leaderboard)")
    print("=" * 80)
    print(f"{'Rank':4} | {'ID':3} | {'C_puct':6} | {'Def_Weight':10} | {'Record (W-L-D)':15} | {'Points':7} | {'Win Rate':8}")
    print("-" * 80)
    for rank, item in enumerate(leaderboard):
        record_str = f"{int(item['wins']):d}-{int(item['losses']):d}-{int(item['draws']):d}"
        print(f"{rank+1:4d} | {item['id']:3d} | {item['c_puct']:6.1f} | {item['defense_weight']:10.1f} | {record_str:15} | {item['points']:7.1f} | {item['win_rate']:7.2f}%")
    print("=" * 80)
    
    best = leaderboard[0]
    print(f"\n★ 최적의 파라미터 조합 추천:")
    print(f"  - C_puct (탐색 가중치): {best['c_puct']:.1f}")
    print(f"  - Defense Weight (수비 가중치): {best['defense_weight']:.1f}")
    print(f"  - 시뮬레이션 승률: {best['win_rate']:.2f}% (기록: {int(best['wins'])}승 {int(best['losses'])}패 {int(best['draws'])}무)")
    print("=" * 80)

if __name__ == '__main__':
    # Required for multiprocessing on Windows
    multiprocessing.freeze_support()
    main()
