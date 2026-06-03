# Competition Omok Environment
'''
This is the competition version of Omok.
Board size: 19 x 19
Win: Black or white stone has to be 5 or more in a row (horizontal, vertical, diagonal)
Compensation Rules:
1. Black's first stone is automatically placed at the center (10, 10). Turn immediately passes to White.
2. 3 red obstacle stones are placed at the beginning of the game. Neither player can place stones there.
Coordinates: X-axis (1--19) from left to right, Y-axis (1--19) from bottom to top.
Origin (1,1) is at the bottom-left corner of the board.
'''

import sys
import numpy as np

GAMEBOARD_SIZE = 19
WIN_STONES = 5

# Coordinate Conversions
def coord_to_matrix(x, y):
    """
    Converts X, Y coordinates (1-19) where (1,1) is bottom-left
    to numpy matrix indices (row, col) where (0,0) is top-left.
    """
    row = GAMEBOARD_SIZE - y
    col = x - 1
    return row, col

def matrix_to_coord(row, col):
    """
    Converts numpy matrix indices (row, col) where (0,0) is top-left
    to X, Y coordinates (1-19) where (1,1) is bottom-left.
    """
    x = col + 1
    y = GAMEBOARD_SIZE - row
    return x, y

def action_to_coord(action_index):
    row = action_index // GAMEBOARD_SIZE
    col = action_index % GAMEBOARD_SIZE
    return matrix_to_coord(row, col)

def coord_to_action(x, y):
    row, col = coord_to_matrix(x, y)
    return row * GAMEBOARD_SIZE + col

def ReturnName():
    return 'competition_omok'

def Return_Num_Action():
    return GAMEBOARD_SIZE * GAMEBOARD_SIZE

def Return_BoardParams():
    return GAMEBOARD_SIZE, GAMEBOARD_SIZE**2

class GameState:
    def __init__(self, obstacles=[]):
        """
        obstacles: list of tuples/lists of X,Y coordinates (1-19) e.g., [(3,5), (10,12), (17,8)]
        """
        self.obstacles = []
        for obs in obstacles:
            x, y = obs
            row, col = coord_to_matrix(x, y)
            self.obstacles.append((row, col))
            
        self.init_game()

    def init_game(self):
        # 0: Empty, 1: Black, -1: White, 2: Red Obstacle
        self.gameboard = np.zeros([GAMEBOARD_SIZE, GAMEBOARD_SIZE], dtype=int)
        
        # Place obstacles
        for r, c in self.obstacles:
            self.gameboard[r, c] = 2
            
        # Rule (1): Black (1) must place first stone at center (10, 10)
        center_row, center_col = coord_to_matrix(10, 10)
        self.gameboard[center_row, center_col] = 1
        
        # White turn: 1 (0: Black, 1: White)
        self.turn = 1
        self.num_stones = 1
        self.init = False

    def step(self, input_action):
        """
        input_action: either an integer action index or a one-hot array of length 361
        Returns: gameboard, check_valid_pos, win_index, turn, action_index
        """
        if self.init:
            self.init_game()

        # Parse action index
        if isinstance(input_action, (int, np.integer)):
            action_index = int(input_action)
        else:
            action_index = np.argmax(input_action)
            
        y_index = action_index // GAMEBOARD_SIZE
        x_index = action_index % GAMEBOARD_SIZE
        
        check_valid_pos = True
        # Check if placement is on an empty space (0)
        if self.gameboard[y_index, x_index] != 0:
            check_valid_pos = False

        if check_valid_pos:
            if self.turn == 0:
                self.gameboard[y_index, x_index] = 1
                self.turn = 1
            else:
                self.gameboard[y_index, x_index] = -1
                self.turn = 0
            self.num_stones += 1

        # Check win condition (5 or more in a row)
        # 0: playing, 1: black win, 2: white win, 3: draw
        win_index = self.check_win_competition()
        
        if win_index != 0:
            self.init = True
        else:
            self.init = False

        return self.gameboard, check_valid_pos, win_index, self.turn, action_index

    def check_win_competition(self):
        """
        Checks win condition of 5 or more stones in a row.
        0: playing, 1: black win, 2: white win, 3: draw
        """
        # We can implement a clean check for horizontal, vertical, and diagonal lines.
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        board = self.gameboard
        
        has_empty = False
        
        for r in range(GAMEBOARD_SIZE):
            for c in range(GAMEBOARD_SIZE):
                stone = board[r, c]
                if stone == 0:
                    has_empty = True
                    continue
                if stone == 2:  # obstacle
                    continue
                
                # Check 4 directions
                for dr, dc in directions:
                    count = 1
                    nr, nc = r + dr, c + dc
                    while 0 <= nr < GAMEBOARD_SIZE and 0 <= nc < GAMEBOARD_SIZE and board[nr, nc] == stone:
                        count += 1
                        nr += dr
                        nc += dc
                        
                    # Since 5 or more wins, count >= WIN_STONES
                    if count >= WIN_STONES:
                        return 1 if stone == 1 else 2
                        
        if not has_empty:
            return 3  # Draw
            
        return 0

    def render_console(self, last_action_index=None):
        """
        Renders the 19x19 board in console using nice colored Unicode text symbols.
        """
        # Color codes
        GREEN = '\033[92m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        YELLOW = '\033[93m'
        RESET = '\033[0m'
        
        # Last action row and col
        last_r, last_c = -1, -1
        if last_action_index is not None:
            last_r = last_action_index // GAMEBOARD_SIZE
            last_c = last_action_index % GAMEBOARD_SIZE

        print("\n" + " " * 4 + GREEN + " ".join(f"{x:2d}" for x in range(1, 20)) + RESET + "  (X)")
        print(" " * 3 + "+" + "-" * 57 + "+")
        
        for r in range(GAMEBOARD_SIZE):
            y = GAMEBOARD_SIZE - r
            row_str = GREEN + f"{y:2d} | " + RESET
            for c in range(GAMEBOARD_SIZE):
                cell = self.gameboard[r, c]
                
                # Render symbol
                if cell == 1:  # Black
                    # On dark terminals, filled circle "●" renders white and open circle "○" renders black.
                    # We swap them so Black is represented by the open circle (dark center) and White by the filled circle.
                    symbol = "○"
                    if r == last_r and c == last_c:
                        symbol = YELLOW + "○" + RESET
                elif cell == -1:  # White
                    symbol = "●"
                    if r == last_r and c == last_c:
                        symbol = YELLOW + "●" + RESET
                elif cell == 2:  # Obstacle
                    symbol = RED + "■" + RESET
                else:  # Empty
                    # Standard grid symbol
                    symbol = "."
                
                row_str += symbol + "  "
            
            row_str += GREEN + f"| {y:2d}" + RESET
            print(row_str)
            
        print(" " * 3 + "+" + "-" * 57 + "+")
        print(" " * 4 + GREEN + " ".join(f"{x:2d}" for x in range(1, 20)) + RESET)
        print(f"  Stones played: {self.num_stones} | Turn: {'Black (First)' if self.turn == 0 else 'White (Second)'}")
        print()
