"""Person 2's package: embeddings, label flip, near-duplicate, OOD, spectral, adapters.

Person 2 replaces `cvassure.core.adapters` (day-2 thin readers, documented in
`contracts/FINDING.md` section 6) with the full adapters, and registers detectors
under `data.*`. The day-2 detector stubs live in `cvassure.core.stubs` and are
removed automatically when a real module with the same id is registered.
"""

from __future__ import annotations
