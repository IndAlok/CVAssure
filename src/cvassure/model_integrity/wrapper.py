"""Model wrapper (P3's contract, `contracts/MODEL_WRAPPER.md`). Person 3 owns this.

**This file is a day-2 stub.** Person 3 replaces it. It exists because the model
stage and the cross-asset link are Person 1's spine, and the spine cannot be
validated end to end while `_load_model` has nothing to import. Without it the
pipeline would honestly report `BLOCKED-ON: P3` and the LINK line could never be
tested before day 4.

What is **real** here:

* `weight_digest()` — a genuine streamed sha256 of the model file. This one is not
  a fixture and it is the same implementation the substitution check will use.
* the access-tier plumbing — `declare_access_tier()` and `capabilities()` derive
  from the requested tier exactly as the contract describes, so the pipeline's
  access rule and its skip path are exercised for real.

What is **not** real, and says so:

* no ONNX session or TorchScript module is opened, so there is no forward pass,
  no activations and no gradients. `predict`, `features` and `gradients` return
  `Unavailable`, never a zero-filled array. A zero array would produce a
  real-looking trigger score of exactly nothing, and a "clean" verdict that was
  never computed is the worst possible output for an integrity tool.

`is_stub` is exposed so the audit can record that a stub wrapper ran. Person 3
deletes that attribute along with the rest of the stub.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cvassure.core.detector import AccessTier, Capability
from cvassure.core.hashing import file_sha256

#: Which capabilities each declared tier implies, per `contracts/MODEL_WRAPPER.md`.
#: The contract's table, written once, in the place that has to honour it.
CAPABILITIES_BY_TIER: dict[str, frozenset[str]] = {
    "white-box": frozenset({"weights", "gradients", "activations", "logits", "query_only"}),
    "gray-box": frozenset({"weights", "activations", "logits", "query_only"}),
    "black-box": frozenset({"logits", "query_only"}),
    "not-applicable": frozenset(),
}


@dataclass(frozen=True)
class Unavailable:
    """A capability the tier does not provide. Falsy, never an exception.

    `if not g:` is the correct caller pattern; `np.asarray(g)` is the bug this
    type exists to prevent.
    """

    reason: str

    def __bool__(self) -> bool:
        return False


class CvModelWrapper:
    """Tier declaration, honest capabilities, and a real file digest."""

    #: Person 3 removes this when the real loader lands.
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

        The stub cannot verify a tier it never opened, so it reports what it was
        asked for and flags itself as a stub. Person 3's loader is the thing that
        can honestly downgrade a declared tier.
        """
        return self._tier

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(CAPABILITIES_BY_TIER[self._tier])  # type: ignore[return-value]

    def weight_digest(self) -> str:
        """Real sha256 of the model file bytes. Not a fixture value."""
        return self._digest

    def predict(self, batch: Any) -> Unavailable:
        return Unavailable("STUB wrapper opens no session; there is no forward pass")

    def features(self, batch: Any) -> Unavailable:
        return Unavailable("STUB wrapper opens no session; there are no activations")

    def gradients(self, batch: Any) -> Unavailable:
        return Unavailable("STUB wrapper opens no session; there are no gradients")


def load_model(path: Path, *, access: str = "white-box") -> CvModelWrapper:
    """Factory the pipeline calls. The only entry point it knows about."""
    return CvModelWrapper(path, access=access)  # type: ignore[arg-type]
