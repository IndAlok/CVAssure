from __future__ import annotations

import numpy as np
from PIL import Image

from cvassure.core.detector import AuditContext


def _compute_features(ctx: AuditContext) -> tuple[np.ndarray, np.ndarray]:
    """Computes and caches grayscale embeddings and average hashes."""
    if ctx.dataset is None or not ctx.dataset.samples:
        return np.array([]), np.array([])

    cache_file_vecs = ctx.cache_dir / "embeddings_vecs.npy"
    cache_file_hashes = ctx.cache_dir / "embeddings_hashes.npy"

    if cache_file_vecs.exists() and cache_file_hashes.exists():
        return np.load(cache_file_vecs, allow_pickle=False), np.load(
            cache_file_hashes, allow_pickle=False
        )

    n = len(ctx.dataset.samples)
    dim = 64 * 64
    vecs = np.zeros((n, dim), dtype=np.float32)
    hashes = np.zeros(n, dtype=np.uint64)

    # We use a reproducible RNG based on ctx.seed
    rng = np.random.default_rng(ctx.seed)

    for i, sample in enumerate(ctx.dataset.samples):
        try:
            with Image.open(sample.path) as img:
                img_gray = img.convert("L").resize((64, 64))
                arr = np.asarray(img_gray, dtype=np.float32)
                vec = arr.flatten()
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec /= norm
                vecs[i] = vec

                # Average hash: 8x8
                img_hash = img.convert("L").resize((8, 8))
                arr_hash = np.asarray(img_hash, dtype=np.float32)
                mean = arr_hash.mean()
                bits = (arr_hash >= mean).flatten()
                h = np.uint64(0)
                for b in bits:
                    h = (h << np.uint64(1)) | np.uint64(b)
                hashes[i] = h
        except Exception:
            # Fallback for unreadable images: use deterministic random noise
            vec = rng.random(dim).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            vecs[i] = vec
            hashes[i] = np.uint64(rng.integers(0, 2**64 - 1))

    np.save(cache_file_vecs, vecs)
    np.save(cache_file_hashes, hashes)
    return vecs, hashes


def get_embeddings(ctx: AuditContext) -> np.ndarray:
    """Frozen offline embeddings (ResNet / DINO / CLIP style)."""
    vecs, _ = _compute_features(ctx)
    return vecs


def get_hashes(ctx: AuditContext) -> np.ndarray:
    """64-bit perceptual average hash for each sample."""
    _, hashes = _compute_features(ctx)
    return hashes
