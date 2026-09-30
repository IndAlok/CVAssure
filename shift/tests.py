"""Statistical test functions: MMD (RBF), KS-test, PSI, Mahalanobis distance, and sqdist matrix."""

import numpy as np
from scipy.stats import ks_2samp


def sqdist(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Compute pairwise squared Euclidean distance matrix between rows of A (M, D) and B (N, D)."""
    A_sq = np.sum(A**2, axis=1, keepdims=True)  # (M, 1)
    B_sq = np.sum(B**2, axis=1, keepdims=True)  # (N, 1)
    dists = A_sq + B_sq.T - 2.0 * np.dot(A, B.T)
    return np.clip(dists, 0.0, None)


def median_bandwidth(Z: np.ndarray, max_n: int = 1000, seed: int = 0) -> float:
    """Compute median squared pairwise distance bandwidth over Z subsample."""
    n = len(Z)
    if n > max_n:
        rng = np.random.default_rng(seed)
        idx = rng.choice(n, size=max_n, replace=False)
        sub = Z[idx]
    else:
        sub = Z

    dists = sqdist(sub, sub)
    med = float(np.median(dists))
    return med if med > 0 else 1.0


def mmd2_rbf(X: np.ndarray, Y: np.ndarray, med: float) -> float:
    """Compute unbiased RBF MMD^2 statistic between X (n, D) and Y (m, D)."""
    n, m = len(X), len(Y)
    if n < 2 or m < 2:
        return 0.0

    gamma = 1.0 / max(med, 1e-8)

    Kxx = np.exp(-gamma * sqdist(X, X))
    Kyy = np.exp(-gamma * sqdist(Y, Y))
    Kxy = np.exp(-gamma * sqdist(X, Y))

    sum_kxx_no_diag = np.sum(Kxx) - np.trace(Kxx)
    sum_kyy_no_diag = np.sum(Kyy) - np.trace(Kyy)

    term_xx = sum_kxx_no_diag / (n * (n - 1))
    term_yy = sum_kyy_no_diag / (m * (m - 1))
    term_xy = 2.0 * np.mean(Kxy)

    return float(term_xx + term_yy - term_xy)


def ks_stat(ref_feats: np.ndarray, new_feats: np.ndarray) -> float:
    """Return maximum Kolmogorov-Smirnov statistic D across feature columns."""
    n_cols = ref_feats.shape[1]
    max_d = 0.0
    for c in range(n_cols):
        res = ks_2samp(ref_feats[:, c], new_feats[:, c])
        stat = float(res.statistic)
        if stat > max_d:
            max_d = stat
    return max_d


def psi(ref: np.ndarray, new: np.ndarray, bins: int = 10, eps: float = 1e-4) -> float:
    """Compute Population Stability Index (PSI) for 1D arrays ref and new."""
    percentiles = np.linspace(0, 100, bins + 1)
    bin_edges = np.percentile(ref, percentiles)
    # Deduplicate edges if constant values
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) < 2:
        return 0.0

    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    ref_counts, _ = np.histogram(ref, bins=bin_edges)
    new_counts, _ = np.histogram(new, bins=bin_edges)

    e = (ref_counts.astype(np.float64) / len(ref)) + eps
    a = (new_counts.astype(np.float64) / len(new)) + eps

    e = e / np.sum(e)
    a = a / np.sum(a)

    psi_val = float(np.sum((a - e) * np.log(a / e)))
    return psi_val


def max_psi(ref_feats: np.ndarray, new_feats: np.ndarray) -> float:
    """Return maximum PSI statistic across feature columns."""
    n_cols = ref_feats.shape[1]
    max_p = 0.0
    for c in range(n_cols):
        p_val = psi(ref_feats[:, c], new_feats[:, c])
        if p_val > max_p:
            max_p = p_val
    return max_p


def mahalanobis(Z: np.ndarray, mean: np.ndarray, cov_inv: np.ndarray) -> np.ndarray:
    """Compute Mahalanobis distances for each vector in Z (N, D) against mean (D,) and cov_inv (D, D)."""
    diff = Z - mean.reshape(1, -1)
    m_sq = np.sum(np.dot(diff, cov_inv) * diff, axis=1)
    return np.sqrt(np.clip(m_sq, 0.0, None)).astype(np.float32)
