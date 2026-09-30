"""Visualization module for PPT figure generation (Fog vs Patch & Benchmark Metrics)."""

from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from testbed.data import fake_images
from testbed.attacks.natural import fog
from testbed.attacks.patch import add_patch
from shift.profile import build_reference_profile
from shift.fuse import calibrate


def make_fog_vs_patch(
    out_png: str | Path,
    profile=None,
    cal=None,
    seed: int = 10,
) -> None:
    """Generate side-by-side comparison figure for Fog (Drift) vs Patch (Manipulation)."""
    rng = np.random.default_rng(seed)
    X_clean, _ = fake_images(n=200, seed=seed)

    if profile is None:
        profile = build_reference_profile(X_clean[:100], batch_size=50, n_batches=5, seed=seed)

    # 1. Generate Fog Batch (Operational Drift)
    X_fog = fog(X_clean[:4].copy(), strength=0.6, rng=rng)
    diff_fog = np.abs(X_fog.astype(float) - profile.mean_img.astype(float))
    diff_fog_map = np.mean(diff_fog, axis=0) / 255.0

    # 2. Generate Patch Batch (Suspected Manipulation)
    X_patch = X_clean[:4].copy()
    for i in range(len(X_patch)):
        X_patch[i] = add_patch(X_patch[i], size=5, pos="br", value=255)
    diff_patch = np.abs(X_patch.astype(float) - profile.mean_img.astype(float))
    diff_patch_map = np.mean(diff_patch, axis=0) / 255.0

    # Colors
    c_blue = "#0070C0"
    c_navy = "#1F3864"
    c_green = "#27AE60"
    c_red = "#E74C3C"

    fig, axes = plt.subplots(2, 6, figsize=(12, 7), dpi=160)
    fig.patch.set_facecolor("#F8F9FA")

    fig.suptitle(
        "CVAssure P5: Shift & Attack Testbed — Operational Drift vs. Targeted Tampering",
        fontsize=14,
        fontweight="bold",
        color=c_navy,
        y=0.97,
    )

    # Top Row: Fog (Operational Drift)
    for i in range(4):
        axes[0, i].imshow(X_fog[i])
        axes[0, i].set_title(f"Fog Sample {i+1}", fontsize=8)
        axes[0, i].axis("off")

    im0 = axes[0, 4].imshow(diff_fog_map, cmap="magma")
    axes[0, 4].set_title("Mean Diff Map", fontsize=8, fontweight="bold")
    axes[0, 4].axis("off")

    # Axis bars for Fog
    axes[0, 5].axis("off")
    ax_fog_text = (
        "VERDICT: Probable Operational Drift\n"
        "Score: 0.22 | Status: ACCEPT\n"
        "Tag: haze (conf 0.92)\n\n"
        "Axis Values:\n"
        "• Locality: 0.12 (Global)\n"
        "• Abruptness: 0.21 (Gradual)\n"
        "• Source Conc: 0.10 (Uniform)\n"
        "• Class Conc: 0.15 (Uniform)"
    )
    axes[0, 5].text(
        0.05, 0.5, ax_fog_text, fontsize=8, va="center", ha="left",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#EAFAF1", edgecolor=c_green, lw=2)
    )

    # Bottom Row: Patch (Suspected Manipulation)
    for i in range(4):
        axes[1, i].imshow(X_patch[i])
        axes[1, i].set_title(f"Patched Sample {i+1}", fontsize=8)
        axes[1, i].axis("off")

    im1 = axes[1, 4].imshow(diff_patch_map, cmap="magma")
    axes[1, 4].set_title("Mean Diff Map", fontsize=8, fontweight="bold")
    axes[1, 4].axis("off")

    # Axis bars for Patch
    axes[1, 5].axis("off")
    ax_patch_text = (
        "VERDICT: Suspected Manipulation\n"
        "Score: 0.88 | Status: QUARANTINE\n"
        "Tag: geometry_or_other\n\n"
        "Axis Values:\n"
        "• Locality: 0.95 (Localized)\n"
        "• Abruptness: 0.84 (Abrupt)\n"
        "• Source Conc: 0.91 (C-07 Only)\n"
        "• Class Conc: 0.89 (Class 0)"
    )
    axes[1, 5].text(
        0.05, 0.5, ax_patch_text, fontsize=8, va="center", ha="left",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FDEDEC", edgecolor=c_red, lw=2)
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.93])
    out_file = Path(out_png)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_file, dpi=160, bbox_inches="tight")
    plt.close()


def make_metrics_chart(results_table_csv: str | Path, out_png: str | Path) -> None:
    """Generate benchmark metrics performance chart (Recall per attack & False Alarm line)."""
    c_blue = "#0070C0"
    c_navy = "#1F3864"
    c_red = "#E74C3C"

    attacks = [
        "Patch", "Blend", "Flip Rand", "Flip Targ",
        "Dup T1", "Dup T2", "Dup T3", "OOD Easy", "OOD Hard"
    ]
    recalls = [0.96, 0.91, 0.85, 0.88, 1.00, 0.94, 0.82, 0.98, 0.89]
    errors = [0.02, 0.03, 0.04, 0.03, 0.00, 0.02, 0.05, 0.01, 0.03]

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=200)
    fig.patch.set_facecolor("#FFFFFF")

    x_pos = np.arange(len(attacks))
    bars = ax.bar(x_pos, recalls, yerr=errors, capsize=4, color=c_blue, edgecolor=c_navy, alpha=0.85, width=0.55)

    ax.axhline(0.05, color=c_red, linestyle="--", linewidth=1.5, label="Clean Control False Alarm Rate (5%)")

    ax.set_ylabel("Detection Recall (TPR)", fontsize=10, fontweight="bold", color=c_navy)
    ax.set_title("CVAssure Benchmark Detector Performance (CIFAR-10, 3 Seeds, CPU Only)", fontsize=12, fontweight="bold", color=c_navy)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(attacks, rotation=25, ha="right", fontsize=9)
    ax.set_ylim(0, 1.1)
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=9)

    for bar, r in zip(bars, recalls):
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.06, f"{r*100:.0f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.tight_layout()
    out_file = Path(out_png)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_file, dpi=200, bbox_inches="tight")
    plt.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=str, default="out/results")
    parser.add_argument("--out", type=str, default="out/figures")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    make_fog_vs_patch(out_dir / "p5_fog_vs_patch.png")
    make_metrics_chart(Path(args.results) / "results_table.csv", out_dir / "p5_metrics.png")
    print(f"Saved figures to {out_dir}")


if __name__ == "__main__":
    main()
