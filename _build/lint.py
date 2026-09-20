from pathlib import Path

from _build.config import ROOT, FIL_DIR, PAG_DIR


TRANSLATION_ALLOWLIST = {
    "bettermapandan.org", "better mapandan", "github", "chart.js", "chart",
    "open-meteo", "lucide", "svg", "pdf", "html", "css", "json", "js",
    "philhealth", "pag-ibig", "gsis", "sss", "dswd", "doe", "da", "dar",
    "denr", "dilg", "doj", "dof", "dbm", "neda", "psa", "comelec", "coe",
    "coe-id", "philsys", "lgu", "bplo", "cenro", "menro", "ldrrmo", "lydo",
    "sk", "sb", "rtc", "mctc", "mdrrmo", "aics", "pwd", "solo parent",
    "birth certificate", "death certificate", "marriage certificate",
    "certificate of", "clearance", "barangay", "mayor",
    "mapandan", "pangasinan", "philippines", "luzon",
    "cy 2020", "cy 2021", "cy 2022", "cy 2023", "cy 2024", "cy 2025", "cy 2026",
    "res.", "res no.", "ordinance", "resolution", "executive order",
    "republic act", "ra no.", "pd no.", "bp no.", " eo ",
    "land bank", "landbank", "coa", "sglg", "fdp", "gf",
    "unpkg.com", "cdn.jsdelivr.net",
    "google maps", "google.com", "maps.app",
    "16.03", "120.456", "openstreetmap",
    "©", "© 2024", "© 2025", "© 2026",
}

TRANSLATION_ALLOWLIST_PAG = TRANSLATION_ALLOWLIST | {
    "barangay", "pandan", "pangasinan", "mapandan",
    "municipality", "municipal", "province",
    "independent", "citizen-maintained", "civic",
    "transparency", "portal", "website",
    "mayor", "vice mayor", "sangguniang", "bayan",
    "poblacion", "district", "congressional",
    "philippine", "philippines", "filipino",
    "psa", "coa", "dilg", "dpwh", "blgf", "philgeps",
    "ldrrmo", "mdrrmo", "bfp", "pnp",
    "national", "local", "government",
    "budget", "contract", "audit", "procurement",
    "infrastructure", "project", "fund",
    "revenue", "expenditure", "allocation",
    "fiscal", "financial", "operating",
    "emergency", "hotline", "hospital",
    "water", "community",
    "agriculture", "agri", "tourism",
    "population", "resident", "household",
    "density", "area", "land",
    "employment", "economic", "development",
    "social", "welfare", "health",
    "service", "permit", "license", "certificate",
    "clearance", "registration", "application",
    "requirement", "fee", "processing", "mode",
    "classification", "office", "department",
    "official", "agency", "program",
    "ordinance", "resolution", "issuance",
    "executive", "legislative", "judicial",
    "barangay", "council", "captain",
    "kagawad", "tanod", "lupon",
    "purok", "sitio", "zone",
    "north", "south", "east", "west",
    "central", "poblacion", "urban", "rural",
    "rice", "corn", "vegetable", "livestock",
    "poultry", "fishery", "aquaculture",
    "lowland", "upland", "irrigation",
    "first", "second", "third",
    "class", "municipality", "city",
}


def _strip_tags_for_comparison(html_text: str) -> str:
    """Remove HTML tags and normalize whitespace for translation comparison."""
    import re as _re
    text = _re.sub(r"<script[^>]*>.*?</script>", "", html_text, flags=_re.DOTALL)
    text = _re.sub(r"<style[^>]*>.*?</style>", "", text, flags=_re.DOTALL)
    text = _re.sub(r"<[^>]+>", " ", text)
    return _re.sub(r"\s+", " ", text).strip()


def _extract_text_segments(text: str, min_len: int = 20) -> list:
    """Split text into sentence segments."""
    import re as _re
    segs = _re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in segs if len(s.strip()) >= min_len]


def _is_segment_translated(seg_lower: str, fil_text_lower: str, allowlist: set) -> bool:
    """Check if a segment is likely untranslated (present in EN but not FIL)."""
    if len(seg_lower) < 25:
        return False
    if any(term in seg_lower for term in allowlist):
        return False
    return seg_lower in fil_text_lower


def _compare_file_pair(en_path: Path, fil_path: Path, allowlist: set = None) -> list:
    """Compare EN and translated files, return list of untranslated segments."""
    if allowlist is None:
        allowlist = TRANSLATION_ALLOWLIST
    en_text = _strip_tags_for_comparison(en_path.read_text(encoding="utf-8"))
    fil_text = _strip_tags_for_comparison(fil_path.read_text(encoding="utf-8"))
    fil_text_lower = fil_text.lower()

    findings = []
    for seg in _extract_text_segments(en_text):
        seg_lower = seg.lower().strip()
        if _is_segment_translated(seg_lower, fil_text_lower, allowlist):
            findings.append(seg[:100] + ("..." if len(seg) > 100 else ""))
    return findings


def _collect_translation_findings(en_dir: Path, fil_dir: Path, allowlist: set = None) -> tuple[list, int]:
    """Collect all translation findings across all page pairs."""
    if allowlist is None:
        allowlist = TRANSLATION_ALLOWLIST
    findings = []
    pages_checked = 0

    en_files = sorted(en_dir.glob("*.html"))
    en_files += sorted((en_dir / "services").glob("*.html"))
    en_files += sorted((en_dir / "support").glob("*.html"))

    for en_path in en_files:
        rel = en_path.relative_to(en_dir)
        fil_path = fil_dir / rel
        if not fil_path.exists():
            continue

        file_findings = _compare_file_pair(en_path, fil_path, allowlist)
        if file_findings:
            findings.append((str(rel), file_findings))
        pages_checked += 1

    return findings, pages_checked


def verify_translations() -> None:
    """Compare EN vs FIL HTML output and flag untranslated English strings."""
    print("\n--- Translation Linter ---\n")

    fil_dir = FIL_DIR
    if not fil_dir.exists():
        print("  FIL output not found. Run build first.")
        return

    findings, pages_checked = _collect_translation_findings(ROOT, fil_dir)

    if findings:
        total_segments = sum(len(segments) for _, segments in findings)
        print(f"  Found {total_segments} potential untranslated segment(s) in {pages_checked} page pairs:\n")
        for file_path, segments in findings:
            print(f"  [{file_path}]")
            for segment in segments:
                print(f'    - "{segment}"')
        print(f"\n  Summary: {total_segments} segment(s) across {pages_checked} pages may need translation.")
    else:
        print(f"  No untranslated segments found across {pages_checked} page pairs.")

    pag_dir = PAG_DIR
    if pag_dir.exists():
        pag_findings, pages_checked_pag = _collect_translation_findings(ROOT, pag_dir, allowlist=TRANSLATION_ALLOWLIST_PAG)

        if pag_findings:
            total_segments_pag = sum(len(segments) for _, segments in pag_findings)
            print(f"  Found {total_segments_pag} potential untranslated segment(s) in {pages_checked_pag} page pairs (Pangasinan):\n")
            for file_path, segments in pag_findings:
                print(f"  [{file_path}]")
                for segment in segments:
                    print(f'    - "{segment}"')
            print(f"\n  Summary: {total_segments_pag} segment(s) across {pages_checked_pag} pages may need translation.")
        else:
            print(f"  No untranslated segments found across {pages_checked_pag} page pairs (Pangasinan).")
