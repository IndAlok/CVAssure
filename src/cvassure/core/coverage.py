"""Coverage statement (D11). Status is derived, never hand-written.

Reads Person 5's `results_table.csv` and turns it into a coverage statement by
the rules in `configs/coverage_rules.yaml`. No row means `Untested`, never
`Supported`. Three classes are `Unsupported` by declaration and a measured row
never flips one of them.

A missing CSV is a legitimate state, not an error: every non-declared row becomes
`Untested` and the CLI prints a one-line warning. Shipping an honest "we have not
measured this yet" is better than a placeholder percentage.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cvassure.core.finding import Finding

REQUIRED_COLUMNS = (
    "attack_class",
    "variant",
    "dataset",
    "n_seeds",
    "detection_rate_mean",
    "detection_rate_std",
    "precision_mean",
    "recall_mean",
    "auroc_mean",
    "false_alarm_rate_mean",
    "runtime_s_median",
    "access_level",
    "notes",
)

STATUS_SUPPORTED = "Supported"
STATUS_PARTIAL = "Partial"
STATUS_UNTESTED = "Untested"
STATUS_UNSUPPORTED = "Unsupported"


@dataclass
class CoverageRow:
    attack_class: str
    status: str
    measured: str | None = None
    access_levels: list[str] = field(default_factory=list)
    n_seeds: int = 0
    limitations: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class Coverage:
    rows: list[CoverageRow]
    assumptions: list[str]
    thresholds: dict[str, Any]
    warning: str | None = None
    declared: list[dict[str, str]] = field(default_factory=list)

    def status_counts(self) -> dict[str, int]:
        counts = {STATUS_SUPPORTED: 0, STATUS_PARTIAL: 0, STATUS_UNTESTED: 0, STATUS_UNSUPPORTED: 0}
        for r in self.rows:
            counts[r.status] = counts.get(r.status, 0) + 1
        return counts

    def to_json(self) -> dict[str, Any]:
        return {
            "status_counts": self.status_counts(),
            "rows": [
                {
                    "attack_class": r.attack_class,
                    "status": r.status,
                    "measured": r.measured,
                    "access_levels": r.access_levels,
                    "n_seeds": r.n_seeds,
                    "limitations": r.limitations,
                    "reason": r.reason,
                }
                for r in self.rows
            ],
            "assumptions": self.assumptions,
            "declared_unsupported": self.declared,
            "thresholds": self.thresholds,
            "warning": self.warning,
        }

    def to_markdown(self) -> str:
        out = [
            "# CVAssure coverage statement",
            "",
            "Status is derived from the results table by the rules in "
            "`configs/coverage_rules.yaml`. It is not written by hand.",
            "",
            "| Attack class | Status | Measured | Access | n seeds |",
            "|---|---|---|---|---|",
        ]
        for r in self.rows:
            out.append(
                f"| {r.attack_class} | {r.status} | {r.measured or '—'} | "
                f"{', '.join(r.access_levels) or '—'} | {r.n_seeds or '—'} |"
            )
        if self.warning:
            out += ["", f"> {self.warning}"]
        out += ["", "## Assumptions", ""]
        out += [f"- {a}" for a in self.assumptions]
        if self.thresholds.get("calibration") == "UNCALIBRATED":
            out += [
                "",
                "> Thresholds in this statement are **UNCALIBRATED** starting values. "
                "They are not a validated detection capability.",
            ]
        return "\n".join(out) + "\n"

    def to_html(self) -> str:
        """Inline-CSS fragment for the report. No CDN, no remote font."""
        css = (
            "font-family:system-ui,-apple-system,'Segoe UI',sans-serif;"
            "border-collapse:collapse;width:100%"
        )
        th = "text-align:left;border-bottom:2px solid #1F3864;padding:6px 10px;font-size:13px"
        td = "border-bottom:1px solid #d8dde3;padding:6px 10px;font-size:13px"
        colour = {
            STATUS_SUPPORTED: "#0070C0",
            STATUS_PARTIAL: "#ffffff",
            STATUS_UNTESTED: "#6b7280",
            STATUS_UNSUPPORTED: "#6b7280",
        }
        rows = []
        for r in self.rows:
            style = f"color:{colour.get(r.status, '#111')}"
            if r.status == STATUS_PARTIAL:
                style += ";border:1px solid #0070C0"
            rows.append(
                f"<tr><td style='{td}'>{r.attack_class}</td>"
                f"<td style='{td};{style}'><b>{r.status}</b></td>"
                f"<td style='{td}'>{r.measured or '—'}</td>"
                f"<td style='{td}'>{r.n_seeds or '—'}</td></tr>"
            )
        return (
            f"<table style='{css}'><thead><tr>"
            f"<th style='{th}'>Attack class</th><th style='{th}'>Status</th>"
            f"<th style='{th}'>Measured</th><th style='{th}'>n seeds</th>"
            f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
        )


def _num(v: str | None) -> float | None:
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_results(path: Path | None) -> tuple[list[dict[str, str]], str | None]:
    """Read the CSV. Missing file is fine and returns a warning, not an exception."""
    if path is None or not path.is_file():
        return [], f"no results table at {path or 'None'}; every non-declared class is Untested"
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        return [], f"{path} is missing columns {missing}; treating all classes as Untested"
    return list(reader), None


def _format_measured(row: dict[str, str]) -> str | None:
    mean = _num(row.get("detection_rate_mean"))
    if mean is None:
        return None
    std = _num(row.get("detection_rate_std"))
    seeds = row.get("n_seeds", "").strip() or "?"
    dataset = row.get("dataset", "").strip() or "unknown dataset"
    body = f"{mean:.2f}"
    if std is not None:
        body += f" ± {std:.2f}"
    return f"{body} ({seeds} seeds, {dataset})"


def build_coverage(
    results_path: Path | None,
    rules_path: Path,
    findings: Sequence[Finding] = (),
) -> Coverage:
    from cvassure.core.config import load_yaml

    rules = load_yaml(rules_path) or {}
    thresholds = dict(rules.get("thresholds") or {})
    declared = list(rules.get("declared_unsupported") or [])
    known = list(rules.get("known_classes") or [])
    assumptions = list(rules.get("assumptions") or [])

    rows, warning = load_results(results_path)
    by_class: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_class.setdefault(row["attack_class"], []).append(row)

    t_support = float(thresholds.get("T_support", 0.80))
    t_far = float(thresholds.get("T_far", 0.05))
    min_seeds = int(thresholds.get("min_seeds", 3))

    out: list[CoverageRow] = []
    for entry in declared:
        out.append(
            CoverageRow(
                attack_class=entry["attack_class"],
                status=STATUS_UNSUPPORTED,
                reason=entry.get("reason", ""),
                limitations=[entry.get("reason", "")],
            )
        )

    stub_findings = [f for f in findings if f.stub]
    for attack_class in known:
        measured_rows = by_class.get(attack_class, [])
        cr = CoverageRow(attack_class=attack_class, status=STATUS_UNTESTED)
        if not measured_rows:
            cr.reason = "no row in the results table"
            out.append(cr)
            continue

        cr.access_levels = sorted(
            {r["access_level"].strip() for r in measured_rows if r.get("access_level", "").strip()}
        )
        cr.n_seeds = max((int(_num(r.get("n_seeds")) or 0) for r in measured_rows), default=0)
        cr.measured = (
            " | ".join(m for m in (_format_measured(r) for r in measured_rows) if m) or None
        )
        notes = sorted({r["notes"].strip() for r in measured_rows if r.get("notes", "").strip()})
        cr.limitations.extend(notes)

        det = max((_num(r.get("detection_rate_mean")) or 0.0 for r in measured_rows), default=0.0)
        far = max((_num(r.get("false_alarm_rate_mean")) or 0.0 for r in measured_rows), default=0.0)
        has_detection = any(_num(r.get("detection_rate_mean")) is not None for r in measured_rows)
        if not has_detection:
            # A row with no detection number is not a weak result, it is no
            # result. Reporting 0.0 here would invent a measurement and turn an
            # honest gap into a fake failure.
            cr.status = STATUS_UNTESTED
            cr.reason = "row present but detection_rate_mean is empty"
            cr.limitations.append("no measurement in the results table")
        elif cr.n_seeds < min_seeds:
            cr.status = STATUS_PARTIAL
            cr.reason = f"n_seeds {cr.n_seeds} < {min_seeds}"
        elif det >= t_support and far <= t_far:
            cr.status = STATUS_SUPPORTED
            cr.reason = f"detection {det:.2f} >= {t_support}, false alarm {far:.2f} <= {t_far}"
        else:
            cr.status = STATUS_PARTIAL
            why = []
            if det < t_support:
                why.append(f"detection {det:.2f} < {t_support}")
            if far > t_far:
                why.append(f"false alarm {far:.2f} > {t_far}")
            cr.reason = ", ".join(why)
        if len(cr.access_levels) == 1 and cr.status == STATUS_SUPPORTED:
            cr.status = STATUS_PARTIAL
            cr.reason += f", measured on {cr.access_levels[0]} only"
        out.append(cr)

    if stub_findings:
        names = sorted({f.detector.id for f in stub_findings if f.detector})
        out.append(
            CoverageRow(
                attack_class="Run integrity",
                status=STATUS_PARTIAL,
                reason="stubs ran in this run",
                limitations=[
                    f"{len(stub_findings)} finding(s) came from day-2 stubs "
                    f"({', '.join(names)}); no real measurement exists for those rows."
                ],
            )
        )

    return Coverage(
        rows=out,
        assumptions=assumptions,
        thresholds=thresholds,
        warning=warning,
        declared=declared,
    )
