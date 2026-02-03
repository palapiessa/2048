"""Core 2048 board mechanics shared by the model server and tests."""

from typing import Iterable, List, Sequence, Tuple

import numpy as np

DIRECTION_NAMES: Sequence[str] = ("UP", "RIGHT", "DOWN", "LEFT")


def _compress(line: Iterable[int]) -> List[int]:
    filtered = [v for v in line if v != 0]
    return filtered + [0] * (4 - len(filtered))


def _merge(line: List[int]) -> List[int]:
    merged: List[int] = []
    skip = False
    for idx, value in enumerate(line):
        if skip:
            skip = False
            continue
        if idx + 1 < len(line) and line[idx + 1] == value:
            merged.append(value * 2)
            skip = True
        else:
            merged.append(value)
    return merged + [0] * (4 - len(merged))


def _apply_left(board: np.ndarray) -> Tuple[np.ndarray, bool]:
    rows = []
    changed_any = False
    for row in board:
        new_row = np.array(_merge(_compress(row.tolist())), dtype=int)
        rows.append(new_row)
        if not np.array_equal(new_row, row):
            changed_any = True
    return np.array(rows, dtype=int), changed_any


def simulate_move(grid: Sequence[Sequence[int]], direction: str) -> Tuple[np.ndarray, bool]:
    arr = np.array(grid, dtype=int)
    original = arr.copy()

    if direction == "LEFT":
        next_board, changed = _apply_left(arr)
    elif direction == "RIGHT":
        flipped = np.fliplr(arr)
        moved, changed = _apply_left(flipped)
        next_board = np.fliplr(moved)
    elif direction == "UP":
        transposed = arr.T
        moved, changed = _apply_left(transposed)
        next_board = moved.T
    elif direction == "DOWN":
        transposed = arr.T
        flipped = np.fliplr(transposed)
        moved, changed = _apply_left(flipped)
        next_board = np.fliplr(moved).T
    else:
        raise ValueError(f"Unknown direction: {direction}")

    if not changed:
        changed = not np.array_equal(next_board, original)

    return next_board, changed


def valid_moves(grid: Sequence[Sequence[int]]) -> List[str]:
    allowed: List[str] = []
    for direction in DIRECTION_NAMES:
        _, changed = simulate_move(grid, direction)
        if changed:
            allowed.append(direction)
    return allowed


__all__ = ["DIRECTION_NAMES", "simulate_move", "valid_moves"]
