"""Data consistency regression tests — locks the Phase 1 integrity fixes.

Canonical source: src/data/transparency-csv.json (CSV) for expenses/surplus.
Guards: surplus == income - expenses, JSON<->CSV parity, composition
tolerances, implementation-rate math, and the pinned 2020 row.
"""
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = ROOT / "src" / "data" / "audit-reports.json"
CSV_PATH = ROOT / "src" / "data" / "transparency-csv.json"
FACTS_PATH = ROOT / "src" / "data" / "municipal-facts.json"
PAGES_WITH_FACTS = ["index", "about", "statistics", "transparency"]


def _load_audit():
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def _load_csv_rows(key):
    raw = json.loads(CSV_PATH.read_text(encoding="utf-8"))[key]
    return list(csv.DictReader(io.StringIO(raw)))


def test_surplus_equals_income_minus_expenses():
    """Every financial_performance row must satisfy surplus == income - expenses."""
    for row in _load_audit()["financial_performance"]:
        assert row["surplus"] == row["income"] - row["expenses"], (
            f"{row['year']}: surplus {row['surplus']} != "
            f"income {row['income']} - expenses {row['expenses']}"
        )


def test_expenses_match_csv():
    """Audit JSON expenses must equal canonical CSV expenses peso-for-peso."""
    csv_rows = {int(r["Year"]): int(r["Expenses"]) for r in _load_csv_rows("financial-performance")}
    for row in _load_audit()["financial_performance"]:
        if row["year"] in csv_rows:
            assert row["expenses"] == csv_rows[row["year"]], (
                f"{row['year']}: audit expenses {row['expenses']} != CSV {csv_rows[row['year']]}"
            )


def test_income_within_csv_rounding():
    """Audit incomes must track CSV incomes (CSV rounds some years to 100k)."""
    csv_rows = {int(r["Year"]): int(r["Income"]) for r in _load_csv_rows("financial-performance")}
    for row in _load_audit()["financial_performance"]:
        if row["year"] in csv_rows:
            assert abs(row["income"] - csv_rows[row["year"]]) <= 3000, (
                f"{row['year']}: income drift {row['income']} vs CSV {csv_rows[row['year']]}"
            )


def test_2020_row_pinned():
    """2020 three-way split must stay fixed: deficit of exactly -2727087."""
    audit_2020 = next(r for r in _load_audit()["financial_performance"] if r["year"] == 2020)
    assert (audit_2020["income"], audit_2020["expenses"], audit_2020["surplus"]) == (
        128331255, 131058342, -2727087,
    )
    csv_2020 = next(r for r in _load_csv_rows("financial-performance") if r["Year"] == "2020")
    assert (int(csv_2020["Income"]), int(csv_2020["Expenses"]), int(csv_2020["Surplus/Deficit"])) == (
        128331255, 131058342, -2727087,
    )


def test_implementation_rates_match_csv_and_math():
    """Audit rates must match CSV and satisfy implemented/total rounding."""
    csv_rows = {r["Period"]: r for r in _load_csv_rows("implementation-rates")}
    for row in _load_audit()["implementation_rates"]:
        key = row["period"].replace("→", " to ")
        assert key in csv_rows, f"period {row['period']} missing from CSV"
        csv_row = csv_rows[key]
        assert row["implemented"] == int(csv_row["Implemented"]), key
        assert row["partial"] == int(csv_row["Partial"]), key
        assert row["not_implemented"] == int(csv_row["Not Implemented"]), key
        total = row["implemented"] + row["partial"] + row["not_implemented"]
        assert row["rate"] == round(100 * row["implemented"] / total), key


def test_implementation_2021_2022_pinned():
    """2021->2022 must stay 12/0/16/43 (was a duplicated 10/0/11/48)."""
    row = next(r for r in _load_audit()["implementation_rates"] if r["period"] == "2021→2022")
    assert (row["implemented"], row["partial"], row["not_implemented"], row["rate"]) == (12, 0, 16, 43)


def test_revenue_composition_labeled_estimates():
    """No revenue_composition row may claim 'precise'/'BLGF' while not summing."""
    income = {r["year"]: r["income"] for r in _load_audit()["financial_performance"]}
    for row in _load_audit()["revenue_composition"]:
        total = row["ira"] + row["local_income"] + row["other"]
        if row["source"] in ("precise", "BLGF"):
            assert abs(total - income[row["year"]]) <= 5000, (
                f"{row['year']}: claims {row['source']} but components sum {total} "
                f"vs income {income[row['year']]}"
            )


def test_municipal_facts_canonical():
    """Shared facts file must hold the canonical headline figures."""
    from _build.facts import facts_placeholders

    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    assert facts["population_2024"] == "38,228"
    assert facts["land_area_km2"] == "32.92"
    assert facts["density_per_km2"] == "1,161.24"
    placeholders = facts_placeholders()
    assert placeholders["POP_2024"] == "38,228"
    assert placeholders["DENSITY"] == "1,161.24"


def test_no_hardcoded_facts_in_pages():
    """Headline figures must come from placeholders, not literals."""
    pages_dir = ROOT / "src" / "pages"
    candidates = [pages_dir / f"{name}.html" for name in PAGES_WITH_FACTS]
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        for literal in ("38,228", "32.92 km", "1,161.24", "1,161/km"):
            assert literal not in text, f"{path.name} hardcodes {literal!r}"
        assert "{POP_2024}" in text or "{DENSITY}" in text or "{LAND_AREA}" in text, (
            f"{path.name} uses no facts placeholders"
        )
