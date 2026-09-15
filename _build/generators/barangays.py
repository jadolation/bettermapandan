import html
import json
from pathlib import Path

from _build.config import ROOT, SRC_DATA


def validate_barangays(barangays: list[dict]) -> list[dict]:
    """Validate and normalize barangay entries. Returns cleaned list."""
    required = {"slug", "name", "punong_barangay"}
    seen_slugs = set()
    normalized = []
    for brgy in barangays:
        slug = brgy.get("slug", "")
        if slug in seen_slugs:
            print(f"  WARNING: duplicate barangay slug '{slug}' - skipping duplicate")
            continue
        if slug:
            seen_slugs.add(slug)
        missing = required - brgy.keys()
        if missing:
            print(f"  WARNING: barangay '{brgy.get('name', '?')}' missing fields: {missing}")
        normalized.append({
            "slug": brgy.get("slug", ""),
            "name": brgy.get("name", ""),
            "pop2024": brgy.get("pop2024", ""),
            "pop2020": brgy.get("pop2020", ""),
            "landUse": brgy.get("landUse", ""),
            "history": brgy.get("history", ""),
            "history_source": brgy.get("history_source", brgy.get("source", "")),
            "punong_barangay": brgy.get("punong_barangay", ""),
            "kagawads": brgy.get("kagawads", []),
            "officials": brgy.get("officials", []),
            "facebook": brgy.get("facebook", ""),
            "phone": brgy.get("phone", ""),
            "photo": brgy.get("photo", ""),
        })
    return normalized


def generate_barangay_councils_table(locale: dict) -> str:
    """Generate the barangay councils table HTML from barangays.json."""
    data_path = SRC_DATA / "barangays.json"
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Malformed JSON in {data_path}: {e}")
    barangays = validate_barangays(data.get("barangays", []))

    desired_order = [
        "Pias", "Poblacion", "Baloling", "Nilombot", "Torres",
        "Luyan", "Jimenez", "Primicias", "Amanoaoac", "Lambayan",
        "Apaya", "Aserda", "Coral", "Golden", "Sta. Maria"
    ]
    brgy_map = {b.get("name", ""): b for b in barangays}

    ordered = []
    for name in desired_order:
        b = brgy_map.get(name)
        if not b:
            b = next((v for k, v in brgy_map.items() if k.startswith(name)), None)
        if not b:
            continue
        ordered.append(b)

    rows = []
    for brgy in ordered:
        name = html.escape(brgy.get("name", ""))
        punong = html.escape(brgy.get("punong_barangay", ""))
        kagawads = brgy.get("kagawads", [])
        kagawad_lis = "\n".join(
            f"                <li>{html.escape(k.get('name', ''))}</li>" for k in kagawads
        )

        officials = brgy.get("officials", [])
        sk_chair = "&mdash;"
        secretary = "&mdash;"
        treasurer = "&mdash;"
        for off in officials:
            pos = off.get("position", "")
            off_name = off.get("name", "")
            if "SK" in pos.upper():
                sk_chair = html.escape(off_name)
            elif "Secretary" in pos:
                secretary = html.escape(off_name)
            elif "Treasurer" in pos:
                treasurer = html.escape(off_name)

        fb = brgy.get("facebook", "")
        if fb:
            fb_link = f'<a href="{html.escape(fb)}" target="_blank" rel="noopener">Facebook</a>'
        else:
            fb_link = "&mdash;"

        phone = brgy.get("phone", "")
        if phone:
            phone_td = html.escape(str(phone))
        else:
            phone_td = "&mdash;"

        rows.append(
            f"          <tr>\n"
            f"            <td>{name}</td>\n"
            f"            <td>{punong}</td>\n"
            f"            <td>\n"
            f"              <ul style=\"margin: 0; padding-left: 1.2em;\">\n"
            f"                {kagawad_lis}\n"
            f"              </ul>\n"
            f"            </td>\n"
            f"            <td>{sk_chair}</td>\n"
            f"            <td>{secretary}</td>\n"
            f"            <td>{treasurer}</td>\n"
            f"            <td>{fb_link}</td>\n"
            f"            <td>{phone_td}</td>\n"
            f"          </tr>"
        )

    return "\n".join(rows)


def generate_barangays() -> None:

    """Generate barangay-data.js for homepage from JSON data."""
    data_path = SRC_DATA / "barangays.json"
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Malformed JSON in {data_path}: {e}")
    barangays = validate_barangays(data.get("barangays", []))

    js_data = [{
        "slug": brgy.get("slug", ""),
        "name": brgy.get("name", ""),
        "pop2024": brgy.get("pop2024", ""),
        "pop2020": brgy.get("pop2020", ""),
        "landUse": brgy.get("landUse", ""),
        "history": brgy.get("history", ""),
        "source": brgy.get("history_source", brgy.get("source", "")),
        "punong": brgy.get("punong_barangay", ""),
        "kagawads": brgy.get("kagawads", []),
        "officials": brgy.get("officials", []),
        "facebook": brgy.get("facebook", ""),
        "phone": brgy.get("phone", ""),
        "photo": brgy.get("photo", ""),
    } for brgy in barangays]

    js_content = "// Auto-generated from barangays.json — do not edit manually\nvar BARANGAY_DATA = " + json.dumps(js_data, ensure_ascii=False, indent=2) + ";\n"
    (ROOT / "assets" / "barangay-data.js").write_text(js_content)


def build_barangay_comparison_script() -> str:
    data_path = SRC_DATA / "barangays.json"
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Malformed JSON in {data_path}: {e}")
    barangays = data.get("barangays", [])

    desired_order = [
        "Pias", "Poblacion", "Baloling", "Nilombot", "Torres",
        "Luyan", "Jimenez", "Primicias", "Amanoaoac", "Lambayan",
        "Apaya", "Aserda", "Coral", "Golden", "Sta. Maria"
    ]
    brgy_map = {b.get("name", ""): b for b in barangays}

    names = []
    pop2020 = []
    pop2024 = []
    growth = []

    for name in desired_order:
        b = brgy_map.get(name)
        if not b:
            b = next((v for k, v in brgy_map.items() if k.startswith(name)), None)
        if not b:
            continue
        names.append(b.get("name", ""))
        p20 = b.get("pop2020", "0")
        p24 = b.get("pop2024", "0")
        v20 = int(p20.replace(",", "")) if p20 else 0
        v24 = int(p24.replace(",", "")) if p24 else 0
        pop2020.append(v20)
        pop2024.append(v24)
        g = round((v24 - v20) / v20 * 100, 2) if v20 else 0.0
        growth.append(g)

    comparison_data = {
        "names": names,
        "pop2020": pop2020,
        "pop2024": pop2024,
        "growth": growth,
    }
    return f"<script>window.BARANGAY_COMPARISON = {json.dumps(comparison_data, ensure_ascii=False)};</script>\n"
