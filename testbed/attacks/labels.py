"""Label flip attack generator (random and targeted)."""

import numpy as np


def flip_labels(
    y: np.ndarray,
    pool: np.ndarray,
    rate: float,
    rng: np.random.Generator,
    mode: str = "random",
    src: int | None = None,
    dst: int | None = None,
    n_classes: int = 10,
) -> tuple[np.ndarray, np.ndarray]:
    """Flip labels in pool according to rate and mode ("random" or "targeted").

    Returns (new_y, flipped_indices).
    """
    new_y = y.copy()

    if mode == "random":
        n_target = round(rate * len(pool))
        if n_target == 0:
            return new_y, np.array([], dtype=np.int64)

        flipped_indices = rng.choice(pool, size=min(n_target, len(pool)), replace=False)
        for idx in flipped_indices:
            orig_c = y[idx]
            possible = [c for c in range(n_classes) if c != orig_c]
            new_y[idx] = rng.choice(possible)

        return new_y, flipped_indices

    elif mode == "targeted":
        if src is None or dst is None:
            raise ValueError("src and dst must be specified for targeted label flip")

        candidates = pool[y[pool] == src]
        n_target = round(rate * len(candidates))
        if n_target == 0:
            return new_y, np.array([], dtype=np.int64)

        flipped_indices = rng.choice(candidates, size=min(n_target, len(candidates)), replace=False)
        new_y[flipped_indices] = dst
        return new_y, flipped_indices

    else:
        raise ValueError(f"Unknown label flip mode '{mode}'")
