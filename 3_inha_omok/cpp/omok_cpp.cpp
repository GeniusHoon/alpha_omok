#include <iostream>
#include <vector>
#include <unordered_map>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>

// const int BOARD_SIZE = 19;
// const int WIN_STONES = 5;
#define BOARD_SIZE 19
#define WIN_STONES 5

// Helper function to convert 2D index to 1D index
inline int idx(int r, int c) {
    return r * BOARD_SIZE + c;
}

// C++ implementation of check_win
extern "C" __declspec(dllexport) int check_win_cpp(const int* board) {
    int directions[4][2] = {{0, 1}, {1, 0}, {1, 1}, {1, -1}};
    bool has_empty = false;
    
    for (int r = 0; r < BOARD_SIZE; ++r) {
        for (int c = 0; c < BOARD_SIZE; ++c) {
            int stone = board[idx(r, c)];
            if (stone == 0) {
                has_empty = true;
                continue;
            }
            if (stone == 2 || stone == -2) { // Obstacle
                continue;
            }
            
            for (int d = 0; d < 4; ++d) {
                int dr = directions[d][0];
                int dc = directions[d][1];
                int count = 1;
                int nr = r + dr;
                int nc = c + dc;
                
                while (nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[idx(nr, nc)] == stone) {
                    count++;
                    nr += dr;
                    nc += dc;
                }
                
                if (count >= WIN_STONES) {
                    return (stone == 1) ? 1 : 2;
                }
            }
        }
    }
    
    if (!has_empty) {
        return 3; // Draw
    }
    return 0; // Playing
}

// Structure to store local lines on stack without dynamic allocation
struct LocalLines {
    int data[4][BOARD_SIZE];
    int lengths[4];
};

// Helper to extract 4 local lines passing through (r, c)
LocalLines get_local_lines_cpp(const int* board, int r, int c) {
    LocalLines lines;
    
    // 1. Row
    lines.lengths[0] = BOARD_SIZE;
    for (int col = 0; col < BOARD_SIZE; ++col) {
        lines.data[0][col] = board[idx(r, col)];
    }
    
    // 2. Column
    lines.lengths[1] = BOARD_SIZE;
    for (int row = 0; row < BOARD_SIZE; ++row) {
        lines.data[1][row] = board[idx(row, c)];
    }
    
    // 3. Diagonal (Top-Left to Bottom-Right)
    int diag_offset = c - r;
    int idx_diag = 0;
    for (int row = 0; row < BOARD_SIZE; ++row) {
        int col = row + diag_offset;
        if (col >= 0 && col < BOARD_SIZE) {
            lines.data[2][idx_diag++] = board[idx(row, col)];
        }
    }
    lines.lengths[2] = idx_diag;
    
    // 4. Anti-diagonal (Top-Right to Bottom-Left)
    int sum_val = r + c;
    int idx_anti = 0;
    for (int row = 0; row < BOARD_SIZE; ++row) {
        int col = sum_val - row;
        if (col >= 0 && col < BOARD_SIZE) {
            lines.data[3][idx_anti++] = board[idx(row, col)];
        }
    }
    lines.lengths[3] = idx_anti;
    
    return lines;
}

// C++ implementation of score_line
extern "C" __declspec(dllexport) int score_line_cpp(const int* line, int len, int target_player, const int* score_table) {
    // Translate line to: 1 = Self, -1 = Block (Opponent or Obstacle), 0 = Empty
    int simp[BOARD_SIZE];
    for (int i = 0; i < len; ++i) {
        int cell = line[i];
        if (cell == target_player) {
            simp[i] = 1;
        } else if (cell == 0) {
            simp[i] = 0;
        } else {
            simp[i] = -1;
        }
    }
    
    int score = 0;
    
    // 1. Window of size 6
    if (len >= 6) {
        for (int i = 0; i <= len - 6; ++i) {
            // Check patterns
            int w[6];
            for (int k = 0; k < 6; ++k) w[k] = simp[i + k];
            
            // Active Four: . 1 1 1 1 .
            if (w[0] == 0 && w[1] == 1 && w[2] == 1 && w[3] == 1 && w[4] == 1 && w[5] == 0) {
                score += score_table[1];
            }
            // Active Three:
            // . . 1 1 1 . (0, 0, 1, 1, 1, 0)
            // . 1 1 1 . . (0, 1, 1, 1, 0, 0)
            // . 1 . 1 1 . (0, 1, 0, 1, 1, 0)
            // . 1 1 . 1 . (0, 1, 1, 0, 1, 0)
            else if (w[0] == 0 && w[5] == 0) {
                if ((w[1] == 0 && w[2] == 1 && w[3] == 1 && w[4] == 1) ||
                    (w[1] == 1 && w[2] == 1 && w[3] == 1 && w[4] == 0) ||
                    (w[1] == 1 && w[2] == 0 && w[3] == 1 && w[4] == 1) ||
                    (w[1] == 1 && w[2] == 1 && w[3] == 0 && w[4] == 1)) {
                    score += score_table[3];
                }
            }
            // Active Two:
            // . . 1 1 . . (0, 0, 1, 1, 0, 0)
            // . . 1 . 1 . (0, 0, 1, 0, 1, 0)
            // . 1 . 1 . . (0, 1, 0, 1, 0, 0)
            else if (w[0] == 0 && w[5] == 0) {
                if ((w[1] == 0 && w[2] == 1 && w[3] == 1 && w[4] == 0) ||
                    (w[1] == 0 && w[2] == 1 && w[3] == 0 && w[4] == 1) ||
                    (w[1] == 1 && w[2] == 0 && w[3] == 1 && w[4] == 0)) {
                    score += score_table[5];
                }
            }
        }
    }
    
    // 2. Window of size 5
    if (len >= 5) {
        for (int i = 0; i <= len - 5; ++i) {
            int ones = 0;
            int zeros = 0;
            for (int k = 0; k < 5; ++k) {
                if (simp[i + k] == 1) ones++;
                else if (simp[i + k] == 0) zeros++;
            }
            
            if (ones == 5) {
                score += score_table[0];
            } else if (ones == 4 && zeros == 1) {
                score += score_table[2]; // Four in a row
            } else if (ones == 3 && zeros == 2) {
                score += score_table[4]; // Three in a row
            } else if (ones == 2 && zeros == 3) {
                score += score_table[6]; // Two in a row
            } else if (ones == 1 && zeros == 4) {
                score += score_table[7]; // Single
            }
        }
    }
    
    return score;
}

// C++ implementation of check_double_three
extern "C" __declspec(dllexport) bool check_double_three_cpp(const int* board, int action_index, int player) {
    int r = action_index / BOARD_SIZE;
    int c = action_index % BOARD_SIZE;
    
    // 1. Temporarily place stone (in-place modification to avoid heap allocation & copy)
    int* mutable_board = const_cast<int*>(board);
    int original_stone = mutable_board[action_index];
    mutable_board[action_index] = player;
    
    // 2. If it wins, it is allowed
    if (check_win_cpp(mutable_board) != 0) {
        mutable_board[action_index] = original_stone; // Restore
        return false;
    }
    
    int directions[4][2] = {{0, 1}, {1, 0}, {1, 1}, {1, -1}};
    int open_threes = 0;
    
    for (int d = 0; d < 4; ++d) {
        int dr = directions[d][0];
        int dc = directions[d][1];
        
        // Build 11-cell line centered at (r, c)
        // index 5 in this line is the placed stone (r, c)
        int line[11];
        std::fill(line, line + 11, 2); // default to obstacle (2)
        for (int i = -5; i <= 5; ++i) {
            int nr = r + i * dr;
            int nc = c + i * dc;
            if (nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE) {
                line[i + 5] = mutable_board[idx(nr, nc)];
            }
        }
        
        // Check 6-cell windows
        for (int start_idx = 0; start_idx < 6; ++start_idx) {
            int window[6];
            for (int k = 0; k < 6; ++k) window[k] = line[start_idx + k];
            int placed_rel_idx = 5 - start_idx;
            
            // Check patterns
            // patterns:
            // 1. [0, 0, P, P, P, 0], active indices: 2, 3, 4
            // 2. [0, P, 0, P, P, 0], active indices: 1, 3, 4
            // 3. [0, P, P, 0, P, 0], active indices: 1, 2, 4
            // 4. [0, P, P, P, 0, 0], active indices: 1, 2, 3
            bool is_open_three = false;
            
            // P1: [0, 0, player, player, player, 0]
            if (window[0] == 0 && window[1] == 0 && window[2] == player && window[3] == player && window[4] == player && window[5] == 0) {
                if (placed_rel_idx == 2 || placed_rel_idx == 3 || placed_rel_idx == 4) is_open_three = true;
            }
            // P2: [0, player, 0, player, player, 0]
            else if (window[0] == 0 && window[1] == player && window[2] == 0 && window[3] == player && window[4] == player && window[5] == 0) {
                if (placed_rel_idx == 1 || placed_rel_idx == 3 || placed_rel_idx == 4) is_open_three = true;
            }
            // P3: [0, player, player, 0, player, 0]
            else if (window[0] == 0 && window[1] == player && window[2] == player && window[3] == 0 && window[4] == player && window[5] == 0) {
                if (placed_rel_idx == 1 || placed_rel_idx == 2 || placed_rel_idx == 4) is_open_three = true;
            }
            // P4: [0, player, player, player, 0, 0]
            else if (window[0] == 0 && window[1] == player && window[2] == player && window[3] == player && window[4] == 0 && window[5] == 0) {
                if (placed_rel_idx == 1 || placed_rel_idx == 2 || placed_rel_idx == 3) is_open_three = true;
            }
            
            if (is_open_three) {
                open_threes++;
                break; // Only count at most one open three per direction
            }
        }
    }
    
    mutable_board[action_index] = original_stone; // Restore
    return open_threes >= 2;
}

// C++ implementation of evaluate_board
extern "C" __declspec(dllexport) double evaluate_board_cpp(const int* board, int player, const int* score_table) {
    int score_self = 0;
    int score_opp = 0;
    
    // 1. Rows (contiguous in memory, pass pointer directly)
    for (int r = 0; r < BOARD_SIZE; ++r) {
        score_self += score_line_cpp(board + idx(r, 0), BOARD_SIZE, player, score_table);
        score_opp += score_line_cpp(board + idx(r, 0), BOARD_SIZE, -player, score_table);
    }
    
    // 2. Columns (stack array)
    for (int c = 0; c < BOARD_SIZE; ++c) {
        int col[BOARD_SIZE];
        for (int r = 0; r < BOARD_SIZE; ++r) col[r] = board[idx(r, c)];
        score_self += score_line_cpp(col, BOARD_SIZE, player, score_table);
        score_opp += score_line_cpp(col, BOARD_SIZE, -player, score_table);
    }
    
    // 3. Diagonals (Top-Left to Bottom-Right) (stack array)
    for (int offset = -(BOARD_SIZE - 5); offset <= BOARD_SIZE - 5; ++offset) {
        int diag[BOARD_SIZE];
        int idx_diag = 0;
        for (int r = 0; r < BOARD_SIZE; ++r) {
            int c = r + offset;
            if (c >= 0 && c < BOARD_SIZE) {
                diag[idx_diag++] = board[idx(r, c)];
            }
        }
        score_self += score_line_cpp(diag, idx_diag, player, score_table);
        score_opp += score_line_cpp(diag, idx_diag, -player, score_table);
    }
    
    // 4. Anti-diagonals (Top-Right to Bottom-Left) (stack array)
    for (int offset = -(BOARD_SIZE - 5); offset <= BOARD_SIZE - 5; ++offset) {
        int anti_diag[BOARD_SIZE];
        int idx_anti = 0;
        for (int r = 0; r < BOARD_SIZE; ++r) {
            int c_flipped = r + offset;
            if (c_flipped >= 0 && c_flipped < BOARD_SIZE) {
                int c = BOARD_SIZE - 1 - c_flipped;
                anti_diag[idx_anti++] = board[idx(r, c)];
            }
        }
        score_self += score_line_cpp(anti_diag, idx_anti, player, score_table);
        score_opp += score_line_cpp(anti_diag, idx_anti, -player, score_table);
    }
    
    double norm_const = score_table[1] == 0 ? 1.0 : (double)score_table[1];
    return std::tanh((score_self - score_opp) / norm_const);
}

// C++ implementation of get_heuristic_policy
void get_heuristic_policy_cpp(const int* board, const int* legal_actions, int num_legal, int player, double defense_weight, double tau, double* out_probs, const int* score_table) {
    double scores[BOARD_SIZE * BOARD_SIZE] = {0.0};
    
    int* mutable_board = const_cast<int*>(board);
    
    for (int idx_act = 0; idx_act < num_legal; ++idx_act) {
        int action = legal_actions[idx_act];
        int r = action / BOARD_SIZE;
        int c = action % BOARD_SIZE;
        
        // Affected lines before placement
        LocalLines lines_before = get_local_lines_cpp(board, r, c);
        
        // Attack (Self stone) - modify in-place
        mutable_board[action] = player;
        LocalLines lines_after_self = get_local_lines_cpp(mutable_board, r, c);
        
        // Defense (Opponent stone) - modify in-place
        mutable_board[action] = -player;
        LocalLines lines_after_opp = get_local_lines_cpp(mutable_board, r, c);
        
        // Restore board
        mutable_board[action] = 0;
        
        double attack = 0.0;
        double defense = 0.0;
        
        for (size_t i = 0; i < 4; ++i) {
            attack += score_line_cpp(lines_after_self.data[i], lines_after_self.lengths[i], player, score_table) -
                      score_line_cpp(lines_before.data[i], lines_before.lengths[i], player, score_table);
            defense += score_line_cpp(lines_after_opp.data[i], lines_after_opp.lengths[i], -player, score_table) -
                       score_line_cpp(lines_before.data[i], lines_before.lengths[i], -player, score_table);
        }
        
        scores[action] = attack + defense_weight * defense;
    }
    
    // Apply softmax with temperature scaling to translate scores to probabilities.
    // To prevent numeric overflow, we subtract the max score first.
    double max_score = -1e9;
    for (int idx_act = 0; idx_act < num_legal; ++idx_act) {
        int action = legal_actions[idx_act];
        if (scores[action] > max_score) {
            max_score = scores[action];
        }
    }
    
    double sum_exp = 0.0;
    double exp_scores[BOARD_SIZE * BOARD_SIZE] = {0.0};
    for (int idx_act = 0; idx_act < num_legal; ++idx_act) {
        int action = legal_actions[idx_act];
        exp_scores[action] = std::exp((scores[action] - max_score) / tau);
        sum_exp += exp_scores[action];
    }
    
    std::fill(out_probs, out_probs + BOARD_SIZE * BOARD_SIZE, 0.0);
    for (int idx_act = 0; idx_act < num_legal; ++idx_act) {
        int action = legal_actions[idx_act];
        if (sum_exp > 0.0) {
            out_probs[action] = exp_scores[action] / sum_exp;
        } else {
            out_probs[action] = 1.0 / num_legal;
        }
    }
}

const int MAX_NODES = 2000000;

// Tree Node for C++ MCTS - optimized to be flat, stack/global pool compatible
// Align to 32 bytes for cache efficiency
struct alignas(32) MCTSNode {
    int32_t parent_idx = -1;
    int32_t first_child_idx = -1;
    float total_value = 0.0f;
    float mean_value = 0.0f;
    float prior_prob = 0.0f;
    int16_t action = -1;
    uint16_t visit_count = 0;
    int16_t num_children = 0;
    bool is_expanded = false;
    char padding[5] = {0}; // Pad to exactly 32 bytes (cache line aligned)
};

// Global pre-allocated node pool for zero-allocation MCTS search
MCTSNode node_pool[MAX_NODES];
int node_counter = 0;

// C++ MCTS simulation step (optimized with float variables and outside std::sqrt)
int select_leaf_cpp(int root_idx, int* board, int& player, float c_puct) {
    int node_idx = root_idx;
    while (node_pool[node_idx].is_expanded && node_pool[node_idx].num_children > 0) {
        float max_qu = -1e9f;
        int best_child_idx = -1;
        
        int first_child = node_pool[node_idx].first_child_idx;
        int num_children = node_pool[node_idx].num_children;
        
        int total_n = 0;
        for (int i = 0; i < num_children; ++i) {
            total_n += node_pool[first_child + i].visit_count;
        }
        
        // Cache square root computation outside loop
        float sqrt_total_n = std::sqrt(total_n);
        for (int i = 0; i < num_children; ++i) {
            int child_idx = first_child + i;
            float q = node_pool[child_idx].mean_value;
            float u = c_puct * node_pool[child_idx].prior_prob * sqrt_total_n / (node_pool[child_idx].visit_count + 1);
            float qu = q + u;
            if (qu > max_qu) {
                max_qu = qu;
                best_child_idx = child_idx;
            }
        }
        
        if (best_child_idx == -1) {
            break;
        }
        
        node_idx = best_child_idx;
        board[node_pool[node_idx].action] = player;
        player = -player;
    }
    return node_idx;
}

// Perform C++ MCTS and return the best action index
extern "C" __declspec(dllexport) int mcts_search_cpp(const int* start_board, int start_turn, int num_mcts, double c_puct, double defense_weight, double tau, const int* score_table) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Cast input params to float internally for fast float computation
    float c_puct_f = static_cast<float>(c_puct);
    float defense_weight_f = static_cast<float>(defense_weight);
    float tau_f = static_cast<float>(tau);
    
    // Reset global node counter
    node_counter = 0;
    
    // Allocate root node (index 0)
    int root_idx = node_counter++;
    node_pool[root_idx].parent_idx = -1;
    node_pool[root_idx].action = -1;
    node_pool[root_idx].visit_count = 0;
    node_pool[root_idx].total_value = 0.0f;
    node_pool[root_idx].mean_value = 0.0f;
    node_pool[root_idx].prior_prob = 0.0f;
    node_pool[root_idx].first_child_idx = -1;
    node_pool[root_idx].num_children = 0;
    node_pool[root_idx].is_expanded = false;
    
    for (int i = 0; i < num_mcts; ++i) {
        // Cutoff at 2.8 seconds
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > 2.8) {
            break;
        }
        
        // 1. Selection
        int sim_board[BOARD_SIZE * BOARD_SIZE];
        std::copy(start_board, start_board + BOARD_SIZE * BOARD_SIZE, sim_board);
        int player = (start_turn == 0) ? 1 : -1; // 0: Black(1), 1: White(-1)
        
        int leaf_idx = select_leaf_cpp(root_idx, sim_board, player, c_puct_f);
        
        // 2. Expansion & Evaluation
        int win_index = check_win_cpp(sim_board);
        float value = 0.0f;
        bool is_terminal = (win_index != 0);
        
        if (is_terminal) {
            // Leaf represents a terminal win/loss/draw
            int prev_player = -player;
            if (win_index == 1) { // Black won
                value = (prev_player == 1) ? 1.0f : -1.0f;
            } else if (win_index == 2) { // White won
                value = (prev_player == -1) ? 1.0f : -1.0f;
            } else {
                value = 0.0f;
            }
        } else {
            // Identify legal actions
            int legal_actions[BOARD_SIZE * BOARD_SIZE];
            int num_legal = 0;
            for (int action = 0; action < BOARD_SIZE * BOARD_SIZE; ++action) {
                if (sim_board[action] == 0) {
                    // Check double three
                    if (!check_double_three_cpp(sim_board, action, player)) {
                        legal_actions[num_legal++] = action;
                    }
                }
            }
            
            if (num_legal == 0) {
                // No moves left => Draw
                value = 0.0f;
                is_terminal = true;
            } else {
                // Get prior policy using heuristic
                double prior_prob[BOARD_SIZE * BOARD_SIZE] = {0.0};
                get_heuristic_policy_cpp(sim_board, legal_actions, num_legal, player, defense_weight_f, tau_f, prior_prob, score_table);
                
                // Expand node (allocate contiguous block from global pool)
                // Safety check to prevent pool overflow
                if (node_counter + num_legal < MAX_NODES) {
                    node_pool[leaf_idx].first_child_idx = node_counter;
                    node_pool[leaf_idx].num_children = num_legal;
                    
                    for (int idx_act = 0; idx_act < num_legal; ++idx_act) {
                        int child_idx = node_counter++;
                        int action = legal_actions[idx_act];
                        
                        node_pool[child_idx].parent_idx = leaf_idx;
                        node_pool[child_idx].action = action;
                        node_pool[child_idx].visit_count = 0;
                        node_pool[child_idx].total_value = 0.0f;
                        node_pool[child_idx].mean_value = 0.0f;
                        node_pool[child_idx].prior_prob = static_cast<float>(prior_prob[action]);
                        node_pool[child_idx].first_child_idx = -1;
                        node_pool[child_idx].num_children = 0;
                        node_pool[child_idx].is_expanded = false;
                    }
                    node_pool[leaf_idx].is_expanded = true;
                }
                
                // Evaluate board from the current player's perspective
                value = static_cast<float>(evaluate_board_cpp(sim_board, player, score_table));
            }
        }
        
        // 3. Backup
        float temp_val = is_terminal ? value : -value;
        int curr_idx = leaf_idx;
        while (curr_idx != -1) {
            node_pool[curr_idx].visit_count++;
            node_pool[curr_idx].total_value += temp_val;
            node_pool[curr_idx].mean_value = node_pool[curr_idx].total_value / node_pool[curr_idx].visit_count;
            temp_val = -temp_val;
            curr_idx = node_pool[curr_idx].parent_idx;
        }
    }
    
    // Choose the best child based on visit count
    int best_action = -1;
    int max_visits = -1;
    int first_child = node_pool[root_idx].first_child_idx;
    int num_children = node_pool[root_idx].num_children;
    
    for (int i = 0; i < num_children; ++i) {
        int child_idx = first_child + i;
        if (node_pool[child_idx].visit_count > max_visits) {
            max_visits = node_pool[child_idx].visit_count;
            best_action = node_pool[child_idx].action;
        }
    }
    
    return best_action;
}
