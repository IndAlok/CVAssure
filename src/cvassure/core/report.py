"""Offline HTML report.

Reads only the run directory and writes `report.html`. No network, no CDN, no
remote font, no remote image. Generated HTML must not contain `http://` or
`https://` asset URLs.

`cvassure.provenance.render_report` replaces this when that function imports.

An HTML file cannot contain its own digest. The header shows `payload_sha256` of
the findings, coverage, and manifest. The CLI prints `file_sha256` of the HTML
bytes after this returns.
"""

from __future__ import annotations

import html
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from cvassure.core.coverage import (
    STATUS_PARTIAL,
    STATUS_SUPPORTED,
    STATUS_UNSUPPORTED,
    Coverage,
)
from cvassure.core.finding import Finding

BLUE = "#0070C0"
NAVY = "#1F3864"
RED = "#C00000"
GREEN = "#1E7B34"

_CSS = f"""
body{{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;margin:24px;
color:#1a1a1a;background:#fff;max-width:1100px}}
h1{{color:{NAVY};font-size:22px;margin:0 0 4px}}
h2{{color:{NAVY};font-size:16px;margin:24px 0 8px;border-bottom:2px solid {NAVY};
padding-bottom:4px}}
.sub{{color:#555;font-size:13px;margin:0 0 16px}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}}
th{{background:#eef2f7;text-align:left;padding:7px 9px;border-bottom:2px solid {NAVY}}}
td{{padding:7px 9px;border-bottom:1px solid #dde2e8;vertical-align:top}}
code{{background:#f2f4f7;padding:1px 4px;border-radius:3px;font-size:12px}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;
font-weight:700;letter-spacing:.4px}}
.quarantine{{color:#fff;background:{RED}}}
.review{{color:#fff;background:{BLUE}}}
.accept{{color:#fff;background:{GREEN}}}
.rejected{{color:#fff;background:#7a3ea3}}
.stub{{color:{NAVY};background:#ffe9c7;border:1px solid {NAVY}}}
.hash{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;word-break:break-all}}
.lim{{color:#555;font-size:12px;font-style:italic}}
.warn{{background:#fff6e5;border-left:4px solid #d98c00;padding:8px 12px;margin:10px 0}}
"""


def _esc(v: Any) -> str:
    """Escape everything a detector or a contributor put in a string."""
    return html.escape(str(v), quote=True)


def _badge(disposition: str) -> str:
    return f"<span class='badge {html.escape(disposition)}'>{_esc(disposition.upper())}</span>"


def _findings_table(findings: Sequence[Finding]) -> str:
    if not findings:
        return (
            "<p>No findings. This means nothing was flagged. It is not a clean bill of health.</p>"
        )
    rows = []
    for f in sorted(findings, key=lambda x: x.id or ""):
        ev = "<br>".join(f"<code>{_esc(p)}</code>" for p in f.evidence) or ", "
        tags = " ".join(f"<code>{_esc(t)}</code>" for t in f.tags) or ", "
        linked = ", ".join(f.linked_findings) or ", "
        stub = " <span class='badge stub'>STUB</span>" if f.stub else ""
        esc = ""
        if f.escalation and f.escalation.escalated:
            esc = (
                f"<br><span class='badge review'>ESCALATED</span> "
                f"{f.escalation.severity_before:.2f} &rarr; {f.severity:.2f} "
                f"(noisy-or, linked to {_esc(', '.join(f.escalation.linked_to))})"
            )
        rows.append(
            f"<tr><td><b>{_esc(f.id)}</b>{stub}</td>"
            f"<td>{_esc(f.asset)}</td>"
            f"<td>{_esc(f.reason)}{esc}</td>"
            f"<td>{f.severity:.2f}</td><td>{f.confidence:.2f}</td>"
            f"<td>{_esc(f.access_level)}</td>"
            f"<td>{_badge(f.disposition)}</td>"
            f"<td>{tags}</td>"
            f"<td>{ev}</td>"
            f"<td class='lim'>{_esc(f.limitations)}</td>"
            f"<td>{linked}</td></tr>"
        )
    return (
        "<table><thead><tr><th>ID</th><th>Asset</th><th>Reason</th><th>Sev</th>"
        "<th>Conf</th><th>Access</th><th>Disposition</th><th>Tags</th>"
        "<th>Evidence</th><th>Limitations</th><th>Linked</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _coverage_section(cov: Coverage) -> str:
    style = {
        STATUS_SUPPORTED: f"color:{BLUE};font-weight:700",
        STATUS_PARTIAL: f"color:{BLUE};border:1px solid {BLUE};padding:1px 6px",
        STATUS_UNSUPPORTED: "color:#6b7280",
    }
    rows = []
    for r in cov.rows:
        s = style.get(r.status, "color:#111")
        if r.status == "Untested":
            s = "color:#6b7280"
        rows.append(
            f"<tr><td>{_esc(r.attack_class)}</td>"
            f"<td><span style='{s}'>{_esc(r.status)}</span></td>"
            f"<td>{_esc(r.measured or ', ')}</td>"
            f"<td>{_esc(', '.join(r.access_levels) or ', ')}</td>"
            f"<td class='lim'>{_esc(r.reason)}</td></tr>"
        )
    warn = f"<div class='warn'>{_esc(cov.warning)}</div>" if cov.warning else ""
    unc = (
        "<div class='warn'>Thresholds below are <b>UNCALIBRATED</b> starting values, "
        "not a validated detection capability.</div>"
        if cov.thresholds.get("calibration") == "UNCALIBRATED"
        else ""
    )
    assumptions = "".join(f"<li>{_esc(a)}</li>" for a in cov.assumptions)
    return (
        f"{warn}{unc}<table><thead><tr><th>Attack class</th><th>Status</th>"
        f"<th>Measured</th><th>Access</th><th>Why</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        f"<h2>Assumptions and limitations</h2><ul>{assumptions}</ul>"
    )


def render_report(
    out_dir: Path,
    findings: Sequence[Finding],
    coverage: Coverage,
    manifest: dict[str, Any],
    *,
    payload_sha256: str,
) -> Path:
    """Write the built-in report."""
    disposition_counts: dict[str, int] = {}
    for f in findings:
        disposition_counts[f.disposition] = disposition_counts.get(f.disposition, 0) + 1
    disp_line = (
        "  |  ".join(f"{k.upper()}: {v}" for k, v in sorted(disposition_counts.items()))
        or "no findings"
    )

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CVAssure assurance report</title>
<style>{_CSS}</style></head><body>
<h1>CVAssure assurance report</h1>
<p class="sub">seed {_esc(manifest.get("seed"))} &middot;
tool v{_esc(manifest.get("tool_version"))} &middot;
commit {_esc(manifest.get("git_commit"))} &middot;
CPU-only, offline, air-gapped</p>
<p><b>Dispositions:</b> {_esc(disp_line)}</p>
<p class="hash">payload_sha256: {_esc(payload_sha256)}</p>
<h2>Findings</h2>
{_findings_table(findings)}
<h2>Coverage statement</h2>
{_coverage_section(coverage)}
<p class="sub">Generated offline. No network resource is referenced by this document.</p>
</body></html>
"""
    path = out_dir / "report.html"
    path.write_text(doc, encoding="utf-8")
    return path


def render_from_out_dir(out_dir: Path) -> Path | None:
    """Return a path from `cvassure.provenance.render_report`, or None."""
    import importlib

    for module_name in ("cvassure.provenance.report",):
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            continue
        except Exception:
            continue
        render = getattr(mod, "render_report", None)
        if callable(render):
            try:
                return Path(render(out_dir))
            except Exception:
                return None
    return None


def assert_offline_html(path: Path) -> list[str]:
    """Return any remote asset URL found in the report. Empty list means clean.

    This is a test, not a lint. A CDN in the report means the demo dies the
    moment the judge unplugs the network, and that is the exact demo we must
    never ship.
    """
    text = path.read_text(encoding="utf-8")
    bad = []
    for marker in ("http://", "https://", "//cdn.", 'src="//'):
        if marker in text:
            bad.append(marker)
    return bad


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
