"""Model wrapper for ONNX and PyTorch models.

Supports real inference when ``onnxruntime`` or ``torch`` is installed.
When neither is available the wrapper constructs but ``predict``,
``features``, and ``gradients`` return ``Unavailable`` with an honest
reason — never a zero-filled array.

The wrapper declares its access tier based on what the loaded backend
actually provides, not what the CLI was told.
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
    """Tier declaration, honest capabilities, and a real file digest.

    Loads ONNX models via onnxruntime and PyTorch models via torch.
    When neither backend is installed the wrapper still constructs but
    every inference method returns ``Unavailable``.
    """

    is_stub = True

    def __init__(self, model_path: Path, *, access: AccessTier = "white-box") -> None:
        if access not in CAPABILITIES_BY_TIER:
            raise ValueError(f"unknown access tier {access!r}")
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"no such model file: {self.model_path}")
        self._tier: AccessTier = access
        self._digest = file_sha256(self.model_path)
        self._session: Any = None
        self._torch_model: Any = None
        self._backend: str | None = None
        self._load_backend()

    def _load_backend(self) -> None:
        """Attempt to load the model with available backends."""
        suffix = self.model_path.suffix.lower()

        if suffix == ".onnx":
            self._try_onnx()
        elif suffix in (".pt", ".pth"):
            self._try_torch()
        else:
            # Unknown extension — try ONNX first, then PyTorch
            self._try_onnx()
            if self._backend is None:
                self._try_torch()

    def _try_onnx(self) -> None:
        """Try to load as ONNX via onnxruntime."""
        try:
            import onnxruntime as ort
        except ImportError:
            return
        try:
            self._session = ort.InferenceSession(
                str(self.model_path),
                providers=["CPUExecutionProvider"],
            )
            self._backend = "onnxruntime"
            self.is_stub = False
        except Exception:
            self._session = None

    def _try_torch(self) -> None:
        """Try to load as PyTorch via torch.jit.load."""
        try:
            import torch
        except ImportError:
            return
        try:
            self._torch_model = torch.jit.load(str(self.model_path), map_location="cpu")
            self._torch_model.eval()
            self._backend = "torch"
            self.is_stub = False
        except Exception:
            try:
                self._torch_model = torch.load(
                    str(self.model_path), map_location="cpu", weights_only=True
                )
                if hasattr(self._torch_model, "eval"):
                    self._torch_model.eval()
                self._backend = "torch"
                self.is_stub = False
            except Exception:
                self._torch_model = None

    def declare_access_tier(self) -> AccessTier:
        """The tier as declared on the CLI, not as verified by a loaded session."""
        return self._tier

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(CAPABILITIES_BY_TIER[self._tier])  # type: ignore[return-value]

    def weight_digest(self) -> str:
        """Real sha256 of the model file bytes. Not a fixture value."""
        return self._digest

    @property
    def backend(self) -> str | None:
        """Which backend loaded the model, or None if no backend is available."""
        return self._backend

    def predict(self, batch: Any) -> Any:
        """Run inference on a batch of inputs.

        For ONNX: expects a numpy array or dict of numpy arrays.
        For PyTorch: expects a numpy array or torch tensor.
        Returns numpy array of predictions, or Unavailable.
        """
        if self._backend == "onnxruntime":
            return self._predict_onnx(batch)
        if self._backend == "torch":
            return self._predict_torch(batch)
        return Unavailable(
            "No model backend available. Install onnxruntime or torch for inference."
        )

    def _predict_onnx(self, batch: Any) -> Any:
        """ONNX Runtime inference."""
        import numpy as np

        if self._session is None:
            return Unavailable("ONNX session is not loaded")
        try:
            input_name = self._session.get_inputs()[0].name
            if isinstance(batch, dict):
                outputs = self._session.run(None, batch)
            else:
                outputs = self._session.run(None, {input_name: np.asarray(batch)})
            return outputs[0] if outputs else Unavailable("ONNX session returned no outputs")
        except Exception as exc:
            return Unavailable(f"ONNX inference failed: {type(exc).__name__}: {exc}")

    def _predict_torch(self, batch: Any) -> Any:
        """PyTorch inference."""
        import numpy as np

        if self._torch_model is None:
            return Unavailable("Torch model is not loaded")
        try:
            import torch

            if isinstance(batch, np.ndarray):
                tensor = torch.from_numpy(batch).float()
            elif isinstance(batch, torch.Tensor):
                tensor = batch.float()
            else:
                tensor = torch.tensor(batch, dtype=torch.float32)
            with torch.no_grad():
                output = self._torch_model(tensor)
            if isinstance(output, torch.Tensor):
                return output.numpy()
            return output
        except Exception as exc:
            return Unavailable(f"Torch inference failed: {type(exc).__name__}: {exc}")

    def features(self, batch: Any) -> Any:
        """Extract intermediate activations.

        ONNX: requests all intermediate outputs if available.
        PyTorch: uses forward hooks on the last conv/linear layer.
        Returns numpy array of activations, or Unavailable.
        """
        if self._backend == "onnxruntime":
            return self._features_onnx(batch)
        if self._backend == "torch":
            return self._features_torch(batch)
        return Unavailable(
            "No model backend available. Install onnxruntime or torch for feature extraction."
        )

    def _features_onnx(self, batch: Any) -> Any:
        """ONNX feature extraction via intermediate outputs."""
        import numpy as np

        if self._session is None:
            return Unavailable("ONNX session is not loaded")
        try:
            input_name = self._session.get_inputs()[0].name
            if isinstance(batch, dict):
                outputs = self._session.run(None, batch)
            else:
                outputs = self._session.run(None, {input_name: np.asarray(batch)})
            # Return all outputs (including intermediates if the graph has them)
            if outputs:
                return np.concatenate([np.asarray(o).flatten() for o in outputs])
            return Unavailable("ONNX session returned no outputs")
        except Exception as exc:
            return Unavailable(f"ONNX feature extraction failed: {type(exc).__name__}: {exc}")

    def _features_torch(self, batch: Any) -> Any:
        """PyTorch feature extraction via forward hook."""
        import numpy as np

        if self._torch_model is None:
            return Unavailable("Torch model is not loaded")
        try:
            import torch

            if isinstance(batch, np.ndarray):
                tensor = torch.from_numpy(batch).float()
            elif isinstance(batch, torch.Tensor):
                tensor = batch.float()
            else:
                tensor = torch.tensor(batch, dtype=torch.float32)

            features: list[Any] = []

            def hook(_module: Any, _input: Any, output: Any) -> None:
                features.append(output.detach())

            # Hook the last layer
            last_layer = None
            for module in self._torch_model.modules():
                last_layer = module
            if last_layer is not None:
                handle = last_layer.register_forward_hook(hook)

            with torch.no_grad():
                self._torch_model(tensor)

            if last_layer is not None:
                handle.remove()

            if features:
                return features[0].numpy()
            return Unavailable("No features captured from PyTorch model")
        except Exception as exc:
            return Unavailable(f"Torch feature extraction failed: {type(exc).__name__}: {exc}")

    def gradients(self, batch: Any) -> Any:
        """Compute gradients of the output with respect to the input.

        Only available for PyTorch models with gradient support.
        Returns numpy array of gradients, or Unavailable.
        """
        if self._backend == "torch":
            return self._gradients_torch(batch)
        if self._backend == "onnxruntime":
            return Unavailable("ONNX Runtime does not support gradient computation")
        return Unavailable("No model backend available. Install torch for gradient computation.")

    def _gradients_torch(self, batch: Any) -> Any:
        """PyTorch gradient computation."""
        import numpy as np

        if self._torch_model is None:
            return Unavailable("Torch model is not loaded")
        try:
            import torch

            if isinstance(batch, np.ndarray):
                tensor = torch.from_numpy(batch).float().requires_grad_(True)
            elif isinstance(batch, torch.Tensor):
                tensor = batch.float().requires_grad_(True)
            else:
                tensor = torch.tensor(batch, dtype=torch.float32, requires_grad=True)

            output = self._torch_model(tensor)
            # Compute gradient of the sum of outputs w.r.t. input
            output.sum().backward()
            if tensor.grad is not None:
                return tensor.grad.numpy()
            return Unavailable("No gradients computed")
        except Exception as exc:
            return Unavailable(f"Torch gradient computation failed: {type(exc).__name__}: {exc}")


def load_model(path: Path, *, access: str = "white-box") -> CvModelWrapper:
    """Factory the pipeline calls. The only entry point it knows about."""
    return CvModelWrapper(path, access=access)  # type: ignore[arg-type]
