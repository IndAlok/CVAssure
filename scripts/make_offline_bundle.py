"""Build the offline install bundle (D15).

Air-gapped machines cannot reach PyPI. Build a wheelhouse once on a machine that
can, copy the whole repo across, and install with no index:

    python scripts/make_offline_bundle.py --out wheelhouse
    # then, on the offline machine:
    python -m pip install --no-index --find-links wheelhouse -e .

`wheelhouse/` is gitignored on purpose: it is a few tens of megabytes of binaries
and it belongs in the hand-over medium (USB, internal share), not in git history.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTALL_ONE_LINER = 'python -m pip install --no-index --find-links wheelhouse -e ".[dev]"'
INSTALL_DOC = "docs/p1/HANDOVER.md"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="wheelhouse")
    ap.add_argument(
        "--with-dev",
        action="store_true",
        help="include pytest/ruff as well; the demo does not need them",
    )
    args = ap.parse_args()

    target = (REPO / args.out).resolve()
    target.mkdir(parents=True, exist_ok=True)

    spec = ".[dev]" if args.with_dev else "."
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--dest",
        str(target),
        spec,
    ]
    # Local dependencies only: a source wheel for this package would need the
    # index again on the offline machine, and `-e .` installs from the checkout.
    cmd.append("--only-binary=:all:")

    print("$ " + " ".join(cmd))
    run = subprocess.run(cmd, cwd=REPO)
    if run.returncode != 0:
        print(
            "\npip download failed. If it blames --only-binary, a dependency ships "
            "as sdist only; drop that flag and expect to build it offline.",
            file=sys.stderr,
        )
        return run.returncode

    wheels = sorted(target.glob("*.whl"))
    print(f"\n{len(wheels)} wheels in {target}")
    for w in wheels[:5]:
        print(f"  {w.name}")
    if len(wheels) > 5:
        print(f"  ... and {len(wheels) - 5} more")

    print(f"\nCopy the repo and {args.out}/ to the offline machine, then:\n")
    print(f"  {INSTALL_ONE_LINER}\n")
    print(f"That one-liner is also documented in {INSTALL_DOC}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
