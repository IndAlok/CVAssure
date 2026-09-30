"""Near-duplicate attack generator (tiers 1, 2, 3)."""

import cv2
import numpy as np


def light_edit(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Light edit: horizontal flip 50%, pixel roll up to 2px, brightness 0.9-1.1."""
    edited = img.copy()

    # 50% mirror
    if rng.random() < 0.5:
        edited = np.fliplr(edited)

    # Shift up to 1 px with reflection padding instead of edge wrap
    shift_h = float(rng.integers(-1, 2))
    shift_w = float(rng.integers(-1, 2))
    if shift_h != 0 or shift_w != 0:
        h, w = edited.shape[:2]
        M = np.float32([[1, 0, shift_w], [0, 1, shift_h]])
        edited = cv2.warpAffine(edited, M, (w, h), borderMode=cv2.BORDER_REFLECT)

    # Brightness adjustment
    factor = rng.uniform(0.9, 1.1)
    edited = np.clip(edited.astype(np.float32) * factor, 0, 255).astype(np.uint8)

    return edited


def heavy_edit(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Heavy edit: random crop 80-95% + resize, rotation up to 8 deg, JPEG q=40."""
    h, w = img.shape[:2]
    edited = img.copy()

    # Random crop 80-95% and resize back
    crop_scale = rng.uniform(0.80, 0.95)
    ch, cw = max(1, int(h * crop_scale)), max(1, int(w * crop_scale))
    top = rng.integers(0, max(1, h - ch + 1))
    left = rng.integers(0, max(1, w - cw + 1))

    cropped = edited[top : top + ch, left : left + cw]
    edited = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    # Rotate up to 8 degrees
    angle = rng.uniform(-8.0, 8.0)
    center = (w / 2.0, h / 2.0)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    edited = cv2.warpAffine(edited, rot_mat, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # JPEG compression quality 40
    bgr = cv2.cvtColor(edited, cv2.COLOR_RGB2BGR)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
    _, buf = cv2.imencode(".jpg", bgr, encode_param)
    decoded_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    edited = cv2.cvtColor(decoded_bgr, cv2.COLOR_BGR2RGB)

    return edited


def make_duplicates(
    X: np.ndarray,
    y: np.ndarray,
    pool: np.ndarray,
    n_seed: int,
    copies: int,
    tier: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate near-duplicates for n_seed seed images from pool, creating copies copies each.

    Returns (X_new, y_new, dup_of, seed_indices).
    X_new and y_new contain original X and y plus generated duplicate copies appended.
    dup_of has length N_new; original samples are -1, duplicates hold index of seed image.
    """
    n_orig = len(X)
    seed_indices = rng.choice(pool, size=min(n_seed, len(pool)), replace=False)

    dup_X_list = []
    dup_y_list = []
    dup_of_list = []

    for seed_idx in seed_indices:
        seed_img = X[seed_idx]
        seed_label = y[seed_idx]

        for _ in range(copies):
            if tier == 1:
                dup_img = seed_img.copy()
            elif tier == 2:
                dup_img = light_edit(seed_img, rng)
            elif tier == 3:
                dup_img = heavy_edit(seed_img, rng)
            else:
                raise ValueError(f"Unknown duplicate tier {tier}. Must be 1, 2, or 3.")

            dup_X_list.append(dup_img)
            dup_y_list.append(seed_label)
            dup_of_list.append(seed_idx)

    if not dup_X_list:
        dup_of_orig = np.full(n_orig, -1, dtype=np.int64)
        return X.copy(), y.copy(), dup_of_orig, seed_indices

    X_new = np.concatenate([X, np.array(dup_X_list, dtype=np.uint8)], axis=0)
    y_new = np.concatenate([y, np.array(dup_y_list, dtype=np.int64)], axis=0)
    dup_of = np.concatenate(
        [np.full(n_orig, -1, dtype=np.int64), np.array(dup_of_list, dtype=np.int64)], axis=0
    )

    return X_new, y_new, dup_of, seed_indices
