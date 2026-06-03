from collections import deque
import os
import ctypes
import numpy as np

ALPHABET = ' A B C D E F G H I J K L M N O P Q R S'

# Load high-performance C++ shared library if available
_cpp_lib = None
dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cpp', 'omok_cpp.dll')
if os.path.exists(dll_path):
    try:
        _cpp_lib = ctypes.CDLL(dll_path)
        
        # Configure ctypes function signatures
        _cpp_lib.check_win_cpp.argtypes = [ctypes.POINTER(ctypes.c_int)]
        _cpp_lib.check_win_cpp.restype = ctypes.c_int
        
        _cpp_lib.check_double_three_cpp.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int]
        _cpp_lib.check_double_three_cpp.restype = ctypes.c_bool
        
        _cpp_lib.evaluate_board_cpp.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        _cpp_lib.evaluate_board_cpp.restype = ctypes.c_double
        
        _cpp_lib.mcts_search_cpp.argtypes = [
            ctypes.POINTER(ctypes.c_int), # board
            ctypes.c_int,                 # start_turn
            ctypes.c_int,                 # num_mcts
            ctypes.c_double,              # c_puct
            ctypes.c_double,              # defense_weight
            ctypes.c_double               # tau
        ]
        _cpp_lib.mcts_search_cpp.restype = ctypes.c_int
        print(f"[알림] 성공적으로 C++ 최적화 DLL({dll_path})을 로드했습니다.")
    except Exception as e:
        print(f"[경고] C++ DLL 로드 실패: {e}. 파이썬 모드로 작동합니다.")
else:
    print(f"[알림] C++ 최적화 DLL을 찾을 수 없습니다. 파이썬 모드로 작동합니다.")



def valid_actions(board):
    actions = []
    count = 0
    board_size = len(board)

    for i in range(board_size):
        for j in range(board_size):
            if board[i][j] == 0:
                actions.append([(i, j), count])
            count += 1

    return actions


def legal_actions(node_id, board_size):
    all_action = {a for a in range(board_size**2)}
    action = set(node_id[1:])
    actions = all_action - action

    return list(actions)


def check_win(board, win_mark):
    """
    Safe check_win implementation that scans the board lines instead of summing,
    preventing issues with obstacle stones (value 2).
    Calls C++ optimized version if DLL is loaded and board is 19x19.
    """
    board_size = len(board)
    if _cpp_lib is not None and board_size == 19 and win_mark == 5:
        flat_board = board.flatten().astype(np.int32)
        board_ptr = flat_board.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        return int(_cpp_lib.check_win_cpp(board_ptr))
        
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    has_empty = False
    
    for r in range(board_size):
        for c in range(board_size):
            stone = board[r, c]
            if stone == 0:
                has_empty = True
                continue
            if stone == 2 or stone == -2:  # obstacle
                continue
            
            for dr, dc in directions:
                count = 1
                nr, nc = r + dr, c + dc
                while 0 <= nr < board_size and 0 <= nc < board_size and board[nr, nc] == stone:
                    count += 1
                    nr += dr
                    nc += dc
                if count >= win_mark:
                    return 1 if stone == 1 else 2
                    
    # Draw (no empty spaces left)
    if np.count_nonzero(board == 0) == 0:
        return 3
        
    return 0


def check_double_three(board, action_index, player):
    """
    Returns True if placing a stone at action_index for player (1 or -1)
    creates a forbidden double open three (3-3) on the board.
    Calls C++ optimized version if DLL is loaded and board is 19x19.
    """
    board_size = len(board)
    if _cpp_lib is not None and board_size == 19:
        flat_board = board.flatten().astype(np.int32)
        board_ptr = flat_board.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        return bool(_cpp_lib.check_double_three_cpp(board_ptr, int(action_index), int(player)))
        
    r = action_index // board_size
    c = action_index % board_size
    
    # 1. Place stone temporarily
    temp_board = board.copy()
    temp_board[r, c] = player
    
    # 2. Check if this placement wins the game. If it wins, it is allowed!
    if check_win(temp_board, 5) != 0:
        return False
        
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    open_threes = 0
    
    for dr, dc in directions:
        # Build a line of 11 cells centered at (r, c)
        # index 5 corresponds to (r, c)
        line = []
        for i in range(-5, 6):
            nr, nc = r + i*dr, c + i*dc
            if 0 <= nr < board_size and 0 <= nc < board_size:
                line.append(temp_board[nr, nc])
            else:
                line.append(2)  # Treat out of board as obstacle
                
        # Now check all 6-cell windows in this line
        # There are 6 windows starting at index 0 to 5
        for start_idx in range(6):
            window = line[start_idx : start_idx + 6]
            placed_rel_idx = 5 - start_idx
            
            # We want to check if window matches one of the four patterns:
            # player (1 or -1), 0 (empty)
            # The placed stone must be one of the player's active stones.
            patterns = [
                ([0, 0, player, player, player, 0], [2, 3, 4]),
                ([0, player, 0, player, player, 0], [1, 3, 4]),
                ([0, player, player, 0, player, 0], [1, 2, 4]),
                ([0, player, player, player, 0, 0], [1, 2, 3])
            ]
            
            is_open_three = False
            for pat, p_indices in patterns:
                if all(int(window[i]) == pat[i] for i in range(6)):
                    if placed_rel_idx in p_indices:
                        is_open_three = True
                        break
            
            if is_open_three:
                open_threes += 1
                break  # Only count at most one open three per direction
                
    return open_threes >= 2



def render_str(board, board_size, action_index):
    if action_index is not None:
        row = action_index // board_size
        col = action_index % board_size
    count = np.count_nonzero(board)
    board_str = '\n  {}\n'.format(ALPHABET[:board_size * 2])
    for i in range(board_size):
        for j in range(board_size):
            if j == 0:
                board_str += '{:2}'.format(i + 1)
            if board[i][j] == 0:
                if count > 0:
                    if col + 1 < board_size:
                        if (i, j) == (row, col + 1):
                            board_str += '.'
                        else:
                            board_str += ' .'
                    else:
                        board_str += ' .'
                else:
                    board_str += ' .'
            if board[i][j] == 1:
                if (i, j) == (row, col):
                    board_str += '(O)'
                elif (i, j) == (row, col + 1):
                    board_str += 'O'
                else:
                    board_str += ' O'
            if board[i][j] == -1:
                if (i, j) == (row, col):
                    board_str += '(X)'
                elif (i, j) == (row, col + 1):
                    board_str += 'X'
                else:
                    board_str += ' X'
            if j == board_size - 1:
                board_str += ' \n'
        if i == board_size - 1:
            board_str += '  ' + '-' * (board_size - 6) + \
                '  MOVE: {:2}  '.format(count) + '-' * (board_size - 6)
    print(board_str)


def get_state_tf(id, turn, board_size, channel_size):
    state = np.zeros([board_size, board_size, channel_size])
    length_game = len(id)

    state_1 = np.zeros([board_size, board_size])
    state_2 = np.zeros([board_size, board_size])

    channel_idx = channel_size - 1

    for i in range(length_game):
        row_idx = int(id[i] / board_size)
        col_idx = int(id[i] % board_size)

        if i != 0:
            if i % 2 == 0:
                state_1[row_idx, col_idx] = 1
            else:
                state_2[row_idx, col_idx] = 1

        if length_game - i < channel_size:
            channel_idx = length_game - i - 1
            if i % 2 == 0:
                state[:, :, channel_idx] = state_1
            else:
                state[:, :, channel_idx] = state_2

    if turn == 0:
        state[:, :, channel_size - 1] = 1
    else:
        state[:, :, channel_size - 1] = 0

    return state


def get_state_pt(node_id, board_size, channel_size):
    state_b = np.zeros((board_size, board_size))
    state_w = np.zeros((board_size, board_size))
    color = np.ones((board_size, board_size))
    color_idx = 1
    history = deque(
        [np.zeros((board_size, board_size)) for _ in range(channel_size)],
        maxlen=channel_size)

    for i, action_idx in enumerate(node_id):
        if i == 0:
            history.append(state_b.copy())
            history.append(state_w.copy())
        else:
            row = action_idx // board_size
            col = action_idx % board_size

            if i % 2 == 1:
                state_b[row, col] = 1
                history.append(state_b.copy())
                color_idx = 0
            else:
                state_w[row, col] = 1
                history.append(state_w.copy())
                color_idx = 1

    history.append(color * color_idx)
    state = np.stack(history)

    return state


def get_board(node_id, board_size, obstacles=[]):
    board = np.zeros(board_size**2)
    for obs in obstacles:
        board[obs] = 2
    for i, action_index in enumerate(node_id[1:]):
        if i % 2 == 0:
            board[action_index] = 1
        else:
            board[action_index] = -1

    return board.reshape(board_size, board_size)



def get_turn(node_id):
    if len(node_id) % 2 == 1:
        return 0
    else:
        return 1


def get_action(pi):
    action_size = len(pi)
    action = np.zeros(action_size)
    action_index = np.random.choice(action_size, p=pi)
    action[action_index] = 1

    return action, action_index


def argmax_onehot(pi):
    action_size = len(pi)
    action = np.zeros(action_size)
    max_idx = np.argwhere(pi == pi.max())
    action_index = max_idx[np.random.choice(len(max_idx))]
    action[action_index] = 1

    return action, action_index[0]


def get_reward(win_index, leaf_id):
    turn = get_turn(leaf_id)
    if win_index == 1:
        if turn == 1:
            reward = 1.
        else:
            reward = -1.
    elif win_index == 2:
        if turn == 1:
            reward = -1.
        else:
            reward = 1.
    else:
        reward = 0.

    return reward


def augment_dataset(memory, board_size):
    aug_dataset = []
    for (s, pi, z) in memory:
        for i in range(4):
            s_rot = np.rot90(s, i, axes=(1, 2)).copy()
            pi_rot = np.rot90(pi.reshape(board_size, board_size), i)
            pi_flat = pi_rot.flatten().copy()
            aug_dataset.append((s_rot, pi_flat, z))

            s_flip = np.flip(s_rot, 2).copy()
            pi_flip = np.fliplr(pi_rot).flatten().copy()
            aug_dataset.append((s_flip, pi_flip, z))

    return aug_dataset


def evaluate_board(board, player):
    """
    [Heuristic Evaluation Function V(s)]
    Scans the board in all 4 directions (rows, cols, diagonals, anti-diagonals)
    and sums up pattern scores for both player and opponent.
    Returns a normalized value in the range [-1.0, 1.0].
    Calls C++ optimized version if DLL is loaded and board is 19x19.
    """
    board_size = len(board)
    if _cpp_lib is not None and board_size == 19:
        flat_board = board.flatten().astype(np.int32)
        board_ptr = flat_board.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        return float(_cpp_lib.evaluate_board_cpp(board_ptr, int(player)))
        
    lines = get_all_lines(board)
    
    score_self = 0
    score_opp = 0
    
    # Evaluate every line on the board of length >= 5
    for line in lines:
        line_list = line.tolist()
        score_self += score_line(line_list, player)
        score_opp += score_line(line_list, -player)
        
    # Hyperbolic tangent (tanh) maps the raw score difference to [-1.0, 1.0].
    # C=10000 ensures that a difference of one Active Four (10,000) or several Active Threes
    # pushes the MCTS node evaluation close to absolute win (1.0) or loss (-1.0).
    val = np.tanh((score_self - score_opp) / 10000.0)
    return val


def get_all_lines(board):
    """
    Extracts all lines of length >= 5 from the 19x19 board.
    Includes all 19 rows, 19 columns, and all diagonals / anti-diagonals of length >= 5.
    """
    lines = []
    board_size = len(board)
    
    # 1. Rows
    for r in range(board_size):
        lines.append(board[r, :])
        
    # 2. Columns
    for c in range(board_size):
        lines.append(board[:, c])
        
    # 3. Diagonals (Top-Left to Bottom-Right)
    # The length of a diagonal with offset is board_size - abs(offset).
    # Since length must be >= 5, offset range is from -14 to 14.
    for offset in range(-(board_size - 5), board_size - 4):
        lines.append(np.diagonal(board, offset))
        
    # 4. Anti-diagonals (Top-Right to Bottom-Left)
    flipped_board = np.fliplr(board)
    for offset in range(-(board_size - 5), board_size - 4):
        lines.append(np.diagonal(flipped_board, offset))
        
    return lines


def get_local_lines(board, r, c):
    """
    OPTIMIZATION: Extracts only the 4 lines passing through cell (r, c).
    Instead of scanning the whole board (96 lines) for each candidate move,
    we only scan the affected row, col, diagonal, and anti-diagonal.
    """
    board_size = len(board)
    lines = []
    
    # 1. Row
    lines.append(board[r, :].tolist())
    
    # 2. Column
    lines.append(board[:, c].tolist())
    
    # 3. Diagonal (Top-Left to Bottom-Right passing through r, c)
    diag_offset = c - r
    lines.append(np.diagonal(board, diag_offset).tolist())
    
    # 4. Anti-diagonal (Top-Right to Bottom-Left passing through r, c)
    # Convert col index 'c' to its flipped index on fliplr board
    flipped_c = board_size - 1 - c
    anti_diag_offset = flipped_c - r
    lines.append(np.diagonal(np.fliplr(board), anti_diag_offset).tolist())
    
    return lines


def score_line(simp_line, target_player):
    """
    [Pattern Matching Window Scanner]
    Slides windows of size 5 and 6 across a single line.
    Assigns scores based on classical Omok heuristic patterns.
    """
    # Translate board values to: 1 = Self, -1 = Block (Opponent or Obstacle), 0 = Empty
    simp = []
    for cell in simp_line:
        if cell == target_player:
            simp.append(1)
        elif cell == 0:
            simp.append(0)
        else:
            simp.append(-1)
            
    score = 0
    n = len(simp)
    
    # 1. Slide window of size 6 for open/active threats (both ends must be empty)
    for i in range(n - 5):
        w = simp[i : i+6]
        
        # Active Four (Open 4): . 1 1 1 1 . (Win guaranteed next turn)
        if w == [0, 1, 1, 1, 1, 0]:
            score += 10000
            
        # Active Three (Open 3): e.g., . . 1 1 1 . or . 1 . 1 1 . (Creates Open 4 if unblocked)
        elif w in [
            [0, 0, 1, 1, 1, 0],
            [0, 1, 1, 1, 0, 0],
            [0, 1, 0, 1, 1, 0],
            [0, 1, 1, 0, 1, 0]
        ]:
            score += 1000
            
        # Active Two (Open 2): e.g., . . 1 1 . . or . . 1 . 1 .
        elif w in [
            [0, 0, 1, 1, 0, 0],
            [0, 0, 1, 0, 1, 0],
            [0, 1, 0, 1, 0, 0]
        ]:
            score += 100
            
    # 2. Slide window of size 5 for closed/absolute threats
    for i in range(n - 4):
        w = simp[i : i+5]
        ones = w.count(1)
        zeros = w.count(0)
        
        # Five in a row: 1 1 1 1 1 (Immediate Win)
        if ones == 5:
            score += 100000
            
        # Closed Four (Blocked 4): e.g., x 1 1 1 1 . or . 1 1 0 1 1 (Can make a Five)
        elif ones == 4 and zeros == 1:
            score += 1000
            
        # Closed Three (Blocked 3): e.g., x 1 1 1 . .
        elif ones == 3 and zeros == 2:
            score += 100
            
        # Closed Two (Blocked 2): e.g., x 1 1 . . .
        elif ones == 2 and zeros == 3:
            score += 10
            
        # Single stone: e.g., . . 1 . . (Base development potential)
        elif ones == 1 and zeros == 4:
            score += 1
            
    return score


def get_heuristic_policy(board, legal_actions, player):
    """
    [Prior Probability Policy Function P(s, a)]
    For each candidate move 'a', computes the score delta (Attack value) and the opponent's
    potential score delta if they played there (Defense/Block value).
    Returns a probability distribution over the legal actions.
    """
    board_size = len(board)
    scores = np.zeros(board_size**2)
    
    # Evaluate each action locally
    for action in legal_actions:
        r = action // board_size
        c = action % board_size
        
        # Get the 4 affected lines before the placement
        lines_before = get_local_lines(board, r, c)
        
        # Simulate placing player's own stone (Attack)
        temp_board_self = board.copy()
        temp_board_self[r, c] = player
        lines_after_self = get_local_lines(temp_board_self, r, c)
        
        # Simulate placing opponent's stone (Defense/Block)
        temp_board_opp = board.copy()
        temp_board_opp[r, c] = -player
        lines_after_opp = get_local_lines(temp_board_opp, r, c)
        
        attack = 0
        defense = 0
        # Calculate local score changes in all 4 directions
        for i in range(len(lines_before)):
            attack += score_line(lines_after_self[i], player) - score_line(lines_before[i], player)
            defense += score_line(lines_after_opp[i], -player) - score_line(lines_before[i], -player)
            
        # Action score = Attack + 1.2 * Defense.
        # Defense is weighted slightly higher (1.2) to ensure the AI blocks vital threats first.
        scores[action] = attack + 1.2 * defense
        
    probs = np.zeros(board_size**2)
    if not legal_actions:
        return probs
        
    # Apply softmax with temperature scaling to translate scores to probabilities.
    # To prevent numeric overflow in np.exp, we subtract the max score first.
    legal_scores = scores[legal_actions]
    max_score = np.max(legal_scores)
    
    # Temperature tau = 2.0. Smoothes probabilities slightly to allow MCTS exploration.
    tau = 2.0
    exp_scores = np.exp((legal_scores - max_score) / tau)
    sum_exp = np.sum(exp_scores)
    
    if sum_exp > 0:
        probs[legal_actions] = exp_scores / sum_exp
    else:
        probs[legal_actions] = 1.0 / len(legal_actions)
        
    return probs


