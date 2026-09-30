from pathlib import Path
import numpy as np
import pytest
from testbed.manifest import (
    Scenario,
    save_scenario,
    load_scenario,
    scenario_digest,
    validate_scenario,
)


def make_dummy_scenario(n: int = 10, seed: int = 42) -> Scenario:
    rng = np.random.default_rng(seed)
    X = rng.integers(0, 256, size=(n, 32, 32, 3), dtype=np.uint8)
    y_given = rng.integers(0, 10, size=n, dtype=np.int64)
    y_true = y_given.copy()
    sample_id = np.arange(100, 100 + n, dtype=np.int64)
    contributor = np.array(["C-01"] * n, dtype=str)
    batch = np.zeros(n, dtype=np.int32)
    attack_bits = np.zeros(n, dtype=np.int32)
    dup_of = np.full(n, -1, dtype=np.int64)

    # Set one attack sample
    attack_bits[0] = 1

    return Scenario(
        name="dummy_test",
        seed=seed,
        dataset="cifar10",
        X=X,
        y_given=y_given,
        y_true=y_true,
        sample_id=sample_id,
        contributor=contributor,
        batch=batch,
        attack_bits=attack_bits,
        dup_of=dup_of,
        attack_names=["patch_trigger"],
        params={"rate": 0.1},
    )


def test_round_trip(tmp_path: Path):
    sc = make_dummy_scenario()
    save_dir = tmp_path / "scenario_out"
    save_scenario(sc, save_dir)

    loaded_sc = load_scenario(save_dir)

    assert loaded_sc.name == sc.name
    assert loaded_sc.seed == sc.seed
    assert loaded_sc.dataset == sc.dataset
    assert loaded_sc.attack_names == sc.attack_names
    assert loaded_sc.params == sc.params

    np.testing.assert_array_equal(loaded_sc.X, sc.X)
    np.testing.assert_array_equal(loaded_sc.y_given, sc.y_given)
    np.testing.assert_array_equal(loaded_sc.y_true, sc.y_true)
    np.testing.assert_array_equal(loaded_sc.sample_id, sc.sample_id)
    np.testing.assert_array_equal(loaded_sc.contributor, sc.contributor)
    np.testing.assert_array_equal(loaded_sc.batch, sc.batch)
    np.testing.assert_array_equal(loaded_sc.attack_bits, sc.attack_bits)
    np.testing.assert_array_equal(loaded_sc.dup_of, sc.dup_of)


def test_digest_sensitivity():
    sc = make_dummy_scenario()
    d1 = scenario_digest(sc)

    # Mutate a single pixel
    sc_modified = make_dummy_scenario()
    sc_modified.X[0, 0, 0, 0] = np.uint8((int(sc_modified.X[0, 0, 0, 0]) + 1) % 256)
    d2 = scenario_digest(sc_modified)

    assert d1 != d2


def test_validation_errors():
    sc = make_dummy_scenario()
    validate_scenario(sc)  # Should pass clean

    # 1. Invalid length
    corrupted = make_dummy_scenario()
    corrupted.y_given = corrupted.y_given[:-1]
    with pytest.raises(ValueError, match="Array length mismatch"):
        validate_scenario(corrupted)

    # 2. Non-uint8 X
    corrupted = make_dummy_scenario()
    corrupted.X = corrupted.X.astype(np.float32)
    with pytest.raises(ValueError, match="Image array X must be uint8"):
        validate_scenario(corrupted)

    # 3. Non-unique sample_id
    corrupted = make_dummy_scenario()
    corrupted.sample_id[1] = corrupted.sample_id[0]
    with pytest.raises(ValueError, match="sample_id contains non-unique values"):
        validate_scenario(corrupted)

    # 4. Out of range attack_bits
    corrupted = make_dummy_scenario()
    corrupted.attack_bits[0] = 100  # only 1 attack name defined (max bit val 1)
    with pytest.raises(ValueError, match="attack_bits contain values out of valid range"):
        validate_scenario(corrupted)

    # 5. Unknown dup_of reference
    corrupted = make_dummy_scenario()
    corrupted.dup_of[0] = 999999
    with pytest.raises(ValueError, match="dup_of references unknown sample_id"):
        validate_scenario(corrupted)
