"""Person 4's package: signed records, hash chain, Merkle, offline HTML report, QR.

Person 4 owns `render_report(out_dir) -> Path` and the signed record format in
`contracts/RECORD.md`. The pipeline calls the report renderer through a
missing-import check, and the audit chain through
`cvassure.core.audit.make_chain`, so neither blocks Person 1's spine.
"""

from __future__ import annotations
