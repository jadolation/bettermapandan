#!/usr/bin/env python3
"""Report Pangasinan translation coverage (informational, exit 0 always).

Tracks four workstreams so reviewers see what's left:
  1. locales/pag.json — empty values (EN fallback) and review-queue size
  2. src/data/services.json — *_pag content fields per service/category
  3. src/data/page-meta.json — per-language front-matter coverage
  4. src/data/pag-review.json — the 64-item speaker-review queue

Content translations (workstreams 2) and speaker review (4) require a
fluent Pangasinan speaker — this script measures, it never generates.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name):
    path = ROOT / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"WARN: cannot read {name}: {exc}")
        return None


def flatten(data, prefix=""):
    out = {}
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, full))
        else:
            out[full] = value
    return out


def main() -> int:
    print("=== Pangasinan (pag) translation coverage ===\n")

    en = load("locales/en.json") or {}
    pag = load("locales/pag.json") or {}
    en_flat, pag_flat = flatten(en), flatten(pag)
    missing = sorted(set(en_flat) - set(pag_flat))
    empty = sorted(k for k in set(en_flat) & set(pag_flat) if not pag_flat[k])
    same_as_en = sorted(
        k for k in set(en_flat) & set(pag_flat)
        if pag_flat[k] and pag_flat[k] == en_flat[k] and len(str(pag_flat[k])) > 3
    )
    print(f"1. locales/pag.json: {len(pag_flat)}/{len(en_flat)} keys present, "
          f"{len(empty)} empty (EN fallback), {len(same_as_en)} identical to EN")
    if missing:
        print(f"   missing: {', '.join(missing[:8])}{'...' if len(missing) > 8 else ''}")

    review = load("src/data/pag-review.json") or []
    by_status: dict[str, int] = {}
    for entry in review:
        by_status[entry.get("pangasinan_status", "?")] = by_status.get(entry.get("pangasinan_status", "?"), 0) + 1
    print(f"2. speaker-review queue: {len(review)} entries {by_status}")

    services = load("src/data/services.json") or {}
    svcs = services.get("services", []) if isinstance(services, dict) else []
    cats = services.get("categories", []) if isinstance(services, dict) else []
    for field in ("name_pag", "description_pag", "hero_lede_pag"):
        done = sum(1 for s in svcs if isinstance(s, dict) and s.get(field))
        print(f"3. services {field}: {done}/{len(svcs)}")
    for field in ("name_pag", "description_pag"):
        done = sum(1 for c in cats if isinstance(c, dict) and c.get(field))
        print(f"   categories {field}: {done}/{len(cats)}")

    meta = load("src/data/page-meta.json") or {}
    for lang in ("fil", "pag"):
        covered = sum(1 for v in meta.values() if isinstance(v, dict) and v.get(lang, {}).get("title"))
        print(f"4. page-meta {lang}: {covered}/{len(meta)} pages with title")
    drafts = sorted(k for k, v in meta.items() if isinstance(v, dict) and v.get("pag_status") == "draft")
    print(f"   page-meta pag drafts: {len(drafts)} ({', '.join(drafts) if drafts else 'none'})")
    print("\nDone. Content + review work needs a fluent Pangasinan speaker.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
