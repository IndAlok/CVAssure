import numpy as np
import pytest
from testbed.scenarios import build_attack_scenario, build_demo_scenario, build_timeline
from testbed.manifest import scenario_digest


def test_determinism_scenarios():
    sc1 = build_attack_scenario("patch", seed=42, n=100, fake=True)
    sc2 = build_attack_scenario("patch", seed=42, n=100, fake=True)

    assert scenario_digest(sc1) == scenario_digest(sc2)


def test_clean_scenario():
    sc = build_attack_scenario("clean", seed=0, n=100, fake=True)
    assert np.all(sc.attack_bits == 0)
    assert sc.attack_names == []


def test_demo_scenario():
    sc = build_demo_scenario(seed=42, n_per_contrib=200, fake=True)

    # Attack samples must only come from C-07
    attacked_mask = sc.is_attacked()
    attacked_contribs = sc.contributor[attacked_mask]

    assert len(attacked_contribs) > 0
    assert set(attacked_contribs) == {"C-07"}


def test_build_timeline():
    tl = build_timeline("fog", seed=10, n_batches=6, batch_size=60, onset=3, fake=True)

    assert tl.name == "fog"
    assert tl.kind == "drift"
    assert len(tl.batches) == 6

    for b in tl.batches:
        assert len(b.X) == 60
        assert len(b.contributor) == 60
