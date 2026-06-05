# Play Omok on GUI using Tkinter
import sys
import os
import time
import threading
import numpy as np
import tkinter as tk
from tkinter import messagebox

# Adjust path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from env import env_competition as game
import utils
import agents

class OmokGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("인하 오목 AI 대전 (Tkinter GUI)")
        self.root.geometry("960x680")
        self.root.resizable(False, False)
        
        # Windows styling
        self.root.configure(bg="#121214")
        
        # Game State Variables
        self.board_size = 19
        self.obstacles = []       # List of action indices
        self.obstacles_coords = [] # List of (x, y) coordinates
        self.player_color = 0     # 0: Black (First), 1: White (Second)
        
        self.env = None
        self.ai_agent = None
        self.root_id = (0, 180)   # Root node ID starts with Black's center placement
        self.action_index = 180
        self.game_started = False
        self.game_over = False
        self.ai_thinking = False
        
        # Background MCTS communication
        self.ai_action = None
        self.ai_completed = False
        
        # Hover tracking
        self.hover_pos = None
        
        # History for Undo
        self.history = [] # List of tuples: (root_id, gameboard_copy, turn, num_stones, last_action_index)
        
        # Board geometry
        self.margin = 40
        self.cell_size = 30
        self.stone_radius = 12
        
        # Star points (Hoshi) coordinates (0-indexed)
        self.star_points = [
            (3, 3), (3, 9), (3, 15),
            (9, 3), (9, 9), (9, 15),
            (15, 3), (15, 9), (15, 15)
        ]
        
        # Setup UI layout
        self.create_widgets()
        
        # Draw initial blank board
        self.draw_board()
        
        # Check DLL status
        self.check_dll_status()

    def check_dll_status(self):
        if utils._cpp_lib is not None:
            self.lbl_dll_status.configure(text="C++ 최적화 DLL: 로드 완료 (속도 최상)", fg="#4caf50")
        else:
            self.lbl_dll_status.configure(text="C++ 최적화 DLL: 로드 실패 (파이썬 모드 작동)", fg="#f44336")

    def create_widgets(self):
        # 1. Canvas Frame (Left)
        self.frame_left = tk.Frame(self.root, bg="#121214")
        self.frame_left.pack(side=tk.LEFT, padx=15, pady=15)
        
        # Canvas board size: 40 + 18*30 + 40 = 620
        self.canvas = tk.Canvas(self.frame_left, width=620, height=620, bg="#e4a853", highlightthickness=0)
        self.canvas.pack()
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        self.canvas.bind("<Leave>", self.on_canvas_leave)
        
        # 2. Control Sidebar Frame (Right)
        self.frame_right = tk.Frame(self.root, bg="#1a1a1e", width=280)
        self.frame_right.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 15), pady=15)
        self.frame_right.pack_propagate(False)
        
        # Game Header Title
        lbl_title = tk.Label(self.frame_right, text="INHA OMOK AI", font=("Malgun Gothic", 18, "bold"), bg="#1a1a1e", fg="#ffffff")
        lbl_title.pack(pady=(20, 10))
        
        lbl_subtitle = tk.Label(self.frame_right, text="인하 오목 MCTS 대회용 에이전트", font=("Malgun Gothic", 9), bg="#1a1a1e", fg="#8a8a8f")
        lbl_subtitle.pack(pady=(0, 20))
        
        # Separator line
        sep = tk.Frame(self.frame_right, height=1, bg="#2c2c30")
        sep.pack(fill=tk.X, padx=15, pady=5)
        
        # DLL status
        self.lbl_dll_status = tk.Label(self.frame_right, text="C++ 최적화 DLL 상태 확인 중...", font=("Malgun Gothic", 9, "bold"), bg="#1a1a1e", fg="#ff9800")
        self.lbl_dll_status.pack(pady=5)
        
        # Main setup container
        self.setup_frame = tk.Frame(self.frame_right, bg="#1a1a1e")
        self.setup_frame.pack(fill=tk.BOTH, expand=True, padx=15)
        
        # Setup instruction
        self.lbl_instruct = tk.Label(self.setup_frame, text="[단계 1: 장애물 배치]\n바둑판 위를 클릭하여 빨간색 장애물 돌\n3개를 배치해주세요 (중앙 10,10 제외).", font=("Malgun Gothic", 10), bg="#1a1a1e", fg="#ff9800", justify=tk.LEFT)
        self.lbl_instruct.pack(pady=10, fill=tk.X)
        
        # Obstacle status label
        self.lbl_obs_status = tk.Label(self.setup_frame, text="설정된 장애물 수: 0 / 3", font=("Malgun Gothic", 10, "bold"), bg="#1a1a1e", fg="#ffffff")
        self.lbl_obs_status.pack(pady=5)
        
        # Random obstacle button
        self.btn_random_obs = tk.Button(self.setup_frame, text="장애물 무작위 배치", font=("Malgun Gothic", 10), bg="#33333b", fg="#ffffff", activebackground="#44444f", activeforeground="#ffffff", borderwidth=0, relief=tk.FLAT, command=self.generate_random_obstacles)
        self.btn_random_obs.pack(pady=5, fill=tk.X)
        
        # Player Color Selector Frame
        self.color_frame = tk.LabelFrame(self.setup_frame, text="돌 색상 선택", font=("Malgun Gothic", 10, "bold"), bg="#1a1a1e", fg="#ffffff", borderwidth=1, relief=tk.GROOVE)
        self.color_frame.pack(pady=15, fill=tk.X, ipady=5)
        
        self.color_var = tk.IntVar(value=0) # 0: Black, 1: White
        self.rb_black = tk.Radiobutton(self.color_frame, text="흑돌 (선수, 10,10 자동착수)", variable=self.color_var, value=0, bg="#1a1a1e", fg="#ffffff", selectcolor="#1a1a1e", font=("Malgun Gothic", 9), activebackground="#1a1a1e", activeforeground="#ffffff")
        self.rb_black.pack(anchor=tk.W, padx=10, pady=2)
        self.rb_white = tk.Radiobutton(self.color_frame, text="백돌 (후수)", variable=self.color_var, value=1, bg="#1a1a1e", fg="#ffffff", selectcolor="#1a1a1e", font=("Malgun Gothic", 9), activebackground="#1a1a1e", activeforeground="#ffffff")
        self.rb_white.pack(anchor=tk.W, padx=10, pady=2)
        
        # MCTS Simulations entry
        self.sim_frame = tk.Frame(self.setup_frame, bg="#1a1a1e")
        self.sim_frame.pack(pady=5, fill=tk.X)
        lbl_sim = tk.Label(self.sim_frame, text="MCTS 시뮬레이션 횟수:", font=("Malgun Gothic", 9), bg="#1a1a1e", fg="#8a8a8f")
        lbl_sim.pack(side=tk.LEFT)
        self.ent_sim = tk.Entry(self.sim_frame, width=8, font=("Malgun Gothic", 9), justify=tk.RIGHT, bg="#2c2c35", fg="#ffffff", insertbackground="#ffffff", borderwidth=0)
        self.ent_sim.insert(0, "2000")
        self.ent_sim.pack(side=tk.RIGHT)
        
        # Start game button
        self.btn_start = tk.Button(self.setup_frame, text="대국 시작하기", font=("Malgun Gothic", 11, "bold"), bg="#2c2c30", fg="#5a5a60", activebackground="#2c2c30", activeforeground="#5a5a60", borderwidth=0, relief=tk.FLAT, state=tk.DISABLED, command=self.start_game)
        self.btn_start.pack(pady=(20, 10), fill=tk.X, ipady=5)
        
        # Game control widgets (hidden at start)
        self.game_frame = tk.Frame(self.frame_right, bg="#1a1a1e")
        
        self.lbl_game_turn = tk.Label(self.game_frame, text="차례: 대기 중", font=("Malgun Gothic", 12, "bold"), bg="#1a1a1e", fg="#ff9800")
        self.lbl_game_turn.pack(pady=10)
        
        self.lbl_game_stones = tk.Label(self.game_frame, text="놓인 돌 수: 0", font=("Malgun Gothic", 10), bg="#1a1a1e", fg="#ffffff")
        self.lbl_game_stones.pack(pady=5)
        
        self.lbl_last_move = tk.Label(self.game_frame, text="마지막 착수: 없음", font=("Malgun Gothic", 10), bg="#1a1a1e", fg="#8a8a8f")
        self.lbl_last_move.pack(pady=5)
        
        self.lbl_warning = tk.Label(self.game_frame, text="", font=("Malgun Gothic", 9, "bold"), bg="#1a1a1e", fg="#f44336")
        self.lbl_warning.pack(pady=10)
        
        # Undo button
        self.btn_undo = tk.Button(self.game_frame, text="한 수 무르기 (Undo)", font=("Malgun Gothic", 10, "bold"), bg="#2196f3", fg="#ffffff", activebackground="#1976d2", activeforeground="#ffffff", borderwidth=0, relief=tk.FLAT, command=self.undo_move)
        self.btn_undo.pack(pady=5, fill=tk.X, ipady=3)
        
        # Reset button
        self.btn_reset = tk.Button(self.game_frame, text="대국 리셋 (재시작)", font=("Malgun Gothic", 10, "bold"), bg="#ff9800", fg="#ffffff", activebackground="#f57c00", activeforeground="#ffffff", borderwidth=0, relief=tk.FLAT, command=self.reset_game)
        self.btn_reset.pack(pady=5, fill=tk.X, ipady=3)
        
        # Exit button
        btn_exit = tk.Button(self.frame_right, text="대국 종료", font=("Malgun Gothic", 10, "bold"), bg="#f44336", fg="#ffffff", activebackground="#d32f2f", activeforeground="#ffffff", borderwidth=0, relief=tk.FLAT, command=self.root.quit)
        btn_exit.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=20, ipady=3)

    def draw_board(self):
        self.canvas.delete("all")
        
        # Board boundary line
        self.canvas.create_rectangle(self.margin, self.margin, 
                                     self.margin + 18 * self.cell_size, 
                                     self.margin + 18 * self.cell_size, 
                                     outline="#2b2b2b", width=2)
        
        # Grid lines (19x19)
        for i in range(1, 18):
            pos = self.margin + i * self.cell_size
            # Horizontal lines
            self.canvas.create_line(self.margin, pos, self.margin + 18 * self.cell_size, pos, fill="#2b2b2b", width=1)
            # Vertical lines
            self.canvas.create_line(pos, self.margin, pos, self.margin + 18 * self.cell_size, fill="#2b2b2b", width=1)
            
        # Draw Star points (Hoshi)
        for r, c in self.star_points:
            cx = self.margin + c * self.cell_size
            cy = self.margin + r * self.cell_size
            self.canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="#2b2b2b", outline="")

        # Draw coordinate labels (X: 1-19, Y: 1-19)
        label_font = ("Segoe UI", 9, "bold")
        label_color = "#1a1a1a" # Dark high-contrast color for maximum visibility
        
        for i in range(self.board_size):
            cx = self.margin + i * self.cell_size
            cy = self.margin + i * self.cell_size
            
            # X-axis label (1 to 19 from left to right)
            x_val = i + 1
            # Top label
            self.canvas.create_text(cx, self.margin - 18, text=str(x_val), font=label_font, fill=label_color)
            # Bottom label
            self.canvas.create_text(cx, self.margin + 18 * self.cell_size + 18, text=str(x_val), font=label_font, fill=label_color)
            
            # Y-axis label (1 to 19 from bottom to top)
            y_val = self.board_size - i
            # Left label
            self.canvas.create_text(self.margin - 18, cy, text=str(y_val), font=label_font, fill=label_color)
            # Right label
            self.canvas.create_text(self.margin + 18 * self.cell_size + 18, cy, text=str(y_val), font=label_font, fill=label_color)

        # Draw actual game entities
        if self.game_started and self.env is not None:
            board = self.env.gameboard
            for r in range(self.board_size):
                for c in range(self.board_size):
                    cell = board[r, c]
                    self.draw_entity(r, c, cell)
        else:
            # Drawing obstacles placed during setup mode
            for r, c in self.obstacles_coords:
                self.draw_entity(r, c, 2)
            # Draw center point as empty (normally Black places here first when game starts)
            # Center coordinates: row 9, col 9 (10,10 in X,Y coords)
            if self.game_started is False:
                # Preview center indicator
                cx, cy = self.grid_to_canvas(9, 9)
                self.canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill="#000000", outline="")

        # Highlight last move if present
        if self.game_started and self.action_index is not None:
            r = self.action_index // self.board_size
            c = self.action_index % self.board_size
            cx, cy = self.grid_to_canvas(r, c)
            # Small yellow ring on center of the last stone
            self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, outline="#ffeb3b", width=2)
            
        # Draw Hover guide
        if self.hover_pos is not None and not self.ai_thinking and not self.game_over:
            hr, hc = self.hover_pos
            # Check occupied status
            occupied = False
            if self.game_started:
                occupied = (self.env.gameboard[hr, hc] != 0)
            else:
                occupied = ((hr, hc) in self.obstacles_coords)
                
            if not occupied:
                cx, cy = self.grid_to_canvas(hr, hc)
                if self.game_started:
                    # Show preview of player stone color
                    preview_color = "#ffffff" if self.player_color == 1 else "#000000"
                    self.canvas.create_oval(cx - self.stone_radius, cy - self.stone_radius, 
                                             cx + self.stone_radius, cy + self.stone_radius, 
                                             outline=preview_color, dash=(4, 4), width=2)
                else:
                    # Obstacle setup hover preview
                    if (hr, hc) != (9, 9):  # Cannot place obstacle on center (10,10)
                        self.canvas.create_rectangle(cx - self.stone_radius + 2, cy - self.stone_radius + 2, 
                                                     cx + self.stone_radius - 2, cy + self.stone_radius - 2, 
                                                     outline="#f44336", dash=(4, 4), width=2)

    def draw_entity(self, r, c, val):
        cx, cy = self.grid_to_canvas(r, c)
        rad = self.stone_radius
        
        if val == 1: # Black stone (Rendered with 3D gradient look)
            # Main black body
            self.canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, fill="#1e1e22", outline="#0a0a0f", width=1)
            # Light reflection (offset small white-gray oval)
            self.canvas.create_oval(cx - rad + 3, cy - rad + 3, cx - rad + 9, cy - rad + 9, fill="#5a5a66", outline="", width=0)
            
        elif val == -1: # White stone (Rendered with 3D gradient look and soft drop shadow)
            # Soft shadow
            self.canvas.create_oval(cx - rad + 1, cy - rad + 1, cx + rad + 1, cy + rad + 1, fill="#8f8f9e", outline="", width=0)
            # Main white body
            self.canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, fill="#ffffff", outline="#dcdce6", width=1)
            # Light reflection (offset bright highlight)
            self.canvas.create_oval(cx - rad + 3, cy - rad + 3, cx - rad + 9, cy - rad + 9, fill="#f2f2f8", outline="", width=0)
            
        elif val == 2: # Red Obstacle Stone
            # Red square warning block
            self.canvas.create_rectangle(cx - rad + 2, cy - rad + 2, cx + rad - 2, cy + rad - 2, fill="#ff4d4d", outline="#b32d2d", width=2)
            # White cross inside
            self.canvas.create_line(cx - rad + 6, cy - rad + 6, cx + rad - 6, cy + rad - 6, fill="#ffffff", width=2)
            self.canvas.create_line(cx - rad + 6, cy + rad - 6, cx + rad - 6, cy - rad + 6, fill="#ffffff", width=2)

    def canvas_to_grid(self, x, y):
        c = round((x - self.margin) / self.cell_size)
        r = round((y - self.margin) / self.cell_size)
        return r, c

    def grid_to_canvas(self, r, c):
        cx = self.margin + c * self.cell_size
        cy = self.margin + r * self.cell_size
        return cx, cy

    def generate_random_obstacles(self):
        if self.game_started:
            return
            
        # Select 3 random intersections, excluding center (9, 9)
        self.obstacles_coords = []
        while len(self.obstacles_coords) < 3:
            rx = np.random.randint(1, 20)
            ry = np.random.randint(1, 20)
            row, col = game.coord_to_matrix(rx, ry)
            if (row, col) != (9, 9) and (row, col) not in self.obstacles_coords:
                self.obstacles_coords.append((row, col))
                
        self.obstacles = [game.coord_to_action(game.matrix_to_coord(r, c)[0], game.matrix_to_coord(r, c)[1]) for r, c in self.obstacles_coords]
        self.update_obstacle_status()
        self.draw_board()

    def update_obstacle_status(self):
        count = len(self.obstacles_coords)
        self.lbl_obs_status.configure(text=f"설정된 장애물 수: {count} / 3")
        
        if count == 3:
            self.btn_start.configure(state=tk.NORMAL, bg="#4caf50", fg="#ffffff", activebackground="#45a049")
            self.lbl_instruct.configure(text="[단계 2: 색상 및 수읽기 설정]\n옵션을 구성하고 '대국 시작하기' 버튼을\n클릭하여 게임을 시작하십시오.", fg="#4caf50")
        else:
            self.btn_start.configure(state=tk.DISABLED, bg="#2c2c30", fg="#5a5a60", activebackground="#2c2c30")
            self.lbl_instruct.configure(text="[단계 1: 장애물 배치]\n바둑판 위를 클릭하여 빨간색 장애물 돌\n3개를 배치해주세요 (중앙 10,10 제외).", fg="#ff9800")

    def start_game(self):
        if len(self.obstacles_coords) != 3:
            messagebox.showerror("장애물 부족", "반드시 3개의 장애물 돌이 지정되어야 대국을 시작할 수 있습니다.")
            return
            
        try:
            sims = int(self.ent_sim.get().strip())
            if sims < 10 or sims > 10000:
                raise ValueError()
            self.mcts_simulations = sims
        except ValueError:
            messagebox.showerror("수치 오류", "시뮬레이션 횟수는 10~10000 범위의 양의 정수여야 합니다. (기본값 2000 사용)")
            self.ent_sim.delete(0, tk.END)
            self.ent_sim.insert(0, "2000")
            self.mcts_simulations = 2000
            
        self.player_color = self.color_var.get()
        
        # Get obstacles in action index format
        obstacles_actions = []
        for r, c in self.obstacles_coords:
            x, y = game.matrix_to_coord(r, c)
            obstacles_actions.append(game.coord_to_action(x, y))
        self.obstacles = obstacles_actions
        
        # Initialize env
        obstacles_xy_list = []
        for r, c in self.obstacles_coords:
            x, y = game.matrix_to_coord(r, c)
            obstacles_xy_list.append((x, y))
        self.env = game.GameState(obstacles=obstacles_xy_list)
        
        # Agent MCTS setup
        if utils._cpp_lib is not None:
            self.ai_agent = agents.CppHeuristicMCTS(board_size=19, num_mcts=self.mcts_simulations, obstacles=self.obstacles)
        else:
            self.ai_agent = agents.HeuristicMCTS(board_size=19, num_mcts=min(self.mcts_simulations, 800), obstacles=self.obstacles)
            
        # Black center placement rule is automatically initialized in GameState
        # Root node ID starts with (0, 180) (Black placed at 10, 10, index 180)
        self.root_id = (0, 180)
        self.action_index = 180
        self.history = []
        self.game_started = True
        self.game_over = False
        self.ai_thinking = False
        
        # Transition Sidebar View
        self.setup_frame.pack_forget()
        self.game_frame.pack(fill=tk.BOTH, expand=True, padx=15)
        
        # Push initial state to history for undoing White's first move
        self.push_history()
        
        self.draw_board()
        self.update_game_panel()
        
        # If player is White, AI is Black and has already made the first move.
        # So turn is 1 (White's turn), which means it is Player's turn.
        # If player is Black, Black has automatic move at center. Turn is 1 (White's turn),
        # which means it is AI's (White) turn to make move.
        if self.player_color == 0: # Player is Black
            self.trigger_ai_turn()

    def update_game_panel(self):
        if not self.game_started:
            return
            
        turn_str = ""
        turn_color = "#ffffff"
        if self.game_over:
            turn_str = "대국 종료"
            turn_color = "#f44336"
        elif self.ai_thinking:
            turn_str = "AI 수읽기 중..."
            turn_color = "#ff9800"
        elif self.env.turn == self.player_color:
            turn_str = "당신의 차례 (착수 가"
            turn_str += " 흑돌)" if self.player_color == 0 else " 백돌)"
            turn_color = "#4caf50"
        else:
            turn_str = "AI 차례"
            turn_color = "#ff9800"
            
        self.lbl_game_turn.configure(text=f"상태: {turn_str}", fg=turn_color)
        self.lbl_game_stones.configure(text=f"놓인 돌 수: {self.env.num_stones}")
        
        if self.action_index is not None:
            ax, ay = game.action_to_coord(self.action_index)
            color_lbl = "흑돌" if self.env.gameboard[self.action_index // 19, self.action_index % 19] == 1 else "백돌"
            if self.action_index == 180 and self.env.num_stones == 1:
                color_lbl = "흑돌 (자동)"
            self.lbl_last_move.configure(text=f"마지막 착수: {color_lbl} {ax},{ay}")
        else:
            self.lbl_last_move.configure(text="마지막 착수: 없음")

    def push_history(self):
        # Deepcopy the board state and history metadata
        hist_tuple = (
            self.root_id,
            np.copy(self.env.gameboard),
            self.env.turn,
            self.env.num_stones,
            self.action_index
        )
        self.history.append(hist_tuple)

    def on_canvas_click(self, event):
        if self.ai_thinking or self.game_over:
            return
            
        r, c = self.canvas_to_grid(event.x, event.y)
        if not (0 <= r < self.board_size and 0 <= c < self.board_size):
            return
            
        if not self.game_started:
            # 1. Setup Mode: obstacle placement
            if (r, c) == (9, 9):
                messagebox.showwarning("좌표 불가", "중앙점(10,10)은 첫 돌의 위치이므로 장애물을 놓을 수 없습니다.")
                return
                
            if (r, c) in self.obstacles_coords:
                self.obstacles_coords.remove((r, c))
            else:
                if len(self.obstacles_coords) >= 3:
                    messagebox.showwarning("초과 지정", "장애물은 최대 3개까지 배치할 수 있습니다.")
                    return
                self.obstacles_coords.append((r, c))
                
            # Keep action indices updated
            self.obstacles = [game.coord_to_action(game.matrix_to_coord(obs[0], obs[1])[0], game.matrix_to_coord(obs[0], obs[1])[1]) for obs in self.obstacles_coords]
            self.update_obstacle_status()
            self.draw_board()
            
        else:
            # 2. Gameplay Mode: player placement
            if self.env.turn != self.player_color:
                return # Not player's turn
                
            # Verify coordinates are unoccupied
            if self.env.gameboard[r, c] != 0:
                return
                
            act_idx = r * self.board_size + c
            player_val = 1 if self.player_color == 0 else -1
            
            # Check 3-3 restriction rule
            if utils.check_double_three(self.env.gameboard, act_idx, player_val):
                self.lbl_warning.configure(text="경고: 쌍삼(3-3)은 착수 금지입니다!")
                self.root.after(3000, lambda: self.lbl_warning.configure(text=""))
                return
                
            # Player Move placement
            self.lbl_warning.configure(text="")
            self.action_index = act_idx
            
            # Save history before changing board state
            self.push_history()
            
            # Apply move
            _, _, win_index, turn, _ = self.env.step(self.action_index)
            self.root_id += (self.action_index,)
            
            self.draw_board()
            self.check_game_over(win_index)
            self.update_game_panel()
            
            if not self.game_over:
                self.trigger_ai_turn()

    def on_canvas_motion(self, event):
        r, c = self.canvas_to_grid(event.x, event.y)
        if 0 <= r < self.board_size and 0 <= c < self.board_size:
            if self.hover_pos != (r, c):
                self.hover_pos = (r, c)
                self.draw_board()
        else:
            if self.hover_pos is not None:
                self.hover_pos = None
                self.draw_board()

    def on_canvas_leave(self, event):
        if self.hover_pos is not None:
            self.hover_pos = None
            self.draw_board()

    def trigger_ai_turn(self):
        self.ai_thinking = True
        self.update_game_panel()
        self.draw_board()
        
        self.ai_completed = False
        self.ai_action = None
        
        # Start background thread for MCTS logic to prevent GUI blocking
        ai_thread = threading.Thread(target=self.run_mcts_in_background)
        ai_thread.daemon = True
        ai_thread.start()
        
        # Periodically check progress of the MCTS thread
        self.root.after(50, self.check_ai_status)

    def run_mcts_in_background(self):
        try:
            # We fetch state properties to safely run search without race conditions
            board_copy = np.copy(self.env.gameboard)
            turn = self.env.turn
            root_id_copy = self.root_id
            
            # Run C++ MCTS
            pi = self.ai_agent.get_pi(root_id_copy, board_copy, turn, tau=0)
            self.ai_action = int(np.argmax(pi))
        except Exception as e:
            print("[에러] AI 백그라운드 탐색 실패:", e)
            self.ai_action = -1
        self.ai_completed = True

    def check_ai_status(self):
        if self.ai_completed:
            self.ai_thinking = False
            
            if self.ai_action != -1:
                # Apply move
                self.action_index = self.ai_action
                self.push_history()
                
                _, _, win_index, turn, _ = self.env.step(self.action_index)
                self.root_id += (self.action_index,)
                
                # Dynamic tree garbage collection
                self.ai_agent.del_parents(self.root_id)
                
                self.draw_board()
                self.check_game_over(win_index)
            else:
                messagebox.showerror("AI 에러", "AI가 유효한 착수를 결정하지 못했습니다. 강제로 임의의 수로 진행합니다.")
                # Fallback random move
                legal = [a for a in range(361) if self.env.gameboard[a // 19, a % 19] == 0]
                if legal:
                    self.action_index = np.random.choice(legal)
                    self.push_history()
                    _, _, win_index, turn, _ = self.env.step(self.action_index)
                    self.root_id += (self.action_index,)
                    self.draw_board()
                    self.check_game_over(win_index)
            
            self.update_game_panel()
        else:
            # Check status again
            self.root.after(50, self.check_ai_status)

    def check_game_over(self, win_index):
        if win_index == 1:
            self.game_over = True
            messagebox.showinfo("대국 결과", "게임 종료!\n결과: 흑돌(선수) 승리! 🎉")
        elif win_index == 2:
            self.game_over = True
            messagebox.showinfo("대국 결과", "게임 종료!\n결과: 백돌(후수) 승리! 🎉")
        elif win_index == 3:
            self.game_over = True
            messagebox.showinfo("대국 결과", "게임 종료!\n결과: 무승부! 🤝")

    def undo_move(self):
        if not self.game_started or self.ai_thinking:
            return
            
        # We need to pop 2 moves: AI's move and the Player's move
        # But if the game has ended, we allow undo.
        # If the player is White, the very first turn is a Player turn. In this case,
        # root_id is (0, 180) at start. After player makes White placement, root_id is (0, 180, P1).
        # In this case, undoing once pops P1 and returns the board back to the initial state.
        # If player is Black, player selected Black. Black starts with center automated move (0, 180).
        # AI then plays P1 (White) automatically. Then player plays P2 (Black).
        # Root id is: (0, 180, P1, P2). In this case, we pop P2 (player) and P1 (AI), returning
        # the board to state (0, 180) where it's AI's turn (White).
        
        # Check undo eligibility based on history entries count
        if len(self.history) < 2:
            messagebox.showwarning("무르기 실패", "무를 수 있는 기보 이력이 존재하지 않습니다.")
            return
            
        # Pop last state (which is the state right before the current turn)
        self.history.pop() # current state
        prev_state = self.history.pop() # state before player's last move
        
        self.root_id = prev_state[0]
        self.env.gameboard = prev_state[1]
        self.env.turn = prev_state[2]
        self.env.num_stones = prev_state[3]
        self.action_index = prev_state[4]
        
        # Clear AI agent internal tree states
        self.ai_agent.reset()
        self.game_over = False
        
        # Re-push current state to history
        self.push_history()
        
        self.draw_board()
        self.update_game_panel()
        
        # If it was Black player's turn, AI was White. By undoing P2 and P1, we return to the state where
        # AI (White) is about to play. We must automatically trigger the AI turn again!
        if self.player_color == 0 and self.env.turn != self.player_color:
            self.trigger_ai_turn()

    def reset_game(self):
        if messagebox.askyesno("대국 재시작", "정말로 현재 대국을 중단하고 설정 화면으로 리셋하시겠습니까?"):
            self.game_started = False
            self.game_over = False
            self.ai_thinking = False
            
            # Show Setup Panel, Hide Game Panel
            self.game_frame.pack_forget()
            self.setup_frame.pack(fill=tk.BOTH, expand=True, padx=15)
            
            self.obstacles = []
            self.obstacles_coords = []
            self.action_index = 180
            self.update_obstacle_status()
            
            self.draw_board()

def main():
    root = tk.Tk()
    app = OmokGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
