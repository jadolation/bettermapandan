"""Audit & Compliance page generators — data-driven from audit-reports.json.

Renders COA key findings, the implementation-rate table, the accessible
opinion table, and the per-year report archive so the page never drifts
from the canonical dataset. Mirrors the generator style of generators/dpwh.py.
"""
import html
import json

from _build.config import ROOT, SRC_DATA
from _build.locales import t

STATUS_ORDER = ["open", "chronic", "improving", "partial", "resolved"]
STATUS_DEFAULT = {
    "open": "Open Findings",
    "chronic": "Chronic / Recurring",
    "improving": "Improving",
    "partial": "Partially Addressed",
    "resolved": "Resolved",
}
SEVERITY_DEFAULT = {"high": "High", "medium": "Medium", "low": "Low"}
EXT_BADGE = {
    "pdf": ("file-pdf", "PDF"),
    "docx": ("file-docx", "DOCX"),
    "doc": ("file-docx", "DOC"),
    "xlsx": ("file-xlsx", "XLSX"),
    "xml": ("file-docx", "XML"),
}


def _load() -> dict:
    path = SRC_DATA / "audit-reports.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _peso(value) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return ""
    if not amount:
        return ""
    if amount >= 1_000_000_000:
        return f"&#8369;{amount / 1_000_000_000:.2f}B"
    if amount >= 1_000_000:
        return f"&#8369;{amount / 1_000_000:.2f}M"
    if amount >= 1_000:
        return f"&#8369;{amount / 1_000:,.1f}K"
    return f"&#8369;{amount:,.0f}"


def _period(finding: dict) -> str:
    first, last = finding.get("first_cited"), finding.get("last_cited")
    if first == last or last is None:
        return str(first)
    return f"{first}\u2013{last}"


def _human_size(num_bytes) -> str:
    if not num_bytes:
        return "\u2014"
    if num_bytes >= 1 << 20:
        return f"{num_bytes / (1 << 20):.1f} MB"
    if num_bytes >= 1 << 10:
        return f"{round(num_bytes / (1 << 10))} KB"
    return f"{num_bytes} B"


def generate_audit_findings(locale: dict) -> str:
    """Findings grid grouped by resolution status, newest citation first.

    Card anchors live on the wrapping card (id="finding-<json id>"); group
    headings carry id="findings-<status>" so the section sub-nav lists the
    ~5 status groups instead of being truncated at 10 individual findings.
    """
    findings = _load().get("key_findings", [])
    groups: dict[str, list] = {}
    for f in findings:
        groups.setdefault(f.get("status", "open"), []).append(f)
    ordered = [s for s in STATUS_ORDER if s in groups]
    ordered += [s for s in groups if s not in STATUS_ORDER]

    blocks = []
    for status in ordered:
        items = sorted(
            groups[status],
            key=lambda f: (-(f.get("last_cited") or 0), f.get("first_cited") or 0),
        )
        label = t(locale, f"transparency.audit_status_{status}",
                  STATUS_DEFAULT.get(status, status.title()))
        cards = []
        for f in items:
            severity = f.get("severity", "")
            sev_label = t(locale, f"transparency.audit_severity_{severity}",
                          SEVERITY_DEFAULT.get(severity, severity.title()))
            amount = _peso(f.get("amount"))
            figure = ""
            if amount:
                category = html.escape(f.get("category", ""))
                figure = (f'<p class="figure text-lg">{amount} '
                          f'<span class="text-xs text-ink-soft">({category})</span></p>')
            cards.append(
                f'<div class="card" id="finding-{html.escape(f.get("id", ""))}">\n'
                f'  <div class="flex-center mb-12">\n'
                f'    <span class="pill pill-severity-{html.escape(severity)}">'
                f'{html.escape(sev_label)}</span>\n'
                f'    <span class="text-sm text-ink-soft">{html.escape(label)} '
                f'&middot; {html.escape(_period(f))}</span>\n'
                f'  </div>\n'
                f'  <h3>{html.escape(f.get("title", ""))}</h3>\n'
                f'  {figure}\n'
                f'  <p>{html.escape(f.get("description", ""))}</p>\n'
                f'</div>'
            )
        blocks.append(
            f'<div class="findings-group">\n'
            f'  <h3 class="findings-group-title" id="findings-{html.escape(status)}">'
            f'{html.escape(label)} <span class="text-sm text-ink-soft">({len(items)})</span></h3>\n'
            f'  <div class="grid grid-2">\n    '
            + "\n    ".join(cards)
            + "\n  </div>\n</div>"
        )
    return "\n".join(blocks)


def generate_audit_opinion_sr_table(locale: dict) -> str:
    """Accessible text equivalent of the audit-opinion chart."""
    opinions = _load().get("opinions", [])
    year_h = t(locale, "transparency.audit_sr_year", "Year")
    opinion_h = t(locale, "transparency.audit_sr_opinion", "Opinion")
    caption = t(locale, "transparency.audit_opinion_title", "COA Audit Opinions")
    rows = []
    for o in opinions:
        label = str(o.get("opinion", ""))
        if o.get("opinion_type") == "compliance_audit":
            label += " (LDRRMF)"
        rows.append(
            f'<tr><td>{html.escape(str(o.get("year", "")))}</td>'
            f'<td>{html.escape(label)}</td></tr>'
        )
    return (
        '<table class="sr-only">\n'
        f'  <caption>{html.escape(caption)}</caption>\n'
        f'  <thead><tr><th scope="col">{html.escape(year_h)}</th>'
        f'<th scope="col">{html.escape(opinion_h)}</th></tr></thead>\n'
        '  <tbody>\n    ' + "\n    ".join(rows) + '\n  </tbody>\n</table>'
    )


def generate_audit_implementation_table(locale: dict) -> str:
    """Recommendation-implementation table from implementation_rates."""
    rates = _load().get("implementation_rates", [])
    headers = {
        "period": t(locale, "transparency.impl_table_period", "Period"),
        "implemented": t(locale, "transparency.impl_table_implemented", "Implemented"),
        "partial": t(locale, "transparency.impl_table_partial", "Partial"),
        "not_implemented": t(locale, "transparency.impl_table_not_implemented", "Not Implemented"),
        "rate": t(locale, "transparency.impl_table_rate", "Rate"),
    }
    rows = []
    for r in rates:
        rate = r.get("rate", 0)
        cls = "text-green-bright" if rate >= 70 else "text-gold"
        period = html.escape(str(r.get("period", ""))).replace("\u2192", "&rarr;")
        rows.append(
            f'<tr><td>{period}</td><td>{r.get("implemented", 0)}</td>'
            f'<td>{r.get("partial", 0)}</td><td>{r.get("not_implemented", 0)}</td>'
            f'<td class="{cls}">{rate}%</td></tr>'
        )
    return (
        '<div class="table-wrap">\n'
        '<table aria-label="Audit recommendation implementation rates" '
        'id="implementation-rates-table">\n'
        '  <thead>\n    <tr>\n'
        f'      <th scope="col">{html.escape(headers["period"])}</th>\n'
        f'      <th scope="col">{html.escape(headers["implemented"])}</th>\n'
        f'      <th scope="col">{html.escape(headers["partial"])}</th>\n'
        f'      <th scope="col">{html.escape(headers["not_implemented"])}</th>\n'
        f'      <th scope="col">{html.escape(headers["rate"])}</th>\n'
        '    </tr>\n  </thead>\n  <tbody>\n    '
        + "\n    ".join(rows)
        + '\n  </tbody>\n</table>\n</div>'
    )


def generate_audit_archive(locale: dict) -> str:
    """Per-year report cards with on-disk file sizes and type badges."""
    archive = _load().get("audit_archive", [])
    cards = []
    for i, entry in enumerate(archive):
        year = entry.get("year", "")
        latest = " audit-year-latest" if i == 0 else ""
        note = entry.get("note")
        note_html = f'<p class="audit-year-meta">{html.escape(note)}</p>' if note else ""
        files = []
        for f in entry.get("files", []):
            path = f.get("path", "")
            ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
            badge_cls, badge_lbl = EXT_BADGE.get(ext, ("file-docx", ext.upper() or "FILE"))
            disk = ROOT / path.lstrip("/")
            size = _human_size(disk.stat().st_size if disk.is_file() else None)
            files.append(
                f'<li><a class="link-arrow" href="{html.escape(path)}" '
                f'target="_blank" rel="noopener">{html.escape(f.get("label", ""))} '
                f'<span class="file-badge {badge_cls}">{badge_lbl}</span> '
                f'<span class="file-size">{size}</span></a></li>'
            )
        cards.append(
            f'<div class="card audit-year-card{latest}">\n'
            f'  <h3>CY {html.escape(str(year))}</h3>\n'
            f'  {note_html}\n'
            f'  <ul class="audit-file-list">\n    '
            + "\n    ".join(files)
            + '\n  </ul>\n</div>'
        )
    return ('<div class="grid grid-3 audit-year-grid">\n  '
            + "\n  ".join(cards)
            + '\n</div>')
