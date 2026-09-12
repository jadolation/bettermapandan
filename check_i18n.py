#!/usr/bin/env python3
"""Check i18n key parity between en.json and fil.json."""
import json
import sys
from pathlib import Path


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

    if not en_path.exists() or not fil_path.exists():
        print("ERROR: Missing locale files")
        return 1

    en_data = json.loads(en_path.read_text(encoding="utf-8"))
    fil_data = json.loads(fil_path.read_text(encoding="utf-8"))

    en_keys = flatten_keys(en_data)
    fil_keys = flatten_keys(fil_data)

    missing_in_fil = sorted(en_keys - fil_keys)
    missing_in_en = sorted(fil_keys - en_keys)

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

    if missing_in_fil:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
