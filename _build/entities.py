"""Canonical entity + relationship layer (Data Architecture v2).

Source datasets (procurement.json, dpwh.json, fdp_disclosures.json,
audit-reports.json) stay authoritative and untouched. This module derives
a knowledge layer from them at build time:

  entities/{projects,contracts,contractors,funds,audit-findings}.json
  relationships.json            (every edge carries evidence[])
  review/project-matches.json   (near-misses awaiting human triage)
  assets indexes                (project/contractor/audit/fund)

Matching reuses _build/entity_resolution.py (deterministic Rules 1-5).
Anything below that bar becomes a `possible` review candidate — never a
silent auto-match. All amounts keep full float precision; labels
distinguish SOURCE REPORTED vs MATCHED/CALCULATED BY BETTER MAPANDAN.
"""
import json
import shutil
from pathlib import Path

from _build.config import SRC_DATA
from _build.entity_resolution import (
    EVIDENCE_LEVELS,  # noqa: F401  (re-exported for tests/consumers)
    match_records,
    norm_contractor,
    norm_fdp_bid,
    norm_philgeps_contract,
    norm_title,
)
from src.data._utils import load_json, normalize_barangays, write_json

try:
    from src.data.link_procurement_dpwh import _token_overlap
except (ImportError, AttributeError):  # fallback if linker internals move
    def _token_overlap(a: str, b: str) -> float:
        sa, sb = set(a.split()), set(b.split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / max(len(sa), len(sb))


ENTITY_DIRNAME = "entities"
REVIEW_DIRNAME = "review"


def _prov(source: str, record_id: str, document: str = "", retrieved_at=None, **extra) -> dict:
    prov = {"source": source, "record_id": record_id}
    if document:
        prov["document"] = document
    if retrieved_at:
        prov["retrieved_at"] = retrieved_at
    prov.update(extra)
    return prov


def _file_mtime_datestr(path: Path):
    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return None


def build_contractors(contracts: list, retrieved_at=None) -> tuple[list, dict]:
    """Deduplicate awardees -> contractors.json + lookup by normalized name."""
    groups: dict[str, dict] = {}
    for c in contracts:
        raw = c.get("awardee", "") or ""
        norm = norm_contractor(raw)
        if not norm:
            continue
        g = groups.setdefault(norm, {"names": {}, "total": 0.0, "count": 0})
        g["names"][raw] = g["names"].get(raw, 0) + 1
        g["total"] += float(c.get("amount") or 0)
        g["count"] += 1
    contractors = []
    lookup = {}
    for i, norm in enumerate(sorted(groups), start=1):
        g = groups[norm]
        canonical = max(g["names"], key=lambda n: (g["names"][n], n))
        cid = f"CTR-{i:04d}"
        lookup[norm] = cid
        contractors.append({
            "contractor_id": cid,
            "canonical_name": canonical,
            "source_names": sorted(g["names"]),
            "contract_count": g["count"],
            "total_represented": round(g["total"], 2),
            "note": ("Total contract values represented in the indexed "
                     "PhilGEPS records."),
            "provenance": [_prov("PhilGEPS", f"awardee:{norm}",
                                 document="procurement.json",
                                 retrieved_at=retrieved_at,
                                 record_role="contract_record")],
        })
    return contractors, lookup


def build_contracts(contracts: list, contractor_lookup: dict, retrieved_at=None) -> list:
    """PhilGEPS rows -> contracts.json with awardee links + provenance."""
    out = []
    used_ids: dict[str, int] = {}
    for i, c in enumerate(contracts, start=1):
        ref = (c.get("reference_id") or c.get("contract_no") or "").strip()
        cid = ref if ref and ref not in used_ids else f"PHG-{i:05d}"
        used_ids[cid] = used_ids.get(cid, 0) + 1
        if used_ids[cid] > 1:
            cid = f"{cid}#{used_ids[cid]}"
        norm = norm_contractor(c.get("awardee", ""))
        out.append({
            "contract_id": cid,
            "title": c.get("title", ""),
            "awardee_id": contractor_lookup.get(norm),
            "awardee_name": c.get("awardee", ""),
            "award_amount": float(c.get("amount") or 0),
            "award_date": c.get("award_date", ""),
            "status": c.get("status", ""),
            "category": c.get("business_category", ""),
            "organization": c.get("organization_name", ""),
            "source_record_id": f"procurement.json#{i}",
            "provenance": [_prov("PhilGEPS", cid, document="procurement.json",
                                 retrieved_at=retrieved_at,
                                 record_role="contract_record",
                                 source_as_of=(c.get("award_date", "") or ""))],
        })
    return out


def build_projects(fdp: dict, dpwh: list, coa_infra: list, retrieved: dict) -> list:
    """Union of DILG dev rows (deduped), DPWH records, COA infra refs."""
    projects = []
    seen_dev: dict[tuple, dict] = {}

    def _add(pid, name, ptype, barangays, year, prov, extra=None):
        rec = {"project_id": pid, "canonical_name": name,
               "project_type": ptype, "municipality": "Mapandan",
               "province": "Pangasinan", "barangay": sorted(barangays),
               "fiscal_year": year, "provenance": [prov]}
        if extra:
            rec.update(extra)
        projects.append(rec)
        return rec

    counters: dict[str, int] = {}
    for doc in fdp.get("dev_fund", []):
        period = doc.get("period", "")
        year = doc.get("year")
        for row in doc.get("projects", []):
            title = norm_title(row.get("project", ""))
            brgys = tuple(sorted(normalize_barangays(row.get("location", ""))))
            if not title:
                continue
            key = (title, brgys)
            if key in seen_dev:
                seen_dev[key]["provenance"].append(
                    _prov("DILG-FDP", f"{period}:{row.get('project','')[:40]}",
                          document=doc.get("source_file", ""), retrieved_at=retrieved.get("fdp"),
                          record_role="project_record", source_as_of=period))
                prev = seen_dev[key].get("reported_costs", [])
                prev.append(float(row.get("cost") or 0))
                seen_dev[key]["reported_costs"] = prev
                continue
            counters["dev"] = counters.get("dev", 0) + 1
            pid = f"BM-PROJ-{year or 'XXXX'}-{counters['dev']:03d}"
            seen_dev[key] = _add(
                pid, row.get("project", ""), "lgu_development", list(brgys), year,
                _prov("DILG-FDP", f"{period}:{row.get('project','')[:40]}",
                      document=doc.get("source_file", ""), retrieved_at=retrieved.get("fdp"),
                      record_role="project_record", source_as_of=period),
                {"reported_costs": [float(row.get("cost") or 0)]},
            )
    for p in dpwh:
        year = p.get("fiscal_year")
        counters["dpwh"] = counters.get("dpwh", 0) + 1
        pid = f"BM-PROJ-{year or 'XXXX'}-D{counters['dpwh']:03d}"
        _add(pid, p.get("project_name", ""), "dpwh_infrastructure",
             normalize_barangays(p.get("barangay_location", "")), year,
             _prov("DPWH Transparency Portal", p.get("contract_id", ""),
                   verification_method="manual",
                   checked_at=retrieved.get("dpwh"),
                   record_role="infrastructure_record",
                   source_as_of=str(p.get("fiscal_year") or "")),
             {"dpwh_contract_id": p.get("contract_id", ""),
              "contract_amount": p.get("contract_amount"),
              "contractor": p.get("contractor", "")})
    for r in coa_infra:
        year = r.get("year_started") or r.get("year_completed")
        coa_norm = {"source": "coa", "ref": "", "title": norm_title(r.get("name", "")),
                    "contractor": "", "amount": 0,
                    "year": str(year or "") or None, "barangays": []}
        merged_into = None
        for p in projects:
            if p["project_type"] != "lgu_development" or "-C" in p["project_id"] or "-D" in p["project_id"]:
                continue
            dev_norm = {"source": "dev", "ref": "", "title": norm_title(p["canonical_name"]),
                        "contractor": "", "amount": 0,
                        "year": str(p.get("fiscal_year") or "") or None,
                        "barangays": p.get("barangay", [])}
            out = match_records(coa_norm, dev_norm)
            if out["matched"] and out["level"] in ("explicit", "strong", "probable"):
                p["provenance"].append(
                    _prov("COA", r.get("id", ""), report="Mapandan AAR",
                          retrieved_at=retrieved.get("coa"),
                          record_role="audit_record",
                          source_as_of=str(year or "")))
                merged_into = p["project_id"]
                break
        if merged_into:
            continue
        counters["coa"] = counters.get("coa", 0) + 1
        pid = f"BM-PROJ-{year or 'XXXX'}-C{counters['coa']:03d}"
        _add(pid, r.get("name", ""), "lgu_development", [], year,
             _prov("COA", r.get("id", ""), report="Mapandan AAR",
                   retrieved_at=retrieved.get("coa"),
                   record_role="audit_record",
                   source_as_of=str(year or "")),
             {"reported_cost": r.get("cost"), "status": r.get("status", "")})
    return projects


def build_funds(fdp: dict, retrieved_at=None) -> list:
    """Per-period fund snapshots (source-reported figures only)."""
    funds = []
    by_period: dict[str, dict] = {}
    for doc in fdp.get("dev_fund", []):
        per = doc.get("period", "")
        rec = by_period.setdefault(per, {"period": per, "year": doc.get("year")})
        rec["dev_total"] = round(rec.get("dev_total", 0.0) + sum(
            float(p.get("cost") or 0) for p in doc.get("projects", [])), 2)
    for doc in fdp.get("sef", []):
        rec = by_period.setdefault(doc.get("period", ""), {"period": doc.get("period", ""), "year": doc.get("year")})
        if doc.get("balance") is not None:
            rec["sef_balance"] = doc.get("balance")
    for doc in fdp.get("ldrrmf", []):
        rec = by_period.setdefault(doc.get("period", ""), {"period": doc.get("period", ""), "year": doc.get("year")})
        totals = doc.get("totals") or {}
        if totals.get("unutilized") is not None:
            rec["ldrrmf_unutilized"] = totals.get("unutilized")
    for per in sorted(by_period):
        rec = by_period[per]
        funds.append({
            "fund_id": f"DILG-FUND-{per}",
            "period": per,
            "year": rec.get("year"),
            "figures": {k: v for k, v in rec.items() if k not in ("period", "year")},
            "provenance": [_prov("DILG-FDP", per, document="fdp_disclosures.json",
                                 retrieved_at=retrieved_at,
                                 record_role="fund_record", source_as_of=per)],
        })
    return funds


def build_audit_findings(audit: dict, retrieved_at=None) -> list:
    """COA key findings -> audit-findings.json with report provenance."""
    out = []
    for f in audit.get("key_findings", []):
        out.append({
            "finding_id": f"COA-F-{f.get('id', 'unknown')}",
            "title": f.get("title", ""),
            "category": f.get("category", ""),
            "first_observed": f.get("first_cited"),
            "last_observed": f.get("last_cited"),
            "amount": f.get("amount"),
            "status": f.get("status", ""),
            "severity": f.get("severity", ""),
            "provenance": [_prov("COA", f.get("id", ""),
                                 report="Mapandan AAR "
                                 f"{f.get('first_cited', '')}-{f.get('last_cited', '')}",
                                 retrieved_at=retrieved_at,
                                 record_role="audit_record",
                                 source_as_of=str(f.get("last_cited") or ""))],
        })
    return out


def _rel(rid: str, frm: str, to: str, rtype: str, level: str, evidence: list) -> dict:
    assert level in EVIDENCE_LEVELS, level
    return {"id": rid, "from": frm, "to": to, "type": rtype,
            "confidence": level, "evidence": evidence}


def norm_project_entity(p: dict) -> dict:
    """Adapter: canonical project entity -> normalized comparison record."""
    return {"source": "project", "ref": "", "title": norm_title(p.get("canonical_name", "")),
            "contractor": "", "amount": 0,
            "year": str(p.get("fiscal_year") or "") or None,
            "barangays": p.get("barangay", [])}


def build_relationships(contracts_n, bids_n, projects: list, dpwh_raw: list | None = None,
                        contractor_lookup: dict | None = None) -> tuple[list, list]:
    """Deterministic edges + near-miss review queue.

    - contract -> contractor (awarded_to, explicit: source states it)
    - FDP bid <-> PhilGEPS contract via match_records (has_contract)
    - dev/COA project entity <-> PhilGEPS contract via match_records
      (has_contract) — direct pass so shared-contract co-members (e.g. two
      courts under one award) are never dropped by first-match-wins
    - DPWH <-> PhilGEPS pairs never auto-link (national vs municipal
      procurement universes); qualifying near-misses go to review only
    - dev/DPWH/COA project rows carry their own identity; cross-links only
      where match_records fires, else unmatched (no edge).
    Near-misses (title overlap, same year, no rule fired) -> review queue.
    """
    rels, review = [], []
    counters: dict[str, int] = {}
    seen_pairs = set()

    def _next(prefix: str) -> str:
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}-{counters[prefix]:04d}"

    def _emit(frm: str, to: str, rtype: str, level: str, evidence: list,
              match_path: str | None = None) -> None:
        if (frm, to, rtype) in seen_pairs:
            return
        seen_pairs.add((frm, to, rtype))
        edge = _rel(_next("REL"), frm, to, rtype, level, evidence)
        if match_path:
            edge["match_path"] = match_path
        rels.append(edge)

    def _amount_note(a_amount, c_amount) -> list:
        """Corroborating annotation only: never fires, upgrades, or
        downgrades a match. Records agreement when both sides report
        amounts within 10%."""
        try:
            ba, ca = float(a_amount or 0), float(c_amount or 0)
            if ba > 0 and ca > 0:
                pct = abs(ba - ca) / max(ba, ca) * 100
                if pct <= 10:
                    return [f"reported amounts within {pct:.2f}% of each other"]
        except (TypeError, ValueError, ZeroDivisionError):
            pass
        return []

    for c in contracts_n:
        if c.get("awardee_norm") and c.get("awardee_id"):
            _emit(f"contract:{c['cid']}", f"contractor:{c['awardee_id']}",
                  "awarded_to", "explicit", ["source record names awardee"])
    for b in bids_n:
        best = None
        for c in contracts_n:
            out = match_records(b["norm"], c["norm"])
            if out["matched"]:
                anchor = b.get("project_id") or f"fdp-bid:{b['ref']}"
                evidence = list(out["evidence"]) + _amount_note(
                    b["norm"].get("amount"), c["norm"].get("amount"))
                _emit(f"project:{anchor}", f"contract:{c['cid']}", "has_contract",
                      out["level"], evidence + [out["rule"]],
                      match_path="bid-bridge")
                best = out
                break
        if best is None:
            for c in contracts_n:
                try:
                    ydiff = abs(int(b["norm"].get("year") or 0) - int(c["norm"].get("year") or 0))
                except (TypeError, ValueError):
                    continue
                overlap = _token_overlap(b["norm"]["title"], c["norm"]["title"])
                if ydiff <= 1 and overlap >= 0.5:
                    ev = ["similar project title"]
                    ev.append("same fiscal year" if ydiff == 0 else "adjacent fiscal year (bid vs award lag)")
                    review.append({
                        "candidate_id": _next("MATCH"),
                        "record_a": f"fdp-bid:{b['ref']}",
                        "record_b": f"contract:{c['cid']}",
                        "match_score": round(overlap, 2),
                        "evidence": ev,
                        "decision": "pending",
                    })
                    if len(review) >= 200:
                        break
            if len(review) >= 200:
                break
    # Direct project-entity <-> contract pass: catches co-members that share
    # one award (first-match-wins in the bid loop would otherwise drop them).
    direct_linked: set[str] = set()
    for p in projects:
        if p.get("project_type") == "dpwh_infrastructure":
            continue
        pn = norm_project_entity(p)
        for c in contracts_n:
            out = match_records(pn, c["norm"])
            if out["matched"]:
                # Amount corroboration lives on the bid-loop edge, where both
                # sides report amounts; project entities carry quarterly
                # allocation series instead of a single figure.
                _emit(f"project:{p['project_id']}", f"contract:{c['cid']}", "has_contract",
                      out["level"], out["evidence"] + [out["rule"]],
                      match_path="direct")
                direct_linked.add(p["project_id"])
    # Dev/COA project entities with no direct match: near-miss review so
    # synonym cases (renovation/improvement) stay triageable, never silent.
    for p in projects:
        if p.get("project_type") == "dpwh_infrastructure":
            continue
        if p["project_id"] in direct_linked:
            continue
        pn = norm_project_entity(p)
        for c in contracts_n:
            try:
                ydiff = abs(int(pn.get("year") or 0) - int(c["norm"].get("year") or 0))
            except (TypeError, ValueError):
                continue
            if ydiff > 1:
                continue
            overlap = _token_overlap(pn["title"], c["norm"]["title"])
            if overlap < 0.5:
                continue
            ev = ["similar project title"]
            ev.append("same fiscal year" if ydiff == 0 else "adjacent fiscal year (bid vs award lag)")
            review.append({
                "candidate_id": _next("MATCH"),
                "record_a": f"project:{p['project_id']}",
                "record_b": f"contract:{c['cid']}",
                "match_score": round(overlap, 2),
                "evidence": ev,
                "decision": "pending",
            })
            if len(review) >= 200:
                break
        if len(review) >= 200:
            break
    # DPWH <-> PhilGEPS: review-only, never auto-linked (national vs
    # municipal procurement universes). Qualifies only with specific
    # shared work-type tokens (>=2 significant tokens, or 1 token plus
    # comparable scale) — single generic tokens alone are noise.
    # Separately, DPWH contractor *identity* (not contract linkage) resolves
    # against canonical contractor entities: exact normalized name, else
    # token-subset for known variants (e.g. SAFEWAY CONSTRUCTION).
    lookup = contractor_lookup or {}
    _seen_identity: set[str] = set()
    _STOP = {"of", "the", "and", "for", "at", "in", "with", "along", "brgy",
             "barangay", "mapandan", "pangasinan", "phase", "section"}
    for d in dpwh_raw or []:
        dn = {"source": "dpwh", "ref": d.get("contract_id", ""),
              "title": norm_title(d.get("project_name", "")),
              "contractor": "", "amount": 0,
              "year": str(d.get("fiscal_year") or "") or None, "barangays": []}
        dc = norm_contractor(d.get("contractor", ""))
        if dc and d.get("contract_id") not in _seen_identity:
            target = lookup.get(dc)
            if target:
                _seen_identity.add(d.get("contract_id", ""))
                _emit(f"dpwh:{d.get('contract_id', '')}", f"contractor:{target}",
                      "same_contractor_as", "explicit",
                      ["same normalized contractor name"])
            else:
                for norm, cid in lookup.items():
                    dt, nt = dc.split(), norm.split()
                    if len(dt) >= 2 and len(nt) >= 2 and (
                            all(w in nt for w in dt) or all(w in dt for w in nt)):
                        _seen_identity.add(d.get("contract_id", ""))
                        _emit(f"dpwh:{d.get('contract_id', '')}", f"contractor:{cid}",
                              "same_contractor_as", "probable",
                              ["contractor name token-subset — verify legal entity"])
                        break
        if not dc:
            continue
        for c in contracts_n:
            try:
                ydiff = abs(int(dn["year"] or 0) - int(c["norm"].get("year") or 0))
            except (TypeError, ValueError):
                continue
            if ydiff > 1:
                continue
            cc = c["norm"].get("contractor", "")
            if not cc or not (dc == cc or dc in cc or cc in dc):
                continue
            overlap = _token_overlap(dn["title"], c["norm"]["title"])
            shared = sorted({w for w in dn["title"].split() if len(w) > 3 and w not in _STOP} &
                            {w for w in c["norm"]["title"].split() if len(w) > 3 and w not in _STOP})
            scale_ok = False
            try:
                _da, _ca = float(d.get("contract_amount") or 0), float(c["norm"].get("amount") or 0)
                scale_ok = bool(_da and _ca) and 0.5 <= _da / _ca <= 2.0
            except (TypeError, ValueError, ZeroDivisionError):
                pass
            if not (len(shared) >= 2 or (len(shared) == 1 and scale_ok)):
                continue
            review.append({
                "candidate_id": _next("MATCH"),
                "record_a": f"dpwh:{d.get('contract_id', '')}",
                "record_b": f"contract:{c['cid']}",
                "match_score": round(overlap, 2),
                "evidence": ["same contractor",
                             "same fiscal year" if ydiff == 0 else "adjacent fiscal year",
                             f"shared work-type token(s): {', '.join(shared)}"] +
                            (["comparable scale"] if len(shared) == 1 and scale_ok else []),
                "decision": "pending",
            })
            if len(review) >= 200:
                break
        if len(review) >= 200:
            break
    # Shared-award conflicts: one contract claimed by multiple projects.
    # Tag every edge in the group so reviewers see the collision explicitly.
    _by_contract: dict[str, list] = {}
    for _r in rels:
        if _r["type"] == "has_contract":
            _by_contract.setdefault(_r["to"], []).append(_r)
    for _cid, _group in _by_contract.items():
        _projs = sorted({_r["from"] for _r in _group})
        if len(_projs) < 2:
            continue
        for _r in _group:
            _others = ", ".join(p for p in _projs if p != _r["from"])
            _tag = f"shared award — also linked to {_others}"
            if _tag not in _r["evidence"]:
                _r["evidence"].append(_tag)
    return rels, review


def build_indexes(projects, contracts, contractors, findings, funds, rels) -> dict:
    """Lightweight frontend indexes (lazy-load friendly).

    Project entries carry per-source link strength (reported vs the
    strongest edge confidence) plus contracts/funds anchors — everything
    the Explorer renders without re-running matching client-side.
    """
    by_project_contracts: dict[str, list] = {}
    summary: dict[str, dict] = {}
    for r in rels:
        if r["type"] != "has_contract":
            continue
        frm = r["from"]
        if not frm.startswith("project:BM-PROJ-"):
            continue
        pid = frm.split(":", 1)[1]
        cid = r["to"].split(":", 1)[1]
        by_project_contracts.setdefault(pid, [])
        if cid not in by_project_contracts[pid]:
            by_project_contracts[pid].append(cid)
        lvl = r["confidence"]
        if lvl in ("explicit", "strong", "probable", "possible"):
            key = {"explicit": "confirmed", "strong": "strong",
                   "probable": "probable", "possible": "possible"}[lvl]
            s = summary.setdefault(pid, {"confirmed": 0, "strong": 0,
                                         "probable": 0, "possible": 0})
            s[key] += 1
    fund_periods: dict[str, list] = {}
    for f in funds:
        fund_periods.setdefault(str(f.get("year", "")), []).append(f["fund_id"])
    proj_index = []
    for p in projects:
        pid = p["project_id"]
        linked = by_project_contracts.get(pid, [])
        srcs = {"dilg": any(s["source"] == "DILG-FDP" for s in p["provenance"]),
                "philgeps": bool(linked),
                "dpwh": any(s["source"] == "DPWH Transparency Portal" for s in p["provenance"]),
                "coa": any(s["source"] == "COA" for s in p["provenance"])}
        proj_index.append({"id": pid, "name": p["canonical_name"],
                           "year": p.get("fiscal_year"), "barangay": p.get("barangay", []),
                           "type": p.get("project_type"), "sources": srcs,
                           "contracts": linked,
                           "relationship_summary": summary.get(pid, {"confirmed": 0, "strong": 0,
                                                                     "probable": 0, "possible": 0}),
                           "funds_same_year": fund_periods.get(str(p.get("fiscal_year") or ""), [])})
    contracts_by_id = {c["contract_id"]: c for c in contracts}
    contractor_contracts: dict[str, list] = {}
    for r in rels:
        if r["type"] == "awarded_to":
            contractor_contracts.setdefault(r["to"].split(":", 1)[1], []).append(
                r["from"].split(":", 1)[1])
    contractor_index = []
    for c in contractors:
        cids = contractor_contracts.get(c["contractor_id"], [])
        years = sorted({(contracts_by_id.get(i) or {}).get("award_date", "")[:4]
                        for i in cids if (contracts_by_id.get(i) or {}).get("award_date")})
        contractor_index.append({"id": c["contractor_id"], "name": c["canonical_name"],
                                 "contracts": c["contract_count"], "total": c["total_represented"],
                                 "contract_ids": sorted(cids), "years": [y for y in years if y]})
    fund_projects: dict[str, list] = {}
    for p in projects:
        for fid in fund_periods.get(str(p.get("fiscal_year") or ""), []):
            fund_projects.setdefault(fid, [])
            if p["project_id"] not in fund_projects[fid]:
                fund_projects[fid].append(p["project_id"])
    return {
        "project-index": sorted(proj_index, key=lambda x: (str(x["year"]), x["id"])),
        "contractor-index": contractor_index,
        "audit-index": [{"id": f["finding_id"], "title": f["title"],
                         "status": f["status"], "severity": f["severity"],
                         "category": f.get("category", ""),
                         "first_observed": f.get("first_observed"),
                         "last_observed": f.get("last_observed"),
                         "amount": f.get("amount")}
                        for f in findings],
        "fund-index": [{"id": f["fund_id"], "period": f["period"], "figures": f["figures"],
                        "projects_same_year": fund_projects.get(f["fund_id"], [])}
                       for f in funds],
    }


def _merge_review_decisions(review: list, review_dir: Path | None) -> list:
    """Preserve human triage across rebuilds.

    Carries decisions forward for pairs that still exist, drops stale
    pairs, adds new ones as pending. Never silently overwrites a
    confirmed/rejected/uncertain decision.
    """
    if review_dir is None:
        review_dir = Path(__file__).resolve().parent.parent / "datasets" / "review"
    prior_path = review_dir / "project-matches.json"
    if not prior_path.exists():
        return review
    try:
        prior = {(r.get("record_a"), r.get("record_b")): r
                 for r in json.loads(prior_path.read_text(encoding="utf-8"))
                 if isinstance(r, dict)}
    except (json.JSONDecodeError, OSError):
        return review
    merged = []
    for cand in review:
        key = (cand["record_a"], cand["record_b"])
        if key in prior and prior[key].get("decision", "pending") != "pending":
            keep = dict(cand)
            keep["decision"] = prior[key]["decision"]
            for extra in ("decided_by", "decided_at", "note",
                          "reviewed_by", "reviewed_at", "notes",
                          "evidence_used"):
                if extra in prior[key]:
                    keep[extra] = prior[key][extra]
            merged.append(keep)
        else:
            merged.append(cand)
    return merged


def build_all(src_data: Path = SRC_DATA, data_out: Path = SRC_DATA,
              assets_out: Path | None = None,
              review_dir: Path | None = None) -> dict:
    """Run the full entity pipeline; write + return artifact summary."""
    procurement = load_json(src_data / "procurement.json")
    dpwh = load_json(src_data / "dpwh.json")
    fdp = load_json(src_data / "fdp_disclosures.json")
    audit = load_json(src_data / "audit-reports.json")
    retrieved = {
        "philgeps": (procurement.get("metrics", {}) or {}).get("last_updated"),
        "fdp": (fdp.get("meta", {}) or {}).get("retrieved"),
        "dpwh": _file_mtime_datestr(src_data / "dpwh.json"),
        "coa": None,
    }
    contracts_raw = procurement.get("contracts", [])
    contractors, contractor_lookup = build_contractors(contracts_raw, retrieved["philgeps"])
    contracts = build_contracts(contracts_raw, contractor_lookup, retrieved["philgeps"])

    bids_n = []
    for doc in fdp.get("bids", []):
        for key in ("civil_works", "goods", "consulting"):
            for b in doc.get(key, []) or []:
                norm = norm_fdp_bid(b)
                if not norm.get("year") and doc.get("period"):
                    norm["year"] = doc["period"].split("-")[0]
                bids_n.append({"ref": b.get("ref", ""), "norm": norm,
                               "period": doc.get("period", "")})
    contracts_n = []
    for i, c in enumerate(contracts, start=1):
        raw = contracts_raw[i - 1]
        norm = norm_philgeps_contract(raw)
        alook = next((k for k, v in contractor_lookup.items() if v == c["awardee_id"]), "")
        contracts_n.append({"cid": c["contract_id"], "awardee_norm": alook,
                            "awardee_id": c["awardee_id"], "norm": norm})
    # Attach project links for dev-linked bids later; dev matching via title.
    projects = build_projects(fdp, dpwh.get("projects", []),
                              audit.get("infrastructure_projects", []), retrieved)
    funds = build_funds(fdp, retrieved["fdp"])
    findings = build_audit_findings(audit)

    # Link FDP bids to dev projects by title+period for project: anchors.
    for b in bids_n:
        b["project_id"] = None
        for p in projects:
            if p["project_type"] != "lgu_development" or "-D" in p["project_id"] or "-C" in p["project_id"]:
                continue
            out = match_records(
                {"source": "fdp-bids", "ref": b["ref"], "title": b["norm"]["title"],
                 "contractor": b["norm"]["contractor"], "amount": b["norm"]["amount"],
                 "year": b["norm"]["year"], "barangays": b["norm"]["barangays"]},
                {"source": "dev", "ref": "", "title": norm_title(p["canonical_name"]),
                 "contractor": "", "amount": 0,
                 "year": str(p.get("fiscal_year") or "") or None,
                 "barangays": p.get("barangay", [])})
            if out["matched"] and out["level"] in ("explicit", "strong", "probable"):
                b["project_id"] = p["project_id"]
                break

    rels, review = build_relationships(contracts_n, bids_n, projects, dpwh.get("projects", []),
                                        contractor_lookup)
    indexes = build_indexes(projects, contracts, contractors, findings, funds, rels)
    review = _merge_review_decisions(review, review_dir)
    # Stewardship loop closed: human-confirmed pairs become edges.
    _rel_n = sum(1 for _r in rels if _r["id"].startswith("REL-"))
    for _cand in review:
        if _cand.get("decision") != "confirmed":
            continue
        _a, _b = _cand.get("record_a", ""), _cand.get("record_b", "")
        if not _a or not _b:
            continue
        _exists = any(_r["from"] == _a and _r["to"] == _b and _r["type"] == "has_contract" for _r in rels)
        if _exists:
            continue
        _rel_n += 1
        rels.append({"id": f"REL-{_rel_n:04d}", "from": _a, "to": _b,
                     "type": "has_contract", "confidence": "explicit",
                     "evidence": list(_cand.get("evidence", [])) + ["human-confirmed"]})

    ent_dir = data_out / ENTITY_DIRNAME
    ent_dir.mkdir(parents=True, exist_ok=True)
    write_json(ent_dir / "projects.json", projects)
    write_json(ent_dir / "contracts.json", contracts)
    write_json(ent_dir / "contractors.json", contractors)
    write_json(ent_dir / "funds.json", funds)
    write_json(ent_dir / "audit-findings.json", findings)
    write_json(data_out / "relationships.json", rels)
    if review_dir is None:
        review_dir = Path(__file__).resolve().parent.parent / "datasets" / "review"
    # Review queue lives in datasets/ per architecture (git-tracked triage).
    # review_dir is injectable so tests never touch the real tree.
    review_dir.mkdir(parents=True, exist_ok=True)
    write_json(review_dir / "project-matches.json", review)
    if assets_out is not None:
        adir = assets_out / "data"
        adir.mkdir(parents=True, exist_ok=True)
        for key in ("project-index", "contractor-index", "audit-index", "fund-index"):
            write_json(adir / f"{key}.json", indexes[key])
        # Full detail bundles, lazy-loaded by the Project Explorer only.
        for name in ("projects.json", "contracts.json"):
            src = ent_dir / name
            if src.exists():
                shutil.copy2(src, adir / f"entity-{name}")
        rsrc = data_out / "relationships.json"
        if rsrc.exists():
            shutil.copy2(rsrc, adir / "entity-relationships.json")
    return {"projects": len(projects), "contracts": len(contracts),
            "contractors": len(contractors), "funds": len(funds),
            "findings": len(findings), "relationships": len(rels),
            "review": len(review)}
