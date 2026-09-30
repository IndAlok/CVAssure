"""Nightly demo. Regenerate seed 42, audit it, and check the demo still works.

    python scripts/nightly_demo.py --out out

Checks:

* the audit exits 0
* the chain verifies
* a LINK is present, and the contributor it names comes from the scenario
  builder, not from a hard-coded id in the pipeline
* two record rejections
* both shift verdicts, one of them drift

Once the real detectors land, add `--strict`: it exits 5 while any stub still
runs, so this script fails on a stub left in place by accident.

Also writes `out/runtime.json`, the median of at least five runs plus the
hardware. A single run is not a runtime claim.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

from cvassure.core.audit import verify_file  # noqa: E402
from fixtures.synthetic_scenario import build_all  # noqa: E402

MIN_RUNS = 5


def _hardware() -> dict[str, object]:
    import os

    return {
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "cpu": platform.processor() or "unknown",
        "cpu_cores": os.cpu_count(),
        "ram_gb": round(_ram_gb(), 1),
        "python": platform.python_version(),
        "gpu": "none (CPU-only by design)",
    }


def _ram_gb() -> float:
    try:
        pages = __import__("ctypes").windll.kernel32.GlobalMemoryStatusEx  # Windows
    except AttributeError:
        try:
            return int(open("/proc/meminfo").readline().split()[1]) / (
                1024 * 1024
            )  # Linux fallback
        except Exception:
            return 0.0
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(stat)
    pages(ctypes.byref(stat))
    return stat.ullTotalPhys / (1024**3)


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "cvassure.core.cli", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--runs", type=int, default=MIN_RUNS)
    ap.add_argument("--strict", action="store_true", help="fail if any stub ran")
    args = ap.parse_args()

    work = REPO / ".demo_scratch"
    paths = build_all(work)
    out = (REPO / args.out).resolve()

    cmd = [
        "audit",
        "--data",
        str(paths["data"]),
        "--model",
        str(paths["model"]),
        "--records",
        str(paths["records"]),
        "--out",
        str(out),
        "--config",
        str(REPO / "configs" / "demo.yaml"),
        "--coverage-rules",
        str(REPO / "configs" / "coverage_rules.yaml"),
        "--seed",
        "42",
        "--plain",
        "--reproducible",
    ]
    if args.strict:
        cmd.append("--strict")

    durations: list[float] = []
    last = None
    for i in range(max(1, args.runs)):
        t0 = time.perf_counter()
        last = _cli(*cmd)
        durations.append(time.perf_counter() - t0)
        if last.returncode not in (0, 5):
            print(f"run {i + 1}: exit {last.returncode}", file=sys.stderr)
            print(last.stdout[-4000:], file=sys.stderr)
            print(last.stderr[-4000:], file=sys.stderr)
            return 1

    assert last is not None
    expected = 5 if args.strict else 0
    if last.returncode != expected:
        print(
            f"exit {last.returncode}, expected {expected}. "
            f"{'A stub ran under --strict.' if args.strict else 'Internal error.'}",
            file=sys.stderr,
        )
        return 1

    failures: list[str] = []

    findings = json.loads((out / "findings.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))

    # The contributor id comes from the scenario builder, not from this script.
    poisoned = __import__("fixtures.synthetic_scenario", fromlist=["x"]).POISONED_CONTRIBUTOR

    data_f = [f for f in findings if f["asset"] == "data" and f.get("source_id")]
    if not data_f:
        failures.append("no data finding with a source_id")
    else:
        top = sorted(data_f, key=lambda f: (-f["severity"], f["id"]))[0]
        if top["source_id"] != poisoned:
            failures.append(f"top source {top['source_id']!r}, builder says {poisoned!r}")

    model_f = [f for f in findings if f["asset"] == "model"]
    if not model_f:
        failures.append("no model finding: the LINK line cannot exist without one")
    elif not model_f[0].get("linked_findings"):
        failures.append("model finding did not link to the data patch")

    rejected = [f for f in findings if f["disposition"] == "rejected"]
    if len(rejected) != 2:
        failures.append(f"{len(rejected)} rejected records, expected 2")

    verdicts = {
        f["batch_id"]: ("manipulation" if "manipulation" in f["tags"] else "drift")
        for f in findings
        if f["asset"] == "shift"
    }
    if set(verdicts.values()) != {"drift", "manipulation"}:
        failures.append(f"shift verdicts {verdicts}, expected one drift and one manipulation")

    verification = verify_file(out / "audit.log", expected_head=manifest.get("audit_head"))
    if not verification.ok:
        failures.append(f"audit chain did not verify: {verification.reason}")

    if failures:
        print("nightly demo FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    runtime = {
        "n_runs": len(durations),
        "median_s": round(statistics.median(durations), 3),
        "min_s": round(min(durations), 3),
        "max_s": round(max(durations), 3),
        "all_s": [round(d, 3) for d in durations],
        "command": "cvassure " + " ".join(cmd),
        "offline": True,
        "hardware": _hardware(),
        "note": (
            "Wall clock of the command, which includes process start. A median of "
            f"{len(durations)} runs; one run is not a runtime claim."
        ),
    }
    (out / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")

    print("nightly demo OK")
    print(last.stdout.strip())
    print(
        f"\nruntime: median {runtime['median_s']}s "
        f"(min {runtime['min_s']}, max {runtime['max_s']}, n={runtime['n_runs']})"
    )
    print(f"written: {out}/runtime.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
