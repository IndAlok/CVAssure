"""Plugin registry (D5). Entry points, then config modules, then built-in stubs.

Three jobs, and they are the reason this file exists:

1. **Prefer the real module over the stub with the same id.** A teammate's PR
   should replace a stub without anyone editing core. That is why the stub and the
   real detector register under one id.
2. **Refuse a plugin that breaks the contract**, loudly, at load. A half-typed
   class that would crash at stage 3 is worse than a load-time failure.
3. **Isolate everything.** A plugin that raises on import, or a detector that
   raises in `run`, becomes a `system` Finding. It never kills the run.

No `pluggy`, no extra dependency. The Detector ABC is a five-attribute contract
and the loader is fifty lines.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from cvassure.core.detector import Detector, interface_errors
from cvassure.core.errors import DetectorsError
from cvassure.core.finding import Finding

ENTRY_POINT_GROUP = "cvassure.detectors"


@dataclass
class Loaded:
    """One detector, plus where it came from and whether it is a stub."""

    detector: Detector
    module: str
    is_stub: bool = False
    load_error: str | None = None

    @property
    def id(self) -> str:
        return self.detector.id

    @property
    def asset(self) -> str:
        return self.detector.asset

    def manifest_entry(self) -> dict[str, Any]:
        from cvassure.core.hashing import file_sha256

        entry = {
            "id": self.id,
            "version": self.detector.version,
            "owner": self.detector.owner,
            "module": self.module,
            "stub": self.is_stub,
        }
        try:
            mod = importlib.import_module(self.module)
            src = getattr(mod, "__file__", None)
            if src:
                from pathlib import Path

                entry["file_sha256"] = file_sha256(Path(src))
        except Exception:  # a module with no readable file is not fatal to the run
            pass
        return entry


def _instantiate(module_name: str) -> Detector:
    """Import a module (or a `module:Class` path) and build its one Detector.

    Accepts `pkg.mod` and `pkg.mod:ClassName`. A module may define exactly one
    concrete Detector; more than one is an error rather than a guess, because
    picking the wrong class silently registers a detector nobody reviewed.
    """
    module_name, _, wanted = module_name.partition(":")
    mod = importlib.import_module(module_name)

    if wanted:
        obj = getattr(mod, wanted, None)
        if obj is None:
            raise DetectorsError(f"{module_name} has no attribute {wanted!r}")
        if not (isinstance(obj, type) and issubclass(obj, Detector)):
            raise DetectorsError(f"{module_name}:{wanted} is not a Detector subclass")
        if inspect_is_abstract(obj):
            raise DetectorsError(f"{module_name}:{wanted} is abstract")
        return obj()

    found: list[type[Detector]] = []
    for obj in vars(mod).values():
        if (
            isinstance(obj, type)
            and issubclass(obj, Detector)
            and obj is not Detector
            and obj.__module__ == module_name
            and not inspect_is_abstract(obj)
        ):
            found.append(obj)
    if not found:
        raise DetectorsError(f"{module_name} defines no concrete Detector subclass")
    if len(found) > 1:
        names = ", ".join(sorted(c.__name__ for c in found))
        raise DetectorsError(
            f"{module_name} defines {len(found)} Detector classes ({names}); "
            "name one with module:Class"
        )
    return found[0]()


def inspect_is_abstract(cls: type) -> bool:
    return bool(getattr(cls, "__abstractmethods__", frozenset()))


def load_from_entry_points() -> list[Loaded]:
    """Installed detectors. Wrapped: a broken plugin must not stop the load."""
    from importlib.metadata import entry_points

    out: list[Loaded] = []
    try:
        eps = entry_points(group=ENTRY_POINT_GROUP)
    except Exception as exc:  # pragma: no cover - importlib.metadata is reliable on 3.11
        raise DetectorsError(f"cannot read entry points: {exc}") from exc
    for ep in eps:
        try:
            obj = ep.load()
        except Exception as exc:
            out.append(
                Loaded(
                    detector=_broken_stub(f"entrypoint:{ep.name}"),
                    module=f"{ENTRY_POINT_GROUP}:{ep.name}",
                    load_error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        target = obj() if isinstance(obj, type) else obj
        problems = interface_errors(target)
        if problems:
            raise DetectorsError(
                f"entry point {ep.name!r} breaks the contract: {'; '.join(problems)}"
            )
        out.append(Loaded(detector=target, module=ep.value))
    return out


def load_from_modules(module_names: Iterable[str]) -> list[Loaded]:
    out: list[Loaded] = []
    for name in module_names:
        try:
            det = _instantiate(name)
        except Exception as exc:
            out.append(
                Loaded(
                    detector=_broken_stub(name),
                    module=name,
                    load_error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        problems = interface_errors(det)
        if problems:
            raise DetectorsError(f"{name} breaks the contract: {'; '.join(problems)}")
        out.append(Loaded(detector=det, module=name))
    return out


def _broken_stub(module_name: str) -> Detector:
    """A placeholder that emits a system Finding instead of silently vanishing.

    A plugin that fails to import is a fact about the run that a judge needs to
    see. Dropping it would make a broken build look like a clean one.
    """

    class BrokenStub(Detector):
        id = "system.plugin_load_failed"
        asset = "system"
        owner = "P1"
        version = "0"
        requires = frozenset()

        def run(self, ctx: Any) -> Any:
            from cvassure.core.detector import DetectorResult

            return DetectorResult(
                status="error",
                findings=[
                    Finding.draft(
                        asset="system",
                        reason=f"[STUB] plugin {module_name} failed to load, run continued",
                        evidence=[],
                        severity=0.3,
                        confidence=1.0,
                        access_level="not-applicable",
                        limitations=(
                            "[STUB] This detector did not run at all. Its result is "
                            "unknown and must not be read as a clean result."
                        ),
                        disposition="review",
                        stub=True,
                        metadata={"module": module_name},
                    )
                ],
                skipped_reason=f"plugin load failed: {module_name}",
            )

    BrokenStub.id = f"system.load_failed.{module_name}"
    return BrokenStub()


def build_registry(
    module_names: Iterable[str] = (), *, use_entry_points: bool = True
) -> list[Loaded]:
    """Entry points, then config modules, then stubs. Real beats stub on id.

    A duplicate id from two *real* modules is a config error. A real module and
    the built-in stub sharing an id is the intended day-2 to day-6 transition and
    is not an error.
    """
    from cvassure.core.stubs import STUB_MODULES

    loaded: list[Loaded] = []
    if use_entry_points:
        loaded.extend(load_from_entry_points())
    loaded.extend(load_from_modules(module_names))

    # Stubs are loaded last and tagged here. Tagging at the load site instead
    # would mean a future stub module could forget it, and `is_stub` is what
    # drives the STUB badge and the `--strict` exit 5, so it must not be
    # optional.
    for item in load_from_modules(STUB_MODULES):
        item.is_stub = True
        loaded.append(item)

    by_id: dict[str, Loaded] = {}
    for item in loaded:
        existing = by_id.get(item.id)
        if existing is None:
            by_id[item.id] = item
            continue
        if existing.is_stub and not item.is_stub:
            by_id[item.id] = item  # the real module wins
        elif item.is_stub and not existing.is_stub:
            pass
        elif existing.module != item.module:
            raise DetectorsError(
                f"detector id {item.id!r} is provided by two real modules: "
                f"{existing.module} and {item.module}"
            )
    return list(by_id.values())


def order_registry(loaded: list[Loaded], order: Iterable[str]) -> list[Loaded]:
    """Explicit order from config first, then the rest, stable within an asset."""
    rank = {name: i for i, name in enumerate(order)}
    return sorted(
        loaded,
        key=lambda item: (
            rank.get(item.id, len(rank)),
            ("data", "model", "records", "shift", "system").index(item.asset)
            if item.asset in ("data", "model", "records", "shift", "system")
            else 9,
            item.id,
        ),
    )
