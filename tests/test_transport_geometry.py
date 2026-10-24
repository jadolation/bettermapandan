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


@pytest.mark.parametrize("pattern_id", [p["id"] for p in load_transport_data()["transport/route_waypoints.json"]["patterns"]])
def test_real_captured_response(pattern_id):
    data = load_transport_data()
    patterns = data["transport/route_waypoints.json"]["patterns"]
    pattern = next(p for p in patterns if p["id"] == pattern_id)
    response = json.loads((FIXTURES / (pattern["id"] + ".json")).read_text())
    points = ordered(pattern, patterns)
    result = parse_response(response, points, sparse_segments=pattern.get("sparse_segments", ()))
    assert len(result["legs"]) == len(points)-1
    assert result == parse_response(response, points, sparse_segments=pattern.get("sparse_segments", ()))
    assert max(result["snap_offsets_m"]) <= 30
    generated = next((f for f in data["transport/route_shapes.geojson"]["features"] if f["id"] == pattern["id"]), None)
    if generated:
        assert generated["geometry"] == result["geometry"]
    else:
        assert matching_issues(pattern, points, result)
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
    assert len(report["patterns"]) == len(patterns)
    for item, pattern in zip(report["patterns"], patterns):
        assert item["input_hash"] == digest(ordered(pattern, patterns))
        if item["pattern_id"] in ("jeep-mapandan-mangaldan", "jeep-mangaldan-mapandan"):
            assert item["status"] == "candidate"
            assert any("conservative_display_review" in warning for warning in item["warnings"])
    bundle = reference_bundle()
    assert len(bundle["shapes"]) == sum(p["classification"] == "passenger_candidate" for p in patterns)
    assert len(bundle["patterns"]) == len(patterns) - 1
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


def test_expansion_observations_partial_origin_and_independent_shared_leg():
    data = load_transport_data()
    patterns = data["transport/route_waypoints.json"]["patterns"]
    by_id = {p["id"]: p for p in patterns}
    assert by_id["mini-mapandan-manaoag"]["coordinates"] == [[120.4537424255,16.0271905088],[120.4593303732,16.0214492605],[120.4834076541,16.0376770060],[120.4854454611,16.0434458815],[120.4857012528,16.0434294929],[120.4856927264,16.0439293450],[120.4863702448,16.0439189698]]
    derived = {d["index"] for d in by_id["tri-guam-mapandan"]["derived_waypoints"]}
    assert [p for i, p in enumerate(by_id["tri-guam-mapandan"]["coordinates"]) if i not in derived] == [[120.4978397275,15.9767050433],[120.4924608781,15.9902390412],[120.4546204349,16.0260434594],[120.4538217097,16.0271171000],[120.4529887567,16.0266228515]]
    assert by_id["shared-mapandan-border-arch"]["coordinates"] == [[120.4524476598,16.0264535118],[120.4377032368,16.0293339702],[120.4193286072,16.0271295850]]
    assert by_id["tri-border-arch-tuliao"]["coordinates"] == [[120.4193286072,16.0271295850],[120.4021994347,16.0071289665]]
    assert "jeep-tuliao-calasiao" in by_id and "tri-tuliao-sta-barbara" in by_id
    for forward, reverse in [("mini-mapandan-manaoag", "mini-manaoag-mapandan"), ("tri-guam-mapandan", "tri-mapandan-guam")]:
        assert ordered(by_id[reverse], patterns) == list(reversed(by_id[forward]["coordinates"]))
        a, b = [json.loads((FIXTURES / (pid + ".json")).read_text())["routes"][0] for pid in (forward, reverse)]
        assert b["geometry"]["coordinates"] != list(reversed(a["geometry"]["coordinates"]))


def test_discrepancies_review_warnings_and_candidates_published():
    data = load_transport_data()
    report = {p["pattern_id"]: p for p in data["transport/generation_report.json"]["patterns"]}
    public = {f["properties"]["pattern_id"] for f in reference_bundle()["shapes"]}
    for pid in ("mini-mapandan-manaoag", "mini-manaoag-mapandan", "tri-guam-mapandan", "tri-mapandan-guam"):
        item = report[pid]
        assert item["status"] == "candidate" and pid in public
        assert item["response_checksum"] and item["response_summary"]
        assert max(item["reported_snap_offsets_m"]) <= 30
    assert any("Maloko" in warning for warning in report["mini-mapandan-manaoag"]["warnings"])
    assert any("Galaban" in warning for warning in report["mini-mapandan-manaoag"]["warnings"])
    assert report["tri-guam-mapandan"]["overview_sampling_reconstructed"]
    assert any("contiguous_ordered_steps" in w for w in report["tri-guam-mapandan"]["warnings"])
    assert "Fire Tree Avenue" in str(report["tri-guam-mapandan"]["response_summary"])
    assert {"shared-mapandan-border-arch", "tri-border-arch-tuliao"} <= public


@pytest.mark.parametrize("pid", ["tri-guam-mapandan", "tri-mapandan-guam"])
def test_guam_clipping_vertex_and_substantive_mismatch(pid):
    patterns = load_transport_data()["transport/route_waypoints.json"]["patterns"]
    pattern = next(p for p in patterns if p["id"] == pid)
    response = json.loads((FIXTURES / (pid + ".json")).read_text())
    result = parse_response(response, ordered(pattern, patterns), sparse_segments=pattern.get("sparse_segments", ()))
    assert result["overview_sampling_reconstructed"]
    assert [120.45381, 16.027095] in result["geometry"]["coordinates"]
    response["routes"][0]["geometry"]["coordinates"][20][0] += .001
    with pytest.raises(ValueError, match="full_geometry_differs"):
        parse_response(response, ordered(pattern, patterns), sparse_segments=pattern.get("sparse_segments", ()))


def test_missing_labels_warn_but_wrong_order_and_unrelated_corridor_fail():
    patterns = load_transport_data()["transport/route_waypoints.json"]["patterns"]
    pattern = next(p for p in patterns if p["id"] == "mini-mapandan-manaoag")
    response = json.loads((FIXTURES / (pattern["id"] + ".json")).read_text())
    result = parse_response(response, pattern["coordinates"])
    assert not matching_issues(pattern, pattern["coordinates"], result)
    assert any("Maloko" in w for w in matching_issues(pattern, pattern["coordinates"], result, name_warnings=True))
    for leg in result["legs"]:
        leg["road_names"] = ["Unrelated Street"]
    assert matching_issues(pattern, pattern["coordinates"], result)
    result["legs"][0]["road_names"] = ["Tabayoyong", "Tiong", "Firetree"]
    assert any("out_of_order" in w for w in matching_issues(pattern, pattern["coordinates"], result))


def test_missing_name_warning_cannot_be_silently_removed():
    data = load_transport_data()
    feature = next(f for f in data["transport/route_shapes.geojson"]["features"] if f["id"] == "mini-mapandan-manaoag")
    feature["properties"]["warnings"].remove("road_name_unresolved_review: Maloko")
    assert any("missing road-name review warning" in error for error in validate_shapes(data))


@pytest.mark.parametrize("mutation,reason", [
    (lambda r: r["routes"][0]["legs"][0]["steps"][1]["geometry"]["coordinates"][0].__setitem__(0, 120.9), "discontinuous_steps"),
    (lambda r: r["routes"][0]["legs"].reverse(), "unordered_leg_endpoints"),
    (lambda r: r["routes"][0]["legs"][2]["steps"][-1]["geometry"]["coordinates"][-1].__setitem__(1, 16.027105), "unordered_leg_endpoints"),
])
def test_reject_step_gaps_and_wrong_order(mutation, reason):
    patterns = load_transport_data()["transport/route_waypoints.json"]["patterns"]
    pattern = next(p for p in patterns if p["id"] == "tri-guam-mapandan")
    response = json.loads((FIXTURES / (pattern["id"] + ".json")).read_text())
    mutation(response)
    with pytest.raises(ValueError, match=reason):
        parse_response(response, ordered(pattern, patterns), sparse_segments=pattern.get("sparse_segments", ()))


def test_new_patterns_do_not_inherit_tiny_leg_exception():
    data = load_transport_data()
    pattern = next(p for p in data["transport/route_waypoints.json"]["patterns"] if p["id"] == "shared-mapandan-border-arch")
    result = parse_response(json.loads((FIXTURES / (pattern["id"] + ".json")).read_text()), pattern["coordinates"])
    result["legs"][0]["distance_m"] = 3.9
    assert matching_issues(pattern, pattern["coordinates"], result)


def test_full_generator_replay_is_offline_and_reproducible(tmp_path, monkeypatch):
    import shutil

    from _build.transport import generate
    data_dir = tmp_path / "data"
    captures = tmp_path / "captures"
    shutil.copytree(generate.DATA, data_dir)
    shutil.copytree(FIXTURES, captures)
    expected_report = (data_dir / "generation_report.json").read_bytes()
    expected_shapes = (data_dir / "route_shapes.geojson").read_bytes()
    monkeypatch.setattr(generate, "DATA", data_dir)
    monkeypatch.setattr("sys.argv", ["generate", "--endpoint", "https://routing.openstreetmap.de/routed-car", "--policy-url", "https://routing.openstreetmap.de/about.html", "--capture-dir", str(captures), "--replay"])
    with patch("urllib.request.urlopen", side_effect=AssertionError("replay network")), patch("time.sleep", side_effect=AssertionError("replay delay")):
        generate.main()
    assert (data_dir / "generation_report.json").read_bytes() == expected_report
    assert (data_dir / "route_shapes.geojson").read_bytes() == expected_shapes


def test_network_capture_requires_explicit_policy_review(monkeypatch, tmp_path):
    from _build.transport import generate
    monkeypatch.setattr("sys.argv", ["generate", "--endpoint", "https://configured.invalid", "--policy-url", "https://configured.invalid/policy", "--capture-dir", str(tmp_path)])
    with patch("urllib.request.urlopen", side_effect=AssertionError("unapproved network")), pytest.raises(SystemExit):
        generate.main()


def test_firetree_shaping_and_sparse_edge_have_actual_osm_evidence():
    import hashlib
    import xml.etree.ElementTree as ET

    raw = (FIXTURES / "firetree-osm.xml").read_bytes()
    data = load_transport_data()
    audit = next(s for s in data["transport/sources.json"]["sources"] if s["id"] == "firetree-osm-audit")
    assert hashlib.sha256(raw).hexdigest() == audit["sha256"]
    root = ET.fromstring(raw)
    nodes = {int(n.get("id")): [float(n.get("lon")), float(n.get("lat"))] for n in root.findall("node")}
    ways = {int(w.get("id")): w for w in root.findall("way")}
    for pid in ("tri-guam-mapandan", "tri-mapandan-guam"):
        p = next(p for p in data["transport/route_waypoints.json"]["patterns"] if p["id"] == pid)
        for derived in p["derived_waypoints"]:
            assert p["coordinates"][derived["index"]] == nodes[derived["osm_node"]]
        for sparse in p["sparse_segments"]:
            refs = [int(n.get("ref")) for n in ways[sparse["osm_way"]].findall("nd")]
            assert abs(refs.index(sparse["osm_nodes"][0]) - refs.index(sparse["osm_nodes"][1])) == 1
            assert sparse["coordinates"] == [nodes[n] for n in sparse["osm_nodes"]]
        response = json.loads((FIXTURES / (pid + ".json")).read_text())
        with pytest.raises(ValueError, match="geometry_gap"):
            parse_response(response, p["coordinates"])
        result = parse_response(response, p["coordinates"], sparse_segments=p["sparse_segments"])
        names = {name for leg in result["legs"] for name in leg["road_names"]}
        assert not names.intersection({"Acacia Street", "Caimito Street"})
    for way_id in audit["road_way_ids"]:
        tags = {t.get("k"): t.get("v") for t in ways[way_id].findall("tag")}
        assert tags["name"] == "Fire Tree Avenue"
        assert not {"access", "motor_vehicle", "motorcar", "motorcycle", "oneway"}.intersection(tags)
    history = data["transport/route_shapes.geojson"]["historical_features"]
    assert any(f["id"] == "tri-guam-mapandan" and f["properties"]["distance_m"] == 8333.6 for f in history)


def test_final_leg_precision_partial_approaches_and_no_invented_connectors():
    data = load_transport_data()
    patterns = {p["id"]: p for p in data["transport/route_waypoints.json"]["patterns"]}
    sm = patterns["mini-manaoag-sm"]
    assert sm["coordinates"] == [[120.4862474315581,16.04395435752346],[120.48743296792928,16.04398786809919],[120.489156001604,16.041175533275535],[120.49142263243151,16.037653211273575],[120.56004355150428,15.981808857530375],[120.57100308966663,15.979247314289665],[120.5717685441116,15.969723185220058],[120.57163979808034,15.970620569087611]]
    assert "75 m" in sm["endpoint_caveat"]
    assert patterns["tri-tuliao-sta-barbara"]["coordinates"] == [[120.40212464271654,16.007106182475425],[120.40302899276354,16.006480374232265],[120.40337277883535,16.00189355329774]]
    assert patterns["tri-tuliao-sta-barbara"]["unrouted_endpoint"] == [120.40309090560488,16.00082843128207]
    failure = json.loads((FIXTURES / "sta-barbara-plaza-no-segment.json").read_text())
    assert failure["code"] == "NoSegment"
    with pytest.raises(ValueError, match="NoSegment"):
        parse_response(failure, patterns["tri-tuliao-sta-barbara"]["coordinates"])
    bundle = reference_bundle()
    assert all(f["geometry"]["type"] == "LineString" for f in bundle["shapes"])
    assert not any(p["id"] == "mini-sm-manaoag" for p in bundle["patterns"])
    assert data["transport/transfer_rules.json"]["rules"] == []
