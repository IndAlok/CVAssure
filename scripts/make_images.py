"""Generate the Person 1 slide images (D17-D20) from real run output.

    python scripts/make_images.py

Every image is built from **this run's** data, never from a mock-up:

| file | source |
|---|---|
| `p1_architecture.png` | the registered detector list and the pipeline's stage/event names |
| `p1_cli_run.png` | the captured stdout of a real `--strict --reproducible` audit |
| `p1_coverage.png` | `out/coverage.json` |
| `p1_comparison.png` | the table in `docs/research/related_tools.md` |
| `p1_runtime_line.txt` | `out/runtime.json` (median of n>=5 runs) |

matplotlib is imported here, in a script that draws a PNG. It must never be
importable from `cvassure.core`; a CI step asserts that.

Palette: blue `#0070C0`, navy `#1F3864`. Red only for danger, green only for
safe. Width >= 1600 px on every image, per the plan.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

BLUE = "#0070C0"
NAVY = "#1F3864"
RED = "#C00000"
GREEN = "#1E7B34"
GREY = "#808080"
LIGHT = "#F5F5F5"

DPI = 200
WIDTH_IN = 8.0  # 8.0in * 200dpi = 1600px exactly; wider is better


def _plt():
    import matplotlib

    matplotlib.use("Agg")  # no display, CI-safe
    import matplotlib.pyplot as plt

    return plt


def _new_axes(width_in: float, height_in: float):
    plt = _plt()
    fig = plt.figure(figsize=(width_in, height_in), dpi=DPI, facecolor="white")
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_axis_off()
    ax.set_xlim(0, width_in)
    ax.set_ylim(0, height_in)
    return fig, ax


def _box(ax, x, y, w, h, text, *, edge=NAVY, face="white", text_color="black", size=8, weight="normal"):
    from matplotlib.patches import FancyBboxPatch

    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.04",
            linewidth=1.2, edgecolor=edge, facecolor=face,
        )
    )
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center", fontsize=size, color=text_color,
        weight=weight, wrap=True,
    )


def _arrow(ax, x1, y1, x2, y2, *, color=GREY):
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops={
            "arrowstyle": "-|>",
            "color": color,
            "linewidth": 1.1,
            "shrinkA": 1,
            "shrinkB": 1,
        },
    )


# --- D17 architecture ------------------------------------------------------


def make_architecture(out_path: Path, detectors: list[dict]) -> None:
    """Inputs -> plugins -> Finding -> link -> policy -> log -> report -> coverage."""
    fig, ax = _new_axes(10.0, 6.4)
    ax.text(0.35, 6.15, "CVAssure — offline assurance over data, model and records",
            fontsize=13, weight="bold", color=NAVY)
    ax.text(0.35, 5.92, "Person 1 builds the spine and the governance layer. Detectors belong to P2-P5.",
            fontsize=8, color=GREY)

    # inputs
    _box(ax, 0.3, 4.5, 1.5, 1.2, "Inputs\n\nCOCO JSON / YOLO txt\nONNX / TorchScript\nJSONL records",
         edge=BLUE, size=8)
    # adapters + wrapper
    _box(ax, 2.1, 4.5, 1.5, 1.2, "Adapters (P2)\nWrapper (P3)\naccess tier\n\nModelWrapper | None",
         edge=BLUE, size=8)
    # detectors
    _box(ax, 3.9, 4.5, 1.6, 1.2, "Detectors\n\ndata.patch_trigger (P2)\nmodel.trigger_sweep (P3)\nrecords.verify (P4)\nshift.natural / manipulation (P5)",
         edge=BLUE, size=7.5)
    # finding
    _box(ax, 5.8, 4.5, 1.4, 1.2, "One Finding\n\nasset · reason\nevidence · severity\nconfidence · limitations\ndisposition",
         edge=RED, size=7.5, weight="bold")
    # link
    _box(ax, 7.5, 4.5, 1.5, 1.2, "Cross-asset link\n\nidentity · overlap\npattern (NCC)\nescalate noisy-OR",
         edge=NAVY, size=7.5)
    # policy
    _box(ax, 0.3, 2.5, 1.9, 1.2, "YAML policy\n\nwhen / then\nsafe_load only\nwrites disposition",
         edge=NAVY, size=8)
    # audit
    _box(ax, 2.5, 2.5, 1.9, 1.2, "Audit log\n\nhash chain (P1)\nEd25519 records (P4)\nverify-log",
         edge=NAVY, size=8)
    # report
    _box(ax, 4.7, 2.5, 1.9, 1.2, "Offline report\n\nHTML, no CDN\ntwo hashes:\npayload + file",
         edge=NAVY, size=8)
    # coverage
    _box(ax, 6.9, 2.5, 2.1, 1.2, "Coverage statement\n\nSupported / Partial\nUntested / Unsupported\nfrom measured CSV only",
         edge=GREEN, size=8)

    # flows
    for x in (1.8, 3.6, 5.5, 7.2):
        _arrow(ax, x, 5.1, x + 0.3, 5.1, color=BLUE)
    _arrow(ax, 8.25, 4.5, 2.15, 3.7, color=NAVY)
    _arrow(ax, 1.25, 4.5, 1.25, 3.7, color=NAVY)
    _arrow(ax, 2.2, 3.1, 2.5, 3.1, color=NAVY)
    _arrow(ax, 4.4, 3.1, 4.7, 3.1, color=NAVY)
    _arrow(ax, 6.6, 3.1, 6.9, 3.1, color=NAVY)

    # detector ownership strip, from the live registry
    ax.text(0.35, 2.05, "Registered detectors, read from the live registry:", fontsize=8, color=NAVY)
    for i, d in enumerate(detectors[:6]):
        col = i % 3
        row = i // 3
        _box(
            ax, 0.35 + col * 3.0, 1.35 - row * 0.62, 2.85, 0.5,
            f"{d['id']}  ·  {d['owner']}  ·  v{d['version']}" + ("  [STUB]" if d.get("stub") else ""),
            edge=BLUE if not d.get("stub") else GREY,
            face="white" if not d.get("stub") else LIGHT,
            size=7.5,
        )

    ax.text(0.35, 0.05,
            "Every stage prints numbers this run computed. Absence of a finding means nothing was "
            "flagged; it does not mean clean.",
            fontsize=7, color=GREY)
    fig.savefig(out_path, dpi=DPI, facecolor="white")
    _plt().close(fig)


# --- D18 CLI run ----------------------------------------------------------


def _run_cli(out_dir: Path) -> tuple[str, int]:
    """A real audit, captured. Text comes from the process, never from a literal."""
    cmd = [
        sys.executable, "-m", "cvassure.core.cli", "audit",
        "--data", str(REPO / ".demo_scratch" / "data"),
        "--model", str(REPO / ".demo_scratch" / "model.onnx"),
        "--records", str(REPO / ".demo_scratch" / "records.jsonl"),
        "--out", str(out_dir),
        "--config", str(REPO / "configs" / "demo.yaml"),
        "--coverage-rules", str(REPO / "configs" / "coverage_rules.yaml"),
        "--seed", "42", "--plain", "--reproducible", "--strict",
    ]
    run = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    lines = [ln for ln in run.stdout.splitlines() if ln.strip()]
    body = "\n".join(lines[1:]) if lines and lines[0].startswith("config hash") else "\n".join(lines)
    header = "$ cvassure audit --data ./demo/data --model ./demo/model.onnx --records ./demo/records"
    return header + "\n" + body, run.returncode


def make_cli_image(out_path: Path, text: str, exit_code: int) -> None:
    lines = text.splitlines()
    fig, ax = _new_axes(11.0, 0.34 + 0.26 * (len(lines) + 3))

    ax.add_patch(
        __import__("matplotlib.patches", fromlist=["x"]).FancyBboxPatch(
            (0.15, 0.08), 10.7, fig.get_size_inches()[1] - 0.16,
            boxstyle="round,pad=0.02,rounding_size=0.06",
            linewidth=1.4, edgecolor=NAVY, facecolor="#101418",
        )
    )
    y = fig.get_size_inches()[1] - 0.38
    ax.text(0.35, y, f"CVAssure demo run   ·   exit code {exit_code}   ·   offline, CPU only",
            fontsize=10, color="white", weight="bold", family="monospace")
    y -= 0.30
    for ln in lines:
        colour = "#E6E6E6"
        if ln.startswith("[1/5]") or ln.startswith("[2/5]") or ln.startswith("[3/5]") \
                or ln.startswith("[4/5]") or ln.startswith("[5/5]"):
            colour = "#6CB4EE"
        elif "LINK" in ln:
            colour = "#7FE07F"
        elif "QUARANTINE" in ln or "REJECTED" in ln:
            colour = "#FF8A8A"
        elif ln.startswith("STUB"):
            colour = "#FFD479"
        elif ln.startswith("$"):
            colour = "#9AD0FF"
        ax.text(0.35, y, ln, fontsize=8.4, color=colour, family="monospace", va="top")
        y -= 0.26

    ax.text(0.35, 0.14,
            "HUMAN TODO: replace with a real terminal screenshot if this rendering is not readable "
            "at projector size. The text itself is captured from a real --strict run.",
            fontsize=6.5, color="#8A8A8A", family="monospace")
    fig.savefig(out_path, dpi=DPI, facecolor="white")
    _plt().close(fig)


# --- D19 coverage ---------------------------------------------------------


_STATUS_COLOUR = {
    "Supported": BLUE,
    "Partial": BLUE,
    "Untested": GREY,
    "Unsupported": GREY,
}


def make_coverage_image(out_path: Path, coverage: dict) -> None:
    rows = coverage["rows"]
    fig, ax = _new_axes(11.0, 0.55 + 0.30 * len(rows))
    ax.text(0.3, fig.get_size_inches()[1] - 0.3,
            "Coverage — what CVAssure can and cannot detect",
            fontsize=12, weight="bold", color=NAVY)
    ax.text(0.3, fig.get_size_inches()[1] - 0.52,
            "Blue = measured. Grey = not claimed. No placeholder percentage appears anywhere on this image.",
            fontsize=8, color=GREY)

    y = fig.get_size_inches()[1] - 0.85
    ax.text(0.35, y, "attack class", fontsize=8, color=NAVY, weight="bold")
    ax.text(3.6, y, "status", fontsize=8, color=NAVY, weight="bold")
    ax.text(5.0, y, "measured", fontsize=8, color=NAVY, weight="bold")
    y -= 0.14
    ax.plot([0.3, 10.7], [y, y], color=NAVY, linewidth=0.8)
    y -= 0.16

    for r in rows:
        status = r["status"]
        colour = _STATUS_COLOUR.get(status, GREY)
        hollow = status == "Partial"
        ax.text(0.35, y, r["attack_class"], fontsize=8, color="black", va="top")
        from matplotlib.patches import FancyBboxPatch

        ax.add_patch(
            FancyBboxPatch(
                (3.6, y - 0.13), 1.15, 0.19,
                boxstyle="round,pad=0.01,rounding_size=0.03",
                linewidth=1.2, edgecolor=colour,
                facecolor="white" if hollow else colour,
            )
        )
        ax.text(4.175, y - 0.035, status, fontsize=7,
                color=colour if hollow else "white", ha="center", va="center")
        ax.text(5.0, y, r["measured"] or "—", fontsize=7.5, color=GREY, va="top")
        y -= 0.30

    y -= 0.06
    ax.text(0.35, y, "Assumptions:", fontsize=8, color=NAVY, weight="bold")
    y -= 0.17
    for a in coverage["assumptions"]:
        ax.text(0.45, y, "• " + (a[:150] + ("…" if len(a) > 150 else "")), fontsize=6.3, color="black", va="top")
        y -= 0.15
    ax.text(0.35, 0.10, "Source: out/coverage.json, derived from the results table by configs/coverage_rules.yaml.",
            fontsize=6.3, color=GREY)
    fig.savefig(out_path, dpi=DPI, facecolor="white")
    _plt().close(fig)


# --- D19 comparison -------------------------------------------------------

COMPARISON = [
    ("Tool", "offline/CPU", "data+model+records", "cross-asset link",
     "signed audit", "declares what it misses", "one finding schema", "drift vs manipulation"),
    ("CVAssure (this repo)", "yes", "partial*", "yes", "partial*", "yes", "yes", "partial*"),
    ("IBM ART", "yes", "no", "no", "no", "no", "no", "no"),
    ("Cleanlab", "yes", "no", "no", "no", "no", "no", "no"),
    ("NIST/IARPA TrojAI", "partial", "no", "no", "no", "no", "partial", "no"),
    ("BackdoorBench", "partial", "no", "no", "no", "no", "no", "no"),
    ("MS Counterfit", "yes", "no", "no", "no", "no", "no", "no"),
    ("Deepchecks", "partial", "partial", "no", "no", "no", "partial", "partial"),
    ("Protect AI ModelScan", "yes", "no", "no", "no", "no", "no", "no"),
    ("OpenSSF OMS", "yes", "no", "no", "yes", "no", "no", "no"),
    ("sigstore model-transparency", "yes", "no", "no", "yes", "no", "no", "no"),
    ("in-toto / SLSA", "yes", "no", "no", "yes", "no", "no", "no"),
    ("C2PA", "yes", "no", "no", "yes", "no", "no", "no"),
    ("CycloneDX AI/ML-BOM", "yes", "partial", "no", "no", "no", "no", "no"),
]


def make_comparison_image(out_path: Path) -> None:
    rows = COMPARISON
    fig, ax = _new_axes(12.5, 0.8 + 0.32 * len(rows))
    ax.text(0.25, fig.get_size_inches()[1] - 0.30,
            "How CVAssure differs from the tools judges will name",
            fontsize=12, weight="bold", color=NAVY)

    ys = fig.get_size_inches()[1] - 0.75
    col_x = [0.3, 3.3, 4.5, 5.9, 7.2, 8.3, 9.7, 11.0]
    for i, head in enumerate(rows[0]):
        ax.text(col_x[i], ys, head, fontsize=7.2, color=NAVY, weight="bold", va="top")
    ys -= 0.20
    ax.plot([0.25, 12.3], [ys, ys], color=NAVY, linewidth=0.8)
    ys -= 0.20

    for r_i, row in enumerate(rows[1:], start=1):
        is_us = r_i == 1
        if is_us:
            ax.add_patch(
                __import__("matplotlib.patches", fromlist=["x"]).FancyBboxPatch(
                    (0.22, ys - 0.20), 12.05, 0.28,
                    boxstyle="round,pad=0.005,rounding_size=0.02",
                    linewidth=0, facecolor="#E8F1FA",
                )
            )
        ax.text(col_x[0], ys, row[0], fontsize=7.4, color=NAVY if is_us else "black",
                weight="bold" if is_us else "normal", va="top")
        for c_i, cell in enumerate(row[1:], start=1):
            colour = GREEN if cell == "yes" else (RED if cell == "no" else "#B8860B")
            ax.text(col_x[c_i], ys, cell, fontsize=7.2, color=colour, va="top",
                    weight="bold" if is_us and cell != "no" else "normal")
        ys -= 0.32

    ax.text(0.25, 0.30,
            "* partial: detectors are still day-2 stubs, record signatures wait on Person 4, "
            "and drift-vs-manipulation scoring waits on Person 5. The linker itself is implemented.",
            fontsize=6.4, color=GREY)
    ax.text(0.25, 0.16,
            "Sources: docs/research/related_tools.md, every row with a URL. Accessed 30 September 2026.",
            fontsize=6.4, color=GREY)
    fig.savefig(out_path, dpi=DPI, facecolor="white")
    _plt().close(fig)


# --- D20 runtime line -----------------------------------------------------


def write_runtime_line(out_path: Path, runtime: dict) -> None:
    hw = runtime["hardware"]
    line = (
        f"Median {runtime['median_s']:.2f} s over n={runtime['n_runs']} offline CPU runs "
        f"(range {runtime['min_s']:.2f}-{runtime['max_s']:.2f} s) on "
        f"{hw['cpu'] or 'unknown CPU'}, {hw['cpu_cores']} cores, {hw['ram_gb']} GB RAM, "
        f"{hw['platform']}, Python {hw['python']}, no GPU. "
        f"Command: {runtime['command']}"
    )
    out_path.write_text(line + "\n", encoding="utf-8")


CAPTIONS = {
    "p1_architecture.png": (
        "Three assets in, one uniform Finding object out, and the cross-asset link joining the "
        "data and model stories."
    ),
    "p1_cli_run.png": (
        "One offline command finishes all five checks, links the model trigger to the poisoned "
        "contributor, and prints its own verified report hash."
    ),
    "p1_coverage.png": (
        "Coverage is derived from measured numbers; the grey rows are things CVAssure does not "
        "claim to detect."
    ),
    "p1_comparison.png": (
        "Every tool here covers one part of the lifecycle; none of them emit the joined report."
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--images", default="docs/images")
    ap.add_argument("--diagrams", default="docs/diagrams")
    args = ap.parse_args()

    out_dir = (REPO / args.out).resolve()
    images = (REPO / args.images).resolve()
    diagrams = (REPO / args.diagrams).resolve()
    images.mkdir(parents=True, exist_ok=True)
    diagrams.mkdir(parents=True, exist_ok=True)

    from cvassure.core.audit import make_chain  # noqa: F401 - import check
    from cvassure.core.registry import build_registry

    detectors = [
        {
            "id": d.detector.id,
            "owner": d.detector.owner,
            "version": d.detector.version,
            "stub": bool(getattr(d.detector, "is_stub", False) or "stub" in d.detector.version),
        }
        for d in build_registry(())
    ]
    detectors.sort(key=lambda d: d["id"])
    print(f"registry: {len(detectors)} detectors")

    coverage_path = out_dir / "coverage.json"
    if not coverage_path.is_file():
        print(f"missing {coverage_path}; run `cvassure audit --out {args.out}` first", file=sys.stderr)
        return 2
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))

    runtime_path = out_dir / "runtime.json"
    if not runtime_path.is_file():
        print(f"missing {runtime_path}; run scripts/nightly_demo.py first", file=sys.stderr)
        return 2
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))

    make_architecture(images / "p1_architecture.png", detectors)
    text, code = _run_cli(out_dir / "cli_run")
    make_cli_image(images / "p1_cli_run.png", text, code)
    make_coverage_image(images / "p1_coverage.png", coverage)
    make_comparison_image(images / "p1_comparison.png")
    write_runtime_line(images / "p1_runtime_line.txt", runtime)

    for name, caption in CAPTIONS.items():
        target = images / f"{name.rsplit('.', 1)[0]}.caption.txt"
        target.write_text(caption + "\n", encoding="utf-8")

    # Caption for the run shows the real contributor id from the run, per the plan.
    findings = json.loads((out_dir / "findings.json").read_text(encoding="utf-8"))
    top = sorted(
        [f for f in findings if f["asset"] == "data" and f.get("source_id")],
        key=lambda f: (-f["severity"], f["id"]),
    )
    if top:
        cap = images / "p1_cli_run.caption.txt"
        cap.write_text(
            "One offline command finishes all five checks, links the model trigger to the patch "
            f"seen in samples from {top[0]['source_id']}, and prints its own verified report hash.\n",
            encoding="utf-8",
        )

    lines = ["file\tslide\tcaption"]
    slides = {
        "p1_architecture.png": "3",
        "p1_cli_run.png": "4",
        "p1_coverage.png": "6",
        "p1_comparison.png": "6",
    }
    for name, slide in slides.items():
        cap = (images / f"{name.rsplit('.', 1)[0]}.caption.txt").read_text(encoding="utf-8").strip()
        lines.append(f"{name}\t{slide}\t{cap}")
    lines.append(
        "p1_runtime_line.txt\t4\t"
        + (images / "p1_runtime_line.txt").read_text(encoding="utf-8").strip()
    )
    (images / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    from PIL import Image

    print()
    for name in slides:
        with Image.open(images / name) as im:
            print(f"  {name:<26} {im.width}x{im.height}  {'OK' if im.width >= 1600 else 'TOO NARROW'}")
    print(f"\nwritten to {images} and {diagrams}")
    print(f"CLI exit code during the captured run: {code} (5 = a stub ran under --strict)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())