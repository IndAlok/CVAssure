"""Scenario and Timeline builder functions and CLI module."""

import argparse
from pathlib import Path
from typing import Any
import numpy as np

from testbed.data import get_splits, load_ood
from testbed.manifest import (
    Scenario,
    Batch,
    Timeline,
    save_scenario,
    validate_scenario,
)
from testbed.attacks.patch import poison_patch, add_patch
from testbed.attacks.blend import poison_blend
from testbed.attacks.labels import flip_labels
from testbed.attacks.duplicates import make_duplicates
from testbed.attacks.ood import insert_ood
from testbed.attacks.natural import fog, brightness

ATTACKS = [
    "clean",
    "patch",
    "patch_clean_label",
    "blend",
    "flip_random",
    "flip_targeted",
    "dup_tier1",
    "dup_tier2",
    "dup_tier3",
    "ood_easy",
    "ood_hard",
]


def build_attack_scenario(
    name: str,
    seed: int = 0,
    n: int = 3000,
    fake: bool | None = None,
    rate: float | None = None,
    **kw: Any,
) -> Scenario:
    """Build a single-attack scenario with one contributor 'C-01'."""
    if name not in ATTACKS:
        raise ValueError(f"Unknown attack scenario name '{name}'. Must be one of {ATTACKS}")

    rng = np.random.default_rng(seed)
    splits = get_splits(seed=seed, n_scen=n, fake=fake)
    X_base, y_base = splits["scen"]

    n_samples = len(X_base)
    X = X_base.copy()
    y_given = y_base.copy()
    y_true = y_base.copy()
    sample_id = np.arange(100000, 100000 + n_samples, dtype=np.int64)
    contributor = np.array(["C-01"] * n_samples, dtype=object)
    batch = (np.arange(n_samples) % 4).astype(np.int32)
    attack_bits = np.zeros(n_samples, dtype=np.int32)
    dup_of = np.full(n_samples, -1, dtype=np.int64)
    pool = np.arange(n_samples)

    attack_names = [name] if name != "clean" else []
    params: dict[str, Any] = {"seed": seed, "rate": rate}

    if name == "clean":
        pass

    elif name in ("patch", "patch_clean_label"):
        r = rate if rate is not None else 0.05
        clean_lbl = (name == "patch_clean_label")
        poisoned_idx = poison_patch(
            X, y_given, y_true, pool, target=0, rate=r, rng=rng, size=4, pos="br", clean_label=clean_lbl
        )
        for idx in poisoned_idx:
            attack_bits[idx] |= 1
        params["rate"] = r
        params["target_class"] = 0
        params["clean_label"] = clean_lbl

    elif name == "blend":
        r = rate if rate is not None else 0.05
        poisoned_idx, _ = poison_blend(
            X, y_given, y_true, pool, target=0, rate=r, rng=rng, alpha=0.1
        )
        for idx in poisoned_idx:
            attack_bits[idx] |= 1
        params["rate"] = r
        params["target_class"] = 0

    elif name in ("flip_random", "flip_targeted"):
        r = rate if rate is not None else 0.05
        mode = "random" if name == "flip_random" else "targeted"
        src, dst = (1, 0) if mode == "targeted" else (None, None)
        y_given, flipped_idx = flip_labels(
            y_given, pool, rate=r, rng=rng, mode=mode, src=src, dst=dst, n_classes=10
        )
        for idx in flipped_idx:
            attack_bits[idx] |= 1
        params["rate"] = r
        params["mode"] = mode

    elif name in ("dup_tier1", "dup_tier2", "dup_tier3"):
        tier = int(name[-1])
        n_seed = kw.get("n_seed", 10)
        copies = kw.get("copies", 60)
        X_new, y_given_new, dup_of_new, seed_indices = make_duplicates(
            X, y_given, pool, n_seed=n_seed, copies=copies, tier=tier, rng=rng
        )
        n_added = len(X_new) - n_samples

        # Map 0-based seed indices in dup_of_new to sample_id values
        dup_of_mapped = np.array(
            [-1 if ref == -1 else sample_id[ref] for ref in dup_of_new], dtype=np.int64
        )
        dup_of = dup_of_mapped

        y_true = np.concatenate([y_true, y_given_new[n_samples:]], axis=0)
        sample_id = np.arange(100000, 100000 + len(X_new), dtype=np.int64)
        contributor = np.array(["C-01"] * len(X_new), dtype=object)
        batch = np.concatenate([batch, (np.arange(n_added) % 4).astype(np.int32)], axis=0)

        attack_bits = np.zeros(len(X_new), dtype=np.int32)
        for s_idx in seed_indices:
            attack_bits[s_idx] |= 1
        attack_bits[n_samples:] |= 1

        X = X_new
        y_given = y_given_new
        params["tier"] = tier
        params["n_seed"] = n_seed
        params["copies"] = copies

    elif name in ("ood_easy", "ood_hard"):
        r = rate if rate is not None else 0.05
        n_ood = round(r * n_samples)
        ood_kind = "svhn" if name == "ood_easy" else "cifar100"
        X_ood_raw = load_ood(kind=ood_kind, n=n_ood, seed=seed, fake=fake)
        X_ood, y_ood = insert_ood(X_ood_raw, target=0)

        selected = rng.choice(pool, size=n_ood, replace=False)
        X[selected] = X_ood
        y_given[selected] = y_ood
        for idx in selected:
            attack_bits[idx] |= 1
        params["rate"] = r
        params["ood_kind"] = ood_kind

    sc = Scenario(
        name=name,
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
        attack_names=attack_names,
        params=params,
    )
    validate_scenario(sc)
    return sc


def build_demo_scenario(
    seed: int = 42, n_per_contrib: int = 1500, fake: bool | None = None
) -> Scenario:
    """Build the C-07 demo scenario with contributors C-01, C-04, C-07 across 6 batches."""
    rng = np.random.default_rng(seed)
    n_total = 3 * n_per_contrib
    splits = get_splits(seed=seed, n_scen=n_total, fake=fake)
    X_base, y_base = splits["scen"]

    X = X_base.copy()
    y_given = y_base.copy()
    y_true = y_base.copy()

    # Contributors assignment
    contrib_list = ["C-01", "C-04", "C-07"]
    contrib_arr = []
    for c in contrib_list:
        contrib_arr.extend([c] * n_per_contrib)
    contributor = np.array(contrib_arr, dtype=object)

    # 6 batches round robin
    batch = (np.arange(n_total) % 6).astype(np.int32)
    sample_id = np.arange(900000, 900000 + n_total, dtype=np.int64)
    attack_bits = np.zeros(n_total, dtype=np.int32)
    dup_of = np.full(n_total, -1, dtype=np.int64)

    attack_names = ["patch_trigger", "near_duplicate"]

    # C-07 patch trigger on 3% of C-07 samples in batches >= 2
    c07_mask = (contributor == "C-07") & (batch >= 2)
    c07_indices = np.where(c07_mask)[0]

    n_patch = round(0.03 * len(c07_indices))
    if n_patch > 0:
        patch_candidates = c07_indices[y_true[c07_indices] != 0]
        selected_patch = rng.choice(patch_candidates, size=min(n_patch, len(patch_candidates)), replace=False)
        for idx in selected_patch:
            X[idx] = add_patch(X[idx], size=4, pos="br", value=255)
            y_given[idx] = 0
            attack_bits[idx] |= 1  # bit 0: patch_trigger

    # C-07 10x60 tier-2 duplicate flood
    c07_all = np.where(contributor == "C-07")[0]
    X_c07 = X[c07_all]
    y_c07 = y_given[c07_all]
    pool_c07 = np.arange(len(c07_all))

    X_dup, y_dup, dup_of_dup, seed_indices_c07 = make_duplicates(
        X_c07, y_c07, pool_c07, n_seed=10, copies=60, tier=2, rng=rng
    )

    n_added = len(X_dup) - len(X_c07)
    if n_added > 0:
        added_X = X_dup[len(X_c07):]
        added_y = y_dup[len(X_c07):]
        added_dup_of = dup_of_dup[len(X_c07):]

        # Map dup_of references to scenario sample_ids
        mapped_dup_of = np.array([sample_id[c07_all[ref]] for ref in added_dup_of], dtype=np.int64)

        X = np.concatenate([X, added_X], axis=0)
        y_given = np.concatenate([y_given, added_y], axis=0)
        y_true = np.concatenate([y_true, added_y], axis=0)
        contributor = np.concatenate([contributor, np.array(["C-07"] * n_added, dtype=object)], axis=0)
        batch = np.concatenate([batch, (np.arange(n_added) % 6).astype(np.int32)], axis=0)
        dup_of = np.concatenate([dup_of, mapped_dup_of], axis=0)

        added_attack_bits = np.full(n_added, 2, dtype=np.int32)  # bit 1: near_duplicate
        attack_bits = np.concatenate([attack_bits, added_attack_bits], axis=0)

        # Mark seed images bit 1
        for s_idx in seed_indices_c07:
            global_s_idx = c07_all[s_idx]
            attack_bits[global_s_idx] |= 2

        sample_id = np.arange(900000, 900000 + len(X), dtype=np.int64)

    params = {
        "patch_trigger": {"target_class": 0, "size": 4, "pos": "br", "rate": 0.03, "contributor": "C-07"},
        "near_duplicate": {"seed_images": 10, "copies_each": 60, "tier": 2, "contributor": "C-07"},
    }

    sc = Scenario(
        name="demo",
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
        attack_names=attack_names,
        params=params,
    )
    validate_scenario(sc)
    return sc


def build_timeline(
    kind: str,
    seed: int,
    n_batches: int = 8,
    batch_size: int = 300,
    onset: int = 4,
    fake: bool | None = None,
) -> Timeline:
    """Build a time-series timeline of batches ("fog", "patch", "clean", "fog_step", "brightness")."""
    rng = np.random.default_rng(seed)
    n_total = n_batches * batch_size
    splits = get_splits(seed=seed, n_tl=n_total, fake=fake)
    X_base, y_base = splits["timeline"]

    kind_to_label = {
        "fog": "drift",
        "patch": "manipulation",
        "clean": "none",
        "fog_step": "ambiguous",
        "brightness": "drift",
    }
    if kind not in kind_to_label:
        raise ValueError(f"Unknown timeline kind '{kind}'. Must be one of {list(kind_to_label.keys())}")

    batches = []
    contrib_list = ["C-01", "C-04", "C-07"]

    for t in range(n_batches):
        start_idx = t * batch_size
        end_idx = start_idx + batch_size
        X_b = X_base[start_idx:end_idx].copy()
        y_b = y_base[start_idx:end_idx].copy()

        # Contributor assignment (1/3 per contributor)
        b_contrib = np.array([contrib_list[i % 3] for i in range(batch_size)], dtype=object)
        is_attacked_b = np.zeros(batch_size, dtype=bool)

        shift_strength = 0.0

        if kind == "fog":
            shift_strength = (t / max(1, n_batches - 1)) * 0.75
            X_b = fog(X_b, strength=shift_strength, rng=rng)
            is_attacked_b[:] = (shift_strength > 0)

        elif kind == "brightness":
            shift_strength = (t / max(1, n_batches - 1)) * 0.4
            X_b = brightness(X_b, delta=shift_strength)
            is_attacked_b[:] = (shift_strength > 0)

        elif kind == "fog_step":
            if t >= onset:
                shift_strength = 0.6
                X_b = fog(X_b, strength=shift_strength, rng=rng)
                is_attacked_b[:] = True

        elif kind == "patch":
            if t >= onset:
                shift_strength = 1.0
                c07_mask = (b_contrib == "C-07") & (y_b != 0)
                c07_indices = np.where(c07_mask)[0]
                n_patch = len(c07_indices) // 2
                if n_patch > 0:
                    selected = rng.choice(c07_indices, size=n_patch, replace=False)
                    for idx in selected:
                        X_b[idx] = add_patch(X_b[idx], size=4, pos="br", value=255)
                        y_b[idx] = 0
                        is_attacked_b[idx] = True

        elif kind == "clean":
            shift_strength = 0.0

        batches.append(
            Batch(
                t=t,
                X=X_b,
                y_given=y_b,
                contributor=b_contrib,
                is_attacked=is_attacked_b,
                shift_strength=shift_strength,
            )
        )

    return Timeline(name=kind, seed=seed, kind=kind_to_label[kind], batches=batches)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and save attack scenarios and demo timeline.")
    parser.add_argument("--all", action="store_true", help="Generate all attack scenarios and demo scenario.")
    parser.add_argument("--name", type=str, default="demo", help="Scenario name to build.")
    parser.add_argument("--seed", type=int, default=0, help="Random seed.")
    parser.add_argument("--n", type=int, default=3000, help="Number of samples.")
    parser.add_argument("--out", type=str, default="out/scenarios", help="Output directory.")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        for attack_name in ATTACKS:
            sc = build_attack_scenario(name=attack_name, seed=args.seed, n=args.n)
            save_scenario(sc, out_dir / attack_name)
            print(f"Saved scenario '{attack_name}' to {out_dir / attack_name}")

        demo_sc = build_demo_scenario(seed=args.seed)
        save_scenario(demo_sc, out_dir / "demo")
        print(f"Saved demo scenario to {out_dir / 'demo'}")

    else:
        if args.name == "demo":
            sc = build_demo_scenario(seed=args.seed)
        else:
            sc = build_attack_scenario(name=args.name, seed=args.seed, n=args.n)
        save_scenario(sc, out_dir / args.name)
        print(f"Saved scenario '{args.name}' to {out_dir / args.name}")


if __name__ == "__main__":
    main()
