"""Manual smoke run of the day-2 stub pipeline. Not part of pytest.

Builds the synthetic scenario, runs the audit, prints the terminal output, then
verifies the two hashes and the chain. Use it when you want to *see* the run:

    python scripts/smoke_demo.py [--out out_demo]

pytest covers the same ground with assertions; this exists so a human can watch
the CLI print and know the demo will look right.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

from fixtures.synthetic_scenario import build_all  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out_demo", help="output directory")
    args = ap.parse_args()

    work = REPO / ".demo_scratch"
    paths = build_all(work)
    out = REPO / args.out

    cmd = [
        sys.executable,
        "-m",
        "cvassure.core.cli",
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
        "--plain",
    ]
    print("$ " + " ".join(cmd[2:]), "\n")
    run = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    print(run.stdout)
    if run.stderr:
        print(run.stderr, file=sys.stderr)
    print(f"exit code: {run.returncode}  (5 = a stub ran under --strict, 0 = clean)\n")

    for sub in ("verify-log", "verify-report"):
        v = subprocess.run(
            [
                sys.executable,
                "-m",
                "cvassure.core.cli",
                sub,
                str(out / ("audit.log" if sub == "verify-log" else "report.html")),
                *(["--manifest", str(out / "run_manifest.json")] if sub == "verify-log" else []),
                *(["--out", str(out)] if sub == "verify-report" else []),
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        print(f"$ cvassure {sub}\n{v.stdout.strip()}\n  exit {v.returncode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
