"""Explicit maintainer-only OSRM capture. Never imported by the build for networking."""
import argparse
import difflib
import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "src/data/transport"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def ordered(pattern, patterns):
    return pattern.get("coordinates") or list(reversed(next(p["coordinates"] for p in patterns if p["id"] == pattern["reverse_of"])))


def distance(a, b):
    x, y = map(math.radians, a)
    u, v = map(math.radians, b)
    return 6371000 * 2 * math.asin(min(1, math.sqrt(math.sin((v-y)/2)**2 + math.cos(y)*math.cos(v)*math.sin((u-x)/2)**2)))


def coordinate(c):
    return isinstance(c, list) and len(c) == 2 and all(type(v) in (int, float) and math.isfinite(v) for v in c) and abs(c[0]) <= 180 and abs(c[1]) <= 90


def deduplicate(coords):
    return [c for i, c in enumerate(coords) if not i or c != coords[i-1]]


def equivalent_sampling(overview, steps):
    """Only permit ordered, sub-metre clipping/sampling changes, never detours."""
    a, b = deduplicate(overview), deduplicate(steps)
    if not a or not b or not all(coordinate(c) for c in a):
        return False
    if a[0] != b[0] or a[-1] != b[-1]:
        return False
    for tag, i, j, k, stop in difflib.SequenceMatcher(None, list(map(tuple, a)), list(map(tuple, b)), autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            return False
        line, start, end = (b, k, stop) if tag == "insert" else (a, i, j)
        if start == 0 or end == len(line):
            return False
        # Triangle excess bounds deviation from the unchanged enclosing segment.
        segment = line[start-1:end+1]
        direct = distance(segment[0], segment[-1])
        length = sum(distance(x, y) for x, y in zip(segment, segment[1:]))
        if length - direct > .1 or any(min(distance(c, segment[0]), distance(c, segment[-1])) > 2 for c in segment[1:-1]):
            return False
    return True


def fetch_response(url):
    """At most two serial attempts; never switch service on failure."""
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "BetterMapandan-maintenance/1.0 (https://github.com/jadolation/bettermapandan)"})
            with urllib.request.urlopen(request, timeout=35) as response:
                raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise ValueError("response_size_limit")
            return raw
        except OSError:
            if attempt:
                raise
            time.sleep(2.1)


def sourced_sparse_segment(a, b, segments):
    """A sparse edge is allowed only where captured OSM has adjacent road nodes."""
    return distance(a, b) <= 1000 and any(distance(a, ends[0]) < .2 and distance(b, ends[1]) < .2
               for segment in segments for ends in (segment["coordinates"], list(reversed(segment["coordinates"]))))


def parse_response(response, points, radius=30, sparse_segments=()):
    """Validate ordered step geometry, not proximity to a whole-route line."""
    if response.get("code") != "Ok":
        raise ValueError("no_route: " + str(response.get("code")))
    routes = response.get("routes", [])
    snaps = response.get("waypoints", [])
    if len(routes) != 1 or len(snaps) != len(points):
        raise ValueError("ambiguous_route_or_waypoint_count")
    route = routes[0]
    legs = route.get("legs", [])
    if len(legs) != len(points)-1:
        raise ValueError("wrong_leg_count")
    offsets = []
    for source, snap in zip(points, snaps):
        if not coordinate(source) or not coordinate(snap.get("location")):
            raise ValueError("invalid_coordinate")
        offset = distance(source, snap["location"])
        offsets.append(round(offset, 3))
        if offset > radius or not math.isfinite(snap.get("distance", float("inf"))) or snap["distance"] > radius:
            raise ValueError("excessive_snap: " + str(offset))
    combined, reports = [], []
    for i, leg in enumerate(legs):
        line, names = [], []
        for step in leg.get("steps", []):
            geometry = step.get("geometry", {})
            coords = geometry.get("coordinates", [])
            if geometry.get("type") != "LineString" or len(coords) < 2 or not all(coordinate(c) for c in coords):
                raise ValueError("corrupt_step_geometry")
            if line and line[-1] != coords[0]:
                raise ValueError("discontinuous_steps")
            line.extend(coords if not line else coords[1:])
            if step.get("name") and (not names or names[-1] != step["name"]):
                names.append(step["name"])
        if len(line) < 2 or distance(line[0], snaps[i]["location"]) > 2 or distance(line[-1], snaps[i+1]["location"]) > 2:
            raise ValueError("unordered_leg_endpoints")
        if combined and combined[-1] != line[0]:
            overview = route.get("geometry", {}).get("coordinates", [])
            # OSRM can clip the two sides of a via point differently. The tiny
            # interval must already be covered by an actual overview segment.
            if distance(combined[-1], line[0]) > 2 or not any(
                all(abs(distance(a, p) + distance(p, b) - distance(a, b)) <= .1 for p in (combined[-1], line[0]))
                for a, b in zip(overview, overview[1:])
            ):
                raise ValueError("discontinuous_legs")
        if not math.isfinite(leg.get("distance", -1)) or leg["distance"] <= 0:
            raise ValueError("degenerate_leg")
        if any(distance(a, b) > 500 and not sourced_sparse_segment(a, b, sparse_segments) for a, b in zip(line, line[1:])):
            raise ValueError("geometry_gap")
        reports.append({"sequence": i, "distance_m": leg["distance"], "road_names": names, "geometry": {"type": "LineString", "coordinates": line}})
        combined.extend(line)
    geometry = route.get("geometry", {})
    if geometry.get("type") != "LineString" or not equivalent_sampling(geometry.get("coordinates", []), combined):
        raise ValueError("full_geometry_differs_from_ordered_legs")
    sampling_warning = deduplicate(geometry["coordinates"]) != deduplicate(combined)
    geometry = {"type": "LineString", "coordinates": deduplicate(combined)}
    total = route.get("distance")
    if type(total) not in (int, float) or not math.isfinite(total) or abs(total-sum(leg["distance_m"] for leg in reports)) > 2:
        raise ValueError("invalid_network_distance")
    return {"geometry": geometry, "overview_sampling_reconstructed": sampling_warning, "distance_m": total, "engine_duration_s": route.get("duration"), "snap_offsets_m": offsets, "snapped_waypoints": [s["location"] for s in snaps], "legs": reports}


def matching_issues(pattern, points, result, *, name_warnings=False):
    issues = []
    ambiguous = [i for i, leg in enumerate(result["legs"]) if leg["distance_m"] < distance(points[i], points[i+1]) * .25 and not reviewed_short_leg(pattern, points, result, i)]
    if ambiguous:
        issues.append("ambiguous_snap_collapsed_legs: " + str(ambiguous))
    names = [name for leg in result["legs"] for name in leg["road_names"]]
    if pattern["classification"] != "operational_vehicle_movement":
        groups = pattern.get("expected_road_groups", [["Pandan"], ["Santa Barbara"]])
        if "expected_road_groups" in pattern:
            cursor = 0
            for group in groups:
                match = next((i for i in range(cursor, len(names)) if any("".join(alias.casefold().split()) in "".join(names[i].casefold().split()) for alias in group)), None)
                if match is None:
                    present = any(any("".join(alias.casefold().split()) in "".join(name.casefold().split()) for alias in group) for name in names)
                    if present or name_warnings:
                        issues.append(("unexpected_road_corridor: out_of_order_" if present else "road_name_unresolved_review: ") + "/".join(group))
                else:
                    cursor = match + 1
            if cursor == 0:
                issues.append("unexpected_road_corridor: no_expected_roads")
        elif not all(any(expected[0] in name for name in names) for expected in groups):
            issues.append("unexpected_road_corridor")
    return issues


def reviewed_short_leg(pattern, points, result, i):
    """Narrow display-only exception for captured nearby National Highway observations.

    Both captures have a 3.9 m National Highway leg and a 25.593 m terminal
    offset: nearby observations snap in order to a continuous nonzero road leg.
    This is not field verification or terminal access evidence; the road line ends
    at its snap, with no connector to the unchanged terminal marker.
    """
    expected = {"jeep-mangaldan-mapandan": 0, "jeep-mapandan-mangaldan": 4}
    if expected.get(pattern["id"]) != i:
        return False
    reviewed_points = [[120.404355, 16.065126], [120.4044767783, 16.0649723099]]
    if pattern["id"] == "jeep-mapandan-mangaldan":
        reviewed_points.reverse()
    if points[i:i+2] != reviewed_points:
        return False
    leg = result["legs"][i]
    coords = deduplicate(leg["geometry"]["coordinates"])
    return (0 < distance(points[i], points[i+1]) <= 30
            and leg["road_names"] == ["National Highway"]
            and 0 < leg["distance_m"] <= 5
            and len(coords) >= 2
            and 0 < sum(distance(a, b) for a, b in zip(coords, coords[1:])) <= 5
            and all(distance(points[j], result["snapped_waypoints"][j]) <= 30 for j in (i, i+1))
            and distance(coords[0], result["snapped_waypoints"][i]) <= 2
            and distance(coords[-1], result["snapped_waypoints"][i+1]) <= 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--policy-url", required=True)
    parser.add_argument("--profile", default="driving")
    parser.add_argument("--radius", type=float, default=30)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--replay", action="store_true", help="Parse previous captures without network")
    parser.add_argument("--only", nargs="+", help="Explicit maintenance subset; retain unrelated candidates and reports")
    parser.add_argument("--policy-checked", action="store_true", help="Maintainer has read and checked the endpoint usage policy")
    args = parser.parse_args()
    if urllib.parse.urlparse(args.endpoint).scheme != "https" or not 0 < args.radius <= 30:
        parser.error("HTTPS and radius in (0, 30] required")
    if not args.replay and not args.policy_checked:
        parser.error("Read the endpoint policy and explicitly pass --policy-checked before network capture")
    args.capture_dir.mkdir(parents=True, exist_ok=True)
    inputs = json.loads((DATA / "route_waypoints.json").read_text())
    patterns = inputs["patterns"]
    previous_report = DATA / "generation_report.json"
    previous = json.loads(previous_report.read_text()) if previous_report.exists() else {}
    retrieved = previous["retrieved_at"] if args.replay and previous else datetime.now(timezone.utc).isoformat()
    report = {"schema_version": 1, "endpoint": args.endpoint, "profile": args.profile, "policy_url": args.policy_url, "retrieved_at": retrieved, "patterns": []}
    services = json.loads((DATA / "service_patterns.json").read_text())["patterns"]
    report["unavailable_patterns"] = [{"pattern_id": p["id"], "status": "withheld", "warnings": [p["geometry_source"]]} for p in services if p.get("geometry_source", "").startswith("missing_")]
    shapes = []
    for pattern in patterns:
        if args.only and pattern["id"] not in args.only:
            report["patterns"].extend(p for p in previous.get("patterns", []) if p["pattern_id"] == pattern["id"])
            continue
        points = ordered(pattern, patterns)
        params = {"overview": "full", "geometries": "geojson", "steps": "true", "alternatives": "false", "radiuses": ";".join([str(args.radius)]*len(points))}
        if pattern.get("bearings"):
            params["bearings"] = ";".join(pattern["bearings"])
        url = args.endpoint.rstrip("/") + "/route/v1/" + args.profile + "/" + ";".join(",".join(map(str, p)) for p in points) + "?" + urllib.parse.urlencode(params)
        item = {"pattern_id": pattern["id"], "input_hash": digest(points), "supplied_waypoints": points, "request_parameters": params, "status": "withheld", "warnings": []}
        for field in ("derived_waypoints", "endpoint_caveat", "sparse_segments", "unrouted_endpoint"):
            if field in pattern:
                item[field] = pattern[field]
        names = inputs["waypoint_names"][pattern.get("reverse_of", pattern["id"])]
        item["waypoint_names"] = list(reversed(names)) if "reverse_of" in pattern else names
        try:
            if args.replay:
                raw = (args.capture_dir / (pattern["id"] + ".json")).read_bytes()
            else:
                raw = fetch_response(url)
            if len(raw) > 4_000_000:
                raise ValueError("response_size_limit")
            item["response_checksum"] = hashlib.sha256(raw).hexdigest()
            (args.capture_dir / (pattern["id"] + ".json")).write_bytes(raw)
            response = json.loads(raw)
            item["reported_snap_offsets_m"] = [w.get("distance") for w in response.get("waypoints", [])]
            item["response_summary"] = [{"distance_m": r.get("distance"), "legs": [{"distance_m": leg.get("distance"), "road_names": [step.get("name", "") for step in leg.get("steps", []) if step.get("name")]} for leg in r.get("legs", [])]} for r in response.get("routes", [])]
            result = parse_response(response, points, args.radius, pattern.get("sparse_segments", ()))
            item.update(result)
            reference = pattern.get("reference_m", 15400 if pattern["id"].startswith("mini-") else 8700)
            if pattern["classification"] != "operational_vehicle_movement":
                item["distance_comparison"] = {"reference_m": reference, "difference_m": round(result["distance_m"]-reference, 3), "difference_percent": round((result["distance_m"]-reference)/reference*100, 3)}
            item["warnings"] = ["road_name_aliases_and_unnamed_approaches_require_human_review", "generic_car_profile_not_passenger_service_or_vehicle_legality", "complete_turn_restriction_coverage_not_established", "OSM_vintage_not_exposed"]
            item["warnings"].extend(w for w in matching_issues(pattern, points, result, name_warnings=True) if w.startswith("road_name_unresolved_review:"))
            if result["overview_sampling_reconstructed"]:
                item["warnings"].append("overview_omitted_submetre_clipping_vertex_using_contiguous_ordered_steps")
            if "distance_comparison" in item:
                item["distance_comparison"]["absolute_difference_m"] = abs(item["distance_comparison"]["difference_m"])
                if pattern["id"] in ("mini-mapandan-dagupan-outbound", "mini-dagupan-mapandan-return"):
                    item["distance_comparison"]["upper_reference_m"] = 15800
                    item["distance_comparison"]["difference_from_upper_m"] = round(result["distance_m"] - 15800, 3)
                item["warnings"].append("distance_differs_from_approximate_driving_observation")
            issues = matching_issues(pattern, points, result)
            if any(reviewed_short_leg(pattern, points, result, i) for i in range(len(result["legs"]))):
                item["warnings"].append("conservative_display_review_nearby_same_road_observations_short_nonzero_leg_terminal_access_unverified_no_connector")
            if issues:
                item["warnings"].extend(issues)
            else:
                item["status"] = "candidate"
                props = {**item, "id": pattern["id"], "name": pattern["name"], "classification": pattern["classification"], "geometry_status": "candidate", "verification_status": "unverified", "publication_status": "reference_only", "routing_eligible": False, "endpoint": args.endpoint, "profile": args.profile, "retrieved_at": report["retrieved_at"], "attribution": "OpenStreetMap contributors (ODbL)", "geometry_review": "unreviewed", "max_snap_m": args.radius}
                props.pop("geometry")
                shapes.append({"type": "Feature", "id": pattern["id"], "geometry": result["geometry"], "properties": props})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            item["warnings"] = [type(exc).__name__ + ": " + str(exc)]
        report["patterns"].append(item)
        if not args.replay:
            time.sleep(1.1)
    old = json.loads((DATA / "route_shapes.geojson").read_text())
    history = old.get("historical_features", [])
    generated_ids = {s["id"] for s in shapes}
    for feature in old["features"]:
        replacement = next((s for s in shapes if s["id"] == feature["id"]), None)
        if replacement and replacement["properties"]["input_hash"] != feature["properties"].get("input_hash"):
            history.append(feature)
        if feature["id"] not in generated_ids:
            props = feature["properties"]
            if args.only and feature["id"] not in args.only:
                shapes.append(feature)
                continue
            current = next((p for p in patterns if p["id"] == feature["id"]), None)
            if current and matching_issues(current, props["supplied_waypoints"], props):
                continue
            props["stale"] = not current or props.get("input_hash") != digest(ordered(current, patterns))
            props["withheld"] = True
            shapes.append(feature)
    shape_order = {p["id"]: i for i, p in enumerate(patterns)}
    shapes.sort(key=lambda shape: shape_order.get(shape["id"], len(patterns)))
    (DATA / "route_shapes.geojson").write_text(json.dumps({"type": "FeatureCollection", "schema_version": 2, "notes": "Road geometry must not be manufactured. Candidates are unverified references, never passenger routing evidence.", "features": shapes, "historical_features": history}, indent=2, allow_nan=False) + "\n")
    (DATA / "generation_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps([{k: p.get(k) for k in ("pattern_id", "status", "distance_m", "snap_offsets_m", "warnings")} for p in report["patterns"]], indent=2))


if __name__ == "__main__":
    main()
