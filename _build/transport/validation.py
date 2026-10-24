"""Transport data validation and routing-eligibility gates."""
import json
import math
from pathlib import Path

from _build.transport import (
    FARE_RATE_KINDS,
    SOURCE_TYPES,
    VERIFICATION_STATUSES,
)
from _build.transport.schemas import SCHEMAS

TRANSPORT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "data" / "transport"


def load_transport_data(data_dir=None):
    """Load all transport source JSON/GeoJSON files."""
    data = {}
    for name in SCHEMAS:
        filename = Path(name).name
        path = Path(data_dir or TRANSPORT_DATA_DIR) / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing transport data file: {path}")
        raw = path.read_text(encoding="utf-8")
        try:
            data[name] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in {path}: {exc}") from exc
    return data


def validate_routable_record(record, record_type):
    """Eligibility is necessary but insufficient; routing also requires accepted
    evidence, applicable service permissions, geometry/connectivity, and
    non-withdrawn status.
    """
    if not isinstance(record, dict):
        raise ValueError(f"{record_type} must be an object")
    if record.get("routing_eligible") is True:
        source = record.get("source_type")
        if source in SOURCE_TYPES and source in ("maintainer_provided", "maintainer_local_observation"):
            raise ValueError(
                f"{record.get('id', '?')}: source_type '{source}' cannot authorize routing eligibility"
            )
    return True


def validate_records(data):
    """Enforce reference-only defaults and routing-eligibility rules."""
    errors = []
    errors.extend(_validate_terminals(data))
    errors.extend(_validate_tricycle_stands(data))
    errors.extend(_validate_routes(data))
    errors.extend(_validate_patterns(data))
    errors.extend(_validate_fares(data))
    errors.extend(validate_shapes(data))
    return errors


def validate_shapes(data):
    from _build.transport.generate import (
        coordinate,
        deduplicate,
        digest,
        distance,
        matching_issues,
        ordered,
        reviewed_short_leg,
    )
    errors = []
    patterns = data.get("transport/route_waypoints.json", {}).get("patterns", [])
    known = {p["id"] for p in data.get("transport/service_patterns.json", {}).get("patterns", [])}
    for pattern in patterns:
        try:
            points = ordered(pattern, patterns)
            if pattern["id"] not in known or len(points) < 2 or not all(coordinate(c) for c in points):
                raise ValueError("invalid waypoint input or pattern reference")
        except (KeyError, StopIteration, ValueError) as exc:
            errors.append(f"waypoints: {exc}")
    for feature in data.get("transport/route_shapes.geojson", {}).get("features", []):
        try:
            props = feature["properties"]
            if props.get("stale") or props.get("withheld"):
                if props.get("routing_eligible") is not False:
                    raise ValueError("withheld routing gate")
                continue
            pattern = next(p for p in patterns if p["id"] == props["pattern_id"])
            points = ordered(pattern, patterns)
            if props["input_hash"] != digest(points) or props["supplied_waypoints"] != points:
                raise ValueError("stale candidate inputs")
            if props["routing_eligible"] is not False or props["publication_status"] != "reference_only":
                raise ValueError("candidate routing/publication gate")
            if props["geometry_status"] == "candidate":
                if props["verification_status"] != "unverified" or props.get("geometry_review") != "unreviewed":
                    raise ValueError("candidate must remain unverified")
            elif props["geometry_status"] == "verified":
                review = props.get("human_geometry_review", {})
                if props.get("geometry_review") != "reviewed" or not all(review.get(k) for k in ("date", "reviewer", "evidence_source")) or props["verification_status"] not in ("maintainer_confirmed", "operator_confirmed", "authority_confirmed"):
                    raise ValueError("verified geometry requires separate human review")
                sources = data.get("transport/sources.json", {}).get("sources", [])
                if not any(s["id"] == review["evidence_source"] and s.get("republication_permitted") is True for s in sources):
                    raise ValueError("unresolved human geometry review source")
            else:
                raise ValueError("unsupported geometry status")
            if props["classification"] != pattern["classification"]:
                raise ValueError("operational/passenger classification mismatch")
            for field in ("endpoint", "profile", "retrieved_at", "response_checksum", "attribution", "warnings"):
                if not props.get(field):
                    raise ValueError("missing provenance: " + field)
            snaps, offsets, legs = props["snapped_waypoints"], props["snap_offsets_m"], props["legs"]
            if len(snaps) != len(points) or len(offsets) != len(points) or len(legs) != len(points)-1:
                raise ValueError("invalid candidate leg/waypoint counts")
            combined = []
            for i, leg in enumerate(legs):
                coords = leg["geometry"]["coordinates"]
                if leg["sequence"] != i or not math.isfinite(leg["distance_m"]) or leg["distance_m"] <= 0 or not all(coordinate(c) for c in coords) or len(coords) < 2:
                    raise ValueError("invalid leg geometry")
                if distance(coords[0], snaps[i]) > 2 or distance(coords[-1], snaps[i+1]) > 2:
                    raise ValueError("unordered leg endpoints")
                if leg["distance_m"] < distance(points[i], points[i+1]) * .25:
                    if not reviewed_short_leg(pattern, points, props, i) or "conservative_display_review_nearby_same_road_observations_short_nonzero_leg_terminal_access_unverified_no_connector" not in props["warnings"]:
                        raise ValueError("ambiguous collapsed leg")
                if any(distance(a, b) > 500 for a, b in zip(coords, coords[1:])):
                    raise ValueError("geometry discontinuity")
                combined.extend(coords)
            if feature["geometry"]["type"] != "LineString" or deduplicate(combined) != deduplicate(feature["geometry"]["coordinates"]):
                raise ValueError("full geometry mismatch")
            for point, snap, offset in zip(points, snaps, offsets):
                if not coordinate(snap) or not 0 <= offset <= props["max_snap_m"] <= 30 or abs(distance(point, snap)-offset) > .01:
                    raise ValueError("invalid snap offset")
            if not math.isfinite(props["distance_m"]) or abs(sum(leg["distance_m"] for leg in legs)-props["distance_m"]) > 2:
                raise ValueError("invalid total distance")
            if matching_issues(pattern, points, props):
                raise ValueError("unresolved matching/corridor error")
        except (KeyError, TypeError, ValueError, StopIteration, IndexError) as exc:
            errors.append(f"shape {feature.get('id')}: {exc}")
    return errors


def _validate_terminals(data):
    errors = []
    for feature in data.get("transport/terminals.geojson", {}).get("features", []):
        props = feature.get("properties", {})
        tid = props.get("id", "?")
        _check_enum(props, tid, "verification_status", VERIFICATION_STATUSES, errors)
        _check_not_routable(props, tid, errors)
        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) != 2 or not all(isinstance(c, (int, float)) for c in coords):
            errors.append(f"terminal {tid}: invalid coordinates")
    return errors


def _validate_tricycle_stands(data):
    errors = []
    for feature in data.get("transport/tricycle_stands.geojson", {}).get("features", []):
        props = feature.get("properties", {})
        sid = props.get("id", "?")
        if props.get("transport_type") != "tricycle":
            errors.append(f"tricycle stand {sid}: transport_type must be 'tricycle'")
        _check_enum(props, sid, "verification_status", VERIFICATION_STATUSES, errors)
        if props.get("routing_eligible") is True:
            errors.append(
                f"tricycle stand {sid}: routing_eligible must be false before verified TODA rules"
            )
    return errors


def _validate_routes(data):
    errors = []
    for route in data.get("transport/routes.json", {}).get("routes", []):
        rid = route.get("id", "?")
        if route.get("routing_eligible") is True:
            errors.append(f"route {rid}: routing_eligible must be false until verified")
        _check_enum(route, rid, "service_verification_status", VERIFICATION_STATUSES, errors)
        if _check_enum(route, rid, "operating_status", None, errors) and route.get("operating_status") == "operating":
            if route.get("service_verification_status") != "authority_confirmed":
                errors.append(f"route {rid}: 'operating' requires authority_confirmed service verification")
    return errors


def _validate_patterns(data):
    errors = []
    for pattern in data.get("transport/service_patterns.json", {}).get("patterns", []):
        pid = pattern.get("id", "?")
        if pattern.get("routing_eligible") is True:
            if pattern.get("geometry_verified") is not True:
                errors.append(f"pattern {pid}: routing_eligible requires geometry_verified")
            if pattern.get("default_passenger_routing_eligible") is False:
                errors.append(f"pattern {pid}: operational movement cannot be passenger-routable")
    return errors


def _validate_fares(data):
    errors = []
    fares = data.get("transport/fares.json", {}).get("fares", [])
    if not fares:
        return errors
    if "known_uncertainties" not in data.get("transport/fares.json", {}):
        errors.append("fares.json: missing known_uncertainties when fares exist")
    for fare in fares:
        fid = fare.get("id", "?")
        _check_enum(fare, fid, "rate_kind", FARE_RATE_KINDS, errors)
        if fare.get("verification_status") == "official_verified" and fare.get("rate_kind") != "official_verified":
            errors.append(f"fare {fid}: official_verified requires rate_kind official_verified")
    return errors


def _check_enum(record, rid, field, allowed, errors):
    """Record validation error for enum fields. Returns True if the field value
    is one of the allowed values (or allowed is None)."""
    if allowed is None:
        return True
    value = record.get(field)
    if value is not None and value not in allowed:
        errors.append(f"record {rid}: invalid {field} '{value}'")
        return False
    return value is not None and value in allowed


def _check_not_routable(props, rid, errors):
    """Unverified records must not be routing-eligible."""
    if props.get("routing_eligible") is True:
        errors.append(
            f"terminal {rid}: routing_eligible must be false for unverified records"
        )


def validate_transport_data(data_dir=None):
    """Validate all transport source data files. Returns list of error strings."""
    if data_dir is None:
        data_dir = TRANSPORT_DATA_DIR
    else:
        data_dir = Path(data_dir)

    errors = []

    try:
        import jsonschema
    except ImportError:
        print("WARNING: jsonschema not installed; schema validation skipped for transport data")
        jsonschema = None

    for rel_path, schema in SCHEMAS.items():
        filename = Path(rel_path).name
        path = data_dir / filename
        if not path.exists():
            errors.append(f"Missing transport data file: {path}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Malformed JSON in {filename}: {exc}")
            continue
        if jsonschema is not None:
            try:
                jsonschema.validate(instance=data, schema=schema)
            except jsonschema.ValidationError as exc:
                errors.append(f"Schema validation failed for {filename}: {exc.message} (at: {list(exc.path)})")

    try:
        data = load_transport_data(data_dir)
    except (FileNotFoundError, ValueError) as exc:
        errors.append(str(exc))
        return errors

    errors.extend(validate_records(data))

    _validate_unique_ids(data, errors)
    _validate_references(data, errors)
    _validate_dms_conversion(data, errors)

    return errors


def _validate_unique_ids(data, errors):
    """All IDs must be unique within their collection."""
    id_checks = [
        ("transport/terminals.geojson", "features", "id"),
        ("transport/tricycle_stands.geojson", "features", "id"),
        ("transport/routes.json", "routes", "id"),
        ("transport/service_patterns.json", "patterns", "id"),
        ("transport/fares.json", "fares", "id"),
    ]
    for path, collection, id_key in id_checks:
        items = data.get(path, {}).get(collection, [])
        ids = []
        for item in items:
            if isinstance(item, dict) and "properties" in item:
                item_id = item["properties"].get(id_key)
            else:
                item_id = item.get(id_key)
            if item_id:
                ids.append(item_id)
        seen = set()
        for item_id in ids:
            if item_id in seen:
                errors.append(f"{path}: duplicate ID {item_id}")
            seen.add(item_id)


def _validate_references(data, errors):
    """Route and pattern references must resolve to existing records."""
    routes = _index_by_id(data, "transport/routes.json", "routes")
    pattern_ids = _id_set(data, "transport/service_patterns.json", "patterns")
    terminals = _feature_index(data, "transport/terminals.geojson")
    stands = _feature_index(data, "transport/tricycle_stands.geojson")

    for pattern in data.get("transport/service_patterns.json", {}).get("patterns", []):
        pid = pattern.get("id", "?")
        if pattern.get("route_id") and pattern["route_id"] not in routes:
            errors.append(f"pattern {pid}: route_id {pattern['route_id']} not found")
        origin = pattern.get("origin_id")
        if origin and origin not in terminals:
            errors.append(f"pattern {pid}: origin_id {origin} not found in terminals")

    for route in routes.values():
        rid = route.get("id", "?")
        _check_terminal_ref(route, rid, "origin_id", terminals, errors)
        _check_terminal_ref(route, rid, "destination_id", terminals, errors)
        for pattern_id in route.get("patterns", []):
            if pattern_id not in pattern_ids:
                errors.append(f"route {rid}: pattern {pattern_id} not found")

    _check_linked_routes(terminals, "terminal", routes, errors)
    _check_linked_routes(stands, "stand", routes, errors)


def _index_by_id(data, path, collection):
    return {r["id"]: r for r in data.get(path, {}).get(collection, [])}


def _id_set(data, path, collection):
    return {p["id"] for p in data.get(path, {}).get(collection, [])}


def _feature_index(data, path):
    return {f["properties"]["id"]: f for f in data.get(path, {}).get("features", [])}


def _check_terminal_ref(record, rid, field, terminals, errors):
    ref = record.get(field)
    if ref and ref not in terminals:
        errors.append(f"route {rid}: {field} {ref} not found in terminals")


def _check_linked_routes(features, label, routes, errors):
    for feature in features.values():
        props = feature["properties"]
        fid = props["id"]
        for route_id in props.get("linked_routes", []):
            if route_id not in routes:
                errors.append(f"{label} {fid}: linked_route {route_id} not found")


def _validate_dms_conversion(data, errors):
    """Verify the supplied minibus terminal DMS conversion."""
    terminals = data.get("transport/terminals.geojson", {}).get("features", [])
    for feature in terminals:
        props = feature.get("properties", {})
        if props.get("id") == "term-mini-mapandan":
            expected_lat = 16.0265833333
            expected_lon = 120.4524166667
            actual_lat = props.get("latitude")
            actual_lon = props.get("longitude")
            if actual_lat is not None and abs(actual_lat - expected_lat) > 1e-9:
                errors.append(
                    f"term-mini-mapandan: latitude {actual_lat} != DMS-converted {expected_lat}"
                )
            if actual_lon is not None and abs(actual_lon - expected_lon) > 1e-9:
                errors.append(
                    f"term-mini-mapandan: longitude {actual_lon} != DMS-converted {expected_lon}"
                )
            coords = props.get("geometry", feature.get("geometry", {})).get("coordinates", [])
            if len(coords) >= 2:
                if abs(coords[1] - expected_lat) > 1e-9:
                    errors.append("term-mini-mapandan: coordinate latitude mismatch")
                if abs(coords[0] - expected_lon) > 1e-9:
                    errors.append("term-mini-mapandan: coordinate longitude mismatch")
