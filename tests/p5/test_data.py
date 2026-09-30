import hashlib
import numpy as np
import pytest
from testbed.data import fake_images, load_cifar10, load_ood, get_splits


def test_fake_images_shape_and_range():
    X, y = fake_images(n=50, seed=42, n_classes=10, size=32)

    assert X.shape == (50, 32, 32, 3)
    assert X.dtype == np.uint8
    assert y.shape == (50,)
    assert y.dtype == np.int64
    assert np.all(y >= 0) and np.all(y < 10)


def test_determinism():
    X1, y1 = fake_images(n=20, seed=123)
    X2, y2 = fake_images(n=20, seed=123)

    np.testing.assert_array_equal(X1, X2)
    np.testing.assert_array_equal(y1, y2)


def test_load_cifar10_fake():
    X, y = load_cifar10(split="train", n=100, seed=7, fake=True)
    assert len(X) == 100
    assert X.dtype == np.uint8


def test_load_ood_fake():
    X_svhn = load_ood(kind="svhn", n=30, seed=1, fake=True)
    X_c100 = load_ood(kind="cifar100", n=30, seed=1, fake=True)
    X_noise = load_ood(kind="noise", n=30, seed=1, fake=True)

    assert X_svhn.shape == (30, 32, 32, 3)
    assert X_c100.shape == (30, 32, 32, 3)
    assert X_noise.shape == (30, 32, 32, 3)


def test_disjoint_splits():
    splits = get_splits(
        seed=0, n_ref=100, n_cal=100, n_scen=150, n_tl=100, fake=True
    )

    X_ref, y_ref = splits["ref"]
    X_cal, y_cal = splits["cal"]
    X_scen, y_scen = splits["scen"]
    X_tl, y_tl = splits["timeline"]

    assert len(X_ref) == 100
    assert len(X_cal) == 100
    assert len(X_scen) == 150
    assert len(X_tl) == 100

    def img_hashes(X_arr):
        return {hashlib.sha256(img.tobytes()).hexdigest() for img in X_arr}

    ref_hashes = img_hashes(X_ref)
    cal_hashes = img_hashes(X_cal)
    scen_hashes = img_hashes(X_scen)

    # Train splits ref, cal, scen must be pairwise disjoint
    assert len(ref_hashes.intersection(cal_hashes)) == 0
    assert len(ref_hashes.intersection(scen_hashes)) == 0
    assert len(cal_hashes.intersection(scen_hashes)) == 0
