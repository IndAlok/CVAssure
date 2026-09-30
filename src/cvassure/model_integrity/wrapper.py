"""Model wrapper.

This loader is a stub. Replace `load_model` with a loader that opens the model.

`weight_digest()` is a streamed SHA-256 of the model file. `declare_access_tier`
and `capabilities` follow the requested tier.

No ONNX session or TorchScript module is opened. There is no forward pass, no
activations, and no gradients. `predict`, `features`, and `gradients` return
`Unavailable`, never a zero-filled array.

`is_stub` is true so `--strict` can fail while this loader is in use.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cvassure.core.detector import AccessTier, Capability
from cvassure.core.hashing import file_sha256

#: Capabilities implied by each declared access tier.
CAPABILITIES_BY_TIER: dict[str, frozenset[str]] = {
    "white-box": frozenset({"weights", "gradients", "activations", "logits", "query_only"}),
    "gray-box": frozenset({"weights", "activations", "logits", "query_only"}),
    "black-box": frozenset({"logits", "query_only"}),
    "not-applicable": frozenset(),
}


@dataclass(frozen=True)
class Unavailable:
    """A capability the tier does not provide. Falsy, never an exception.

    Use `if not g:`. `np.asarray(g)` is the bug this
    type exists to prevent.
    """

    reason: str

    def __bool__(self) -> bool:
        return False


class CvModelWrapper:
    """Tier declaration, honest capabilities, and a real file digest."""

    is_stub = True

    def __init__(self, model_path: Path, *, access: AccessTier = "white-box") -> None:
        if access not in CAPABILITIES_BY_TIER:
            raise ValueError(f"unknown access tier {access!r}")
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"no such model file: {self.model_path}")
        self._tier: AccessTier = access
        # Computed once at construction, per the contract: the digest must be
        # deterministic and must not be recomputed mid-run.
        self._digest = file_sha256(self.model_path)

    def declare_access_tier(self) -> AccessTier:
        """The tier as declared on the CLI, not as verified by a loaded session.

        The stub does not open a session, so it reports the tier it was given.
        """
        return self._tier

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(CAPABILITIES_BY_TIER[self._tier])  # type: ignore[return-value]

    def weight_digest(self) -> str:
        """Real sha256 of the model file bytes. Not a fixture value."""
        return self._digest

    def predict(self, batch: Any) -> Unavailable:
        return Unavailable("STUB wrapper opens no session. There is no forward pass")

    def features(self, batch: Any) -> Unavailable:
        return Unavailable("STUB wrapper opens no session. There are no activations")

    def gradients(self, batch: Any) -> Unavailable:
        return Unavailable("STUB wrapper opens no session. There are no gradients")


def load_model(path: Path, *, access: str = "white-box") -> CvModelWrapper:
    """Factory the pipeline calls. The only entry point it knows about."""
    return CvModelWrapper(path, access=access)  # type: ignore[arg-type]
