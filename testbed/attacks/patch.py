"""Patch attack generator for dirty-label and clean-label poisoning."""

import numpy as np


def add_patch(
    img: np.ndarray, size: int = 4, pos: str = "br", value: int = 255
) -> np.ndarray:
    """Add a size x size square patch of specified value to img at position pos (br, bl, tr, tl)."""
    patched = img.copy()
    h, w = patched.shape[:2]

    if pos == "br":
        r_start, c_start = h - size, w - size
    elif pos == "bl":
        r_start, c_start = h - size, 0
    elif pos == "tr":
        r_start, c_start = 0, w - size
    elif pos == "tl":
        r_start, c_start = 0, 0
    else:
        raise ValueError(f"Unknown position '{pos}'. Must be one of 'br', 'bl', 'tr', 'tl'.")

    patched[r_start : r_start + size, c_start : c_start + size] = value
    return patched


def poison_patch(
    X: np.ndarray,
    y_given: np.ndarray,
    y_true: np.ndarray,
    pool: np.ndarray,
    target: int,
    rate: float,
    rng: np.random.Generator,
    size: int = 4,
    pos: str = "br",
    clean_label: bool = False,
    value: int = 255,
) -> np.ndarray:
    """Poison a fraction rate of pool samples with a patch trigger.

    Modifies X and y_given in place. Returns indices of poisoned samples.
    - dirty-label (clean_label=False): candidates have y_true != target; y_given set to target.
    - clean-label (clean_label=True): candidates have y_true == target; y_given unchanged.
    """
    n_target = round(rate * len(pool))
    if n_target == 0:
        return np.array([], dtype=np.int64)

    if clean_label:
        candidates = pool[y_true[pool] == target]
    else:
        candidates = pool[y_true[pool] != target]

    if len(candidates) < n_target:
        selected = candidates
    else:
        selected = rng.choice(candidates, size=n_target, replace=False)

    for idx in selected:
        X[idx] = add_patch(X[idx], size=size, pos=pos, value=value)
        if not clean_label:
            y_given[idx] = target

    return selected
