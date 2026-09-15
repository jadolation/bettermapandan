import json
from _build.config import ROOT, LOCALES_DIR


def load_locale(lang: str) -> dict:
    """Load a locale JSON file. Returns empty dict if missing."""
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"WARNING: Malformed JSON in {path}: {e}")
        return {}


def t(locale: dict, key: str, default: str = "") -> str:
    """Dot-notation locale lookup with fallback to default."""
    parts = key.split(".")
    val: object = locale
    for p in parts:
        if isinstance(val, dict) and p in val:
            val = val[p]
        else:
            return default
    return str(val) if val else default
