"""Reference profile construction, 39 scalar image features, noise-floor estimation, and persistence."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import joblib
import numpy as np
import cv2
from shift.embed import get_embeddings

GRID = 4
FEATURE_NAMES: list[str] = (
    ["brightness", "contrast", "sharpness", "noise", "saturation", "hue", "hf_ratio"]
    + [f"grid_mean_{i}_{j}" for i in range(GRID) for j in range(GRID)]
    + [f"grid_grad_{i}_{j}" for i in range(GRID) for j in range(GRID)]
)


def scalar_features(X: np.ndarray) -> np.ndarray:
    """Extract 39 scalar features per image (N, 32, 32, 3) uint8."""
    n, h, w, c = X.shape
    cell_h, cell_w = h // GRID, w // GRID

    # Precalculate low-frequency radial mask for hf_ratio
    cy, cx = h / 2.0, w / 2.0
    y_grid, x_grid = np.ogrid[:h, :w]
    r_grid = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
    lf_mask = r_grid <= (max(h, w) / 4.0)

    feats_list = []

    for i in range(n):
        img = X[i]
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)

        # 1. Brightness & contrast
        b_val = float(np.mean(gray)) / 255.0
        c_val = float(np.std(gray)) / 255.0

        # 2. Sharpness (Laplacian variance)
        sharp_val = float(cv2.Laplacian(gray, cv2.CV_32F).var()) / (255.0**2)

        # 3. Noise (diff from Gaussian blur)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        noise_val = float(np.std(gray - blurred)) / 255.0

        # 4. Saturation & Hue
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        sat_val = float(np.mean(hsv[:, :, 1])) / 255.0
        hue_val = float(np.mean(hsv[:, :, 0])) / 180.0

        # 5. High-frequency ratio
        fft_shift = np.abs(np.fft.fftshift(np.fft.fft2(gray)))
        total_energy = np.sum(fft_shift) + 1e-8
        lf_energy = np.sum(fft_shift[lf_mask])
        hf_ratio_val = float(1.0 - (lf_energy / total_energy))

        # 6. Grid cell means (16)
        grid_means = []
        for r in range(GRID):
            for col in range(GRID):
                cell_g = gray[r * cell_h : (r + 1) * cell_h, col * cell_w : (col + 1) * cell_w]
                grid_means.append(float(np.mean(cell_g)) / 255.0)

        # 7. Grid cell Sobel gradient magnitude energy (16)
        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = np.sqrt(sobel_x**2 + sobel_y**2)
        grid_grads = []
        for r in range(GRID):
            for col in range(GRID):
                cell_grad = grad_mag[r * cell_h : (r + 1) * cell_h, col * cell_w : (col + 1) * cell_w]
                grid_grads.append(float(np.mean(cell_grad)) / 255.0)

        row_feats = (
            [b_val, c_val, sharp_val, noise_val, sat_val, hue_val, hf_ratio_val]
            + grid_means
            + grid_grads
        )
        feats_list.append(row_feats)

    return np.array(feats_list, dtype=np.float32)


@dataclass
class ReferenceProfile:
    """Holds reference statistical profile, features, noise-floor, and kernel bandwidth."""

    feat_mean: np.ndarray
    feat_std: np.ndarray
    feats: np.ndarray
    pca: Any
    emb: np.ndarray
    emb_mean: np.ndarray
    emb_cov_inv: np.ndarray
    med: float
    mean_img: np.ndarray
    pix_batch_std: np.ndarray
    batch_size: int
    backend: str
    seed: int


def build_reference_profile(
    X_ref: np.ndarray,
    backend: str = "handcrafted",
    batch_size: int = 300,
    n_batches: int = 100,
    seed: int = 0,
    emb_ref: np.ndarray | None = None,
) -> ReferenceProfile:
    """Build ReferenceProfile from reference images dataset."""
    rng = np.random.default_rng(seed)

    feats = scalar_features(X_ref)
    feat_mean = np.mean(feats, axis=0)
    feat_std = np.std(feats, axis=0) + 1e-6

    if emb_ref is None:
        emb, pca = get_embeddings(X_ref, backend=backend, pca_dim=50, pca=None)
    else:
        emb, pca = emb_ref, None

    emb_mean = np.mean(emb, axis=0)
    cov = np.cov(emb, rowvar=False)
    if cov.ndim == 0:
        cov = np.array([[cov]])
    cov_reg = cov + 1e-5 * np.eye(emb.shape[1])
    emb_cov_inv = np.linalg.inv(cov_reg)

    # RBF kernel median bandwidth computation
    n_sub = min(1000, len(emb))
    sub = emb[:n_sub]
    sqdists = np.sum((sub[:, None, :] - sub[None, :, :]) ** 2, axis=-1)
    med_val = float(np.median(sqdists))
    if med_val <= 0:
        med_val = 1.0

    # Noise floor pix_batch_std across clean reference batches
    mean_img = np.mean(X_ref, axis=0).astype(np.float32)
    batch_means = []
    n_ref = len(X_ref)

    for _ in range(n_batches):
        idx = rng.choice(n_ref, size=min(batch_size, n_ref), replace=False)
        b_img = np.mean(X_ref[idx], axis=0)
        batch_means.append(b_img)

    batch_means_arr = np.array(batch_means, dtype=np.float32)  # (n_batches, H, W, 3)
    pix_batch_std = np.mean(np.std(batch_means_arr, axis=0), axis=-1).astype(np.float32)  # (H, W)

    return ReferenceProfile(
        feat_mean=feat_mean,
        feat_std=feat_std,
        feats=feats,
        pca=pca,
        emb=emb,
        emb_mean=emb_mean,
        emb_cov_inv=emb_cov_inv,
        med=med_val,
        mean_img=mean_img,
        pix_batch_std=pix_batch_std,
        batch_size=batch_size,
        backend=backend,
        seed=seed,
    )


def save_profile(p: ReferenceProfile, path: str | Path) -> None:
    """Save ReferenceProfile to disk using joblib."""
    p_path = Path(path)
    p_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(p, p_path)


def load_profile(path: str | Path) -> ReferenceProfile:
    """Load ReferenceProfile from disk using joblib."""
    return joblib.load(path)
