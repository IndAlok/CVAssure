"""Feature embeddings (handcrafted, resnet18, P2 file loader) and PCA reduction."""

from pathlib import Path
from typing import Any
import numpy as np
import cv2
from sklearn.decomposition import PCA


def handcrafted_embed(X: np.ndarray) -> np.ndarray:
    """Extract 126-dimensional handcrafted visual feature embeddings for N images (uint8 N, H, W, 3)."""
    n, h, w, c = X.shape
    features = []

    # Precalculate radius grid for 8-band radial FFT
    cy, cx = h / 2.0, w / 2.0
    y_grid, x_grid = np.ogrid[:h, :w]
    r_grid = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
    max_r = np.max(r_grid) + 1e-6
    radial_masks = [(r_grid >= i * max_r / 8.0) & (r_grid < (i + 1) * max_r / 8.0) for i in range(8)]

    for i in range(n):
        img = X[i]
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)

        # 1. Per-channel 16-bin histograms (3 x 16 = 48)
        hist_feats = []
        for ch in range(3):
            hist, _ = np.histogram(img[:, :, ch], bins=16, range=(0, 256))
            hist_norm = hist.astype(np.float32) / (h * w)
            hist_feats.extend(hist_norm)

        # 2. 4x4 grid cell means per channel (4 x 4 x 3 = 48)
        cell_h, cell_w = h // 4, w // 4
        grid_means = []
        for r in range(4):
            for col in range(4):
                cell = img[r * cell_h : (r + 1) * cell_h, col * cell_w : (col + 1) * cell_w]
                grid_means.extend(np.mean(cell, axis=(0, 1)) / 255.0)

        # 3. 4x4 grid cell Sobel gradient magnitude energy on grayscale (4 x 4 = 16)
        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = np.sqrt(sobel_x**2 + sobel_y**2)
        grid_grads = []
        for r in range(4):
            for col in range(4):
                cell_g = grad_mag[r * cell_h : (r + 1) * cell_h, col * cell_w : (col + 1) * cell_w]
                grid_grads.append(np.mean(cell_g) / 255.0)

        # 4. 8 radial FFT band energies (8)
        fft_shift = np.abs(np.fft.fftshift(np.fft.fft2(gray)))
        total_energy = np.sum(fft_shift) + 1e-8
        fft_bands = [np.sum(fft_shift[m]) / total_energy for m in radial_masks]

        # 5. Mean and std per channel (3 x 2 = 6)
        ch_means = np.mean(img, axis=(0, 1)) / 255.0
        ch_stds = np.std(img, axis=(0, 1)) / 255.0
        stats = list(ch_means) + list(ch_stds)

        sample_vec = hist_feats + grid_means + grid_grads + fft_bands + stats
        features.append(sample_vec)

    return np.array(features, dtype=np.float32)


def resnet18_embed(X: np.ndarray, batch_size: int = 128, upsample: int = 64) -> np.ndarray:
    """Extract 512-dimensional ResNet-18 feature embeddings (requires PyTorch & torchvision)."""
    try:
        import torch
        import torchvision.models as models
        import torchvision.transforms as T
        from PIL import Image
    except ImportError as e:
        raise ImportError(
            "PyTorch and torchvision are required for resnet18_embed. "
            "Install torchvision or use backend='handcrafted'."
        ) from e

    device = torch.device("cpu")
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = torch.nn.Identity()  # Remove classifier head
    model.eval()
    model.to(device)

    transform = T.Compose([
        T.Resize((upsample, upsample)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    n = len(X)
    embeddings = []

    with torch.no_grad():
        for i in range(0, n, batch_size):
            batch_imgs = X[i : i + batch_size]
            tensors = [transform(Image.fromarray(img)) for img in batch_imgs]
            batch_tensor = torch.stack(tensors).to(device)
            out = model(batch_tensor)
            embeddings.append(out.cpu().numpy())

    return np.concatenate(embeddings, axis=0).astype(np.float32)


def load_embeddings_npy(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Load embeddings NPY/NPZ file containing emb (N, D) and sample_id (N,)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Embeddings file not found: {p}")

    if p.suffix == ".npz":
        with np.load(p, allow_pickle=True) as data:
            return data["emb"].astype(np.float32), data["sample_id"].astype(np.int64)

    data = np.load(p, allow_pickle=True)
    if isinstance(data, np.ndarray) and data.dtype.names is not None:
        return data["emb"].astype(np.float32), data["sample_id"].astype(np.int64)
    elif isinstance(data, dict) or hasattr(data, "files"):
        return data["emb"].astype(np.float32), data["sample_id"].astype(np.int64)
    else:
        raise ValueError("Invalid embedding file structure. Expected dict/structured array with keys 'emb' and 'sample_id'.")


def get_embeddings(
    X: np.ndarray,
    backend: str = "handcrafted",
    pca_dim: int = 50,
    pca: Any = None,
) -> tuple[np.ndarray, Any]:
    """Extract raw embeddings using backend and apply PCA dimension reduction."""
    if backend == "handcrafted":
        raw = handcrafted_embed(X)
    elif backend == "resnet18":
        raw = resnet18_embed(X)
    else:
        raise ValueError(f"Unknown embedding backend '{backend}'. Choose 'handcrafted' or 'resnet18'.")

    n_samples, n_features = raw.shape
    actual_dim = min(pca_dim, n_features, n_samples)

    if pca is None:
        pca = PCA(n_components=actual_dim, random_state=0)
        Z = pca.fit_transform(raw)
    else:
        Z = pca.transform(raw)

    return Z.astype(np.float32), pca
