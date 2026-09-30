"""Person 5's package: `build_demo_scenario(seed=42)`, drift vs manipulation, metrics.

`contracts/MANIFEST.md` is Person 5's contract. The audit pipeline must **never**
import the ground-truth manifest; only coverage and evaluation code may.

If Person 5 lands a chain backend at `cvassure.shift.p4chain:P4Chain`,
`cvassure.core.audit.make_chain` picks it up automatically and the audit log
becomes signed. Person 1 does not implement that adapter ahead of time, because
guessing an interface is how two people build two different chains.
"""

from __future__ import annotations
