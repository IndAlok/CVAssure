"""Weight digest verification detector.

Compares the model file's SHA-256 digest against a signed reference
file. Emits a ``weight_digest_mismatch`` finding when they differ.
"""

from __future__ import annotations

from typing import ClassVar

from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.finding import Finding


class WeightDigestDetector(Detector):
    """Verify the model's weight digest against a reference file.

    The reference file is a text file containing the expected SHA-256
    hex digest. It is looked up next to the model file with the
    pattern ``<model_path>.digest.txt``.
    """

    id: ClassVar[str] = "model.weight_digest"
    asset: ClassVar[str] = "model"
    owner: ClassVar[str] = "model"
    version: ClassVar[str] = "0.1.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        res = DetectorResult()
        if ctx.model is None:
            res.status = "skipped"
            res.skipped_reason = "no model wrapper is loaded"
            return res

        model_path = ctx.model.model_path
        digest_path = model_path.with_suffix(model_path.suffix + ".digest.txt")

        if not digest_path.is_file():
            res.status = "skipped"
            res.skipped_reason = f"no digest reference file found at {digest_path.name}"
            res.summary = "no digest reference"
            return res

        try:
            expected = digest_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            res.status = "skipped"
            res.skipped_reason = f"cannot read digest reference: {exc}"
            return res

        actual = ctx.model.weight_digest()

        if actual == expected:
            res.summary = "weight digest matches reference"
            return res

        res.findings.append(
            Finding.draft(
                asset="model",
                reason=(
                    f"Model weight digest {actual[:12]}... does not match "
                    f"reference {expected[:12]}... — model file has been modified"
                ),
                evidence=[],
                severity=0.95,
                confidence=0.99,
                access_level="not-applicable",
                limitations=(
                    "A weight digest mismatch proves the file changed, not how. "
                    "A compromised signing key or an honest re-export with different "
                    "serialization can also cause a mismatch."
                ),
                disposition="review",
                tags=["weight_digest_mismatch"],
                metadata={
                    "expected_digest": expected,
                    "actual_digest": actual,
                    "digest_file": digest_path.name,
                },
            )
        )
        res.summary = "weight digest MISMATCH"
        return res
