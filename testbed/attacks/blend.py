"""Blend attack generator."""

import numpy as np


def make_pattern(shape: tuple[int, ...], rng: np.random.Generator) -> np.ndarray:
    """Generate uint8 noise pattern for blending."""
    return rng.integers(0, 256, size=shape, dtype=np.uint8)


def blend(img: np.ndarray, pattern: np.ndarray, alpha: float = 0.1) -> np.ndarray:
    """Blend image with pattern using weight alpha."""
    blended = (1.0 - alpha) * img.astype(np.float32) + alpha * pattern.astype(np.float32)
    return np.clip(blended, 0, 255).astype(np.uint8)


def poison_blend(
    X: np.ndarray,
    y_given: np.ndarray,
    y_true: np.ndarray,
    pool: np.ndarray,
    target: int,
    rate: float,
    rng: np.random.Generator,
    alpha: float = 0.1,
    pattern: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Poison a fraction rate of pool samples with a blend trigger.

    Modifies X and y_given in place. Returns (poisoned_indices, pattern).
    """
    n_target = round(rate * len(pool))
    if n_target == 0:
        return np.array([], dtype=np.int64), pattern if pattern is not None else np.zeros((32, 32, 3), dtype=np.uint8)

    candidates = pool[y_true[pool] != target]
    if len(candidates) < n_target:
        selected = candidates
    else:
        selected = rng.choice(candidates, size=n_target, replace=False)

    if pattern is None:
        pattern = make_pattern(X.shape[1:], rng)

    for idx in selected:
        X[idx] = blend(X[idx], pattern, alpha=alpha)
        y_given[idx] = target

    return selected, pattern
