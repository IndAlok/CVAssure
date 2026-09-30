"""Signed inference records, hash chain, and the HTML report.

Provide `render_report(out_dir) -> Path` in this package to replace the built-in
report. Provide `cvassure.provenance.chain.SignedChain` to sign the audit log.
"""

from __future__ import annotations
