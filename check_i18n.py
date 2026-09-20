#!/usr/bin/env python3
"""Check i18n key parity across en.json, fil.json, and pag.json."""
import json
import sys
from pathlib import Path



def flatten_values(data: dict, prefix: str = "") -> dict:
    """Flatten nested dict into dot-notation keys to string values."""
    result = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_values(value, full_key))
        else:
            result[full_key] = str(value)
    return result


def detect_untranslated_pag(en_data: dict, pag_data: dict) -> list[str]:
    """Find keys where pag.json value appears identical to en.json (likely untranslated)."""
    en_flat = flatten_values(en_data)
    pag_flat = flatten_values(pag_data)
    untranslated = []
    for key in sorted(en_flat):
        if key not in pag_flat:
            continue
        en_val = en_flat[key].strip()
        pag_val = pag_flat[key].strip()
        if not en_val or not pag_val:
            continue
        if en_val.lower() == pag_val.lower():
            untranslated.append(key)
    return untranslated

def flatten_keys(data: dict, prefix: str = "") -> set:
    """Flatten nested dict keys into dot-separated paths."""
    keys = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(flatten_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys


def main() -> int:
    root = Path(__file__).resolve().parent
    en_path = root / "locales" / "en.json"
    fil_path = root / "locales" / "fil.json"
    pag_path = root / "locales" / "pag.json"

    if not en_path.exists() or not fil_path.exists() or not pag_path.exists():
        print("ERROR: Missing locale files")
        return 1

    en_data = json.loads(en_path.read_text(encoding="utf-8"))
    fil_data = json.loads(fil_path.read_text(encoding="utf-8"))
    pag_data = json.loads(pag_path.read_text(encoding="utf-8"))

    en_keys = flatten_keys(en_data)
    fil_keys = flatten_keys(fil_data)
    pag_keys = flatten_keys(pag_data)

    missing_in_fil = sorted(en_keys - fil_keys)
    missing_in_en = sorted(fil_keys - en_keys)
    missing_in_pag = sorted(en_keys - pag_keys)
    missing_in_en_from_pag = sorted(pag_keys - en_keys)

    if missing_in_fil:
        print("FAIL: Keys in en.json missing from fil.json:")
        for key in missing_in_fil:
            print(f"  - {key}")
        print()
    else:
        print("OK: All en.json keys exist in fil.json")

    if missing_in_en:
        print("INFO: Keys in fil.json missing from en.json:")
        for key in missing_in_en:
            print(f"  + {key}")
        print()

    if missing_in_pag:
        print("FAIL: Keys in en.json missing from pag.json:")
        for key in missing_in_pag:
            print(f"  - {key}")
        print()
    else:
        print("OK: All en.json keys exist in pag.json")

    if missing_in_en_from_pag:
        print("INFO: Keys in pag.json missing from en.json:")
        for key in missing_in_en_from_pag:
            print(f"  + {key}")
        print()

    untranslated = detect_untranslated_pag(en_data, pag_data)
    if untranslated:
        print(f"INFO: {len(untranslated)} Pangasinan values appear identical to English (may need translation):")
        for key in untranslated[:20]:
            print(f"  - {key}")
        if len(untranslated) > 20:
            print(f"  ... and {len(untranslated) - 20} more")
        print()

    if missing_in_fil or missing_in_pag:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
