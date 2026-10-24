"""Explicit maintainer-only OSRM capture. Never imported by the build for networking."""
import argparse
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


def parse_response(response, points, radius=30):
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
            if line and distance(line[-1], coords[0]) > 2:
                raise ValueError("discontinuous_steps")
            line.extend(coords if not line else coords[1:])
            if step.get("name") and (not names or names[-1] != step["name"]):
                names.append(step["name"])
        if len(line) < 2 or distance(line[0], snaps[i]["location"]) > 2 or distance(line[-1], snaps[i+1]["location"]) > 2:
            raise ValueError("unordered_leg_endpoints")
        if not math.isfinite(leg.get("distance", -1)) or leg["distance"] <= 0:
            raise ValueError("degenerate_leg")
        if any(distance(a, b) > 500 for a, b in zip(line, line[1:])):
            raise ValueError("geometry_gap")
        reports.append({"sequence": i, "distance_m": leg["distance"], "road_names": names, "geometry": {"type": "LineString", "coordinates": line}})
        combined.extend(line if not combined else line[1:])
    geometry = route.get("geometry", {})
    if geometry.get("type") != "LineString" or deduplicate(geometry.get("coordinates", [])) != deduplicate(combined):
        raise ValueError("full_geometry_differs_from_ordered_legs")
    total = route.get("distance")
    if type(total) not in (int, float) or not math.isfinite(total) or abs(total-sum(leg["distance_m"] for leg in reports)) > 2:
        raise ValueError("invalid_network_distance")
    return {"geometry": geometry, "distance_m": total, "engine_duration_s": route.get("duration"), "snap_offsets_m": offsets, "snapped_waypoints": [s["location"] for s in snaps], "legs": reports}


def matching_issues(pattern, points, result):
    issues = []
    ambiguous = [i for i, leg in enumerate(result["legs"]) if leg["distance_m"] < distance(points[i], points[i+1]) * .25 and not reviewed_short_leg(pattern, points, result, i)]
    if ambiguous:
        issues.append("ambiguous_snap_collapsed_legs: " + str(ambiguous))
    names = [name for leg in result["legs"] for name in leg["road_names"]]
    if pattern["classification"] != "operational_vehicle_movement" and not all(any(expected in name for name in names) for expected in ("Pandan", "Santa Barbara")):
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
    args = parser.parse_args()
    if urllib.parse.urlparse(args.endpoint).scheme != "https" or not 0 < args.radius <= 30:
        parser.error("HTTPS and radius in (0, 30] required")
    args.capture_dir.mkdir(parents=True, exist_ok=True)
    inputs = json.loads((DATA / "route_waypoints.json").read_text())
    patterns = inputs["patterns"]
    previous_report = DATA / "generation_report.json"
    retrieved = json.loads(previous_report.read_text())["retrieved_at"] if args.replay and previous_report.exists() else datetime.now(timezone.utc).isoformat()
    report = {"schema_version": 1, "endpoint": args.endpoint, "profile": args.profile, "policy_url": args.policy_url, "retrieved_at": retrieved, "patterns": []}
    shapes = []
    for pattern in patterns:
        points = ordered(pattern, patterns)
        params = {"overview": "full", "geometries": "geojson", "steps": "true", "alternatives": "false", "radiuses": ";".join([str(args.radius)]*len(points))}
        url = args.endpoint.rstrip("/") + "/route/v1/" + args.profile + "/" + ";".join(",".join(map(str, p)) for p in points) + "?" + urllib.parse.urlencode(params)
        item = {"pattern_id": pattern["id"], "input_hash": digest(points), "supplied_waypoints": points, "request_parameters": params, "status": "withheld", "warnings": []}
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
            result = parse_response(json.loads(raw), points, args.radius)
            item.update(result)
            reference = 15400 if pattern["id"].startswith("mini-") else 8700
            if pattern["classification"] != "operational_vehicle_movement":
                item["distance_comparison"] = {"reference_m": reference, "difference_m": round(result["distance_m"]-reference, 3), "difference_percent": round((result["distance_m"]-reference)/reference*100, 3)}
            item["warnings"] = ["road_name_aliases_and_unnamed_approaches_require_human_review", "generic_car_profile_not_passenger_service_or_vehicle_legality", "complete_turn_restriction_coverage_not_established", "OSM_vintage_not_exposed"]
            if "distance_comparison" in item:
                item["distance_comparison"]["absolute_difference_m"] = abs(item["distance_comparison"]["difference_m"])
                if pattern["id"].startswith("mini-"):
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
    generated_ids = {s["id"] for s in shapes}
    for feature in old["features"]:
        if feature["id"] not in generated_ids:
            props = feature["properties"]
            current = next((p for p in patterns if p["id"] == feature["id"]), None)
            if current and matching_issues(current, props["supplied_waypoints"], props):
                continue
            props["stale"] = not current or props.get("input_hash") != digest(ordered(current, patterns))
            props["withheld"] = True
            shapes.append(feature)
    (DATA / "route_shapes.geojson").write_text(json.dumps({"type": "FeatureCollection", "schema_version": 2, "notes": "Road geometry must not be manufactured. Candidates are unverified references, never passenger routing evidence.", "features": shapes}, indent=2, allow_nan=False) + "\n")
    (DATA / "generation_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps([{k: p.get(k) for k in ("pattern_id", "status", "distance_m", "snap_offsets_m", "warnings")} for p in report["patterns"]], indent=2))


if __name__ == "__main__":
    main()
