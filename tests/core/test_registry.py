"""Registry tests (D5). Bad plugin, duplicate id, access skip, crash, timeout.

The registry's job is to make a broken teammate's detector a visible fact rather
than a crashed run or, worse, a silent omission.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import ClassVar

import pytest

from cvassure.core.detector import AuditContext, Detector, DetectorResult
from cvassure.core.errors import DetectorsError
from cvassure.core.registry import build_registry, order_registry


class _Real(Detector):
    id: ClassVar[str] = "data.patch_trigger"
    asset: ClassVar[str] = "data"
    owner: ClassVar[str] = "P2"
    version: ClassVar[str] = "1.0.0"
    requires: ClassVar[frozenset[str]] = frozenset()

    def run(self, ctx: AuditContext) -> DetectorResult:
        return DetectorResult(summary="real")


def test_builtin_stubs_load_by_default() -> None:
    loaded = build_registry(use_entry_points=False)
    ids = {item.id for item in loaded}
    assert {
        "data.patch_trigger",
        "model.trigger_sweep",
        "records.verify",
        "shift.natural",
        "shift.manipulation",
    } <= ids


def test_every_stub_is_loud() -> None:
    """A stub must be identifiable from the registry alone."""
    for item in build_registry(use_entry_points=False):
        if item.is_stub:
            assert "stub" in item.detector.version.lower(), (
                f"{item.id} must mark its version as a stub"
            )


def test_a_real_module_replaces_the_stub_with_the_same_id(tmp_path: Path) -> None:
    """The day-2 to day-6 transition. A teammate's PR just works."""
    mod = tmp_path / "real_patch.py"
    mod.write_text(
        textwrap.dedent(
            """
            from typing import ClassVar
            from cvassure.core.detector import Detector, DetectorResult

            class RealPatch(Detector):
                id: ClassVar[str] = "data.patch_trigger"
                asset: ClassVar[str] = "data"
                owner: ClassVar[str] = "P2"
                version: ClassVar[str] = "1.0.0"
                requires: ClassVar[str] = frozenset()

                def run(self, ctx):
                    return DetectorResult(summary="real patch detector")
            """
        ),
        encoding="utf-8",
    )
    import sys

    sys.path.insert(0, str(tmp_path))
    try:
        loaded = build_registry([f"{mod.stem}:RealPatch"], use_entry_points=False)
        by_id = {item.id: item for item in loaded}
        assert "data.patch_trigger" in by_id
        assert by_id["data.patch_trigger"].is_stub is False
        assert by_id["data.patch_trigger"].detector.version == "1.0.0"
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop(mod.stem, None)


def test_two_real_modules_with_one_id_is_an_error(tmp_path: Path) -> None:
    for name in ("dup_a", "dup_b"):
        (tmp_path / f"{name}.py").write_text(
            textwrap.dedent(
                """
                from typing import ClassVar
                from cvassure.core.detector import Detector, DetectorResult

                class D(Detector):
                    id: ClassVar[str] = "data.duplicate"
                    asset: ClassVar[str] = "data"
                    owner: ClassVar[str] = "P2"
                    version: ClassVar[str] = "1.0.0"
                    requires: ClassVar[str] = frozenset()

                    def run(self, ctx):
                        return DetectorResult()
                """
            ),
            encoding="utf-8",
        )
    import sys

    sys.path.insert(0, str(tmp_path))
    try:
        with pytest.raises(DetectorsError, match="two real modules"):
            build_registry(["dup_a:D", "dup_b:D"], use_entry_points=False)
    finally:
        sys.path.remove(str(tmp_path))
        for m in ("dup_a", "dup_b"):
            sys.modules.pop(m, None)


def test_a_module_that_fails_to_import_becomes_a_visible_finding(tmp_path: Path) -> None:
    """Not a crash, and not silence. A broken plugin is a fact about the run."""
    loaded = build_registry(["nonexistent_module_xyz:Thing"], use_entry_points=False)
    broken = [i for i in loaded if i.load_error]
    assert broken, "a failed import must be recorded, not dropped"
    assert "nonexistent_module_xyz" in broken[0].load_error

    res = broken[0].detector.run(
        AuditContext(
            seed=1,
            out_dir=tmp_path,
            evidence_dir=tmp_path / "e",
            cache_dir=tmp_path / "c",
            config={},
        )
    )
    assert res.status == "error"
    assert res.findings[0].asset == "system"
    assert res.findings[0].stub is True
    assert res.findings[0].limitations.startswith("[STUB]")


def test_a_module_with_no_detector_is_reported(tmp_path: Path) -> None:
    (tmp_path / "empty_mod.py").write_text("x = 1\n", encoding="utf-8")
    import sys

    sys.path.insert(0, str(tmp_path))
    try:
        loaded = build_registry(["empty_mod"], use_entry_points=False)
        assert any("no concrete Detector subclass" in (i.load_error or "") for i in loaded)
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("empty_mod", None)


def test_a_broken_contract_is_rejected_loudly(tmp_path: Path) -> None:
    (tmp_path / "bad_mod.py").write_text(
        textwrap.dedent(
            """
            from typing import ClassVar
            from cvassure.core.detector import Detector, DetectorResult

            class Bad(Detector):
                id: ClassVar[str] = "data.bad"
                asset: ClassVar[str] = "not_an_asset"
                owner: ClassVar[str] = "P2"
                version: ClassVar[str] = "1.0.0"
                requires: ClassVar[str] = frozenset()

                def run(self, ctx):
                    return DetectorResult()
            """
        ),
        encoding="utf-8",
    )
    import sys

    sys.path.insert(0, str(tmp_path))
    try:
        with pytest.raises(DetectorsError, match="breaks the contract"):
            build_registry(["bad_mod:Bad"], use_entry_points=False)
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("bad_mod", None)


def test_order_registry_puts_config_order_first() -> None:
    loaded = build_registry(use_entry_points=False)
    ordered = order_registry(loaded, ["records.verify", "data.patch_trigger"])
    assert ordered[0].id == "records.verify"
    assert ordered[1].id == "data.patch_trigger"


def test_order_registry_is_stable_within_a_stage() -> None:
    loaded = build_registry(use_entry_points=False)
    a = [i.id for i in order_registry(loaded, [])]
    b = [i.id for i in order_registry(list(reversed(loaded)), [])]
    assert a == b


def test_manifest_entry_has_id_version_owner_module() -> None:
    for item in build_registry(use_entry_points=False):
        entry = item.manifest_entry()
        assert entry["id"] and entry["version"] and entry["owner"] and entry["module"]
        assert isinstance(entry["stub"], bool)
