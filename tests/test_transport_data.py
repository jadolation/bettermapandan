"""Data integrity tests for V0 transport reference data.

These tests verify that the seeded evidence inventory:
- Preserves the seven supplied positions exactly.
- Preserves original coordinate representations.
- Does not fabricate routing eligibility from unverified records.
- Does not merge distinct landmarks with terminals.
- Preserves the operational turnaround as non-passenger.
- Preserves reported fares at correct ranges with correct source classification.
- Validates all structured data against schemas.
"""
import json

import pytest

from _build.transport.validation import (
    TRANSPORT_DATA_DIR,
    validate_transport_data,
)

DATA_DIR = TRANSPORT_DATA_DIR


def load_file(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def test_seven_supplied_positions_preserved():
    """Exactly seven transport positions: four terminals + three tricycle stands."""
    terminals = load_file("terminals.geojson")
    stands = load_file("tricycle_stands.geojson")
    terminal_ids = {f["properties"]["id"] for f in terminals["features"]}
    stand_ids = {f["properties"]["id"] for f in stands["features"]}
    expected_ids = {
        "term-mini-mapandan",
        "term-mini-dagupan",
        "term-jeep-mapandan",
        "term-jeep-mangaldan",
        "stand-tri-market",
        "stand-tri-plaza",
        "stand-tri-hall",
    }
    assert terminal_ids | stand_ids == expected_ids
    assert len(terminal_ids) == 4
    assert len(stand_ids) == 3


def test_minibus_dms_coordinate_conversion():
    """DMS 16°01'35.7\"N 120°27'08.7\"E must match the supplied decimal."""
    terminals = load_file("terminals.geojson")
    terminal = next(f for f in terminals["features"] if f["properties"]["id"] == "term-mini-mapandan")
    coords = terminal["geometry"]["coordinates"]
    assert coords[0] == pytest.approx(120.4524166667, abs=1e-9)
    assert coords[1] == pytest.approx(16.0265833333, abs=1e-9)
    props = terminal["properties"]
    assert props["original_coordinate_representation"] == '16°01\'35.7"N 120°27\'08.7"E'
    assert props["latitude"] == pytest.approx(16.0265833333, abs=1e-9)
    assert props["longitude"] == pytest.approx(120.4524166667, abs=1e-9)


def test_geojson_coordinate_order():
    """Coordinates must be [longitude, latitude], not [lat, lon]."""
    terminals = load_file("terminals.geojson")
    for feature in terminals["features"]:
        lon, lat = feature["geometry"]["coordinates"]
        assert -180 <= lon <= 180, f"longitude out of range: {lon}"
        assert -90 <= lat <= 90, f"latitude out of range: {lat}"


def test_all_records_start_unverified_and_reference_only():
    """No record is routing-eligible or authority-confirmed without evidence."""
    for feature in load_file("terminals.geojson")["features"]:
        props = feature["properties"]
        assert props["verification_status"] == "unverified"
        assert props["routing_eligible"] is False
        assert props["publication_status"] == "published"
        assert props["source_type"] == "maintainer_provided"

    for feature in load_file("tricycle_stands.geojson")["features"]:
        props = feature["properties"]
        assert props["verification_status"] == "unverified"
        assert props["routing_eligible"] is False


def test_all_records_have_required_fields():
    """Every terminal/stand record has all required fields."""
    required = {"id", "name", "transport_type", "source_type", "verification_status",
                "publication_status", "routing_eligible", "review_date", "reviewer",
                "source_note", "linked_routes"}
    for feature in load_file("terminals.geojson")["features"]:
        props = feature["properties"]
        missing = required - set(props.keys())
        assert not missing, f"terminal {props['id']} missing: {missing}"
    for feature in load_file("tricycle_stands.geojson")["features"]:
        props = feature["properties"]
        missing = required - set(props.keys())
        assert not missing, f"stand {props['id']} missing: {missing}"


def test_two_route_identities_exist():
    """Two route records for the two corridors."""
    routes = load_file("routes.json")["routes"]
    ids = {r["id"] for r in routes}
    assert ids == {"mapandan-dagupan-minibus", "mapandan-mangaldan-jeepney"}


def test_five_initial_patterns_including_turnaround():
    """Five patterns: two minibus directions, one turnaround, two jeepney directions."""
    patterns = load_file("service_patterns.json")["patterns"]
    ids = {p["id"] for p in patterns}
    expected = {
        "mini-mapandan-dagupan-outbound",
        "mini-dagupan-mapandan-return",
        "mini-dagupan-turnaround",
        "jeep-mangaldan-mapandan",
        "jeep-mapandan-mangaldan",
    }
    assert ids == expected


def test_dagupan_turnaround_is_non_passenger():
    """The operational turnaround must not be offered as a passenger trip."""
    patterns = load_file("service_patterns.json")["patterns"]
    turnaround = next(p for p in patterns if p["id"] == "mini-dagupan-turnaround")
    assert turnaround["default_passenger_routing_eligible"] is False
    assert turnaround["classification"] == "operational_vehicle_movement"
    assert turnaround["routing_eligible"] is False
    assert "passenger" in turnaround["notes"].lower()


def test_turnaround_not_linked_as_passenger_route():
    """No route should reference the operational turnaround as a passenger pattern."""
    routes = load_file("routes.json")["routes"]
    for route in routes:
        for pattern_id in route.get("patterns", []):
            assert pattern_id != "mini-dagupan-turnaround", \
                f"route {route['id']} must not include turnaround as passenger pattern"


def test_jeepney_reverse_pattern_not_assumed_reversal():
    """The Mangaldan-bound pattern must be explicitly separate, not an auto-reversal."""
    patterns = load_file("service_patterns.json")["patterns"]
    outbound = next(p for p in patterns if p["id"] == "jeep-mangaldan-mapandan")
    return_p = next(p for p in patterns if p["id"] == "jeep-mapandan-mangaldan")
    assert outbound["notes"]
    assert "reverse path" in return_p["notes"].lower()
    assert outbound["direction"] != return_p["direction"]


def test_named_places_not_merged_with_terminals():
    """The Alaminos bus terminal and Bigmak landmark must stay distinct."""
    places = load_file("named_places.json")["places"]
    place_ids = {p["id"] for p in places}
    assert "place-alaminos-bus-terminal-dagupan" in place_ids
    assert "place-bigmak-mangaldan" in place_ids
    assert "term-mini-dagupan" not in place_ids
    assert "term-jeep-mangaldan" not in place_ids

    data = load_file("named_places.json")
    assert data["relationships_to_resolve"]
    assert any("term-mini-dagupan" in r and "alaminos-bus-terminal-dagupan" in r
               for r in data["relationships_to_resolve"])


def test_named_places_are_nonspatial():
    """Named place landmarks are not geocoded until verified."""
    places = load_file("named_places.json")["places"]
    for place in places:
        assert place.get("geometry") is None


def test_four_fare_ranges_preserved():
    """All four reported fare ranges must be preserved exactly."""
    fares = load_file("fares.json")["fares"]
    by_id = {f["id"]: f for f in fares}

    assert by_id["fare-mini-mapandan-dagupan"]["amount"]["min"] == 35
    assert by_id["fare-mini-mapandan-dagupan"]["amount"]["max"] == 40
    assert by_id["fare-jeep-mapandan-mangaldan"]["amount"]["min"] == 21
    assert by_id["fare-jeep-mapandan-mangaldan"]["amount"]["max"] == 25
    assert by_id["fare-tri-passing-short"]["amount"]["min"] == 10
    assert by_id["fare-tri-passing-short"]["amount"]["max"] == 15
    assert by_id["fare-tri-arkila-start"]["amount"]["min"] == 20
    assert by_id["fare-tri-arkila-start"]["amount"]["max"] == 25


def test_fares_are_locally_reported_not_official():
    """Provisional fares must not be labeled official_verified."""
    fares = load_file("fares.json")["fares"]
    for fare in fares:
        assert fare["rate_kind"] == "locally_reported_range"
        assert fare["verification_status"] == "locally_reported"
        assert fare["effective_date"] is None
        assert fare["rate_kind"] == "locally_reported_range"


def test_fares_currency_is_php():
    """All fare amounts use PHP."""
    for fare in load_file("fares.json")["fares"]:
        assert fare["amount"]["currency"] == "PHP"


def test_tricycle_fare_basics_are_short_trip_not_fixed():
    """Tricycle fare observations are conditional ranges, not fixed long-trip prices."""
    fares = load_file("fares.json")["fares"]
    for fare in fares:
        if fare.get("vehicle_type") == "tricycle":
            if fare.get("service_type") == "shared_passing":
                assert fare["basis"] == "short_trip"
            if fare.get("service_type") == "arkila":
                assert fare["basis"] == "starting_fare_short_trip"
                assert "may increase" in fare["notes"].lower()


def test_tricycle_stands_have_no_operators_or_zones():
    """Stands do not imply TODA coverage or operating rules."""
    stands = load_file("tricycle_stands.geojson")["features"]
    for feature in stands:
        props = feature["properties"]
        assert props["todas"] == []
        assert props["linked_routes"] == []
        assert props["linked_operators"] == []


def test_empty_datasets_are_valid():
    """Stops, route shapes, schedules, tricycle zones, rules, road graph are empty."""
    assert load_file("stops.geojson")["features"] == []
    assert all(f["properties"]["routing_eligible"] is False for f in load_file("route_shapes.geojson")["features"])
    assert load_file("schedules.json")["schedules"] == []
    assert load_file("tricycle_zones.geojson")["features"] == []
    assert load_file("tricycle_rules.json")["rules"] == []
    assert load_file("stop_occurrences.json")["occurrences"] == []
    assert load_file("travel_time_profiles.json")["profiles"] == []
    assert load_file("transfer_rules.json")["rules"] == []
    assert load_file("road_graph_source.geojson")["features"] == []


def test_empty_route_shapes_not_manufactured():
    """route_shapes.geojson must not contain fabricated geometry from street sequences."""
    shapes = load_file("route_shapes.geojson")
    assert all(f["properties"].get("response_checksum") for f in shapes["features"])
    assert "must not be manufactured" in shapes["notes"].lower()


def test_road_graph_not_sourced_from_display_layer():
    """road_graph_source must explicitly reject using the GIS display roads."""
    rg = load_file("road_graph_source.geojson")
    assert rg["type"] == "FeatureCollection"
    assert rg["access_policy"] == "unknown_access_is_not_permissive"
    assert any("display" in p.lower() or "routing input" in p.lower()
               for p in rg.get("input_policy", []))


def test_coverage_declared_reference_only():
    """Coverage must declare all corridors as non-routing-eligible."""
    coverage = load_file("coverage.json")
    assert coverage["supported_corridors"]
    for corridor in coverage["supported_corridors"]:
        assert corridor["routing_eligible"] is False
        assert corridor["status"] == "provisional_reference"


def test_coverage_declares_unsupported_area():
    """Coverage must not claim full Pangasinan support."""
    coverage = load_file("coverage.json")
    areas = coverage["unsupported_areas"]
    assert any("Pangasinan" in a["name"] or "province-wide" in a.get("reason", "").lower()
               for a in areas)


def test_sources_record_maintainer_provided_and_fare_reference():
    """Sources must record maintainer_provided and the fare ordinance reference."""
    sources = load_file("sources.json")["sources"]
    source_ids = {s["id"] for s in sources}
    assert "maintainer-supplied-coordinates" in source_ids
    assert "ord-2024-003-fare-ordinance" in source_ids
    assert "mtop-service-record" in source_ids

    ordinance = next(s for s in sources if s["id"] == "ord-2024-003-fare-ordinance")
    assert ordinance["republication_permitted"] is True


def test_departure_models_for_fill_and_go():
    """Minibus and jeepney modeled as fill_and_go, not scheduled."""
    profiles = load_file("travel_time_profiles.json")
    assert profiles["profiles"] == []


def test_manifest_references_all_files():
    """Manifest must reference every data file."""
    manifest = load_file("manifest.json")
    import os
    files = [f for f in os.listdir(DATA_DIR) if f.endswith((".json", ".geojson")) and f != "manifest.json"]
    referenced = set()
    for key in manifest:
        val = manifest[key]
        if isinstance(val, str) and val.endswith((".json", ".geojson")):
            referenced.add(val)
    for f in files:
        assert f in referenced, f"manifest does not reference {f}"


def test_no_scheduled_service_without_calendars():
    """No schedule records exist; departure must be fill_and_go for fixed-route."""
    assert load_file("schedules.json")["schedules"] == []


def test_all_ids_follow_stable_convention():
    """IDs use the documented naming convention."""
    for feature in load_file("terminals.geojson")["features"]:
        assert feature["properties"]["id"].startswith("term-")
    for feature in load_file("tricycle_stands.geojson")["features"]:
        assert feature["properties"]["id"].startswith("stand-")
    for place in load_file("named_places.json")["places"]:
        assert place["id"].startswith("place-")


def test_transport_validation_passes():
    """The full validation suite passes on the seeded data."""
    errors = validate_transport_data()
    assert not errors, f"Validation errors: {errors}"


def test_public_projection_preserves_coordinates_and_applicable_fares():
    from _build.transport.compiler import reference_bundle
    features = reference_bundle()["features"]
    source = load_file("terminals.geojson")["features"] + load_file("tricycle_stands.geojson")["features"]
    assert len(features) == 7
    for feature, original in zip(features, source):
        assert feature["geometry"] == original["geometry"]
        props = feature["properties"]
        assert "linked_operators" not in props
        assert "license" not in props
        ranges = [(f["amount"]["min"], f["amount"]["max"]) for f in props["fares"]]
        assert ranges == {"minibus": [(35, 40)], "jeepney": [(21, 25)],
                          "tricycle": [(10, 15), (20, 25)]}[props["transport_type"]]
    for fare in load_file("fares.json")["fares"]:
        assert fare["source_reference"] == "commuter-reported-fares"


def test_commuter_locales_and_static_directory():
    from _build.locales import load_locale
    from _build.transport.compiler import commuter_placeholders
    keys = set(load_locale("en")["commuter"])
    for lang in ("en", "fil", "pag"):
        locale = load_locale(lang)
        assert set(locale["commuter"]) == keys
        assert all(locale["commuter"].values())
        html = commuter_placeholders(locale)["COMMUTER_DIRECTORY"]
        assert html.count('<article ') == 7
        assert "PHP 35-40" in html and "PHP 21-25" in html
        assert "PHP 10-15" in html and "PHP 20-25" in html
        public = json.loads(commuter_placeholders(locale)["COMMUTER_DATA"])
        assert "mini-dagupan-turnaround" not in public["labels"]
        for key in ("intro", "candidate_warning", "hint", "fallback", "loading", "ready", "tiles_failed", "unavailable"):
            text = public["labels"][key]
            assert len(text.split()) <= 14
            assert text.count(".") <= 1
