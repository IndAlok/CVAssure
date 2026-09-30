"""Make `tests/` importable so `from fixtures...` and `from cvassure...` work.

Two lines of path juggling, rather than installing the test helpers as a package
just to make imports work. A `conftest.py` in the tests root is picked up
automatically, so no PYTHONPATH needs setting.
"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent

for p in (REPO, TESTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
