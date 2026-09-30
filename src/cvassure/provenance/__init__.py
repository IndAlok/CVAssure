"""Provenance, crypto, and dashboard — Person 4's package.

Provides:
  - ``chain.SignedChain``: Ed25519-signed audit-log chain.
    Picked up automatically by ``cvassure.core.audit.make_chain()`` when this
    package is importable. Replaces the unsigned ``LocalSha256Chain`` fallback.

  - ``report.render_report(out_dir) -> Path``: offline HTML dashboard with
    contributor heatmap, evidence gallery, shift timeline, findings table,
    quarantine export, QR code, and provenance panel.
    Picked up by ``cvassure.core.report.render_from_out_dir()``.

  - ``records``: signed inference records (sign, verify, detect_edit, detect_replay).
  - ``keys``: Ed25519 keypair generation and loading.
  - ``merkle``: RFC 6962-style Merkle tree over log entry hashes.
  - ``verify``: standalone verification and all-seven-attack tamper detection.
  - ``qr``: offline QR code renderer for payload_sha256.
"""

from __future__ import annotations
