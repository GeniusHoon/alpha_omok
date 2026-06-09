# AI Tournament and Matchmaking Simulator (Multi-Threaded)
import sys
import os
import time
import numpy as np
import json
import multiprocessing

# Adjust path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from env import env_competition as game
import utils
import agents

# Pre-defined configurations matching all evaluated algorithms
ALGORITHMS = {
    '1': {
        'name': 'Legacy C++ High Sims (C_puct=3.0, Def=1.2, Sims=4000)',
        'type': 'cpp',
        'num_mcts': 4000,
        'c_puct': 3.0,
        'defense_weight': 1.2,
        'score_table': [100000, 10000, 1000, 1000, 100, 100, 10, 1]
    },
    '2': {
        'name': 'Current C++ High Sims (C_puct=3.0, Def=1.2, Sims=4000, Scores=10:1)',
        'type': 'cpp',
        'num_mcts': 4000,
        'c_puct': 3.0,
        'defense_weight': 1.2,
        'score_table': [1000000, 100000, 10000, 10000, 1000, 100, 10, 1]
    },
    '3': {
        'name': 'Current C++ High Sims (C_puct=3.0, Def=1.2, Sims=4000, Scores=Balanced)',
        'type': 'cpp',
        'num_mcts': 4000,
        'c_puct': 3.0,
        'defense_weight': 1.2,
        'score_table': [1000000, 100000, 20000, 5000, 500, 100, 10, 1]
    },
    '4': {
        'name': 'Current C++ High Sims (C_puct=3.0, Def=1.2, Sims=4000, Scores=ttt)',
        'type': 'cpp',
        'num_mcts': 4000,
        'c_puct': 3.0,
        'defense_weight': 1.2,
        'score_table': [1000000, 100000, 20000, 5000, 1000, 100, 10, 1]
    },
    '5': {
        'name': 'Current C++ High Sims (C_puct=3.0, Def=1.2, Sims=4000, Scores=Aggressive_Attack)',
        'type': 'cpp',
        'num_mcts': 4000,
        'c_puct': 3.0,
        'defense_weight': 1.2,
        'score_table': [1000000, 200000, 10000, 20000, 1000, 500, 10, 1]
    },
    '6': {
        'name': 'Current C++ High Sims (C_puct=3.0, Def=1.2, Sims=4000, Scores=Iron_Wall_Defensive)',
        'type': 'cpp',
        'num_mcts': 4000,
        'c_puct': 3.0,
        'defense_weight': 1.2,
        'score_table': [1000000, 100000, 40000, 5000, 3000, 200, 50, 1]
    },
    '7': {
        'name': 'Current C++ High Sims (C_puct=3.0, Def=1.2, Sims=4000, Scores=Fibonacci_Exponential)',
        'type': 'cpp',
        'num_mcts': 4000,
        'c_puct': 3.0,
        'defense_weight': 1.2,
        'score_table': [1000000, 80000, 20000, 5000, 1000, 200, 50, 1]
    },

}

def create_agent(cfg, board_size, obstacles):
    """
    Creates agent instance based on config dictionary.
    """
    score_table = cfg.get('score_table', None)
    if cfg['type'] == 'cpp' and utils._cpp_lib is not None:
        agent = agents.CppHeuristicMCTS(board_size=board_size, num_mcts=cfg['num_mcts'], obstacles=obstacles, score_table=score_table)
    else:
        agent = agents.HeuristicMCTS(board_size=board_size, num_mcts=cfg['num_mcts'], obstacles=obstacles, score_table=score_table)
            
    agent.c_puct = cfg['c_puct']
    agent.defense_weight = cfg['defense_weight']
    return agent

def play_single_match(cfg_black, cfg_white, obstacles_coords, obstacles_actions):
    """
    Plays a fast match without console output for tournament processing.
    Returns: (win_index, history_list)
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
        
    return win_index, list(root_id)

def tournament_worker(task):
    """
    Worker function for parallelized tournament matches.
    """
    black_id, black_cfg, white_id, white_cfg, game_id = task
    
    # Generate random obstacles
    obstacles_coords = []
    while len(obstacles_coords) < 3:
        rx = int(np.random.randint(1, 20))
        ry = int(np.random.randint(1, 20))
        if (rx, ry) != (10, 10) and (rx, ry) not in obstacles_coords:
            obstacles_coords.append((rx, ry))
    obstacles_actions = [game.coord_to_action(x, y) for x, y in obstacles_coords]
    
    try:
        res, _ = play_single_match(black_cfg, white_cfg, obstacles_coords, obstacles_actions)
        return black_id, white_id, res, None
    except Exception as e:
        return black_id, white_id, None, str(e)

def configure_custom_agent():
    print("\n[사용자 정의 에이전트 설정]")
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
            
    score_table = None
    while True:
        ans = input("휴리스틱 스코어 테이블도 수정하시겠습니까? (y/n) [기본값: n]: ").strip().lower()
        if not ans or ans == 'n':
            break
        if ans == 'y':
            print("8개의 정수 값(쉼표 구분)을 입력하세요.")
            print("순서: 오목, 열린4, 닫힌4, 열린3, 닫힌3, 열린2, 닫힌2, 단일돌")
            print("예시: 100000,50000,20000,5000,1000,100,100,1")
            raw_scores = input("스코어 입력: ").strip()
            try:
                parts = [int(p.strip()) for p in raw_scores.split(',')]
                if len(parts) != 8:
                    print(f"[에러] 입력된 스코어 개수가 {len(parts)}개입니다. 반드시 8개여야 합니다.")
                    continue
                score_table = parts
                print(f"[알림] 스코어 테이블 설정 완료: {score_table}")
                break
            except ValueError:
                print("[에러] 올바른 정수 리스트 형식이 아닙니다.")
        else:
            print("[에러] y 또는 n을 입력하세요.")
            
    name_str = f'Custom ({agent_type.upper()}, Sims={sims}, C_puct={c_puct}, Def={def_w}'
    if score_table is not None:
        name_str += f', DynamicScores'
    name_str += ')'

    return {
        'name': name_str,
        'type': agent_type,
        'num_mcts': sims,
        'c_puct': c_puct,
        'defense_weight': def_w,
        'legacy': is_legacy,
        'score_table': score_table
    }

def print_registered_algorithms():
    print("\n" + "-" * 75)
    print(" 등록된 알고리즘 리스트")
    print("-" * 75)
    for key, cfg in ALGORITHMS.items():
        print(f" {key}: {cfg['name']}")
    print("-" * 75)

def main():
    import sys
    is_auto = "--auto" in sys.argv
    
    print("=" * 60)
    print(" 오목 AI 알고리즘 대전 및 선별 시뮬레이터 (Single-Threaded)")
    print("=" * 60)
    
    if is_auto:
        choice = '2'
        cust_choice = 'n'
    else:
        # Mode selection
        while True:
            print("\n[대국 방식 선택]")
            print(" 1: 1대1 맞대결 (Head-to-Head) - 콘솔 바둑판 렌더링 시각화 포함 (매 게임 저장)")
            print(" 2: 전체 리그전 토너먼트 (Round-Robin League) - 싱글스레드 순차 진행 (매 게임 저장)")
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
        
    # Setup results path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_file = os.path.join(script_dir, "tournament_results.json")
    
    # Load existing results or initialize fresh list
    tournament_games = []
    if os.path.exists(results_file):
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    tournament_games = json.loads(content)
            print(f"[알림] 기존 대국 데이터 {len(tournament_games)}개를 로드했습니다.")
        except Exception as e:
            print(f"[경고] 기존 결과 파일을 읽는 데 실패했습니다 ({e}). 새로 시작합니다.")
            tournament_games = []
            
    # Ask whether to clear or append
    if is_auto:
        tournament_games = []
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump([], f)
    elif tournament_games:
        while True:
            clear_choice = input("기존 대국 결과를 초기화하고 새로 시작하시겠습니까? (y/n): ").strip().lower()
            if clear_choice == 'y':
                tournament_games = []
                with open(results_file, "w", encoding="utf-8") as f:
                    json.dump([], f)
                print("[알림] 기존 대국 결과를 초기화했습니다.")
                break
            elif clear_choice == 'n':
                print("[알림] 기존 대국 결과 뒤에 이어서 기록합니다.")
                break
            print("[에러] y 또는 n을 입력하세요.")
    else:
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump([], f)
            
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
                rx = int(np.random.randint(1, 20))
                ry = int(np.random.randint(1, 20))
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
                print(f"★ {winner} 승리! (흑돌: {black_cfg['name']})")
            elif win_index == 2:
                winner = p_white_name
                print(f"★ {winner} 승리! (백돌: {white_cfg['name']})")
            else:
                winner = "Draw"
                print("★ 무승부!")
                
            if winner == "Agent A":
                stats['A_win'] += 1
            elif winner == "Agent B":
                stats['B_win'] += 1
            else:
                stats['Draw'] += 1
                
            # Save this game immediately to JSON
            if win_index == 1:
                winner_text = black_cfg['name']
            elif win_index == 2:
                winner_text = white_cfg['name']
            else:
                winner_text = "Draw"
                
            game_record = {
                "game_id": len(tournament_games) + 1,
                "black_name": black_cfg['name'],
                "white_name": white_cfg['name'],
                "winner": winner_text,
                "win_index": int(win_index),
                "history": [int(x) for x in root_id],
                "obstacles": [[int(cx), int(cy)] for cx, cy in obstacles_coords]
            }
            tournament_games.append(game_record)
            
            try:
                with open(results_file, "w", encoding="utf-8") as f:
                    json.dump(tournament_games, f, ensure_ascii=False, indent=2)
                print(f"[알림] 대국 {len(tournament_games)} 저장 완료 -> {results_file}")
            except Exception as e:
                print(f"[에러] 대국 저장 중 오류 발생: {e}")
                
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
        # League Tournament Mode (Round-Robin)
        print("\n[전체 리그전 토너먼트 모드 설정]")
        if is_auto:
            pairs_matches = 6
        else:
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
        
        # Generate tasks: each task is a single game matching
        tasks = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                id_a = keys[i]
                id_b = keys[j]
                cfg_a = ALGORITHMS[id_a]
                cfg_b = ALGORITHMS[id_b]
                for g in range(pairs_matches):
                    if g % 2 == 0:
                        # A is Black, B is White
                        tasks.append((id_a, cfg_a, id_b, cfg_b, len(tasks) + 1))
                    else:
                        # B is Black, A is White
                        tasks.append((id_b, cfg_b, id_a, cfg_a, len(tasks) + 1))
                        
        total_games = len(tasks)
        num_cores = multiprocessing.cpu_count()
        print(f"\n총 대국 수: {total_games}판 (멀티프로세싱 병렬화 구동, CPU 코어 수: {num_cores}개)")
        
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
            for black_id, white_id, res, err in pool.imap_unordered(tournament_worker, tasks):
                completed += 1
                sys.stdout.write(
                    f"\r토너먼트 진행도: {completed}/{total_games} 판 완료 ({completed * 100.0 / total_games:.1f}%) "
                    f"| 경과 시간: {time.time() - start_time:.1f}초"
                )
                sys.stdout.flush()
                
                if err is not None:
                    print(f"\n[에러] 대국 중 오류 발생: {err}")
                    continue
                
                played[black_id] += 1
                played[white_id] += 1
                
                if res == 1:
                    wins[black_id] += 1
                    losses[white_id] += 1
                    points[black_id] += 1.0
                elif res == 2:
                    wins[white_id] += 1
                    losses[black_id] += 1
                    points[white_id] += 1.0
                else:
                    draws[black_id] += 1
                    draws[white_id] += 1
                    points[black_id] += 0.5
                    points[white_id] += 0.5
        except KeyboardInterrupt:
            print("\n[알림] 사용자에 의해 토너먼트가 중단되었습니다.")
            pool.terminate()
            sys.exit(1)
        finally:
            pool.close()
            pool.join()
            
        duration = time.time() - start_time
        print(f"\n\n토너먼트 완료! 총 소요 시간: {duration:.1f}초 (평균 판당 {duration / total_games:.3f}초)")
        
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
