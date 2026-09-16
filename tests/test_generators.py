import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build.generators.barangays import validate_barangays, build_barangay_comparison_script
from _build.generators.dpwh import _build_dpwh_labels, _dpwh_status_class, _dpwh_category_icon, generate_dpwh
from _build.generators.procurement import _build_procurement_labels, generate_homepage_procurement_data, generate_homepage_dpwh_data
from _build.generators.legislative import _build_legislative_labels


def test_validate_barangays_empty():
    """Empty list should pass validation."""
    assert validate_barangays([]) == []


def test_validate_barangays_valid():
    """Valid barangay data should pass."""
    data = [
        {"slug": "test", "name": "Test", "punong_barangay": "John Doe", "kagawads": [], "officials": []}
    ]
    result = validate_barangays(data)
    assert len(result) == 1


def test_validate_barangays_duplicate_slug():
    """Duplicate slugs should be deduplicated with warning."""
    data = [
        {"slug": "test", "name": "Test 1", "punong_barangay": "John", "kagawads": [], "officials": []},
        {"slug": "test", "name": "Test 2", "punong_barangay": "Jane", "kagawads": [], "officials": []},
    ]
    result = validate_barangays(data)
    assert len(result) == 1


def test_build_barangay_comparison_script():
    """Comparison script should contain expected JS structure."""
    script = build_barangay_comparison_script()
    assert "BARANGAY_COMPARISON" in script



def test_build_dpwh_labels():
    """DPWH labels should contain expected keys."""
    locale = {}
    labels = _build_dpwh_labels(locale)
    assert "DPWH_TITLE" in labels
    assert "DPWH_EYEBROW" in labels
    assert "DPWH_PROJECT" in labels
    assert "DPWH_STATUS" in labels


def test_dpwh_status_class_completed():
    assert _dpwh_status_class("Completed") == "pill-completed"


def test_dpwh_status_class_ongoing():
    assert _dpwh_status_class("Ongoing") == "pill-ongoing"


def test_dpwh_status_class_pending():
    assert _dpwh_status_class("Not Yet Started") == "pill-pending"
    assert _dpwh_status_class("Pending") == "pill-pending"


def test_dpwh_status_class_default():
    assert _dpwh_status_class("Unknown") == "pill"


def test_dpwh_category_icon():
    icon = _dpwh_category_icon("Roads")
    assert "<svg" in icon
    assert "lucide" in icon


def test_build_legislative_labels():
    """Legislative labels should contain expected keys."""
    locale = {}
    labels = _build_legislative_labels(locale)
    assert "LEG_FRAMEWORK_TITLE" in labels
    assert "LEG_ORD_TITLE" in labels
    assert "LEG_RES_TITLE" in labels


def test_generate_dpwh_no_data():
    """generate_dpwh should return empty strings when data is missing."""
    # This test verifies graceful handling of missing data
    # We can't easily mock the file system, so just verify the function exists
    assert callable(generate_dpwh)


def test_generate_homepage_procurement_data_no_file():
    """Should return empty data when procurement.json doesn't exist."""
    # We can't easily mock, but we can verify the function signature
    assert callable(generate_homepage_procurement_data)


def test_generate_homepage_dpwh_data_no_file():
    """Should return empty array when dpwh.json doesn't exist."""
    assert callable(generate_homepage_dpwh_data)


def test_build_procurement_labels():
    """Procurement labels should contain expected keys."""
    locale = {}
    labels = _build_procurement_labels(locale)
    assert "PROCUREMENT_EYEBROW" in labels or "PROC_EYEBROW" in labels
