import numpy as np
import pytest
from testbed.data import fake_images
from testbed.attacks.natural import fog
from shift.embed import handcrafted_embed, get_embeddings, load_embeddings_npy


def test_handcrafted_embed_shape_and_determinism():
    X, _ = fake_images(n=20, seed=42)

    emb1 = handcrafted_embed(X)
    emb2 = handcrafted_embed(X)

    assert emb1.shape == (20, 126)
    assert emb1.dtype == np.float32
    np.testing.assert_array_equal(emb1, emb2)


def test_pca_reuse():
    X, _ = fake_images(n=40, seed=10)

    Z1, pca = get_embeddings(X, backend="handcrafted", pca_dim=30, pca=None)
    Z2, _ = get_embeddings(X, backend="handcrafted", pca_dim=30, pca=pca)

    assert Z1.shape == (40, 30)
    np.testing.assert_allclose(Z1, Z2, rtol=1e-5, atol=1e-5)


def test_fog_distance_larger_than_clean_split():
    rng = np.random.default_rng(0)
    X_clean, _ = fake_images(n=100, seed=0)

    # Split clean into two halves
    half1 = X_clean[:50]
    half2 = X_clean[50:]

    # Apply heavy fog to second half
    X_fog = fog(half1.copy(), strength=0.75, rng=rng)

    Z_half1, _ = get_embeddings(half1, backend="handcrafted", pca_dim=20)
    Z_half2, _ = get_embeddings(half2, backend="handcrafted", pca_dim=20)
    Z_fog, _ = get_embeddings(X_fog, backend="handcrafted", pca_dim=20)

    # Mean distance between two clean halves
    dist_clean_clean = np.mean(np.linalg.norm(np.mean(Z_half1, axis=0) - np.mean(Z_half2, axis=0)))

    # Mean distance between clean and fogged
    dist_clean_fog = np.mean(np.linalg.norm(np.mean(Z_half1, axis=0) - np.mean(Z_fog, axis=0)))

    assert dist_clean_fog > dist_clean_clean
