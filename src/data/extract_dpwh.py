#!/usr/bin/env python3
"""Extract Mapandan DPWH infrastructure data from raw exports."""
import json
from pathlib import Path

import pandas as pd

CACHE_DIR = Path("datasets/dpwh")
OUTPUT = Path("src/data/dpwh.json")


def _clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (ValueError, TypeError):
        pass
    return str(value)[:500]


def _parse_date(value):
    if value is None:
        return None
    try:
        ts = pd.to_datetime(value)
        return ts.strftime("%Y-%m-%d")
    except Exception:
        return None


def _parse_money(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("₱", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _fiscal_year(value):
    if value is None:
        return None
    s = str(value)
    if len(s) >= 2 and s[:2].isdigit():
        prefix = int(s[:2])
        return 2000 + prefix if prefix < 100 else prefix
    return None


def _coerce_bool(value):
    if value is None:
        return False
    return bool(value)


def main():
    if not CACHE_DIR.exists():
        raise SystemExit(f"ERROR: {CACHE_DIR} not found")

    parquet = CACHE_DIR / "dpwh.parquet"
    csv = CACHE_DIR / "dpwh.csv"
    if parquet.exists():
        df = pd.read_parquet(parquet)
    elif csv.exists():
        df = pd.read_csv(csv)
    else:
        raise SystemExit(f"ERROR: no dpwh.parquet or dpwh.csv in {CACHE_DIR}")

    mask = (
        df["project_name"].astype(str).str.contains("Mapandan", case=False, na=False)
        | df["barangay_location"].astype(str).str.contains("Mapandan", case=False, na=False)
        | df["organization_name"].astype(str).str.contains("Mapandan", case=False, na=False)
    )
    mapandan = df[mask].copy()
    print(f"  Mapandan DPWH records: {len(mapandan)}")

    if len(mapandan) == 0:
        raise SystemExit("No Mapandan records found.")

    projects = []
    for _, row in mapandan.iterrows():
        contract_id = _clean(row.get("contract_id") or row.get("reference_id") or "")
        project_name = _clean(row.get("project_name") or row.get("contract_description") or "")
        category = _clean(row.get("category") or row.get("project_category") or "")
        executing_agency = _clean(row.get("executing_agency") or row.get("implementing_office") or "")
        contractor = _clean(row.get("contractor") or row.get("winning_contractor") or "")
        contractor_id = _clean(row.get("contractor_id") or "")
        approved_budget = _parse_money(row.get("approved_budget"))
        contract_amount = _parse_money(row.get("contract_amount") or row.get("contract_cost"))
        accomplishment = row.get("accomplishment_percent") or row.get("accomplishment")
        try:
            accomplishment_percent = float(accomplishment) if pd.notna(accomplishment) else 0.0
        except (ValueError, TypeError):
            accomplishment_percent = 0.0
        status = _clean(row.get("status") or row.get("contract_status") or "")
        fiscal_year = _fiscal_year(contract_id)
        source_of_funds = _clean(row.get("source_of_funds") or row.get("funding_source") or "")
        contract_effectivity_date = _parse_date(row.get("contract_effectivity_date") or row.get("effectivity_date"))
        contract_expiry_date = _parse_date(row.get("contract_expiry_date") or row.get("expiry_date"))
        actual_start_date = _parse_date(row.get("actual_start_date") or row.get("start_date"))
        actual_completion_date = _parse_date(row.get("actual_completion_date") or row.get("completion_date"))
        barangay_location = _clean(row.get("barangay_location") or "")
        latitude = row.get("latitude")
        longitude = row.get("longitude")
        try:
            latitude = float(latitude) if pd.notna(latitude) else None
        except (ValueError, TypeError):
            latitude = None
        try:
            longitude = float(longitude) if pd.notna(longitude) else None
        except (ValueError, TypeError):
            longitude = None
        project_components = []
        bidders = []
        procurement_activities = []
        source_document_url = _clean(row.get("source_document_url") or "https://transparency.dpwh.gov.ph/")

        projects.append({
            "transaction_id": f"DPWH-{fiscal_year or 0000}-{contract_id}" if fiscal_year else f"DPWH-{contract_id}",
            "contract_id": contract_id,
            "project_name": project_name,
            "category": category,
            "executing_agency": executing_agency,
            "contractor": contractor,
            "contractor_id": contractor_id,
            "approved_budget": approved_budget,
            "contract_amount": contract_amount,
            "accomplishment_percent": accomplishment_percent,
            "status": status,
            "fiscal_year": fiscal_year,
            "source_of_funds": source_of_funds,
            "contract_effectivity_date": contract_effectivity_date,
            "contract_expiry_date": contract_expiry_date,
            "actual_start_date": actual_start_date,
            "actual_completion_date": actual_completion_date,
            "barangay_location": barangay_location,
            "latitude": latitude,
            "longitude": longitude,
            "project_components": project_components,
            "bidders": bidders,
            "procurement_activities": procurement_activities,
            "source_document_url": source_document_url,
            "crossref": {},
        })

    output = {"projects": projects}
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(projects)} projects to {OUTPUT}")


if __name__ == "__main__":
    main()
