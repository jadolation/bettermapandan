#!/usr/bin/env python3
"""Extract Mapandan procurement data from PhilGEPS parquet."""
import json
import pandas as pd
from pathlib import Path

CACHE_DIR = Path("datasets/PhilGEPS")
OUTPUT = Path("src/data/procurement.json")


def main():
    philgeps_path = CACHE_DIR / "philgeps.parquet"
    if not philgeps_path.exists():
        raise SystemExit(f"ERROR: {philgeps_path} not found")

    print(f"Loading {philgeps_path} ...")
    df = pd.read_parquet(philgeps_path)

    mask = df["organization_name"].str.contains("Mapandan", case=False, na=False)
    mapandan = df[mask].copy()
    print(f"  Mapandan records: {len(mapandan)}")

    if len(mapandan) == 0:
        raise SystemExit("No Mapandan records found.")

    mapandan["award_date"] = pd.to_datetime(mapandan["award_date"], errors="coerce")
    mapandan = mapandan.sort_values("award_date", ascending=False)

    total_amount = float(mapandan["contract_amount"].fillna(0).sum())
    contract_count = int(len(mapandan))

    records = []
    for _, row in mapandan.iterrows():
        amount = row.get("contract_amount")
        try:
            amount_f = float(amount) if pd.notna(amount) else 0.0
        except (ValueError, TypeError):
            amount_f = 0.0

        award_date = row.get("award_date")
        if pd.notna(award_date):
            award_date_str = str(award_date)[:10]
        else:
            award_date_str = ""

        records.append({
            "title": str(row.get("award_title", ""))[:200],
            "awardee": str(row.get("awardee_name", ""))[:200],
            "amount": amount_f,
            "award_date": award_date_str,
            "status": str(row.get("award_status", ""))[:50],
            "area": str(row.get("area_of_delivery", ""))[:200],
            "business_category": str(row.get("business_category", ""))[:100],
            "reference_id": str(row.get("reference_id", ""))[:50],
            "contract_no": str(row.get("contract_no", ""))[:50],
        })

    output = {
        "metrics": {
            "total_amount": total_amount,
            "contract_count": contract_count,
            "source": "PhilGEPS",
            "aggregator": "BetterGov.ph Open Data Portal",
            "dataset_id": 5,
            "license": "CC0 1.0 Universal",
            "last_updated": pd.Timestamp.now().isoformat()[:10],
        },
        "contracts": records[:100],
    }

    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {len(records)} contracts to {OUTPUT}")
    print(f"Total: ₱{total_amount:,.0f} across {contract_count} contracts")


if __name__ == "__main__":
    main()
