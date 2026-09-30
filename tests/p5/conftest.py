import os
import pytest
import numpy as np

os.environ.setdefault('CVASSURE_FAKE_DATA', '1')


@pytest.fixture
def rng():
    """Return a deterministic numpy random Generator instance seeded with 0."""
    return np.random.default_rng(0)
