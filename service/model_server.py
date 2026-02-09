import os
import pickle
from typing import Dict, List, Tuple

import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

from board_rules import DIRECTION_NAMES, simulate_move, valid_moves

NAME_TO_INDEX = {name: idx for idx, name in enumerate(DIRECTION_NAMES)}


def resolve_model_path() -> str:
    env_path = os.environ.get("RF_MODEL_PATH")
    if env_path:
        return os.path.abspath(env_path)

    here = os.path.dirname(__file__)
    candidates = [
        os.path.abspath(os.path.join(here, "..", "random_forest_2048.pkl")),
        os.path.abspath(os.path.join(here, "random_forest_2048.pkl")),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    # Fall back to first candidate so we still raise a helpful error later
    return candidates[0]


MODEL_PATH = resolve_model_path()

app = Flask(__name__)
allowed_origins = os.environ.get("RF_ALLOWED_ORIGINS", "*")
CORS(app, resources={r"/predict": {"origins": allowed_origins}})
_model = None


def load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
        with open(MODEL_PATH, "rb") as fh:
            _model = pickle.load(fh)
    return _model


def preprocess_board(grid: List[List[int]]) -> np.ndarray:
    board = np.array(grid, dtype=np.int64)
    if board.shape != (4, 4):
        raise ValueError(f"Expected 4x4 grid, received shape {board.shape}")
    board[board == 0] = 1
    normalized = np.log2(board) / 16.0
    return normalized.flatten().astype(np.float32)


@app.post("/predict")
def predict():
    payload: Dict = request.get_json(force=True, silent=False) or {}
    grid = payload.get("grid")
    if grid is None:
        return jsonify({"error": "Payload must include 'grid' key"}), 400

    try:
        features = preprocess_board(grid)
    except Exception as exc:  # pragma: no cover - defensive for malformed payloads
        return jsonify({"error": str(exc)}), 400

    model = load_model()
    probabilities = model.predict_proba([features])[0]
    predicted_idx = int(np.argmax(probabilities))
    predicted_move = DIRECTION_NAMES[predicted_idx]

    allowed = valid_moves(grid)
    invalid_prediction = predicted_move not in allowed

    if invalid_prediction and allowed:
        allowed_indices = [NAME_TO_INDEX[name] for name in allowed]
        best_idx = max(allowed_indices, key=lambda i: probabilities[i])
        predicted_idx = int(best_idx)
        predicted_move = DIRECTION_NAMES[predicted_idx]

    response = {
        "move": predicted_move,
        "move_index": predicted_idx,
        "predicted_invalid": invalid_prediction,
        "valid_moves": allowed,
        "probabilities": {
            DIRECTION_NAMES[i]: float(probabilities[i]) for i in range(len(DIRECTION_NAMES))
        },
    }

    if payload.get("include_next_grid", False):
        next_grid, _ = simulate_move(grid, predicted_move)
        response["next_grid"] = next_grid.tolist()

    return jsonify(response)


if __name__ == "__main__":
    # Use 0.0.0.0 so the web app can reach it from another process on the same machine.
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=bool(os.environ.get("FLASK_DEBUG")))
