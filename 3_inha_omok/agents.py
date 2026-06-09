import sys
import time
import threading

import numpy as np

import utils


class Agent(object):
    def __init__(self, board_size):

        self.policy = np.zeros(board_size**2, 'float')
        self.visit = np.zeros(board_size**2, 'float')
        self.message = 'Hello'

    def get_policy(self):
        return self.policy

    def get_visit(self):
        return self.visit

    def get_name(self):
        return type(self).__name__

    def get_message(self):
        return self.message

    def get_pv(self, root_id):
        return None, None

class HeuristicMCTS(Agent):
    def __init__(self, board_size, num_mcts, obstacles=[], score_table=None):
        super(HeuristicMCTS, self).__init__(board_size)
        self.board_size = board_size
        self.num_mcts = num_mcts
        self.win_mark = 5
        self.c_puct = 3
        self.obstacles = obstacles  # List of integer action indices
        self.score_table = score_table if score_table is not None else utils.DEFAULT_SCORES
        self.root_id = None
        self.tree = {}

    def reset(self):
        self.root_id = None
        self.tree.clear()

    def get_pi(self, root_id, board, turn, tau):
        self._init_mcts(root_id)
        self._mcts(self.root_id)

        visit = np.zeros(self.board_size**2, 'float')
        policy = np.zeros(self.board_size**2, 'float')

        for action_index in self.tree[self.root_id]['child']:
            child_id = self.root_id + (action_index,)
            visit[action_index] = self.tree[child_id]['n']
            policy[action_index] = self.tree[child_id]['p']

        self.visit = visit
        self.policy = policy

        visit_sum = visit.sum()
        if visit_sum > 0:
            pi = visit / visit_sum
        else:
            pi = np.zeros(self.board_size**2, 'float')
            for action_index in self.tree[self.root_id]['child']:
                pi[action_index] = self.tree[self.root_id + (action_index,)]['p']
            if pi.sum() > 0:
                pi /= pi.sum()
            else:
                pi = np.ones(self.board_size**2, 'float') / (self.board_size**2)

        if tau == 0:
            pi, _ = utils.argmax_onehot(pi)

        return pi

    def _init_mcts(self, root_id):
        self.root_id = root_id
        if self.root_id not in self.tree:
            self.tree[self.root_id] = {'child': [],
                                       'n': 0.,
                                       'w': 0.,
                                       'q': 0.,
                                       'p': 0.}

    def _mcts(self, root_id):
        start_time = time.time()
        for i in range(self.num_mcts):
            if time.time() - start_time > 2.8:
                break
                
            leaf_id, win_index = self._selection(root_id)
            value, reward = self._expansion_evaluation(leaf_id, win_index)
            self._backup(leaf_id, value, reward)

    def _selection(self, root_id):
        node_id = root_id

        while self.tree[node_id]['n'] > 0:
            board = utils.get_board(node_id, self.board_size, self.obstacles)
            win_index = utils.check_win(board, self.win_mark)

            if win_index != 0:
                return node_id, win_index

            qu = {}
            total_n = 0

            for action_idx in self.tree[node_id]['child']:
                edge_id = node_id + (action_idx,)
                total_n += self.tree[edge_id]['n']

            for action_index in self.tree[node_id]['child']:
                child_id = node_id + (action_index,)
                n = self.tree[child_id]['n']
                q = self.tree[child_id]['q']
                p = self.tree[child_id]['p']
                u = self.c_puct * p * np.sqrt(total_n) / (n + 1)
                qu[child_id] = q + u

            if not qu:
                break
                
            max_value = max(qu.values())
            ids = [key for key, value in qu.items() if value == max_value]
            node_id = ids[np.random.choice(len(ids))]

        board = utils.get_board(node_id, self.board_size, self.obstacles)
        win_index = utils.check_win(board, self.win_mark)

        return node_id, win_index

    def _expansion_evaluation(self, leaf_id, win_index):
        if win_index != 0:
            reward = 1.0
            value = False
            return value, reward
            
        board = utils.get_board(leaf_id, self.board_size, self.obstacles)
        turn = utils.get_turn(leaf_id)
        player = 1 if turn == 0 else -1
        
        all_actions = range(self.board_size**2)
        placed = set(leaf_id[1:])
        obstacle_set = set(self.obstacles)
        
        actions = []
        for action in all_actions:
            if action not in placed and action not in obstacle_set:
                if not utils.check_double_three(board, action, player):
                    actions.append(action)
                    
        if not actions:
            reward = 0.0
            value = False
            return value, reward
            
        prior_prob = utils.get_heuristic_policy(board, actions, player, self.score_table)
        
        for action_index in actions:
            child_id = leaf_id + (action_index,)
            self.tree[child_id] = {'child': [],
                                   'n': 0.,
                                   'w': 0.,
                                   'q': 0.,
                                   'p': prior_prob[action_index]}
            self.tree[leaf_id]['child'].append(action_index)
            
        value = utils.evaluate_board(board, player, self.score_table)
        reward = False
        return value, reward

    def _backup(self, leaf_id, value, reward):
        node_id = leaf_id
        count = 0
        while node_id != self.root_id[:-1]:
            self.tree[node_id]['n'] += 1

            if not reward:
                self.tree[node_id]['w'] += (-value) * (-1)**(count)
                count += 1
            else:
                self.tree[node_id]['w'] += reward * (-1)**(count)
                count += 1

            self.tree[node_id]['q'] = (self.tree[node_id]['w'] /
                                       self.tree[node_id]['n'])
            parent_id = node_id[:-1]
            node_id = parent_id

    def del_parents(self, root_id):
        max_len = 0
        if self.tree:
            for key in list(self.tree.keys()):
                if len(key) > max_len:
                    max_len = len(key)
                if len(key) < len(root_id):
                    del self.tree[key]
        print('tree size:', len(self.tree))
        print('tree depth:', 0 if max_len <= 0 else max_len - 1)




class CppHeuristicMCTS(Agent):
    def __init__(self, board_size, num_mcts, obstacles=[], score_table=None):
        super(CppHeuristicMCTS, self).__init__(board_size)
        self.board_size = board_size
        self.num_mcts = num_mcts
        self.obstacles = obstacles  # List of integer action indices
        self.score_table = score_table if score_table is not None else utils.DEFAULT_SCORES
        # Default hyperparameters, which can be modified during grid search
        self.c_puct = 3.0
        self.defense_weight = 1.2
        self.tau = 2.0

    def reset(self):
        pass

    def get_pi(self, root_id, board, turn, tau):
        # 1. Reconstruct board with obstacles
        full_board = utils.get_board(root_id, self.board_size, self.obstacles)
        
        # 2. Convert board array to ctypes pointer of int
        flat_board = full_board.flatten().astype(np.int32)
        import ctypes
        board_ptr = flat_board.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        
        # 3. Call optimized C++ MCTS search
        # start_turn is 0 for Black, 1 for White
        best_action = -1
        if utils._cpp_lib is not None:
            score_table_array = np.array(self.score_table, dtype=np.int32)
            score_table_ptr = score_table_array.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
            best_action = utils._cpp_lib.mcts_search_cpp(
                board_ptr,
                int(turn),
                int(self.num_mcts),
                float(self.c_puct),
                float(self.defense_weight),
                float(self.tau),
                score_table_ptr
            )
        
        # Fallback to random move if DLL fails or cannot find move
        if best_action == -1:
            print("[경고] C++ MCTS에서 행동을 찾지 못해 임의의 적법한 수를 선택합니다.")
            placed = set(root_id[1:])
            obstacle_set = set(self.obstacles)
            legal_moves = [a for a in range(self.board_size**2) if a not in placed and a not in obstacle_set]
            best_action = np.random.choice(legal_moves) if legal_moves else 0

        pi = np.zeros(self.board_size**2, 'float')
        pi[best_action] = 1.0
        
        self.visit = pi
        self.policy = pi
        
        return pi

    def del_parents(self, root_id):
        pass





