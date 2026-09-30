"""OOD insertion attack helper."""

import numpy as np


def insert_ood(X_ood: np.ndarray, target: int) -> tuple[np.ndarray, np.ndarray]:
    """Return OOD images copy and y labels set to target class."""
    y_ood = np.full(len(X_ood), target, dtype=np.int64)
    return X_ood.copy(), y_ood
