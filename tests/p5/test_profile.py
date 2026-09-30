from pathlib import Path
import numpy as np
import pytest
from testbed.data import fake_images
from testbed.attacks.natural import brightness
from testbed.attacks.patch import add_patch
from shift.profile import (
    FEATURE_NAMES,
    scalar_features,
    build_reference_profile,
    save_profile,
    load_profile,
)


def test_scalar_features_shape_and_names():
    X, _ = fake_images(n=10, seed=42)
    feats = scalar_features(X)

    assert feats.shape == (10, 39)
    assert len(FEATURE_NAMES) == 39
    assert feats.dtype == np.float32


def test_brightness_feature_increase():
    X_clean, _ = fake_images(n=10, seed=1)
    X_bright = np.array([brightness(img, delta=0.3) for img in X_clean])

    f_clean = scalar_features(X_clean)
    f_bright = scalar_features(X_bright)

    # brightness is feature index 0
    assert np.mean(f_bright[:, 0]) > np.mean(f_clean[:, 0])


def test_grid_grad_bottom_right_increase():
    X_clean, _ = fake_images(n=10, seed=5)
    X_patched = np.array([add_patch(img, size=4, pos="br", value=255) for img in X_clean])

    f_clean = scalar_features(X_clean)
    f_patched = scalar_features(X_patched)

    # grid_grad_3_3 is the bottom-right cell gradient feature (last feature index 38)
    assert np.mean(f_patched[:, 38]) > np.mean(f_clean[:, 38])


def test_profile_round_trip(tmp_path: Path):
    X_ref, _ = fake_images(n=50, seed=0)
    profile = build_reference_profile(X_ref, backend="handcrafted", batch_size=20, n_batches=5, seed=0)

    save_file = tmp_path / "profile.joblib"
    save_profile(profile, save_file)
    loaded_profile = load_profile(save_file)

    assert loaded_profile.seed == profile.seed
    assert loaded_profile.batch_size == profile.batch_size
    np.testing.assert_array_equal(loaded_profile.feat_mean, profile.feat_mean)
    np.testing.assert_array_equal(loaded_profile.mean_img, profile.mean_img)
