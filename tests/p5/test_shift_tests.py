import numpy as np
import pytest
from shift.tests import (
    sqdist,
    median_bandwidth,
    mmd2_rbf,
    ks_stat,
    psi,
    max_psi,
    mahalanobis,
)


def test_sqdist():
    A = np.array([[0.0, 0.0], [1.0, 1.0]])
    B = np.array([[0.0, 0.0], [2.0, 2.0]])

    dists = sqdist(A, B)
    assert dists.shape == (2, 2)
    assert dists[0, 0] == 0.0
    assert dists[1, 1] == 2.0  # (1-2)^2 + (1-2)^2 = 2


def test_mmd2_same_vs_shifted(rng):
    X = rng.normal(0, 1, size=(200, 10))
    Y_same = rng.normal(0, 1, size=(200, 10))
    Y_shift = rng.normal(1.5, 1, size=(200, 10))

    med = median_bandwidth(X, seed=0)

    mmd_same = mmd2_rbf(X, Y_same, med)
    mmd_shift = mmd2_rbf(X, Y_shift, med)

    assert mmd_same < 0.05
    assert mmd_shift > mmd_same + 0.1


def test_psi_identical_vs_shifted(rng):
    ref = rng.normal(0, 1, size=500)
    new_same = ref.copy()
    new_shift = rng.normal(2.0, 1, size=500)

    psi_same = psi(ref, new_same)
    psi_shift = psi(ref, new_shift)

    assert psi_same < 0.05
    assert psi_shift > 0.5


def test_ks_stat_identical():
    ref = np.random.normal(0, 1, size=(100, 3))
    new = ref.copy()

    stat = ks_stat(ref, new)
    assert stat == 0.0


def test_mahalanobis_mean():
    mean = np.array([1.0, 2.0])
    cov_inv = np.eye(2)
    Z = mean.reshape(1, 2)

    dist = mahalanobis(Z, mean, cov_inv)
    assert dist[0] == 0.0
