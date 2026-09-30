import cv2
import numpy as np
import pytest
from testbed.attacks.patch import add_patch, poison_patch
from testbed.attacks.blend import blend, poison_blend
from testbed.attacks.labels import flip_labels
from testbed.attacks.duplicates import light_edit, heavy_edit, make_duplicates
from testbed.attacks.natural import (
    brightness,
    contrast,
    gaussian_blur,
    gaussian_noise,
    colour_cast,
    fog,
    apply_corruption,
)
from testbed.attacks.records import generate_tampered_records
from testbed.attacks.model_swap import generate_model_swap


def test_poison_patch(rng):
    n = 100
    X = rng.integers(0, 256, size=(n, 32, 32, 3), dtype=np.uint8)
    y_given = rng.integers(0, 10, size=n, dtype=np.int64)
    y_true = y_given.copy()
    pool = np.arange(n)

    target = 0
    rate = 0.1  # expects round(0.1 * 100) = 10 poisoned
    poisoned_idx = poison_patch(
        X, y_given, y_true, pool, target, rate, rng, size=4, pos="br", clean_label=False
    )

    assert len(poisoned_idx) == 10
    assert np.all(y_given[poisoned_idx] == target)
    for idx in poisoned_idx:
        # Check bottom-right 4x4 patch equals 255
        assert np.all(X[idx, -4:, -4:] == 255)


def test_flip_labels(rng):
    n = 100
    y = rng.integers(0, 10, size=n, dtype=np.int64)
    pool = np.arange(n)
    rate = 0.2  # 20 flipped

    new_y, flipped_idx = flip_labels(y, pool, rate, rng, mode="random", n_classes=10)

    assert len(flipped_idx) == 20
    for idx in flipped_idx:
        assert new_y[idx] != y[idx]


from testbed.data import fake_images

def test_duplicate_tier1_and_tier2(rng):
    n = 20
    X, y = fake_images(n=20, seed=42)
    pool = np.arange(n)

    # Tier 1: exact copies
    X_t1, y_t1, dup_of_t1, seeds_t1 = make_duplicates(
        X, y, pool, n_seed=5, copies=3, tier=1, rng=rng
    )
    assert len(X_t1) == n + 15
    for i, seed_idx in enumerate(dup_of_t1):
        if seed_idx != -1:
            assert np.array_equal(X_t1[i], X[seed_idx])

    # Tier 2: dHash Hamming distance check
    def dhash(img):
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        resized = cv2.resize(blurred, (9, 8), interpolation=cv2.INTER_AREA)
        return (resized[:, 1:] > resized[:, :-1]).flatten()

    X_t2, y_t2, dup_of_t2, seeds_t2 = make_duplicates(
        X, y, pool, n_seed=5, copies=10, tier=2, rng=rng
    )
    dists = []
    for i, seed_idx in enumerate(dup_of_t2):
        if seed_idx != -1:
            h_seed = dhash(X[seed_idx])
            h_dup = dhash(X_t2[i])
            h_dup_unflip = dhash(np.fliplr(X_t2[i]))
            dist = min(int(np.sum(h_seed != h_dup)), int(np.sum(h_seed != h_dup_unflip)))
            dists.append(dist)

    dists = np.array(dists)
    assert np.mean(dists <= 10) >= 0.60 or np.mean(dists) <= 10.0


def test_fog_monotonicity(rng):
    img = rng.integers(50, 150, size=(32, 32, 3), dtype=np.uint8)

    means = []
    stds = []
    strengths = [0.0, 0.2, 0.4, 0.6]

    for s in strengths:
        rng_sub = np.random.default_rng(42)
        fogged = fog(img, strength=s, rng=rng_sub)
        means.append(np.mean(fogged))
        stds.append(np.std(fogged))

    # Mean brightness should increase with fog strength
    for i in range(len(strengths) - 1):
        assert means[i + 1] >= means[i]
        assert stds[i + 1] <= stds[i] + 1e-3  # Contrast (std) lowers


def test_stubs():
    with pytest.raises(NotImplementedError):
        generate_tampered_records()
    with pytest.raises(NotImplementedError):
        generate_model_swap()
