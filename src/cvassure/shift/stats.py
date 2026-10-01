import numpy as np


def compute_mmd(X: np.ndarray, Y: np.ndarray, gamma: float = 1.0) -> float:
    """Maximum Mean Discrepancy between X and Y using an RBF kernel."""
    if len(X) == 0 or len(Y) == 0:
        return 0.0

    def rbf_kernel(A, B, gamma):
        A_norm = np.sum(A**2, axis=1, keepdims=True)
        B_norm = np.sum(B**2, axis=1, keepdims=True)
        K = np.exp(-gamma * (A_norm + B_norm.T - 2 * np.dot(A, B.T)))
        return K

    XX = rbf_kernel(X, X, gamma)
    YY = rbf_kernel(Y, Y, gamma)
    XY = rbf_kernel(X, Y, gamma)

    return float(np.mean(XX) + np.mean(YY) - 2 * np.mean(XY))


def compute_ks(X: np.ndarray, Y: np.ndarray) -> float:
    """Kolmogorov-Smirnov test statistic (max CDF difference) for 1D arrays.
    For multi-dimensional arrays, computes the mean of the KS statistic across all features.
    """
    if len(X) == 0 or len(Y) == 0:
        return 0.0

    if X.ndim > 1:
        ks_stats = []
        for i in range(X.shape[1]):
            ks_stats.append(compute_ks(X[:, i], Y[:, i]))
        return float(np.mean(ks_stats))

    X_sorted = np.sort(X)
    Y_sorted = np.sort(Y)

    data_all = np.concatenate([X_sorted, Y_sorted])

    cdf_X = np.searchsorted(X_sorted, data_all, side="right") / len(X_sorted)
    cdf_Y = np.searchsorted(Y_sorted, data_all, side="right") / len(Y_sorted)

    return float(np.max(np.abs(cdf_X - cdf_Y)))


def compute_psi(X: np.ndarray, Y: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index (PSI) between X and Y.
    For multi-dimensional arrays, computes the mean PSI across all features.
    """
    if len(X) == 0 or len(Y) == 0:
        return 0.0

    if X.ndim > 1:
        psi_stats = []
        for i in range(X.shape[1]):
            psi_stats.append(compute_psi(X[:, i], Y[:, i], bins=bins))
        return float(np.mean(psi_stats))

    min_val = min(np.min(X), np.min(Y))
    max_val = max(np.max(X), np.max(Y))

    breaks = np.linspace(min_val, max_val, bins + 1)

    hist_X, _ = np.histogram(X, bins=breaks)
    hist_Y, _ = np.histogram(Y, bins=breaks)

    pct_X = hist_X / len(X)
    pct_Y = hist_Y / len(Y)

    # Replace zeros with small epsilon to avoid div/0 or log(0)
    eps = 1e-4
    pct_X = np.where(pct_X == 0, eps, pct_X)
    pct_Y = np.where(pct_Y == 0, eps, pct_Y)

    psi = np.sum((pct_Y - pct_X) * np.log(pct_Y / pct_X))
    return float(psi)


def conformal_calibrate(scores: np.ndarray, cal_scores: np.ndarray) -> np.ndarray:
    """Calibrate scores using conformal prediction (compute p-values)."""
    if len(cal_scores) == 0:
        return np.zeros_like(scores)

    cal_sorted = np.sort(cal_scores)
    p_values = np.zeros_like(scores, dtype=float)

    for i, score in enumerate(scores):
        # Fraction of calibration scores >= test score
        p_values[i] = np.sum(cal_sorted >= score) / len(cal_sorted)

    return p_values
