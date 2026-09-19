"""Test three-way locale key parity: EN == FIL == PAG."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build.locales import load_locale


def _flatten_keys(data: dict, prefix: str = "") -> set:
    keys = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(_flatten_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys


def test_three_way_locale_key_parity():
    en = load_locale("en")
    fil = load_locale("fil")
    pag = load_locale("pag")
    en_keys = _flatten_keys(en)
    fil_keys = _flatten_keys(fil)
    pag_keys = _flatten_keys(pag)
    assert en_keys == fil_keys == pag_keys, (
        f"Key mismatch: EN={len(en_keys)}, FIL={len(fil_keys)}, PAG={len(pag_keys)}"
    )


def test_pag_locale_has_lang_code():
    pag = load_locale("pag")
    assert pag.get("lang_code") == "pag"


def test_pag_does_not_use_fil_data_fields():
    """Pangasinan locale should not contain Filipino-specific translations."""
    pag = load_locale("pag")
    # Check that nav.home is not a Filipino translation
    assert pag.get("nav", {}).get("home") != "Tahanan"
    # Check that it's either empty (fallback) or Pangasinan
    val = pag.get("nav", {}).get("home", "")
    assert val in ("", "Abong"), f"Unexpected nav.home value: {val}"
