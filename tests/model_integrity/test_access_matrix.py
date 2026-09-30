"""Tests for the access-tier capability matrix generator."""

from __future__ import annotations

from pathlib import Path

from cvassure.model_integrity.access_matrix import MATRIX, MATRIX_METHODS, generate_matrix


def test_matrix_has_all_methods() -> None:
    assert len(MATRIX_METHODS) == 5
    assert "Weight digest vs signed reference" in MATRIX_METHODS
    assert "Query-based trigger sweep (patch library)" in MATRIX_METHODS


def test_matrix_has_all_tiers() -> None:
    assert "white-box" in MATRIX
    assert "gray-box" in MATRIX
    assert "black-box" in MATRIX


def test_white_box_has_all_available() -> None:
    for method in MATRIX_METHODS:
        assert MATRIX["white-box"][method] is True, f"{method} should be available in white-box"


def test_black_box_has_reconstruction_unavailable() -> None:
    assert MATRIX["black-box"]["Trigger reconstruction (Neural Cleanse style)"] is False


def test_black_box_has_sweep_available() -> None:
    assert MATRIX["black-box"]["Query-based trigger sweep (patch library)"] is True


def test_generate_matrix_creates_png(tmp_path: Path) -> None:
    out_path = tmp_path / "access_matrix.png"
    result = generate_matrix(out_path, tier="white-box")
    assert result == out_path
    assert out_path.is_file()
    assert out_path.stat().st_size > 0


def test_generate_matrix_is_deterministic(tmp_path: Path) -> None:
    path1 = tmp_path / "matrix1.png"
    path2 = tmp_path / "matrix2.png"
    generate_matrix(path1, tier="white-box")
    generate_matrix(path2, tier="white-box")
    assert path1.read_bytes() == path2.read_bytes()
