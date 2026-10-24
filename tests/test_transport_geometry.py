"""Offline captured-response and publication regressions. Never call directions APIs."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from _build.transport.compiler import reference_bundle
from _build.transport.generate import (
    digest,
    fetch_response,
    matching_issues,
    ordered,
    parse_response,
)
from _build.transport.validation import load_transport_data, validate_shapes

FIXTURES = Path(__file__).parent / "fixtures/transport-osrm"


@pytest.mark.parametrize("index", range(5))
def test_real_captured_response(index):
    data = load_transport_data()
    patterns = data["transport/route_waypoints.json"]["patterns"]
    pattern = patterns[index]
    response = json.loads((FIXTURES / (pattern["id"] + ".json")).read_text())
    points = ordered(pattern, patterns)
    result = parse_response(response, points)
    assert len(result["legs"]) == len(points)-1
    assert result == parse_response(response, points)
    assert max(result["snap_offsets_m"]) <= 30
    generated = next(f for f in data["transport/route_shapes.geojson"]["features"] if f["id"] == pattern["id"])
    assert generated["geometry"] == response["routes"][0]["geometry"]
    if "reverse_of" in pattern:
        forward = next(p for p in patterns if p["id"] == pattern["reverse_of"])
        assert points == list(reversed(forward["coordinates"]))


@pytest.mark.parametrize("mutation,reason", [
    (lambda r: r["waypoints"][0].update(location=[120.5, 16.1]), "excessive_snap"),
    (lambda r: r["routes"][0]["legs"].pop(), "wrong_leg_count"),
    (lambda r: r["routes"][0]["geometry"].update(type="Polygon"), "full_geometry"),
    (lambda r: r.update(code="NoRoute"), "no_route"),
])
def test_reject_invalid_responses(mutation, reason):
    patterns = load_transport_data()["transport/route_waypoints.json"]["patterns"]
    response = json.loads((FIXTURES / (patterns[0]["id"] + ".json")).read_text())
    mutation(response)
    with pytest.raises(ValueError, match=reason):
        parse_response(response, ordered(patterns[0], patterns))


@pytest.mark.parametrize("field,value", [("routing_eligible", True), ("input_hash", "old"), ("classification", "operational_vehicle_movement"), ("verification_status", "authority_confirmed")])
def test_candidate_publication_gates(field, value):
    data = copy.deepcopy(load_transport_data())
    data["transport/route_shapes.geojson"]["features"][0]["properties"][field] = value
    assert validate_shapes(data)


def test_empty_partial_and_stale_publication_no_network():
    data = load_transport_data()
    shapes = data["transport/route_shapes.geojson"]["features"]
    for subset in ([], shapes[:1], shapes):
        data["transport/route_shapes.geojson"]["features"] = subset
        with patch("_build.transport.compiler.load_transport_data", return_value=data), patch("urllib.request.urlopen", side_effect=AssertionError("build network")):
            bundle = reference_bundle()
        assert len(bundle["features"]) == 7
        assert all(not s["properties"]["routing_eligible"] for s in bundle["shapes"])


def test_explicitly_stale_artifacts_are_retained_but_never_published():
    data = copy.deepcopy(load_transport_data())
    props = data["transport/route_shapes.geojson"]["features"][0]["properties"]
    props.update(stale=True, input_hash="previous-input")
    with patch("_build.transport.compiler.load_transport_data", return_value=data):
        assert props["id"] not in {f["properties"]["id"] for f in reference_bundle()["shapes"]}


def test_approved_coordinate_history_and_higher_precision():
    data = load_transport_data()
    features = {f["id"]: f for f in data["transport/terminals.geojson"]["features"]}
    assert features["term-mini-dagupan"]["geometry"]["coordinates"] == [120.3437554808, 16.0465670984]
    assert features["term-mini-dagupan"]["properties"]["superseded_observations"][0]["coordinates"] == [120.34487896138853, 16.068389474097867]
    assert features["term-jeep-mapandan"]["geometry"]["coordinates"] == [120.45090842493461, 16.025956286653532]
    expected = {"term-mini-mapandan": [120.4524166667, 16.0265833333], "term-jeep-mapandan": [120.45090842493461, 16.025956286653532], "term-jeep-mangaldan": [120.404355, 16.065126], "stand-tri-market": [120.4509837880669, 16.026180552095127], "stand-tri-plaza": [120.452771, 16.026576], "stand-tri-hall": [120.45309, 16.026763]}
    features.update({f["id"]: f for f in data["transport/tricycle_stands.geojson"]["features"]})
    assert {key: features[key]["geometry"]["coordinates"] for key in expected} == expected


def test_service_timeout_is_bounded_and_never_falls_back():
    with patch("urllib.request.urlopen", side_effect=TimeoutError("offline")) as network, patch("time.sleep") as sleep:
        with pytest.raises(TimeoutError):
            fetch_response("https://configured.invalid/route")
    assert network.call_count == 2
    sleep.assert_called_once_with(2.1)
    assert all(call.args[0].full_url == "https://configured.invalid/route" for call in network.call_args_list)


def test_unrelated_corridor_withheld_and_discrepancies_retained():
    data = load_transport_data()
    pattern = data["transport/route_waypoints.json"]["patterns"][0]
    props = copy.deepcopy(data["transport/route_shapes.geojson"]["features"][0]["properties"])
    for leg in props["legs"]:
        leg["road_names"] = ["Unrelated Street"]
    assert "unexpected_road_corridor" in matching_issues(pattern, pattern["coordinates"], props)
    assert props["distance_comparison"]["difference_m"] == 1567.9
    assert props["distance_comparison"]["difference_from_upper_m"] == 1167.9


def test_reviewed_geometry_requires_human_evidence_but_never_routing():
    data = copy.deepcopy(load_transport_data())
    props = data["transport/route_shapes.geojson"]["features"][0]["properties"]
    props.update(geometry_status="verified", geometry_review="reviewed", verification_status="maintainer_confirmed")
    assert validate_shapes(data)
    props["human_geometry_review"] = {"date": "2026-10-24", "reviewer": "fixture only", "evidence_source": "fixture-field-review"}
    data["transport/sources.json"]["sources"].append({"id": "fixture-field-review", "type": "field_survey", "republication_permitted": True})
    assert not validate_shapes(data)
    props["routing_eligible"] = True
    assert validate_shapes(data)


def test_live_generation_report_and_operational_separation():
    data = load_transport_data()
    report = data["transport/generation_report.json"]
    patterns = data["transport/route_waypoints.json"]["patterns"]
    assert len(report["patterns"]) == 5
    for item, pattern in zip(report["patterns"], patterns):
        assert item["input_hash"] == digest(ordered(pattern, patterns))
        if item["pattern_id"].startswith("jeep-"):
            assert item["status"] == "candidate"
            assert any("conservative_display_review" in warning for warning in item["warnings"])
    bundle = reference_bundle()
    assert len(bundle["shapes"]) == 4
    assert len(bundle["patterns"]) == 4
    assert all(s["properties"]["classification"] == "passenger_candidate" for s in bundle["shapes"])
    assert "mini-dagupan-turnaround" not in json.dumps(bundle)


@pytest.mark.parametrize("pattern_id", ["jeep-mangaldan-mapandan", "jeep-mapandan-mangaldan"])
def test_short_same_road_leg_is_candidate_only_with_warning(pattern_id):
    data = load_transport_data()
    feature = next(f for f in data["transport/route_shapes.geojson"]["features"] if f["id"] == pattern_id)
    props = feature["properties"]
    response = json.loads((FIXTURES / (pattern_id + ".json")).read_text())
    assert feature["geometry"] == response["routes"][0]["geometry"]
    assert min(leg["distance_m"] for leg in props["legs"]) == 3.9
    assert max(props["snap_offsets_m"]) == 25.593
    assert props["routing_eligible"] is False
    assert props["verification_status"] == "unverified"
    props["warnings"] = [w for w in props["warnings"] if "conservative_display_review" not in w]
    assert validate_shapes(data)


def test_short_leg_exception_rejects_wrong_road_and_zero_length():
    data = load_transport_data()
    pattern = data["transport/route_waypoints.json"]["patterns"][2]
    points = ordered(pattern, data["transport/route_waypoints.json"]["patterns"])
    result = parse_response(json.loads((FIXTURES / (pattern["id"] + ".json")).read_text()), points)
    result["legs"][0]["road_names"] = ["Other Road"]
    assert matching_issues(pattern, points, result)
    result["legs"][0]["road_names"] = ["National Highway"]
    result["legs"][0]["distance_m"] = 0
    assert matching_issues(pattern, points, result)


def test_short_leg_exception_does_not_follow_changed_observations():
    data = load_transport_data()
    pattern = data["transport/route_waypoints.json"]["patterns"][2]
    points = ordered(pattern, data["transport/route_waypoints.json"]["patterns"])
    result = parse_response(json.loads((FIXTURES / (pattern["id"] + ".json")).read_text()), points)
    changed = copy.deepcopy(points)
    changed[0][0] += .000001
    assert matching_issues(pattern, changed, result)
