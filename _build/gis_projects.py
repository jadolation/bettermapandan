"""Pure, source-faithful DPWH project projection for the GIS explorer."""
import math
import re
from collections import Counter, defaultdict
from urllib.parse import quote

from _build.gis_preview import MAX_FEATURES, safe_url


def _text(value, limit=2000):
    return value.strip()[:limit] if isinstance(value, str) else ""


def _number(value):
    if isinstance(value, str):
        value = value.strip()
        # Accept explicit numeric/currency notation, not arbitrary embedded digits.
        if not re.fullmatch(r"(?i)(?:PHP\s*|\u20b1\s*)?[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", value):
            return None
        value = re.sub(r"(?i)^(?:PHP\s*|\u20b1\s*)", "", value).replace(",", "")
    elif type(value) not in (int, float):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def dpwh_collection(source: dict, canonical_projects: list, lang_code="en") -> dict:
    """Keep every source record; never infer coordinates or canonical identity.

    Invalid identity is a build error rather than an invented ID. Invalid position
    remains a listable null-geometry feature. Canonical joins require one exact
    transaction match and one globally unique canonical project ID.
    """
    rows = source.get("projects") if isinstance(source, dict) else None
    if not isinstance(rows, list) or len(rows) > MAX_FEATURES:
        raise ValueError("DPWH source must contain a projects list within the feature limit")
    if not isinstance(canonical_projects, list):
        raise ValueError("DPWH canonical_projects must be a list")
    by_transaction = defaultdict(list)
    project_ids = Counter()
    for project in canonical_projects:
        if not isinstance(project, dict):
            continue
        pid, transaction = project.get("project_id"), project.get("source_transaction_id")
        valid_pid = isinstance(pid, str) and pid.strip() and len(pid) <= 2000
        if valid_pid:
            project_ids[pid] += 1
        if isinstance(transaction, str) and transaction.strip():
            by_transaction[transaction].append(pid if valid_pid else None)

    prefix = "/" + lang_code if lang_code in ("fil", "pag") else ""
    features, seen = [], {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"DPWH projects[{index}] must be an object with a transaction_id")
        transaction = row.get("transaction_id")
        if not isinstance(transaction, str) or not transaction.strip() or len(transaction) > 2000:
            raise ValueError(f"DPWH projects[{index}] requires a nonempty transaction_id string (max 2000 characters)")
        if transaction in seen:
            raise ValueError(f"Duplicate DPWH transaction_id {transaction!r} at projects[{seen[transaction]}] and projects[{index}]; correct the source IDs")
        seen[transaction] = index
        limitations = ["Source-reported project point; not a surveyed boundary, footprint, or full project alignment."]
        lon, lat = row.get("longitude"), row.get("latitude")
        geometry = None
        if (type(lon) in (int, float) and type(lat) in (int, float)
                and _number(lon) is not None and _number(lat) is not None
                and -180 <= lon <= 180 and -90 <= lat <= 90):
            geometry = {"type": "Point", "coordinates": [lon, lat]}
        else:
            limitations.append("Missing or invalid source coordinates; no map position inferred.")

        matches = by_transaction.get(transaction, [])
        pid = matches[0] if len(matches) == 1 and project_ids[matches[0]] == 1 else None
        if pid is None:
            limitations.append("No unique canonical project match by source transaction ID; linked to the infrastructure source record.")
        year = _number(row.get("fiscal_year"))
        status = _text(row.get("status"))
        status_key = {"completed": "completed", "finished": "completed", "ongoing": "ongoing",
                       "on-going": "ongoing", "on going": "ongoing",
                      "in progress": "ongoing", "in-progress": "ongoing",
                      "not started": "not_started", "not yet started": "not_started",
                      "stopped": "stopped", "suspended": "stopped", "halted": "stopped",
                      "on hold": "stopped", "on-hold": "stopped"}.get(status.casefold(), "unknown")
        props = {
            "id": transaction, "source_transaction_id": transaction,
            "name": _text(row.get("project_name")),
            "category": _text(row.get("category")),
            "fiscal_year": int(year) if year is not None and year.is_integer() else None,
            "contract_id": _text(row.get("contract_id")),
            "contractor": _text(row.get("contractor")),
            "status": status, "status_key": status_key,
            "source": "DPWH Transparency Portal",
            "source_date": _text(row.get("source_date")),
            "location_precision": "source_reported",
            "coordinate_method": "source_reported", "semantic_role": "dpwh_project",
            "limitations": limitations,
            "project_id": pid,
            "project_url": (prefix + "/transparency/projects/?project=" + quote(pid, safe="")
                            if pid else prefix + "/transparency/infrastructure/#dpwh-project-" + quote(transaction, safe="")),
        }
        contractors = row.get("contractors")
        props["contractors"] = list(dict.fromkeys(
            clean for value in (contractors[:100] if isinstance(contractors, list) else [props["contractor"]])
            if (clean := _text(value))))
        for key in ("contract_amount", "approved_budget", "accomplishment_percent"):
            props[key] = _number(row.get(key))
        for key in ("barangay_location", "executing_agency", "source_of_funds",
                    "contract_effectivity_date", "contract_expiry_date",
                    "actual_start_date", "actual_completion_date"):
            props[key] = _text(row.get(key))
        url = row.get("source_document_url")
        url = url.strip() if isinstance(url, str) else ""
        props["source_url"] = props["source_document_url"] = url if safe_url(url) else ""
        features.append({"type": "Feature", "geometry": geometry, "properties": props})
    return {"type": "FeatureCollection", "features": features}
