"""Bounded, deterministic population and explicitly documented project statistics.

Filters must match source/year/status on ONE reference, then union project IDs.
No geometry, title-similarity identity resolution or financial totals belong here.
"""
import json
import re
from collections import defaultdict
from functools import partial
from pathlib import Path
from urllib.parse import quote

from _build.entity_resolution import norm_title
from _build.gis_preview import safe_url
from src.data._utils import normalize_barangays

MUNICIPALITY_PSGC = "0105528000"
EXPECTED_GIDS = {f"0105528{n:03d}" for n in (1, 2, 3, 4, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 18)}
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
SOURCES = ("dpwh", "dilg", "coa", "philgeps")


class IdentityError(ValueError):
    """Canonical identities are unsafe; do not publish partial incorrect joins."""


def _text(value, limit=500):
    return re.sub(r"[\x00-\x1f\x7f<>]", "", value.strip())[:limit] if isinstance(value, str) else ""


def _load(path):
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Source exceeds statistics input bound")
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(value):
    if not isinstance(value, list) or len(value) > 100000 or any(not isinstance(r, dict) for r in value):
        raise ValueError("Expected bounded list of source objects")
    return value


def _year(value):
    if type(value) is int and 1900 <= value <= 2100:
        return value
    if isinstance(value, str) and re.fullmatch(r"(?:19|20)\d{2}", value):
        return int(value)
    return None


def _name(value):
    value = _text(value).casefold().replace("santa", "sta")
    value = re.sub(r"^\s*(?:brgy\.?|barangay)\s*", "", value)
    return re.sub(r"[^a-z0-9]", "", value)


def _status(value, source):
    label = _text(value, 120)
    key = label.casefold()
    if source == "philgeps":
        # An active award is NOT an ongoing construction project.
        return ({"active": "award_active", "cancelled": "award_cancelled",
                 "awarded": "awarded"}.get(key, "unknown"), label)
    return ({"completed": "completed", "finished": "completed", "ongoing": "ongoing",
             "on-going": "ongoing", "on going": "ongoing", "in progress": "ongoing",
             "not started": "not_started", "not yet started": "not_started",
             "suspended": "stopped", "stopped": "stopped"}.get(key, "unknown"), label)


def _population(data):
    features = _load(data / "gis/barangays.geojson").get("features")
    _rows(features)
    barangays, aliases, provenance = {}, defaultdict(set), []
    for feature in features:
        props = feature.get("properties", {})
        gid = props.get("gid")
        if gid not in EXPECTED_GIDS or gid in barangays:
            raise IdentityError("Invalid, duplicate or wrong-municipality barangay PSGC")
        name = _text(props.get("name"))
        if not name:
            raise IdentityError("Barangay requires a name")
        base = name.split("(")[0].strip()
        for alias in [name, base, *re.findall(r"\(([^)]+)\)", name)]:
            aliases[_name(alias)].add(gid)
        if base == "Amanoaoac":
            aliases[_name("Amanaoaoac")].add(gid)
        count = props.get("pop2024")
        status = "available"
        if count is None:
            status = "missing"
        elif type(count) is not int or not 0 <= count <= 10000000:
            status, count = "invalid", None
        reported_year = props.get("population_year")
        if reported_year is None:
            years = re.findall(r"\b(?:19|20)\d{2}\b", _text(props.get("source_as_of")))
            reported_year = int(years[0]) if len(years) == 1 else 2024
        if reported_year != 2024:
            status, count = "mixed_year", None
        prov = props.get("provenance", {})
        if isinstance(prov, dict):
            clean = {k: _text(prov.get(k)) for k in ("source", "retrieved", "last_verified") if _text(prov.get(k))}
            url = prov.get("source_url", "")
            if isinstance(url, str) and safe_url(url):
                clean["source_url"] = url
            if clean and clean not in provenance:
                provenance.append(clean)
        barangays[gid] = {"gid": gid, "name": name, "slug": _text(props.get("slug"), 100),
                          "population": {"count": count, "year": 2024, "status": status, "share": None}}
    if set(barangays) != EXPECTED_GIDS:
        raise IdentityError("Statistics require all 15 canonical barangays")
    complete = all(b["population"]["status"] == "available" for b in barangays.values())
    total = sum(b["population"]["count"] for b in barangays.values()) if complete else None
    if total:
        for b in barangays.values():
            b["population"]["share"] = b["population"]["count"] / total
    return barangays, aliases, provenance, complete, total


def _identities(data):
    canonical = _rows(_load(data / "entities/projects.json"))
    projects, original = {}, {}
    transaction, dpwh_contracts = defaultdict(set), defaultdict(set)
    dilg_keys, coa_ids = defaultdict(set), defaultdict(set)
    for p in canonical:
        pid = p.get("project_id")
        if not isinstance(pid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}", pid) or pid in projects:
            raise IdentityError("Unsafe or duplicate canonical project ID")
        if p.get("municipality") != "Mapandan" or p.get("province") != "Pangasinan":
            raise IdentityError("Canonical project outside municipality context")
        projects[pid] = {"project_id": pid, "name": _text(p.get("canonical_name")),
                         "barangay_gids": [], "references": [],
                         "project_url": "/transparency/projects/?project=" + quote(pid, safe="")}
        original[pid] = p
        if p.get("source_transaction_id"):
            transaction[p["source_transaction_id"]].add(pid)
        prov = _rows(p.get("provenance", []))
        if not p.get("source_transaction_id") and p.get("dpwh_contract_id") and any(
                v.get("source") == "DPWH Transparency Portal" and v.get("record_id") == p["dpwh_contract_id"] for v in prov):
            dpwh_contracts[p["dpwh_contract_id"]].add(pid)
        if any(v.get("source") == "DILG-FDP" for v in prov):
            brgys = p.get("barangay", [])
            if not isinstance(brgys, list) or any(not isinstance(x, str) for x in brgys):
                raise IdentityError("Invalid canonical barangay associations")
            dilg_keys[(norm_title(p.get("canonical_name", "")), tuple(sorted(brgys)))].add(pid)
        for v in prov:
            if v.get("source") == "COA":
                coa_ids[v.get("record_id")].add(pid)
    for index in (transaction, dpwh_contracts, dilg_keys, coa_ids):
        if any(len(ids) != 1 for ids in index.values()):
            raise IdentityError("Exact source identity maps to multiple canonical projects")
    return projects, original, transaction, dpwh_contracts, dilg_keys, coa_ids


def _dpwh_records(data, transaction, dpwh_contracts):
    pending = []
    records = _rows(_load(data / "dpwh.json").get("projects"))
    contracts_seen = defaultdict(int)
    for row in records:
        if row.get("contract_id"):
            contracts_seen[row["contract_id"]] += 1
    seen = set()
    for row in records:
        tid = row.get("transaction_id")
        if not isinstance(tid, str) or not tid or tid in seen:
            raise IdentityError("Missing or duplicate DPWH transaction ID")
        seen.add(tid)
        ids = transaction.get(tid, set())
        if not ids and row.get("contract_id") in dpwh_contracts:
            if contracts_seen[row["contract_id"]] != 1:
                raise IdentityError("Ambiguous exact DPWH contract identity")
            ids = dpwh_contracts[row["contract_id"]]
        pending.append((ids, row, tid, row.get("barangay_location"), _year(row.get("fiscal_year")), "fiscal", "infrastructure_record"))
    return pending


def _dilg_records(data, dilg_keys):
    pending = []
    docs = _rows(_load(data / "fdp_disclosures.json").get("dev_fund"))
    for doc in docs:
        for row in _rows(doc.get("projects")):
            key = (norm_title(row.get("project", "")), tuple(sorted(normalize_barangays(row.get("location", "")))))
            ids = dilg_keys.get(key, set())
            rid = _text(doc.get("period"), 40) + ":" + _text(row.get("project"), 200)
            # Percentage is a fraction in current DILG disclosures. Target
            # completion dates alone never establish completed status.
            row = dict(row)
            pct = row.get("pct")
            if not row.get("status") and type(pct) in (int, float) and 0 <= pct <= 1:
                row["status"] = "completed" if pct == 1 else "ongoing" if pct > 0 else "not started"
            pending.append((ids, row, rid, row.get("location"), _year(doc.get("year")), "disclosure", "project_record"))
    return pending


def _coa_records(data, coa_ids, original, explicit, aliases, report):
    pending = []
    records = _rows(_load(data / "audit-reports.json").get("infrastructure_projects"))
    seen = set()
    for row in records:
        rid = row.get("id")
        if not isinstance(rid, str) or not rid or rid in seen:
            raise IdentityError("Missing or duplicate COA record ID")
        seen.add(rid)
        ids = coa_ids.get(rid, set())
        # Standalone COA identities are exact provenance records. A COA
        # provenance appended to a DILG entity may be a probable merge.
        ids = {pid for pid in ids if not any(v.get("source") == "DILG-FDP" for v in original[pid]["provenance"])
               or any(e.get("from") == "coa:" + rid and e.get("to") == "project:" + pid
                      and e.get("type") == "same_project" for e in explicit)}
        if not ids and coa_ids.get(rid):
            report["excluded_uncertain_links"] += 1
        location = row.get("barangay_location") or row.get("location")
        if not location:
            mentions = []
            for text in (row.get("name", ""), row.get("description", "")):
                for alias in aliases:
                    # Match only an explicit Barangay/Brgy marker plus
                    # a controlled name, never addresses or generic titles.
                    for m in re.finditer(r"(?i)\b(?:barangay|brgy\.?)\s+([a-z .]+)", text):
                        words = m.group(1).strip().split()
                        for n in range(1, min(len(words), 4) + 1):
                            candidate = " ".join(words[:n])
                            if _name(candidate) == alias:
                                mentions.append(candidate)
            location = " / ".join(sorted(set(mentions)))
        year = _year(row.get("year_started"))
        pending.append((ids, row, rid, location, year or _year(row.get("year_completed")),
                        "start" if year else "completion", "audit_record"))
    return pending


def _philgeps_records(data, projects, explicit):
    pending = []
    records = _rows(_load(data / "procurement.json").get("contracts"))
    contracts = _rows(_load(data / "entities/contracts.json"))
    by_record = defaultdict(list)
    contract_ids = set()
    for c in contracts:
        cid = c.get("contract_id")
        if not isinstance(cid, str) or cid in contract_ids:
            raise IdentityError("Invalid or duplicate canonical contract ID")
        contract_ids.add(cid)
        by_record[c.get("source_record_id")].append(c)
    direct, bids, awards = defaultdict(set), defaultdict(set), defaultdict(set)
    for e in explicit:
        frm, to, kind = e.get("from", ""), e.get("to", ""), e.get("type")
        if kind in ("has_contract", "has_bid") and frm.startswith("project:"):
            pid = frm[8:]
            if pid not in projects:
                raise IdentityError("Explicit relationship references unknown project")
            if kind == "has_contract" and to.startswith("contract:"):
                direct[to[9:]].add(pid)
            elif kind == "has_bid" and to.startswith("bid:"):
                bids[to].add(pid)
        if kind == "resulted_in" and frm.startswith("bid:") and to.startswith("contract:"):
            awards[to[9:]].add(frm)
    for index, row in enumerate(records, 1):
        matches = by_record.get(f"procurement.json#{index}", [])
        if len(matches) > 1:
            raise IdentityError("Procurement row maps to multiple canonical contracts")
        ids, rid = set(), f"procurement.json#{index}"
        if matches:
            c = matches[0]
            # Enumeration-based source_record_id is verified against
            # source fields before following exact relationship edges.
            if any(c.get(a) != row.get(b) for a, b in (("title", "title"), ("award_date", "award_date"),
                                                     ("awardee_name", "awardee"), ("award_amount", "amount"))):
                raise IdentityError("Canonical contract does not match its source row")
            rid = c["contract_id"]
            ids.update(direct[rid])
            for bid in awards[rid]:
                ids.update(bids[bid])
        pending.append((ids, row, rid, row.get("barangay_location"),
                        _year(_text(row.get("award_date"))[:4]), "award", "contract_record"))
    return pending


def _associate_records(pending, source, original, resolve, report):
    additions = []
    for ids, row, rid, location, year, basis, kind in pending:
        gids, association = resolve(location)
        report["ambiguous_records"] += association == "ambiguous"
        if not ids:
            report["unmapped_records"] += 1
            continue
        report["mapped_records"] += 1
        # Canonical associations cannot independently override source evidence.
        expected = {g for pid in ids for name in original[pid].get("barangay", []) for g in resolve(name)[0]}
        if gids and expected and set(gids) != expected:
            gids, association = [], "conflicting"
            report["conflicting_records"] += 1
        report["unassigned_records"] += not bool(gids)
        status, label = _status(row.get("status"), source)
        ref = {"source": source, "record_id": _text(rid, 250), "record_kind": kind,
               "year": year, "year_basis": basis, "status": status, "status_label": label,
               "association_status": association, "barangay_gids": gids}
        for pid in sorted(ids):
            additions.append((pid, ref, gids))
    return additions


def _resolve(location, aliases):
    if not isinstance(location, str) or not location.strip():
        return [], "missing"
    found = set()
    for part in re.split(r"\s*(?:/|;|\band\b|&)\s*", location, flags=re.I):
        part = re.sub(r"(?i),?\s*mapandan(?:,?\s*pang(?:asinan)?\.?)?\s*$", "", part).strip()
        matches = aliases.get(_name(part), set())
        if len(matches) != 1:
            return [], "ambiguous" if len(matches) > 1 else "unresolved"
        found.update(matches)
    return sorted(found), "assigned"


def _coverage_totals(projects, coverage, diagnostics):
    active = [p for p in projects.values() if p["references"]]
    for p in active:
        p["references"].sort(key=lambda r: json.dumps(r, sort_keys=True))
    for source, report in coverage.items():
        members = [p for p in active if any(r["source"] == source for r in p["references"])]
        report["canonical_count"] = len(members)
        report["assigned_count"] = sum(any(r["barangay_gids"] for r in p["references"] if r["source"] == source) for p in members)
        report["unassigned_count"] = len(members) - report["assigned_count"]
        if report["supported"] and (report["unassigned_count"] or report["unmapped_records"] or report["ambiguous_records"]):
            report["status"] = "incomplete"
        if report["unmapped_records"]:
            diagnostics.append({"source": source, "code": "unmapped_source_records", "count": report["unmapped_records"]})
    return active


def build_statistics(root):
    """Return schema 1 statistics from a checkout or an isolated build root.

    Missing/malformed optional sources are isolated. Duplicate canonical identity
    or exact source keys mapping to multiple projects fail the entire build.
    """
    data = Path(root) / "src/data"
    barangays, aliases, provenance, complete, total = _population(data)

    resolve = partial(_resolve, aliases=aliases)

    projects, original, transaction, dpwh_contracts, dilg_keys, coa_ids = _identities(data)

    diagnostics, coverage = [], {}
    limitations = [
        "Scoped documented matches, not complete investment coverage; unresolved associations remain unassigned.",
        "Multi-barangay project counts are non-additive; municipality counts are distinct project-ID unions.",
        "DILG inherited identity deduplicates normalized title plus barangay tuple across reporting periods; IDs are enumeration-based.",
        "Only explicit established relationship paths qualify; probable/strong title matches are excluded.",
        "Source/year/status filters must match the same reference. Award status is not implementation status.",
        "Density and financial aggregates are deliberately unavailable.",
    ]

    for source in SOURCES:
        pending = []
        report = {"supported": False, "status": "unavailable", "examined_records": 0,
                  "mapped_records": 0, "unmapped_records": 0, "canonical_count": 0,
                  "assigned_count": 0, "unassigned_count": 0, "ambiguous_records": 0,
                  "unassigned_records": 0, "conflicting_records": 0, "excluded_uncertain_links": 0}
        try:
            relationships = []
            if source in ("coa", "philgeps"):
                relationships = _rows(_load(data / "relationships.json"))
            explicit = [e for e in relationships if e.get("confidence") == "explicit" and e.get("evidence")]
            if source == "dpwh":
                pending = _dpwh_records(data, transaction, dpwh_contracts)
            elif source == "dilg":
                pending = _dilg_records(data, dilg_keys)
            elif source == "coa":
                pending = _coa_records(data, coa_ids, original, explicit, aliases, report)
            else:
                pending = _philgeps_records(data, projects, explicit)
            report["examined_records"] = len(pending)
            additions = _associate_records(pending, source, original, resolve, report)
            report["supported"] = bool(additions) or (source != "philgeps" and not pending)
            # All parsing/validation succeeds before mutating the shared index.
            for pid, ref, gids in additions:
                p = projects[pid]
                if ref not in p["references"]:
                    p["references"].append(ref)
                p["barangay_gids"] = sorted(set(p["barangay_gids"]) | set(gids))
            report["status"] = "scoped" if report["supported"] else "unavailable"
        except IdentityError:
            raise
        except (OSError, ValueError, TypeError, AttributeError, KeyError):
            report["status"] = "unavailable"
            diagnostics.append({"source": source, "code": "source_unavailable"})
        coverage[source] = report

    active = _coverage_totals(projects, coverage, diagnostics)
    supported = any(r["supported"] for r in coverage.values())
    status = "incomplete" if any(r["status"] != "scoped" for r in coverage.values()) else "scoped"
    if not supported:
        status = "unavailable"
    for gid, b in barangays.items():
        ids = sorted(p["project_id"] for p in active if gid in p["barangay_gids"])
        b["projects"] = {"count": len(ids) if supported else None, "ids": ids, "status": status}
    result = {"schema_version": 1, "municipality_psgc": MUNICIPALITY_PSGC,
              "population": {"year": 2024, "total": total, "status": "available" if complete else "incomplete",
                             "provenance": sorted(provenance, key=lambda p: json.dumps(p, sort_keys=True))},
              "barangays": dict(sorted(barangays.items())),
              "projects": sorted(active, key=lambda p: p["project_id"]),
              "project_coverage": {"status": status, "count": len(active) if supported else None,
                                   "assigned_count": sum(bool(p["barangay_gids"]) for p in active),
                                   "unassigned_count": sum(not p["barangay_gids"] for p in active),
                                   "sources": coverage, "limitations": limitations},
              "diagnostics": sorted(diagnostics, key=lambda d: json.dumps(d, sort_keys=True))}
    if len(json.dumps(result, ensure_ascii=True, allow_nan=False).encode()) >= MAX_OUTPUT_BYTES:
        raise ValueError("Statistics exceed runtime 8 MiB bound")
    return result
