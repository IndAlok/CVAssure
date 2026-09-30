"""Data loading, fake-data generator, OOD datasets, and disjoint split generation."""

import os
from pathlib import Path
from typing import Any
import numpy as np
from scipy.ndimage import gaussian_filter


def _is_fake_mode(fake: bool | None) -> bool:
    if fake is not None:
        return fake
    return os.environ.get("CVASSURE_FAKE_DATA", "0") == "1"


def fake_images(
    n: int, seed: int, n_classes: int = 10, size: int = 32
) -> tuple[np.ndarray, np.ndarray]:
    """Generate n synthetic images with class-dependent base colours, low-frequency textures, and noise."""
    rng = np.random.default_rng(seed)
    y = rng.integers(0, n_classes, size=n, dtype=np.int64)

    # Distinct base RGB color palette per class
    palette = rng.integers(40, 215, size=(n_classes, 3), dtype=np.int32)

    X = np.zeros((n, size, size, 3), dtype=np.uint8)

    for i in range(n):
        c = y[i]
        base_color = palette[c].reshape(1, 1, 3).astype(np.float32)

        # Low frequency texture
        low_freq_raw = rng.uniform(-60.0, 60.0, size=(size, size, 3))
        low_freq = np.zeros_like(low_freq_raw)
        for ch in range(3):
            low_freq[:, :, ch] = gaussian_filter(low_freq_raw[:, :, ch], sigma=4.0)

        # Pixel noise
        pixel_noise = rng.uniform(-3.0, 3.0, size=(size, size, 3))

        img = base_color + low_freq + pixel_noise
        X[i] = np.clip(img, 0, 255).astype(np.uint8)

    return X, y


def load_cifar10(
    split: str = "train",
    n: int | None = None,
    seed: int = 0,
    root: str = "data",
    fake: bool | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Load CIFAR-10 dataset (real or fake mode).

    Returns (X, y) where X is uint8 (N, 32, 32, 3) and y is int64 (N,).
    """
    if _is_fake_mode(fake):
        total_n = n if n is not None else (50000 if split == "train" else 10000)
        # Shift seed slightly for train vs test so they differ
        split_seed = seed if split == "train" else seed + 100000
        return fake_images(n=total_n, seed=split_seed)

    try:
        import torch
        import torchvision
        import torchvision.transforms as T
    except ImportError as e:
        raise ImportError(
            "torchvision is required for downloading real CIFAR-10 data. "
            "Install torchvision or run with fake=True / CVASSURE_FAKE_DATA=1."
        ) from e

    ds = torchvision.datasets.CIFAR10(
        root=root, train=(split == "train"), download=True
    )
    X_raw = ds.data  # uint8 (N, 32, 32, 3)
    y_raw = np.array(ds.targets, dtype=np.int64)

    if n is not None and n < len(X_raw):
        rng = np.random.default_rng(seed)
        indices = rng.choice(len(X_raw), size=n, replace=False)
        return X_raw[indices], y_raw[indices]

    return X_raw, y_raw


def load_ood(
    kind: str,
    n: int,
    seed: int,
    root: str = "data",
    fake: bool | None = None,
) -> np.ndarray:
    """Load OOD images of specified kind ("svhn", "cifar100", "noise").

    Returns uint8 array (n, 32, 32, 3).
    """
    rng = np.random.default_rng(seed)

    if kind == "noise":
        return rng.integers(0, 256, size=(n, 32, 32, 3), dtype=np.uint8)

    if _is_fake_mode(fake):
        # Generate distinct fake images for OOD
        ood_seed = seed + (200000 if kind == "svhn" else 300000)
        X_fake, _ = fake_images(n=n, seed=ood_seed, n_classes=20)
        return X_fake

    try:
        import torchvision
    except ImportError as e:
        raise ImportError(
            f"torchvision is required for loading real {kind} data. "
            "Install torchvision or run with fake=True."
        ) from e

    if kind == "svhn":
        ds = torchvision.datasets.SVHN(root=root, split="test", download=True)
        X_raw = np.transpose(ds.data, (0, 2, 3, 1))  # (N, 32, 32, 3)
    elif kind == "cifar100":
        ds = torchvision.datasets.CIFAR100(root=root, train=False, download=True)
        X_raw = ds.data
    else:
        raise ValueError(f"Unknown OOD kind: {kind}")

    indices = rng.choice(len(X_raw), size=min(n, len(X_raw)), replace=(n > len(X_raw)))
    return X_raw[indices]


def get_splits(
    seed: int = 0,
    n_ref: int = 2000,
    n_cal: int = 2000,
    n_scen: int = 3000,
    n_tl: int = 3000,
    fake: bool | None = None,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Return disjoint splits ref, cal, scen (from train) and timeline (from test)."""
    total_train = n_ref + n_cal + n_scen
    X_train, y_train = load_cifar10(split="train", n=None, seed=seed, fake=fake)

    if total_train > len(X_train):
        raise ValueError(
            f"Requested total train split samples ({total_train}) exceeds available ({len(X_train)})"
        )

    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(X_train))

    ref_idx = perm[:n_ref]
    cal_idx = perm[n_ref : n_ref + n_cal]
    scen_idx = perm[n_ref + n_cal : total_train]

    ref = (X_train[ref_idx], y_train[ref_idx])
    cal = (X_train[cal_idx], y_train[cal_idx])
    scen = (X_train[scen_idx], y_train[scen_idx])

    X_test, y_test = load_cifar10(split="test", n=None, seed=seed, fake=fake)
    rng_tl = np.random.default_rng(seed + 50000)
    tl_idx = rng_tl.choice(len(X_test), size=min(n_tl, len(X_test)), replace=False)
    timeline = (X_test[tl_idx], y_test[tl_idx])

    return {"ref": ref, "cal": cal, "scen": scen, "timeline": timeline}
