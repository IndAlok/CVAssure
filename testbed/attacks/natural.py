"""Natural shift corruptions (brightness, darkness, contrast, blur, noise, colour cast, fog)."""

import numpy as np
import cv2
from scipy.ndimage import gaussian_filter


def brightness(img: np.ndarray, delta: float) -> np.ndarray:
    """Additive brightness adjustment. delta in [-1, 1] relative to 255."""
    res = img.astype(np.float32) + delta * 255.0
    return np.clip(res, 0, 255).astype(np.uint8)


def contrast(img: np.ndarray, factor: float) -> np.ndarray:
    """Contrast adjustment by scaling pixel values relative to midpoint 128."""
    res = (img.astype(np.float32) - 128.0) * factor + 128.0
    return np.clip(res, 0, 255).astype(np.uint8)


def gaussian_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian blur per channel."""
    if sigma <= 0:
        return img.copy()
    blurred = np.zeros_like(img, dtype=np.float32)
    for c in range(3):
        blurred[:, :, c] = gaussian_filter(img[:, :, c].astype(np.float32), sigma=sigma)
    return np.clip(blurred, 0, 255).astype(np.uint8)


def gaussian_noise(img: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Add Gaussian pixel noise with standard deviation sigma * 255."""
    if sigma <= 0:
        return img.copy()
    noise = rng.normal(0, sigma * 255.0, size=img.shape)
    res = img.astype(np.float32) + noise
    return np.clip(res, 0, 255).astype(np.uint8)


def colour_cast(img: np.ndarray, shift: tuple[float, float, float]) -> np.ndarray:
    """Apply RGB color cast shift where shift tuple values are in [-1, 1]."""
    res = img.astype(np.float32) + np.array(shift, dtype=np.float32) * 255.0
    return np.clip(res, 0, 255).astype(np.uint8)


def fog(img: np.ndarray, strength: float, rng: np.random.Generator) -> np.ndarray:
    """Continuous realistic fog corruption using smooth spatial cloud pattern."""
    if strength <= 0:
        return img.copy()

    if img.ndim == 4:
        h, w = img.shape[1:3]
    else:
        h, w = img.shape[:2]
    n = gaussian_filter(rng.random((h, w)), sigma=max(h, w) / 6.0)
    n = (n - n.min()) / (n.max() - n.min() + 1e-8)  # low-frequency cloud pattern
    haze = (0.7 + 0.3 * n)[..., None] * 255.0
    return np.clip((1.0 - strength) * img.astype(np.float32) + strength * haze, 0, 255).astype(np.uint8)


def apply_corruption(
    X: np.ndarray, name: str, strength: float, rng: np.random.Generator
) -> np.ndarray:
    """Apply specified corruption to an array of images (N, H, W, 3) at given strength in [0, 1]."""
    res = np.zeros_like(X)

    for i in range(len(X)):
        img = X[i]
        if name == "brightness":
            res[i] = brightness(img, delta=strength * 0.4)
        elif name == "darkness":
            res[i] = brightness(img, delta=-strength * 0.4)
        elif name == "contrast":
            res[i] = contrast(img, factor=1.0 - strength * 0.5)
        elif name == "blur":
            res[i] = gaussian_blur(img, sigma=strength * 2.0)
        elif name == "noise":
            res[i] = gaussian_noise(img, sigma=strength * 0.25, rng=rng)
        elif name == "colour":
            res[i] = colour_cast(img, shift=(strength * 0.3, -strength * 0.1, -strength * 0.2))
        elif name == "fog":
            res[i] = fog(img, strength=strength * 0.75, rng=rng)
        else:
            raise ValueError(f"Unknown corruption name '{name}'")

    return res
