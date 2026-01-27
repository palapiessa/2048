import json
import glob
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.buffers import RolloutBuffer
from stable_baselines3.common.utils import get_device

# 1. Load Logs
all_moves = []

# Find ALL .json files in the 'training_data' folder
log_files = glob.glob("training_data/*.json")
print(f"Found {len(log_files)} log files...")

for filepath in log_files:
    try:
        with open(filepath, "r") as f:
            logs = json.load(f)
            # Filter valid moves from this specific file
            valid_moves = [e for e in logs if e.get("type") == "move" and e.get("valid")]
            all_moves.extend(valid_moves)
            print(f"  - Loaded {len(valid_moves)} moves from {filepath}")
    except Exception as e:
        print(f"  - Error reading {filepath}: {e}")

print(f"Total dataset size: {len(all_moves)} moves.")

# ... (continue with preprocessing using 'all_moves')
# Use the accumulated moves from all files
game_moves = all_moves

print(f"Loaded {len(game_moves)} valid moves for training.")

# 2. Preprocess Data 
# Convert 2048 grid to normalized numpy array (log base 2 helps normalization)
def preprocess_board(grid):
    board = np.array(grid)
    board[board == 0] = 1 # Avoid log2(0)
    return np.log2(board).flatten() / 16.0  # Normalize 0..1 range approx

states = []
actions = []
rewards = []

direction_map = {"UP": 0, "RIGHT": 1, "DOWN": 2, "LEFT": 3}

for move in game_moves:
    # State
    current_state = preprocess_board(move["prev"]["grid"])
    states.append(current_state)
    
    # Action (Discrete 0-3)
    actions.append(direction_map[move["direction"]])
    
    # Reward (Change in score)
    reward = move["next"]["score"] - move["prev"]["score"]
    rewards.append(reward)

# Convert to consistent numpy arrays
states = np.array(states, dtype=np.float32)
actions = np.array(actions, dtype=np.int64) 

# 3. Create a Dummy Agent & Inject Data
# Note: Real offline RL usually requires algorithms like CQL or BC. 
# For simplicity, we can use Supervised Learning on this data 
# OR use PPO to "pre-train" on this buffer if we had a proper Gym environment.

from sklearn.ensemble import RandomForestClassifier

# A simple "Imitation Bot" using Random Forest (easier than setting up full PPO for offline now)
clf = RandomForestClassifier(n_estimators=100)
clf.fit(states, actions)

print("Training complete!")

# 4. Save the "Brain"
import pickle
with open("random_forest_2048.pkl", "wb") as f:
    pickle.dump(clf, f)
    
print("Saved model to random_forest_2048.pkl")
