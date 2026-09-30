"""Audit pipeline.

Order is fixed:

1. Load config and policy, and hash both.
2. Hash inputs.
3. Load data.
4. Run data detectors.
5. Run model detectors.
6. Verify records.
7. Run shift detectors.
8. Assign ids.
9. Validate every finding before linking. One failure aborts with exit 3.
10. Link findings.
11. Apply policy.
12. Write the output files.
13. Use an optional renderer, or the built-in HTML report.
14. Hash the report, append the closing log events, and verify the chain.

Linking edits both findings in a pair, so validation runs first.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cvassure.core.audit import ChainBackend, make_chain
from cvassure.core.config import load_config
from cvassure.core.coverage import Coverage, build_coverage
from cvassure.core.detector import AuditContext, Dataset, DetectorResult
from cvassure.core.errors import ConfigError, DetectorsError
from cvassure.core.finding import Finding, SchemaError, validate_finding
from cvassure.core.hashing import canonical_json, canonical_sha256, file_sha256, tree_sha256
from cvassure.core.linking import apply_links, find_links
from cvassure.core.policy import apply_policy, load_policy
from cvassure.core.registry import Loaded, build_registry, order_registry
from cvassure.core.report import render_from_out_dir, render_report

STAGES: tuple[str, ...] = ("data", "model", "records", "shift")
STAGE_INDEX = {name: i + 1 for i, name in enumerate(STAGES)}


@dataclass
class StageLine:
    """One CLI line. The shape is fixed. The numbers come from this run."""

    index: int
    label: str
    status: str
    detail: str


@dataclass
class RunResult:
    findings: list[Finding]
    coverage: Coverage
    manifest: dict[str, Any]
    stages: list[StageLine]
    link_report: dict[str, Any]
    disposition_line: str
    link_line: str | None
    out_dir: Path
    report_path: Path
    report_file_sha256: str
    payload_sha256: str
    chain_ok: bool
    chain_head: str
    stub_ran: bool
    detector_errors: list[str] = field(default_factory=list)
    coverage_warning: str | None = None
    #: Real elapsed seconds. Kept out of the manifest so `--reproducible` can
    #: freeze the manifest without freezing what the user sees on screen.
    wall_clock_s: float = 0.0


def _git_commit() -> str:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _tool_version() -> str:
    from cvassure import __version__

    return __version__


def _assign_ids(pairs: Sequence[tuple[Finding, str]]) -> list[Finding]:
    """F-001 upward, by stage, then detector, then severity desc, then a stable key.

    Deterministic, so two `--reproducible` runs produce identical ids. The final
    key is reason + source_id + class_label, which is stable across runs because
    a detector that varies it was not deterministic to begin with.

    Takes (finding, stage) pairs rather than trying to recover the stage from the
    finding, which is not on the object and must not be.
    """

    def sort_key(pair: tuple[Finding, str]) -> tuple:
        f, stage = pair
        det = f.detector.id if f.detector else ""
        return (
            STAGE_INDEX.get(stage, 9),
            det,
            -f.severity,
            f.reason,
            f.source_id or "",
            str(f.class_label or ""),
        )

    ordered = sorted(pairs, key=sort_key)
    return [f.to_final(f"F-{i:03d}") for i, (f, _stage) in enumerate(ordered, 1)]


#: Excluded from the ``payload_sha256`` preimage. Each is only knowable *after*
#: the hash exists, so including any of them makes the definition circular.
#: Excluding a field from its own preimage is standard. Excluding the other two
#: is a choice, and it is the one that lets `verify-report` recompute this from
#: `out/` at any time without re-running the audit.
POST_RENDER_FIELDS = ("payload_sha256", "report_file_sha256", "audit_head")


def _payload_sha256(findings, coverage: Coverage, manifest: dict[str, Any]) -> str:
    """SHA-256 of findings + coverage + run manifest, canonical JSON.

    The report header and the QR code show this value. `verify-report`
    recomputes it with exactly this function, so the two can never disagree by
    construction rather than by luck.
    """
    return canonical_sha256(
        {
            "findings": [f.model_dump() for f in findings],
            "coverage": coverage.to_json(),
            "run_manifest": {k: v for k, v in manifest.items() if k not in POST_RENDER_FIELDS},
        }
    )


def _run_detector(
    loaded: Loaded, ctx: AuditContext, *, prior: Sequence[Finding], timeout_s: float
) -> tuple[DetectorResult, str | None]:
    """Run one detector under the access rule and the crash rule.

    Two guarantees the detector author does not have to implement:
    * a `requires` mismatch is a skip, never a call
    * an exception becomes one `asset=system` Finding and the run continues
    """
    ctx = AuditContext(**{**ctx.__dict__, "prior_findings": tuple(prior)})

    if loaded.detector.requires:
        if ctx.model is None:
            reason = (
                f"requires {', '.join(sorted(loaded.detector.requires))}. "
                "No model wrapper is loaded"
            )
        else:
            available = set(ctx.model.capabilities())
            missing = set(loaded.detector.requires) - available
            reason = ""
            if missing:
                reason = (
                    f"requires {', '.join(sorted(loaded.detector.requires))}. "
                    f"Model is {ctx.model.declare_access_tier()} and provides {sorted(available)}"
                )
        if reason:
            return (
                DetectorResult(
                    status="skipped",
                    skipped_reason=reason,
                    limitations=[f"{loaded.id} did not run: {reason}"],
                ),
                None,
            )

    started = time.perf_counter()
    try:
        if timeout_s > 0:
            import concurrent.futures as cf

            with cf.ThreadPoolExecutor(max_workers=1) as pool:
                res = pool.submit(loaded.detector.run, ctx).result(timeout=timeout_s)
        else:
            res = loaded.detector.run(ctx)
    except TimeoutError:
        reason = f"exceeded the {timeout_s:g}s timeout"
        return (
            DetectorResult(
                status="error",
                skipped_reason=reason,
                limitations=[f"{loaded.id} timed out after {timeout_s:g}s and produced no result."],
                findings=[_crash_finding(loaded, f"timed out after {timeout_s:g}s", ctx)],
            ),
            reason,
        )
    except Exception as exc:  # crash rule: isolate, record, continue
        reason = f"{type(exc).__name__}: {exc}"
        return (
            DetectorResult(
                status="error",
                skipped_reason=reason,
                limitations=[f"{loaded.id} raised and did not produce a result."],
                findings=[_crash_finding(loaded, reason, ctx)],
            ),
            reason,
        )
    res.runtime_s = round(time.perf_counter() - started, 3)
    # The pipeline stamps identity. A detector setting these is a bug.
    res.findings = [
        f.with_detector(loaded.id, loaded.detector.version, loaded.detector.owner)
        for f in res.findings
    ]
    return res, None


def _crash_finding(loaded: Loaded, reason: str, ctx: AuditContext) -> Finding:
    return Finding.draft(
        asset="system",
        reason=f"detector {loaded.id} raised {reason}, stage continued without it",
        evidence=[],
        severity=0.3,
        confidence=1.0,
        access_level="not-applicable",
        limitations=(
            f"The crash is the evidence. {loaded.id} did not compute anything, so its "
            "result is unknown and must not be read as a clean result."
        ),
        disposition="review",
        metadata={"error": reason, "detector_status": "error"},
    ).with_detector(loaded.id, loaded.detector.version, loaded.detector.owner)


def _top_source(findings: Sequence[Finding]) -> Finding | None:
    """Highest-severity data finding with a source_id, ties broken by id.

    Scenario-agnostic: no contributor id is known here. The demo shows `C-07`
    because the input data contains it, not because the code does.
    """
    candidates = [f for f in findings if f.asset == "data" and f.source_id]
    if not candidates:
        return None
    return sorted(candidates, key=lambda f: (-f.severity, f.id or ""))[0]


def _disposition_line(findings: Sequence[Finding]) -> str:
    """One line naming quarantine, rejection, and review, grouped by asset.

    Each asset is named once. The highest-severity quarantine for that asset
    is the one printed.
    """
    parts: list[str] = []
    for asset in ("data", "model", "records", "shift"):
        asset_f = [f for f in findings if f.asset == asset]
        if not asset_f:
            continue
        quarantined = [f for f in asset_f if f.disposition == "quarantine"]
        rejected = [f for f in asset_f if f.disposition == "rejected"]
        reviewed = [f for f in asset_f if f.disposition == "review"]
        if quarantined:
            f = sorted(quarantined, key=lambda x: (-x.severity, x.id or ""))[0]
            who = f.source_id or f.batch_id
            parts.append(f"{asset} {who}: QUARANTINE" if who else f"{asset}: QUARANTINE")
        elif rejected:
            parts.append(f"{asset}: {len(rejected)} REJECTED")
        elif reviewed:
            parts.append(f"{asset}: REVIEW")
    return " | ".join(parts) if parts else "no dispositions"


def run_audit(
    *,
    data: Path | None,
    model: Path | None,
    records: Path | None,
    out_dir: Path,
    config_path: Path | None = None,
    policy_path: Path | None = None,
    coverage_rules: Path | None = None,
    results_csv: Path | None = None,
    seed: int | None = None,
    access: str | None = None,
    stages: Sequence[str] = STAGES,
    reproducible: bool = False,
    emit: Callable[[str], None] = lambda _s: None,
) -> RunResult:
    """One full audit. Returns everything the CLI needs and writes `out/`."""
    t0 = time.perf_counter()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = out_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    for label, path in (("--data", data), ("--model", model), ("--records", records)):
        if path is not None and not path.exists():
            raise ConfigError(f"{label}: no such path: {path}")

    cfg = load_config(config_path)
    run_seed = seed if seed is not None else cfg.seed
    run_access = access or cfg.access
    policy_file = policy_path or cfg.policy_path

    ts = f"1970-01-01T00:00:{run_seed % 60:02d}Z" if reproducible else None
    chain: ChainBackend = make_chain(out_dir / "audit.log", deterministic_ts=ts)
    detector_errors: list[str] = []

    chain.append(
        "run_start",
        {
            "tool_version": _tool_version(),
            "git_commit": _git_commit(),
            "seed": run_seed,
            "access": run_access,
            "reproducible": reproducible,
            "stages": list(stages),
            "chain_backend": type(chain).__name__,
        },
    )
    chain.append(
        "config_loaded", {"path": str(config_path or "defaults"), "config_hash": cfg.config_hash}
    )
    emit(f"config hash {cfg.config_hash[:12]}")

    policy = load_policy(policy_file)
    chain.append(
        "policy_loaded",
        {"path": str(policy_file), "policy_hash": policy.policy_hash, "rules": len(policy.rules)},
    )

    # 2. input hashes. Hashing is not inference.
    input_hashes: dict[str, str] = {}
    if data and data.is_dir():
        input_hashes["dataset"] = tree_sha256(data)
    if model and model.is_file():
        input_hashes["model"] = file_sha256(model)
    if records and records.is_file():
        input_hashes["records"] = file_sha256(records)
    chain.append("inputs_hashed", input_hashes)

    # 3. load data
    dataset: Dataset | None = None
    stage_lines: list[StageLine] = []
    if "data" in stages:
        from cvassure.core.adapters import AdapterError, load_dataset

        try:
            dataset = load_dataset(data) if data else None
            if dataset is None:
                stage_lines.append(StageLine(1, "Load data", "skipped", "no data path"))
            else:
                n_src = len(dataset.sources())
                stage_lines.append(
                    StageLine(
                        1,
                        "Load data",
                        "ok",
                        f"{len(dataset.samples)} images, {n_src} contributors "
                        f"({dataset.format}, offline)",
                    )
                )
        except AdapterError as exc:
            # A path the user named does not exist, or is not a dataset we can
            # read. That is a usage error (exit 2), not a detector failure: no
            # detector ran, so exit 3 would blame the wrong thing.
            raise ConfigError(str(exc)) from exc
        except Exception as exc:
            stage_lines.append(StageLine(1, "Load data", "error", f"{type(exc).__name__}: {exc}"))
            detector_errors.append(f"load_data: {exc}")

    model_wrapper, model_load_error = (
        _load_model(model, run_access) if "model" in stages else (None, None)
    )
    # No extra stage line here. Stages 2-5 are built once from the detector
    # results, and a second line for the same stage breaks the fixed shape.

    # 4-7. detectors, grouped by stage
    loaded = build_registry(cfg.detector_modules)
    loaded = order_registry(loaded, cfg.detector_order)
    chain.append(
        "plugins_loaded",
        {"count": len(loaded), "detectors": [item.manifest_entry() for item in loaded]},
    )

    ctx = AuditContext(
        seed=run_seed,
        out_dir=out_dir,
        evidence_dir=evidence_dir,
        cache_dir=cache_dir,
        config=cfg.raw,
        dataset=dataset,
        model=model_wrapper,
        records_path=records,
        pubkey_path=None,
        audit=chain,
    )

    all_findings: list[tuple[Finding, str]] = []
    stage_results: dict[str, list[DetectorResult]] = {s: [] for s in STAGES}
    for item in loaded:
        if item.load_error:
            detector_errors.append(f"{item.module}: {item.load_error}")
        asset = item.asset if item.asset in STAGE_INDEX else "data"
        if asset not in stages:
            continue
        res, err = _run_detector(
            item,
            ctx,
            prior=tuple(f for f, _ in all_findings),
            timeout_s=cfg.timeouts.get(item.id, cfg.timeouts.get("default", 0)),
        )
        if err:
            detector_errors.append(f"{item.id}: {err}")
        stage_results.setdefault(asset, []).append(res)
        for f in res.findings:
            # A crash lands in `system`. It is still that detector's stage for ordering.
            all_findings.append((f, asset))
        chain.append(
            "detector_result",
            {
                "id": item.id,
                "status": res.status,
                "findings": len(res.findings),
                "runtime_s": res.runtime_s,
            },
        )

    # 8. assign ids
    findings = _assign_ids(all_findings)

    # 9. schema gate, BEFORE linking
    validated: list[Finding] = []
    for f in findings:
        try:
            validated.append(
                validate_finding(f.model_dump(), detector_id=f.detector.id if f.detector else None)
            )
        except SchemaError as exc:
            raise DetectorsError(
                f"schema validation failed, aborting before linking: {exc}"
            ) from exc

    # 10. link
    links, link_report = find_links(validated, cfg.link, evidence_dir)
    linked = apply_links(validated, links, evidence_dir)
    for link in links:
        chain.append(
            "link_created",
            {
                "data": link.data_finding,
                "model": link.model_finding,
                "score": round(link.score, 4),
                "components": link.components,
            },
        )

    # 11. policy
    with_policy, rule_hits = apply_policy(linked, policy)
    chain.append("policy_applied", {"rule_hits": rule_hits, "policy_hash": policy.policy_hash})

    # 12. coverage
    cov = build_coverage(
        results_csv, coverage_rules or Path("configs/coverage_rules.yaml"), with_policy
    )
    chain.append(
        "coverage_generated", {"status_counts": cov.status_counts(), "warning": cov.warning}
    )

    stub_ran = any(f.stub for f in with_policy)
    manifest = _build_manifest(
        cfg=cfg,
        policy=policy,
        seed=run_seed,
        access=run_access,
        input_hashes=input_hashes,
        findings=with_policy,
        rule_hits=rule_hits,
        link_report=link_report,
        loaded=loaded,
        stage_results=stage_results,
        detector_errors=detector_errors,
        stub_ran=stub_ran,
        reproducible=reproducible,
        started=t0,
    )
    _write_outputs(out_dir, with_policy, cov, manifest, link_report, links)

    # 13. render. The report header shows payload_sha256, so that hash is settled
    # before the bytes exist. It is not circular: the preimage deliberately
    # excludes the three fields that are only knowable *after* rendering, so the
    # same value is recomputable from out/ by `verify-report` at any time.
    manifest["report_file_sha256"] = ""
    manifest["audit_head"] = ""
    payload_sha256 = _payload_sha256(with_policy, cov, manifest)
    manifest["payload_sha256"] = payload_sha256

    report_path = render_from_out_dir(out_dir)
    if report_path is None:
        report_path = render_report(
            out_dir, with_policy, cov, manifest, payload_sha256=payload_sha256
        )
    report_sha = file_sha256(report_path)
    manifest["report_file_sha256"] = report_sha

    chain.append(
        "report_written",
        {"path": report_path.name, "file_sha256": report_sha, "payload_sha256": payload_sha256},
    )
    chain.append(
        "run_end",
        {
            "status": "ok" if not detector_errors else "degraded",
            "detector_errors": detector_errors,
            "stub_ran": stub_ran,
        },
    )
    manifest["audit_head"] = chain.head()

    (out_dir / "run_manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")

    from cvassure.core.audit import verify_file

    result = verify_file(out_dir / "audit.log", expected_head=chain.head())

    stage_lines.extend(
        _stage_lines(
            with_policy,
            stage_results,
            run_access,
            records,
            bool(model and model.is_file()),
            cov,
            model_load_error,
        )
    )
    link_line = None
    if links:
        lk = links[0]
        src = next((f.source_id for f in with_policy if f.id == lk.data_finding), None)
        if src:
            link_line = (
                f"model trigger matches the patch seen in samples from {src} -> severity escalated"
            )

    return RunResult(
        findings=with_policy,
        coverage=cov,
        manifest=manifest,
        stages=sorted(stage_lines, key=lambda s: s.index),
        link_report=link_report,
        disposition_line=_disposition_line(with_policy),
        link_line=link_line,
        out_dir=out_dir,
        report_path=report_path,
        report_file_sha256=report_sha,
        payload_sha256=payload_sha256,
        chain_ok=result.ok,
        chain_head=result.head,
        stub_ran=stub_ran,
        detector_errors=detector_errors,
        coverage_warning=cov.warning,
        wall_clock_s=round(time.perf_counter() - t0, 3),
    )


def _load_model(path: Path | None, access: str) -> tuple[Any, str | None]:
    """Load the model wrapper when the file exists.

    A missing file and a missing loader are different. The second return value
    names the loader failure. A missing file returns no error.
    """
    if path is None or not path.is_file():
        return None, None
    import importlib

    name = "cvassure.model_integrity.wrapper"
    try:
        mod = importlib.import_module(name)
    except ModuleNotFoundError:
        return None, "cvassure.model_integrity.wrapper is not importable"
    except Exception as exc:
        return None, f"wrapper import failed: {type(exc).__name__}: {exc}"
    factory = getattr(mod, "load_model", None)
    if not callable(factory):
        return None, "cvassure.model_integrity.wrapper has no load_model()"
    try:
        return factory(path, access=access), None
    except Exception as exc:
        return None, f"wrapper refused the model: {type(exc).__name__}: {exc}"


def _stage_lines(  # noqa: PLR0913 - one call site, a params object would be a second shape
    findings, stage_results, access, records, model_present, cov, model_load_error=None
) -> list[StageLine]:
    """Stages 2 to 5. Numbers come from this run. Nothing is a placeholder."""
    out: list[StageLine] = []

    data_f = [f for f in findings if f.asset == "data"]
    top = _top_source(data_f)
    detail = f"{len(data_f)} finding" + ("s" if len(data_f) != 1 else "")
    if top and top.source_id:
        detail += f"   top source: {top.source_id} (risk {top.severity:.2f})"
    out.append(StageLine(2, "Data integrity", "ok" if data_f else "clean", detail))

    model_f = [f for f in findings if f.asset == "model"]
    res_list = stage_results.get("model", [])
    # A real finding is better than a skip, so a producing detector wins even if a
    # sibling skipped. When nothing produced, prefer the *most informative* skip:
    # the one that is not merely "no model in this run", so a missing
    # loader is not drowned out by a stale sibling skip.
    informative = next(
        (
            r
            for r in res_list
            if r.status == "skipped"
            and r.skipped_reason
            and r.skipped_reason != "no model in this run"
        ),
        None,
    )
    skipped = informative or next((r for r in res_list if r.status == "skipped"), None)
    if model_f:
        summ = next((r.summary for r in res_list if r.summary), "")
        out.append(
            StageLine(
                3,
                f"Model integrity ({access})",
                "ok",
                f"{len(model_f)} finding(s)  {summ}".rstrip(),
            )
        )
    elif skipped:
        out.append(
            StageLine(
                3, f"Model integrity ({access})", "skipped", f"skipped ({skipped.skipped_reason})"
            )
        )
    elif model_present:
        # A model file was given but no wrapper could open it. Say that, not
        # "no model": the distinction is the whole point of the access tier.
        out.append(
            StageLine(
                3,
                f"Model integrity ({access})",
                "skipped",
                f"skipped ({model_load_error or 'model file not loadable'})",
            )
        )
    else:
        out.append(StageLine(3, f"Model integrity ({access})", "skipped", "no model in this run"))

    rec_f = [f for f in findings if f.asset == "records"]
    total_records = 0
    if records and records.is_file():
        total_records = sum(
            1 for line in records.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    if rec_f:
        edits = sum(1 for f in rec_f if "replay" not in f.tags)
        replays = sum(1 for f in rec_f if "replay" in f.tags)
        detail = (
            f"{total_records or '?'} records    {len(rec_f)} REJECTED "
            f"({edits} edited, {replays} replayed)"
        )
    else:
        detail = f"{total_records} records    0 rejected"
    out.append(StageLine(4, "Inference records", "ok" if rec_f else "clean", detail))

    shift_f = [f for f in findings if f.asset == "shift"]
    # Deterministic: stage order first, then batch id. Finding id order would
    # depend on severity, and the two shift verdicts are peers, not a ranking.
    depth = {"data.patch_trigger": 0}
    shift_f = sorted(
        shift_f,
        key=lambda f: (
            depth.get(f.detector.id if f.detector else "", 1),
            f.batch_id or "",
        ),
    )
    verdicts = []
    for f in shift_f:
        tag = (
            "manipulation"
            if "manipulation" in f.tags
            else ("drift" if "drift" in f.tags else "undetermined")
        )
        verdicts.append(f"{f.batch_id}: {tag}")
    out.append(
        StageLine(
            5,
            "Shift assessment",
            "ok" if shift_f else "clean",
            " | ".join(verdicts) or "no batch verdicts",
        )
    )
    return out


def _build_manifest(
    *,
    cfg,
    policy,
    seed,
    access,
    input_hashes,
    findings,
    rule_hits,
    link_report,
    loaded,
    stage_results,
    detector_errors,
    stub_ran,
    reproducible,
    started,
) -> dict[str, Any]:
    # A wall-clock reading inside the manifest makes `payload_sha256` differ
    # between two otherwise-identical runs, which breaks the `--reproducible`
    # guarantee on `findings.json` and the payload hash. Under
    # Under `--reproducible` every duration is frozen to zero. The real timing is
    # printed to the terminal and into the runtime line, which is where a human
    # reads it anyway. `wall_clock_s` is deliberately NOT in the manifest.
    def secs(value: float | None) -> float:
        if reproducible:
            return 0.0
        return round(value, 3) if value is not None else 0.0

    return {
        "seed": seed,
        "access": access,
        "reproducible": reproducible,
        "tool_version": _tool_version(),
        "git_commit": _git_commit(),
        "config_hash": cfg.config_hash,
        "policy_hash": policy.policy_hash,
        "policy_name": policy.name,
        "input_hashes": input_hashes,
        "finding_count": len(findings),
        "disposition_counts": {
            d: sum(1 for f in findings if f.disposition == d)
            for d in ("accept", "review", "quarantine", "rejected")
        },
        "policy_rule_hits": rule_hits,
        "detectors": [item.manifest_entry() for item in loaded],
        "stages": {
            stage: [
                {
                    "status": r.status,
                    "findings": len(r.findings),
                    "summary": r.summary,
                    "runtime_s": secs(r.runtime_s),
                    "skipped_reason": r.skipped_reason,
                }
                for r in results
            ]
            for stage, results in stage_results.items()
        },
        "skipped_detectors": [
            {"id": r.detector.id if hasattr(r, "detector") else "", "reason": r.skipped_reason}
            for results in stage_results.values()
            for r in results
            if r.status == "skipped"
        ],
        "stub_flags": {
            "stub_ran": stub_ran,
            "stubs": sorted({f.detector.id for f in findings if f.stub and f.detector}),
        },
        "detector_errors": detector_errors,
        "link_summary": {
            "created": link_report.get("pairs_linked", 0),
            "considered": link_report.get("pairs_considered", 0),
            "tau_link": link_report.get("tau_link"),
            "calibration": link_report.get("calibration"),
        },
        "timings": {"total_s": secs(time.perf_counter() - started)},
    }


def _write_outputs(
    out_dir: Path, findings, coverage: Coverage, manifest, link_report, links
) -> None:
    import json

    (out_dir / "findings.json").write_text(
        json.dumps([f.model_dump() for f in findings], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "coverage.json").write_text(
        json.dumps(coverage.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "coverage.md").write_text(coverage.to_markdown(), encoding="utf-8")
    (out_dir / "coverage_fragment.html").write_text(coverage.to_html(), encoding="utf-8")

    quarantine = {"sources": [], "samples": [], "batches": [], "records": []}
    for f in findings:
        if f.disposition not in ("quarantine", "rejected"):
            continue
        if f.source_id:
            quarantine["sources"].append(
                {"source_id": f.source_id, "finding_ids": [f.id], "reason": f.reason}
            )
        if f.batch_id:
            quarantine["batches"].append(
                {"batch_id": f.batch_id, "finding_ids": [f.id], "reason": f.reason}
            )
        for sid in f.sample_ids:
            quarantine["samples"].append({"sample_id": sid, "finding_ids": [f.id]})
        if f.asset == "records":
            for sid in f.sample_ids:
                quarantine["records"].append({"record_id": sid, "finding_ids": [f.id]})
    (out_dir / "quarantine.json").write_text(
        json.dumps(quarantine, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    report = dict(link_report)
    report["links"] = [
        {
            "data_finding": link.data_finding,
            "model_finding": link.model_finding,
            "score": round(link.score, 4),
            "components": link.components,
            "weights_used": link.weights_used,
            "evidence": link.evidence,
        }
        for link in links
    ]
    (out_dir / "link_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "run_manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")
