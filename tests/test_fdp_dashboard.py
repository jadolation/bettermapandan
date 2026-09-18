"""FDP dashboard tests — normalizer, deltas, summary payload, section HTML."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_normalize_barangay():
    from _build.generators.fdp_analytics import normalize_barangay

    assert normalize_barangay("Brgy. Poblacion, Mapandan.") == "poblacion"
    assert normalize_barangay("Brgy.Jimenez, Mapandan") == "jimenez"
    assert normalize_barangay("Amanoaoac, Mapandan") == "amanoaoac"
    assert normalize_barangay("Brgy. Luyan, Mapandan") == "luyan"
    assert normalize_barangay("Brgy. Sta. Maria, Mapandan") == "sta-maria"
    assert normalize_barangay("Mapandan, Pangasinan") == "municipal-wide"
    assert normalize_barangay("Entire Mapandan, Pang.") == "municipal-wide"
    assert normalize_barangay("Brgy. Golden., Mapandan") == "golden"
    assert normalize_barangay("Nowhereville") is None
    assert normalize_barangay("") is None


def test_quarterly_deltas_derive_flows():
    from _build.generators.fdp_analytics import quarterly_deltas

    series = {p["period"]: p for p in quarterly_deltas()}
    # 2026-Q2 flow = Q2 YTD minus Q1 YTD (never quarterly sums)
    assert series["2026-Q2"]["receipts"] == round(115479786.02 - 62185422.94, 2)
    assert series["2026-Q1"]["receipts"] == 62185422.94
    assert series["2025-Q2"]["receipts"] == round(102816372.45 - 55327641.27, 2)


def test_expenditure_excludes_principal():
    from _build.generators.fdp_analytics import expenditure_by_function

    exp = expenditure_by_function("2026-Q2")
    assert exp["total"] == 82700279.84
    assert not any("principal" in k.lower() for k in exp["items"])


def test_summary_payload_slim_and_exact():
    from _build.generators.fdp_analytics import generate_fdp_summary

    summary = generate_fdp_summary()
    assert summary["latest_period"] == "2026-Q2"
    assert summary["kpis"]["receipts"] == 115479786.02
    assert summary["kpis"]["expenditures"] == 82700279.84
    assert summary["kpis"]["sef_balance"] == 1320774.75
    assert summary["kpis"]["ldrrmf_unutilized"] == 16105969.76
    assert summary["kpis"]["cash_ending"] == 63525772.21
    assert summary["kpis"]["projects"] == 19
    assert len(json.dumps(summary)) < 50 * 1024
    dist = summary["barangay"]["dist"]
    assert "lambayan" not in dist  # zero projects: absent, chart renders it as 0
    assert dist["municipal-wide"]["projects"] > 0
    assert summary["barangay"]["unmatched"] == []
    assert summary["revenue"]["nta_share"] == round(97509396.0 / 115479786.02 * 100, 1)


def test_dashboard_section_html():
    from _build.generators.fdp import generate_fdp_dashboard
    from _build.locales import load_locale

    html = generate_fdp_dashboard(load_locale("en"))
    assert 'id="fiscal-dashboard"' in html
    for canvas in ("chart-fdp-revenue", "chart-fdp-expenditure",
                   "chart-fdp-trend", "chart-fdp-barangay"):
        assert f'id="{canvas}"' in html
    assert "115,479,786.02" in html or "115479786" in html.replace(",", "")
    fil_html = generate_fdp_dashboard(load_locale("fil"))
    assert "Dashboard ng Pananalapi" in fil_html


def test_period_dialogs_present():
    from _build.generators.fdp import generate_fdp
    from _build.locales import load_locale

    html = generate_fdp(load_locale("en"))
    assert 'id="fdp-disclosures"' in html
    assert "data-fdp-dialog=" in html
    assert "<dialog" in html
    assert "11272309.4%" not in html  # loan-row column bug stays fixed
    assert ">TOTAL<" not in html  # summary row never rendered as a project


def _dialog_stats(html):
    import re
    events = [(m.start(), "open" if m.group(0).startswith("<dialog ") or m.group(0) == "<dialog" else "close")
              for m in re.finditer(r"</dialog>|<dialog(?:\s|>)", html)]
    tables = [(m.start(), m.group(0)[:60]) for m in re.finditer(r"<table(?:\s|>)", html)]
    latest_open = html.find('<div class="fdp-latest">')
    depth = ei = in_dialog = in_latest = sr_only = 0
    unwrapped = []
    for pos, tag in tables:
        while ei < len(events) and events[ei][0] < pos:
            depth += 1 if events[ei][1] == "open" else -1
            ei += 1
        if depth > 0:
            in_dialog += 1
        elif latest_open != -1 and latest_open < pos:
            # latest-quarter tables render inline by design; stop at first dialog/details
            rest = html[latest_open:pos]
            if "<dialog" not in rest and "<details" not in rest:
                in_latest += 1
            else:
                unwrapped.append(tag)
        else:
            seg = html[pos:pos + 200]
            if "sr-only" in seg[:seg.find(">")]:
                sr_only += 1
            else:
                unwrapped.append(tag)
    return in_dialog, in_latest, sr_only, unwrapped


def test_all_tables_live_in_dialogs():
    from _build.generators.fdp import generate_fdp
    from _build.locales import load_locale

    for lang in ("en", "fil"):
        html = generate_fdp(load_locale(lang))
        in_dialog, in_latest, sr_only, unwrapped = _dialog_stats(html)
        assert not unwrapped, f"{lang}: {unwrapped[:3]}"
        assert in_dialog > 50, lang
        assert in_latest > 5, lang  # latest quarter renders inline by design
        assert sr_only == 0, lang  # sr-only chart twins live in page source, not FDP output


def test_year_accordions_and_themed_dialogs():
    from _build.generators.fdp import generate_fdp
    from _build.locales import load_locale

    html = generate_fdp(load_locale("en"))
    for year in ("2026", "2025", "2024", "2023"):
        assert f"<div class='section-eyebrow'>{year}</div>" in html, year
    assert "quarter-row" in html
    # year cards replaced the accordions: no year <details> remain
    import re
    assert not re.search(r"<details[^>]*>\s*<summary><strong>20\d\d</strong>", html)
    assert html.count("fdp-archive-card") == 11  # 4 year + 1 undated + 6 themed
    for dialog_id in ("fdp-dialog-budget", "fdp-dialog-workforce", "fdp-dialog-debt",
                      "fdp-dialog-proc-plans", "fdp-dialog-gad", "fdp-dialog-funds"):
        assert f'id="{dialog_id}"' in html, dialog_id
    import re
    ids = re.findall(r'<dialog[^>]*id="([^"]+)"', html)
    assert len(ids) == len(set(ids)), "duplicate dialog IDs"
    buttons = set(re.findall(r'data-fdp-dialog="([^"]+)"', html)) | set(re.findall(r'data-open-modal="([^"]+)"', html))
    assert buttons <= set(ids), f"dangling buttons: {buttons - set(ids)}"


def test_reverted_tables_render_inline():
    """Fiscal snapshot, budget trend, and implementation rates show inline by design."""
    src = (Path(__file__).resolve().parent.parent / "src" / "pages" / "transparency.html").read_text(encoding="utf-8")
    for modal_id in ("modal-snapshot", "modal-budget-trend", "modal-implrate"):
        assert modal_id not in src, modal_id
    for aria, table_id in (("Multi-year fiscal snapshot", "fiscal-snapshot-table"),
                           ("Multi-year budget trend", "budget-trend-table"),
                           ("Audit recommendation implementation rates", "implementation-rates-table")):
        assert f'<table aria-label="{aria}" id="{table_id}">' in src, aria
