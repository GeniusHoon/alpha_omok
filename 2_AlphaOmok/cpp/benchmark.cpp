#include <iostream>
#include <chrono>
#include <vector>
#include <random>

// Import MCTS search and helper functions from omok_cpp.cpp
extern "C" int check_win_cpp(const int* board);
extern "C" int mcts_search_cpp(const int* start_board, int start_turn, int num_mcts, double c_puct, double defense_weight, double tau);

int main() {
    std::cout << "====================================================" << std::endl;
    std::cout << " 오목 C++ 엔진 극한조건 시뮬레이션 및 벤치마크" << std::endl;
    std::cout << "====================================================" << std::endl;
    
    // 1. Initialize board
    std::vector<int> board(19 * 19, 0);
    
    // Place Black's first center stone at (10, 10) -> action index 180
    board[180] = 1; 
    
    // Place 3 arbitrary red obstacle stones (2)
    board[3 * 19 + 5] = 2;   // (6, 4) in X,Y coords
    board[12 * 19 + 17] = 2; // (18, 13) in X,Y coords
    board[15 * 19 + 9] = 2;  // (10, 16) in X,Y coords
    
    // MCTS parameters
    const int NUM_SIMULATIONS = 5000; // 극한 수읽기 조건: 5000회 시뮬레이션
    const int RUNS = 5;
    const double C_PUCT = 5.0;
    const double DEFENSE_WEIGHT = 1.2;
    const double TAU = 2.0;
    
    std::cout << "시뮬레이션 설정:" << std::endl;
    std::cout << " - 바둑판 크기: 19 x 19" << std::endl;
    std::cout << " - 장애물 위치: (6,4), (18,13), (10,16)" << std::endl;
    std::cout << " - 턴: 백돌 (후수) AI 차례" << std::endl;
    std::cout << " - 횟수당 MCTS 탐색 수: " << NUM_SIMULATIONS << " 회" << std::endl;
    std::cout << " - 총 벤치마크 횟수: " << RUNS << " 회" << std::endl;
    std::cout << "----------------------------------------------------" << std::endl;

    double total_sps = 0.0;
    
    for (int r = 1; r <= RUNS; ++r) {
        std::cout << "실행 #" << r << " 시작..." << std::flush;
        
        auto start = std::chrono::high_resolution_clock::now();
        
        // Run C++ MCTS search (White turn = 1)
        int best_action = mcts_search_cpp(board.data(), 1, NUM_SIMULATIONS, C_PUCT, DEFENSE_WEIGHT, TAU);
        
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double, std::milli> duration = end - start;
        
        double seconds = duration.count() / 1000.0;
        double sps = NUM_SIMULATIONS / seconds;
        total_sps += sps;
        
        // Convert action to coordinates
        int ax = (best_action % 19) + 1;
        int ay = 19 - (best_action / 19);
        
        std::cout << " 완료!" << std::endl;
        std::cout << "   - 소요 시간: " << duration.count() << " ms (" << seconds << " 초)" << std::endl;
        std::cout << "   - 계산 속도: " << sps << " Simulations/sec (SPS)" << std::endl;
        std::cout << "   - 선택 좌표: " << ax << "," << ay << " (인덱스: " << best_action << ")" << std::endl;
        std::cout << "----------------------------------------------------" << std::endl;
    }
    
    std::cout << "최종 결과 요약:" << std::endl;
    std::cout << " - 평균 수읽기 속도: " << (total_sps / RUNS) << " SPS" << std::endl;
    std::cout << "====================================================" << std::endl;
    
    return 0;
}
