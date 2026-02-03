from board_rules import simulate_move, valid_moves
'''manual test harness (you could move those few lines into board_rules.py under a if __name__ == "__main__": block instead).'''

if __name__ == "__main__":
    sample = [
        [2, 0, 0, 2],
        [4, 4, 0, 0],
        [0, 0, 8, 8],
        [16, 0, 16, 0],
    ]
    print("Valid moves:", valid_moves(sample))