# AI Tournament and Matchmaking Simulator
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

# Pre-defined configurations
ALGORITHMS = {
    '1': {'name': 'C++ Standard MCTS (C_puct=3.0, Def=1.2, Sims=2000)', 'type': 'cpp', 'num_mcts': 2000, 'c_puct': 3.0, 'defense_weight': 1.2},
    '2': {'name': 'C++ Aggressive MCTS (C_puct=3.0, Def=1.0, Sims=2000)', 'type': 'cpp', 'num_mcts': 2000, 'c_puct': 3.0, 'defense_weight': 1.0},
    '3': {'name': 'C++ Defensive MCTS (C_puct=3.0, Def=1.5, Sims=2000)', 'type': 'cpp', 'num_mcts': 2000, 'c_puct': 3.0, 'defense_weight': 1.5},
    '4': {'name': 'C++ Low Expl MCTS (C_puct=1.0, Def=1.2, Sims=2000)', 'type': 'cpp', 'num_mcts': 2000, 'c_puct': 1.0, 'defense_weight': 1.2},
    '5': {'name': 'C++ High Expl MCTS (C_puct=5.0, Def=1.2, Sims=2000)', 'type': 'cpp', 'num_mcts': 2000, 'c_puct': 5.0, 'defense_weight': 1.2},
    '6': {'name': 'C++ High Sims MCTS (C_puct=3.0, Def=1.2, Sims=4000)', 'type': 'cpp', 'num_mcts': 4000, 'c_puct': 3.0, 'defense_weight': 1.2},
    '7': {'name': 'Python Fallback MCTS (C_puct=3.0, Def=1.2, Sims=400)', 'type': 'python', 'num_mcts': 400, 'c_puct': 3.0, 'defense_weight': 1.2}
}

def create_agent(cfg, board_size, obstacles):
    """
    Creates agent instance based on config dictionary.
    """
    if cfg['type'] == 'cpp' and utils._cpp_lib is not None:
        agent = agents.CppHeuristicMCTS(board_size=board_size, num_mcts=cfg['num_mcts'], obstacles=obstacles)
    else:
        agent = agents.HeuristicMCTS(board_size=board_size, num_mcts=cfg['num_mcts'], obstacles=obstacles)
    agent.c_puct = cfg['c_puct']
    agent.defense_weight = cfg['defense_weight']
    return agent

def play_single_match(cfg_black, cfg_white, obstacles_coords, obstacles_actions):
    """
    Plays a fast match without console output for tournament processing.
    """
    env = game.GameState(obstacles=obstacles_coords)
    black_agent = create_agent(cfg_black, 19, obstacles_actions)
    white_agent = create_agent(cfg_white, 19, obstacles_actions)
    
    root_id = (0, 180)
    action_index = 180
    board = env.gameboard
    turn = env.turn
    win_index = 0
    
    while win_index == 0:
        if turn == 0:
            pi = black_agent.get_pi(root_id, board, turn, tau=0)
        else:
            pi = white_agent.get_pi(root_id, board, turn, tau=0)
            
        action_index = int(np.argmax(pi))
        board, _, win_index, turn, _ = env.step(action_index)
        root_id += (action_index,)
        
    return win_index

def tournament_worker(task):
    """
    Worker function for parallelized tournament matches.
    """
    id_a, cfg_a, id_b, cfg_b, game_id = task
    
    # Generate random obstacles
    obstacles_coords = []
    while len(obstacles_coords) < 3:
        rx = np.random.randint(1, 20)
        ry = np.random.randint(1, 20)
        if (rx, ry) != (10, 10) and (rx, ry) not in obstacles_coords:
            obstacles_coords.append((rx, ry))
    obstacles_actions = [game.coord_to_action(x, y) for x, y in obstacles_coords]
    
    # Run two games with roles swapped to ensure symmetry
    res1 = play_single_match(cfg_a, cfg_b, obstacles_coords, obstacles_actions) # A: Black, B: White
    res2 = play_single_match(cfg_b, cfg_a, obstacles_coords, obstacles_actions) # B: Black, A: White
    
    return id_a, id_b, res1, res2

def configure_custom_agent():
    print("\n[사용자 정의 알고리즘 설정]")
    while True:
        mode = input("에이전트 타입 선택 (1: C++ DLL 사용, 2: Pure Python): ").strip()
        if mode in ['1', '2']:
            agent_type = 'cpp' if mode == '1' else 'python'
            break
        print("[에러] 1 또는 2를 입력하세요.")
        
    while True:
        try:
            sims = int(input("MCTS 시뮬레이션 횟수 입력 (추천 1000~4000): ").strip())
            if sims > 0:
                break
            print("[에러] 0보다 큰 수여야 합니다.")
        except ValueError:
            print("[에러] 양의 정수를 입력하세요.")
            
    while True:
        try:
            c_puct = float(input("C_puct 탐색 가중치 입력 (추천 1.0~5.0): ").strip())
            if c_puct > 0:
                break
            print("[에러] 0보다 큰 수여야 합니다.")
        except ValueError:
            print("[에러] 실수를 입력하세요.")
            
    while True:
        try:
            def_w = float(input("Defense Weight 수비 가중치 입력 (추천 1.0~1.8): ").strip())
            if def_w >= 0:
                break
            print("[에러] 0보다 크거나 같아야 합니다.")
        except ValueError:
            print("[에러] 실수를 입력하세요.")
            
    return {
        'name': f'Custom (Type={agent_type.upper()}, Sims={sims}, C_puct={c_puct}, Def={def_w})',
        'type': agent_type,
        'num_mcts': sims,
        'c_puct': c_puct,
        'defense_weight': def_w
    }

def print_registered_algorithms():
    print("\n" + "-" * 60)
    print(" 등록된 알고리즘 리스트")
    print("-" * 60)
    for key, cfg in ALGORITHMS.items():
        print(f" {key}: {cfg['name']}")
    print("-" * 60)

def main():
    print("=" * 60)
    print(" 오목 AI 알고리즘 대전 및 선별 시뮬레이터")
    print("=" * 60)
    
    # Mode selection
    while True:
        print("\n[대국 방식 선택]")
        print(" 1: 1대1 맞대결 (Head-to-Head) - 콘솔 바둑판 렌더링 시각화 포함")
        print(" 2: 전체 리그전 토너먼트 (Round-Robin League) - 멀티프로세싱 고속 연산")
        choice = input("선택 (1 또는 2): ").strip()
        if choice in ['1', '2']:
            break
        print("[에러] 1 또는 2를 입력하세요.")
        
    # User custom algorithm registration option
    print_registered_algorithms()
    cust_choice = input("사용자 정의 파라미터 알고리즘을 추가로 등록하시겠습니까? (y/n): ").strip().lower()
    if cust_choice == 'y':
        custom_cfg = configure_custom_agent()
        new_key = str(len(ALGORITHMS) + 1)
        ALGORITHMS[new_key] = custom_cfg
        print(f"\n[알림] 알고리즘 {new_key}번으로 등록되었습니다.")
        print_registered_algorithms()
        
    if choice == '1':
        # Head to Head Mode
        print("\n[1대1 맞대결 모드 설정]")
        while True:
            a_idx = input("첫 번째 알고리즘(흑돌 시작) 번호 입력: ").strip()
            if a_idx in ALGORITHMS:
                break
            print("[에러] 등록된 번호를 입력해주세요.")
            
        while True:
            b_idx = input("두 번째 알고리즘(백돌 시작) 번호 입력: ").strip()
            if b_idx in ALGORITHMS:
                break
            print("[에러] 등록된 번호를 입력해주세요.")
            
        while True:
            try:
                games = int(input("진행할 대국 판 수 입력 (짝수 권장, 예: 2 또는 4): ").strip())
                if games >= 1:
                    break
                print("[에러] 1판 이상이어야 합니다.")
            except ValueError:
                print("[에러] 정수를 입력하세요.")
                
        while True:
            try:
                val = input("착수 간 렌더링 대기 시간(초)을 입력하세요 (예: 0.5): ").strip()
                if not val:
                    delay = 0.5
                    break
                delay = float(val)
                if delay >= 0.0:
                    break
                print("[에러] 0보다 크거나 같아야 합니다.")
            except ValueError:
                print("[에러] 실수를 입력해주세요.")
                
        cfg_a = ALGORITHMS[a_idx]
        cfg_b = ALGORITHMS[b_idx]
        
        print(f"\n매치 시작: {cfg_a['name']} vs {cfg_b['name']} ({games}판)")
        
        stats = {'A_win': 0, 'B_win': 0, 'Draw': 0}
        
        for g in range(games):
            print("\n" + "=" * 60)
            print(f" 대국 {g + 1} / {games} 판 시작")
            print("=" * 60)
            
            # Generate random obstacles
            obstacles_coords = []
            while len(obstacles_coords) < 3:
                rx = np.random.randint(1, 20)
                ry = np.random.randint(1, 20)
                if (rx, ry) != (10, 10) and (rx, ry) not in obstacles_coords:
                    obstacles_coords.append((rx, ry))
            obstacles_actions = [game.coord_to_action(x, y) for x, y in obstacles_coords]
            
            # Roles swap on alternate games to ensure color fairness
            if g % 2 == 0:
                black_cfg = cfg_a
                white_cfg = cfg_b
                p_black_name = "Agent A"
                p_white_name = "Agent B"
            else:
                black_cfg = cfg_b
                white_cfg = cfg_a
                p_black_name = "Agent B"
                p_white_name = "Agent A"
                
            env = game.GameState(obstacles=obstacles_coords)
            black_agent = create_agent(black_cfg, 19, obstacles_actions)
            white_agent = create_agent(white_cfg, 19, obstacles_actions)
            
            root_id = (0, 180)
            action_index = 180
            board = env.gameboard
            turn = env.turn
            win_index = 0
            
            while win_index == 0:
                env.render_console(last_action_index=action_index)
                curr_p_name = p_black_name if turn == 0 else p_white_name
                curr_cfg = black_cfg if turn == 0 else white_cfg
                print(f"[{curr_p_name} ({curr_cfg['name']}) 수읽기 중...]")
                
                if turn == 0:
                    pi = black_agent.get_pi(root_id, board, turn, tau=0)
                else:
                    pi = white_agent.get_pi(root_id, board, turn, tau=0)
                    
                action_index = int(np.argmax(pi))
                x, y = game.action_to_coord(action_index)
                print(f"-> 착수 좌표: {x},{y} (Action: {action_index})")
                
                board, _, win_index, turn, _ = env.step(action_index)
                root_id += (action_index,)
                
                if delay > 0:
                    time.sleep(delay)
                    
            env.render_console(last_action_index=action_index)
            print("-" * 60)
            if win_index == 1:
                winner = p_black_name
                print(f"★ {winner} 승리! (흑돌)")
            elif win_index == 2:
                winner = p_white_name
                print(f"★ {winner} 승리! (백돌)")
            else:
                winner = "Draw"
                print("★ 무승부!")
                
            if winner == "Agent A":
                stats['A_win'] += 1
            elif winner == "Agent B":
                stats['B_win'] += 1
            else:
                stats['Draw'] += 1
                
        print("\n" + "=" * 60)
        print(" 1대1 맞대결 결과 요약")
        print("=" * 60)
        print(f" - {cfg_a['name']}: {stats['A_win']} 승")
        print(f" - {cfg_b['name']}: {stats['B_win']} 승")
        print(f" - 무승부: {stats['Draw']} 무")
        
        total_games = stats['A_win'] + stats['B_win'] + stats['Draw']
        win_rate_a = (stats['A_win'] + 0.5 * stats['Draw']) / total_games * 100
        print(f" => {cfg_a['name']} 기준 승률: {win_rate_a:.2f}%")
        print("=" * 60)
        
    else:
        # League Tournament Mode
        print("\n[전체 리그전 토너먼트 모드 설정]")
        while True:
            try:
                pairs_matches = int(input("매치 매칭 당 게임 세트 수 입력 (짝수 권장, 예: 2 또는 4): ").strip())
                if pairs_matches >= 1:
                    break
                print("[에러] 1판 이상이어야 합니다.")
            except ValueError:
                print("[에러] 정수를 입력하세요.")
                
        # Generate tournament tasks
        keys = sorted(list(ALGORITHMS.keys()), key=int)
        tasks = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                for g in range(pairs_matches // 2 + 1 if pairs_matches % 2 != 0 else pairs_matches // 2):
                    tasks.append((keys[i], ALGORITHMS[keys[i]], keys[j], ALGORITHMS[keys[j]], g))
                    
        num_tasks = len(tasks)
        print(f"\n총 대국 매칭 작업 수: {num_tasks}개 (각 작업당 흑/백 대칭으로 2판씩 진행, 총 {num_tasks * 2}판)")
        
        num_cores = multiprocessing.cpu_count()
        print(f"멀티프로세싱 병렬화 구동 (CPU 코어 수: {num_cores}개)")
        
        start_time = time.time()
        
        # Initialize scoreboard
        wins = {k: 0.0 for k in keys}
        losses = {k: 0.0 for k in keys}
        draws = {k: 0.0 for k in keys}
        points = {k: 0.0 for k in keys}
        played = {k: 0.0 for k in keys}
        
        pool = multiprocessing.Pool(processes=num_cores)
        completed = 0
        
        try:
            for id_a, id_b, res1, res2 in pool.imap_unordered(tournament_worker, tasks):
                completed += 1
                sys.stdout.write(
                    f"\r토너먼트 진행도: {completed * 2}/{num_tasks * 2} 판 완료 ({completed * 100.0 / num_tasks:.1f}%) "
                    f"| 경과 시간: {time.time() - start_time:.1f}초 | 매치: ID {id_a} vs ID {id_b}      "
                )
                sys.stdout.flush()
                
                # Game 1: A is Black, B is White
                played[id_a] += 1
                played[id_b] += 1
                if res1 == 1:
                    wins[id_a] += 1
                    losses[id_b] += 1
                    points[id_a] += 1.0
                elif res1 == 2:
                    wins[id_b] += 1
                    losses[id_a] += 1
                    points[id_b] += 1.0
                else:
                    draws[id_a] += 1
                    draws[id_b] += 1
                    points[id_a] += 0.5
                    points[id_b] += 0.5
                    
                # Game 2: B is Black, A is White
                played[id_a] += 1
                played[id_b] += 1
                if res2 == 1:
                    wins[id_b] += 1
                    losses[id_a] += 1
                    points[id_b] += 1.0
                elif res2 == 2:
                    wins[id_a] += 1
                    losses[id_b] += 1
                    points[id_a] += 1.0
                else:
                    draws[id_a] += 1
                    draws[id_b] += 1
                    points[id_a] += 0.5
                    points[id_b] += 0.5
        except KeyboardInterrupt:
            print("\n[알림] 사용자에 의해 토너먼트가 중단되었습니다.")
            pool.terminate()
            sys.exit(1)
        finally:
            pool.close()
            pool.join()
            
        duration = time.time() - start_time
        print(f"\n\n토너먼트 완료! 소요 시간: {duration:.1f}초 (평균 판당 {duration / (num_tasks * 2):.3f}초)")
        
        # Rank calculations
        leaderboard = []
        for k in keys:
            win_rate = (points[k] / played[k]) * 100 if played[k] > 0 else 0
            leaderboard.append({
                'id': k,
                'name': ALGORITHMS[k]['name'],
                'wins': wins[k],
                'losses': losses[k],
                'draws': draws[k],
                'played': played[k],
                'points': points[k],
                'win_rate': win_rate
            })
            
        leaderboard.sort(key=lambda x: x['win_rate'], reverse=True)
        
        print("\n" + "=" * 90)
        print(" 오목 알고리즘 토너먼트 최종 리더보드 (Tournament Leaderboard)")
        print("=" * 90)
        print(f"{'Rank':4} | {'ID':2} | {'Algorithm Name':55} | {'Record':9} | {'Points':6} | {'Win Rate':8}")
        print("-" * 90)
        for rank, item in enumerate(leaderboard):
            rec_str = f"{int(item['wins'])}-{int(item['losses'])}-{int(item['draws'])}"
            print(f"{rank+1:4d} | {item['id']:2} | {item['name'][:55]:55} | {rec_str:9} | {item['points']:6.1f} | {item['win_rate']:7.2f}%")
        print("=" * 90)
        
        best = leaderboard[0]
        print(f"\n★ 선별된 가장 강력한 알고리즘:")
        print(f"  - 명칭: {best['name']}")
        print(f"  - 종합 성적: {int(best['wins'])}승 {int(best['losses'])}패 {int(best['draws'])}무 (승점 {best['points']:.1f}점)")
        print(f"  - 최종 승률: {best['win_rate']:.2f}%")
        print("=" * 90)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    if os.name == 'nt':
        os.system('color')
    main()
