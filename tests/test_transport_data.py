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


def test_corridor_and_journey_identities_exist():
    """Catalog identities are references, not verified services."""
    routes = load_file("routes.json")["routes"]
    ids = {r["id"] for r in routes}
    assert ids == {"mapandan-dagupan-minibus", "mapandan-mangaldan-jeepney", "mapandan-manaoag-minibus", "urdaneta-mapandan-tricycle", "mapandan-calasiao-multileg", "mapandan-sta-barbara-multileg", "manaoag-sm-minibus", "mapandan-manaoag-sm-multileg"}


def test_passenger_patterns_and_operational_separation():
    """Original patterns plus independent candidate directions and missing final legs."""
    patterns = load_file("service_patterns.json")["patterns"]
    ids = {p["id"] for p in patterns}
    expected = {
        "mini-mapandan-dagupan-outbound",
        "mini-dagupan-mapandan-return",
        "mini-dagupan-turnaround",
        "jeep-mangaldan-mapandan",
        "jeep-mapandan-mangaldan",
    }
    expected.update({"mini-mapandan-manaoag", "mini-manaoag-mapandan", "tri-guam-mapandan", "tri-mapandan-guam", "shared-mapandan-border-arch", "tri-border-arch-tuliao", "jeep-tuliao-calasiao", "tri-tuliao-sta-barbara"})
    assert ids == expected | {"mini-manaoag-sm"}


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


def test_unsupplied_named_places_remain_nonspatial():
    """Only explicitly supplied observations may have point geometry."""
    places = load_file("named_places.json")["places"]
    for place in places:
        if place.get("geometry") is not None:
            assert place["source_type"] == "maintainer_local_observation"
            assert place["routing_eligible"] is False
        if place["id"] in {"place-peoples-park", "place-phome", "place-coca-cola", "place-s-and-r", "place-robinsons-pangasinan", "place-jollibee-junction"} or place["source_type"] == "maintainer_provided":
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
        if fare["rate_kind"] == "unknown":
            assert fare["amount"] is None
            continue
        assert fare["rate_kind"] == "locally_reported_range"
        assert fare["verification_status"] == "locally_reported"
        assert fare["effective_date"] is None
        assert fare["rate_kind"] == "locally_reported_range"


def test_fares_currency_is_php():
    """All fare amounts use PHP."""
    for fare in load_file("fares.json")["fares"]:
        if fare["amount"] is not None:
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
        assert fare["source_reference"] in {"commuter-reported-fares", "route-expansion-observation", "final-legs-observation"}


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
        route_html = commuter_placeholders(locale)["COMMUTER_ROUTES"]
        assert route_html.count('<fieldset ') == len(reference_catalog())
        assert "PHP 15-20" in route_html and "PHP 70-100" in route_html and "PHP 50-80" in route_html
        assert locale["commuter"]["unknown_fare"] in route_html
        for route in reference_catalog():
            assert route["id"] in locale["commuter"]
            for leg in route["legs"]:
                assert leg["label_key"] in locale["commuter"]
                assert all(mode in locale["commuter"] for mode in leg["vehicle_types"])
            assert all(pid in locale["commuter"] for direction in route["directions"] for pid in direction)
        assert "PHP 35-40" in html and "PHP 21-25" in html
        assert "PHP 10-15" in html and "PHP 20-25" in html
        public = json.loads(commuter_placeholders(locale)["COMMUTER_DATA"])
        assert "mini-dagupan-turnaround" not in public["labels"]
        assert "swap" not in public["labels"]
        assert all(key in public["labels"] for key in (
            "show_all_places", "sheet_hide", "sheet_show", "sheet_drag", "boundary_note"))
        for key in ("intro", "candidate_warning", "hint", "fallback", "loading", "ready", "tiles_failed", "unavailable"):
            text = public["labels"][key]
            assert len(text.split()) <= 14
            assert text.count(".") <= 1


def reference_catalog():
    from _build.transport.compiler import reference_bundle
    return reference_bundle()["catalog"]


def test_public_sm_journey_preserves_two_source_legs():
    from _build.locales import load_locale
    from _build.transport.compiler import commuter_placeholders, reference_bundle
    bundle = reference_bundle()
    catalog = {r["id"]: r for r in bundle["catalog"]}
    assert "manaoag-sm-minibus" not in catalog
    route = catalog["mapandan-manaoag-sm-multileg"]
    assert route["directions"] == [["mini-mapandan-manaoag", "mini-manaoag-sm"]]
    assert route["transfer_count"] == 1 and len(route["legs"]) == 2
    assert [(leg["fare"]["amount"]["min"], leg["fare"]["amount"]["max"]) for leg in route["legs"]] == [(15, 20), (30, 40)]
    assert catalog["mapandan-manaoag-minibus"]["fare_summary"]["amount"] == {"min": 15, "max": 20, "currency": "PHP"}
    original = {f["properties"]["pattern_id"]: f for f in load_file("route_shapes.geojson")["features"]}
    for pattern in route["directions"][0]:
        assert next(f for f in bundle["shapes"] if f["properties"]["pattern_id"] == pattern)["geometry"] == original[pattern]["geometry"]
    for lang in ("en", "fil", "pag"):
        locale = load_locale(lang)
        html = commuter_placeholders(locale)["COMMUTER_ROUTES"]
        assert 'data-route="manaoag-sm-minibus"' not in html
        assert html.count('data-route="mapandan-manaoag-sm-multileg"') == 1
        assert "Mapandan -&gt; SM Urdaneta" in html
        assert locale["commuter"]["via_manaoag"] in html
        assert len(locale["commuter"]["via_manaoag"].split()) <= 9
        assert "PHP 45-60" in html


def test_explicit_route_marker_subsets_preserve_source_observations():
    from _build.transport.compiler import reference_bundle
    bundle = reference_bundle()
    features = {f["id"]: f for f in bundle["features"] + bundle["observations"]}
    catalog = {r["id"]: r for r in bundle["catalog"]}
    assert catalog["mapandan-dagupan-minibus"]["marker_ids"] == ["term-mini-mapandan", "term-mini-dagupan"]
    assert set(catalog["mapandan-manaoag-sm-multileg"]["marker_ids"]) == {
        "place-firetree-roundabout-manaoag", "place-manaoag-waiting", "place-meditek-manaoag", "place-sm-entry"}
    assert "place-tuliao-jeep" in catalog["mapandan-calasiao-multileg"]["marker_ids"]
    assert "place-tuliao-tricycle" not in catalog["mapandan-calasiao-multileg"]["marker_ids"]
    assert "place-tuliao-tricycle" in catalog["mapandan-sta-barbara-multileg"]["marker_ids"]
    assert "place-tuliao-jeep" not in catalog["mapandan-sta-barbara-multileg"]["marker_ids"]
    source_places = {p["id"]: p for p in load_file("named_places.json")["places"]}
    for feature in bundle["observations"]:
        assert feature["geometry"] == source_places[feature["id"]]["geometry"]
    for route in catalog.values():
        assert 0 < len(route["marker_ids"]) < len(features)
        assert all(i in features for i in route["marker_ids"])
        assert not {"place-peoples-park", "place-phome"}.intersection(route["marker_ids"])


def test_scoped_reported_totals_and_unknown_final_fare():
    import copy

    from _build.transport.compiler import reported_fare_summary
    catalog = {r["id"]: r for r in reference_catalog()}
    for rid, limits in {"mapandan-calasiao-multileg": (80, 120), "mapandan-manaoag-sm-multileg": (45, 60)}.items():
        result = catalog[rid]["fare_summary"]
        assert result["complete"] is True
        assert result["amount"] == {"min": limits[0], "max": limits[1], "currency": "PHP"}
    incomplete = catalog["mapandan-sta-barbara-multileg"]["fare_summary"]
    assert incomplete["complete"] is False and incomplete["amount"] is None
    assert incomplete["known_subtotal"] == {"min": 65, "max": 100, "currency": "PHP"}
    assert incomplete["unknown_leg_ids"] == ["leg-sta-barbara"]
    legs = copy.deepcopy(catalog["mapandan-calasiao-multileg"]["legs"])
    legs[-1]["fare"]["rate_kind"] = "inapplicable_test_fare"
    assert reported_fare_summary(legs)["complete"] is False


def test_distinct_precise_final_places_and_unverified_connections():
    from _build.transport.generate import distance
    data = load_file("named_places.json")
    places = {p["id"]: p for p in data["places"]}
    expected = {
        "place-tuliao-jeep": [120.40215800132748, 16.007041474290205],
        "place-tuliao-tricycle": [120.40212464271654, 16.007106182475425],
        "place-calasiao": [120.35382397535011, 16.021418024226584],
        "place-sta-barbara": [120.40309090560488, 16.00082843128207],
        "place-meditek-manaoag": [120.4862474315581, 16.04395435752346],
        "place-sm-entry": [120.57163979808034, 15.970620569087611],
    }
    for pid, point in expected.items():
        assert places[pid]["geometry"]["coordinates"] == point
    assert places["place-sm-entry"]["classification"] == "entry_approach_not_terminal"
    for c in data["conceptual_connections"]:
        assert c["access"] == "unverified" and c["geometry"] is None and c["routing_eligible"] is False
        a, b = [places[c[k]]["geometry"]["coordinates"] for k in ("from_id", "to_id")]
        assert a != b
        assert distance(a, b) == pytest.approx(c["observation_separation_m"], abs=.001)


def test_expansion_fares_and_incomplete_journeys():
    fares = {f["id"]: f for f in load_file("fares.json")["fares"]}
    for fid, limits in {"fare-mini-mapandan-manaoag": (15, 20), "fare-tri-guam-mapandan": (70, 100), "fare-shared-border-arch": (15, 20), "fare-tri-border-arch-tuliao": (50, 80)}.items():
        assert fares[fid]["amount"] == dict(zip(("min", "max", "currency"), (*limits, "PHP")))
    for fare in fares.values():
        assert fare["source_type"] == "maintainer_local_observation"
        assert fare["rate_kind"] == ("unknown" if fare["amount"] is None else "locally_reported_range")
    catalog = load_file("routes.json")
    shared = next(leg for leg in catalog["legs"] if leg["id"] == "leg-border-arch")
    assert shared["vehicle_types"] == ["minibus", "jeepney"]
    assert shared["route_affiliation"] is None
    for route in catalog["routes"]:
        assert route["routing_eligible"] is False
        if route["vehicle_type"] == "multileg":
            assert len(route["leg_ids"]) >= 2 and route["transfer_count"] == len(route["leg_ids"]) - 1
            assert route["directions"] == [route["patterns"]]
            assert route.get("total_fare") is None and route.get("total_duration_minutes") is None
            assert route["pedestrian_access"] == "unresolved"
            assert route["authorization"] == "unconfirmed"


@pytest.mark.parametrize("mutation", [
    lambda d: d["transport/fares.json"]["fares"][4].update(amount={"min": 0, "max": 0, "currency": "PHP"}),
    lambda d: d["transport/routes.json"]["routes"][4].update(total_fare=65),
    lambda d: d["transport/routes.json"]["routes"][4].update(pedestrian_access="verified"),
    lambda d: d["transport/routes.json"]["routes"][4].update(authorization="authorized"),
    lambda d: d["transport/routes.json"]["routes"][4]["directions"].append(["tri-border-arch-tuliao"]),
    lambda d: d["transport/routes.json"]["routes"][4]["directions"][0].append("mini-dagupan-turnaround"),
    lambda d: d["transport/service_patterns.json"]["patterns"][0].update(routing_eligible=True, geometry_verified=True),
])
def test_catalog_publication_rejects_unsupported_claims(mutation):
    from unittest.mock import patch

    from _build.transport.compiler import reference_bundle
    from _build.transport.validation import load_transport_data
    data = load_transport_data()
    # Mutations below target a multileg record regardless of catalog ordering.
    data["transport/routes.json"]["routes"][4] = next(r for r in data["transport/routes.json"]["routes"] if r["id"] == "mapandan-calasiao-multileg")
    mutation(data)
    with patch("_build.transport.compiler.load_transport_data", return_value=data), pytest.raises(ValueError):
        reference_bundle()
