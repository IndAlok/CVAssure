"""Tests for the real model wrapper."""

from __future__ import annotations

from pathlib import Path

import pytest

from cvassure.model_integrity.wrapper import CvModelWrapper, Unavailable, load_model


def test_wrapper_constructs_with_nonexistent_file() -> None:
    with pytest.raises(FileNotFoundError):
        CvModelWrapper(Path("/nonexistent/model.onnx"))


def test_wrapper_constructs_with_unknown_tier() -> None:
    with pytest.raises(ValueError, match="unknown access tier"):
        CvModelWrapper(Path("/tmp/model.onnx"), access="super-box")  # type: ignore[arg-type]


def test_wrapper_is_stub_when_no_backend_available(tmp_path: Path) -> None:
    """When neither onnxruntime nor torch is installed, the wrapper is a stub."""
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake onnx bytes")
    wrapper = CvModelWrapper(model_file)
    # If no backend is available, is_stub should be True
    if wrapper.backend is None:
        assert wrapper.is_stub is True


def test_wrapper_weight_digest_is_real_sha256(tmp_path: Path) -> None:
    import hashlib

    model_file = tmp_path / "model.onnx"
    payload = b"fake onnx bytes for digest test"
    model_file.write_bytes(payload)
    wrapper = CvModelWrapper(model_file)
    expected = hashlib.sha256(payload).hexdigest()
    assert wrapper.weight_digest() == expected


def test_wrapper_predict_returns_unavailable_without_backend(tmp_path: Path) -> None:
    """predict returns Unavailable when no backend loaded the model."""
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake onnx bytes")
    wrapper = CvModelWrapper(model_file)
    if wrapper.backend is None:
        result = wrapper.predict([[[[1.0]]]])
        assert not result
        assert isinstance(result, Unavailable)
        assert "backend" in result.reason.lower() or "install" in result.reason.lower()


def test_wrapper_features_returns_unavailable_without_backend(tmp_path: Path) -> None:
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake onnx bytes")
    wrapper = CvModelWrapper(model_file)
    if wrapper.backend is None:
        result = wrapper.features([[[[1.0]]]])
        assert not result
        assert isinstance(result, Unavailable)


def test_wrapper_gradients_returns_unavailable_without_backend(tmp_path: Path) -> None:
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake onnx bytes")
    wrapper = CvModelWrapper(model_file)
    if wrapper.backend is None:
        result = wrapper.gradients([[[[1.0]]]])
        assert not result
        assert isinstance(result, Unavailable)


def test_wrapper_declare_access_tier(tmp_path: Path) -> None:
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake")
    wrapper = CvModelWrapper(model_file, access="black-box")
    assert wrapper.declare_access_tier() == "black-box"


def test_wrapper_capabilities_match_tier(tmp_path: Path) -> None:
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake")
    wrapper = CvModelWrapper(model_file, access="white-box")
    caps = wrapper.capabilities()
    assert "weights" in caps
    assert "gradients" in caps


def test_load_model_factory(tmp_path: Path) -> None:
    model_file = tmp_path / "model.onnx"
    model_file.write_bytes(b"fake")
    wrapper = load_model(model_file, access="white-box")
    assert isinstance(wrapper, CvModelWrapper)


def test_unavailable_is_falsy() -> None:
    u = Unavailable("test reason")
    assert not u
    assert bool(u) is False
