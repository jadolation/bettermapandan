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
