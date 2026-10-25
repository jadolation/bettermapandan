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
    errors.extend(_validate_catalog(data))
    errors.extend(validate_directions(data))
    errors.extend(validate_shapes(data))
    return errors


def validate_directions(data):
    """Directions are independent observations, never geometry or reverse inference."""
    import jsonschema

    source = data.get("transport/directions.json", {})
    errors = []
    try:
        jsonschema.validate(source, SCHEMAS["transport/directions.json"])
    except jsonschema.ValidationError as exc:
        return [f"directions: {exc.message}"]
    patterns = {p["id"] for p in data["transport/service_patterns.json"]["patterns"]
                if p.get("classification") != "operational_vehicle_movement"}
    seen = set()
    for collection in source["collections"]:
        pid = collection["pattern_id"]
        if pid not in patterns or pid in seen:
            errors.append(f"directions: unresolved or duplicate pattern {pid}")
        seen.add(pid)
        if [s["sequence"] for s in collection["steps"]] != list(range(1, len(collection["steps"]) + 1)):
            errors.append(f"directions {pid}: sequence must be unique and ordered")
        for step in collection["steps"]:
            point = step["waypoint"]
            if step["distance_m"] is not None and not math.isfinite(step["distance_m"]):
                errors.append(f"directions {pid}: nonfinite reported distance")
            if point is not None and not (all(math.isfinite(c) for c in point) and -180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                errors.append(f"directions {pid}: invalid waypoint")
            if "reverse_of" in step or "reverse_of" in collection:
                errors.append(f"directions {pid}: automatic reversal is not supported")
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
        sourced_sparse_segment,
    )
    errors = []
    patterns = data.get("transport/route_waypoints.json", {}).get("patterns", [])
    known = {p["id"] for p in data.get("transport/service_patterns.json", {}).get("patterns", [])}
    for pattern in patterns:
        try:
            points = ordered(pattern, patterns)
            if pattern["id"] not in known or len(points) < 2 or not all(coordinate(c) for c in points):
                raise ValueError("invalid waypoint input or pattern reference")
            if "bearings" in pattern and len(pattern["bearings"]) != len(points):
                raise ValueError("bearing count differs from waypoint count")
            sources = {s["id"] for s in data.get("transport/sources.json", {}).get("sources", [])}
            for derived in pattern.get("derived_waypoints", []):
                if not 0 <= derived["index"] < len(points) or derived["source"] not in sources or derived["kind"] != "osm_derived_not_user_input":
                    raise ValueError("invalid derived shaping provenance")
            for segment in pattern.get("sparse_segments", []):
                if segment["source"] not in sources or len(segment["osm_nodes"]) != 2 or len(segment["coordinates"]) != 2 or not all(coordinate(c) for c in segment["coordinates"]) or distance(*segment["coordinates"]) > 1000:
                    raise ValueError("invalid sparse road edge evidence")
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
                if combined and distance(combined[-1], coords[0]) > 2:
                    raise ValueError("discontinuous leg endpoints")
                if leg["distance_m"] < distance(points[i], points[i+1]) * .25:
                    if not reviewed_short_leg(pattern, points, props, i) or "conservative_display_review_nearby_same_road_observations_short_nonzero_leg_terminal_access_unverified_no_connector" not in props["warnings"]:
                        raise ValueError("ambiguous collapsed leg")
                if any(distance(a, b) > 500 and not sourced_sparse_segment(a, b, pattern.get("sparse_segments", ())) for a, b in zip(coords, coords[1:])):
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
            for warning in matching_issues(pattern, points, props, name_warnings=True):
                if warning.startswith("road_name_unresolved_review:") and warning not in props["warnings"]:
                    raise ValueError("missing road-name review warning")
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
            errors.append(f"pattern {pid}: reference-only routing gate")
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
        amount = fare.get("amount")
        if fare.get("rate_kind") == "unknown":
            if amount is not None:
                errors.append(f"fare {fid}: unknown amount must be null")
        elif not isinstance(amount, dict) or not all(type(amount.get(k)) in (int, float) and math.isfinite(amount[k]) for k in ("min", "max")) or not 0 < amount["min"] <= amount["max"]:
            errors.append(f"fare {fid}: invalid reported range")
        if fare.get("verification_status") == "official_verified" and fare.get("rate_kind") != "official_verified":
            errors.append(f"fare {fid}: official_verified requires rate_kind official_verified")
    return errors


def _validate_catalog(data):
    from _build.transport.generate import coordinate

    errors = []
    catalog = data.get("transport/routes.json", {})
    legs = {leg["id"]: leg for leg in catalog.get("legs", [])}
    fares = {f["id"]: f for f in data.get("transport/fares.json", {}).get("fares", [])}
    patterns = {p["id"]: p for p in data.get("transport/service_patterns.json", {}).get("patterns", [])}
    for leg in legs.values():
        if leg.get("fare_id") not in fares:
            errors.append(f"leg {leg['id']}: missing fare")
        if len(leg.get("vehicle_types", [])) > 1 and (leg.get("route_affiliation") is not None or leg.get("vehicle_identity") != "unknown_alternative_not_two_services"):
            errors.append(f"leg {leg['id']}: unsupported vehicle identity or affiliation")
    for place in data.get("transport/named_places.json", {}).get("places", []):
        geometry = place.get("geometry")
        if place.get("routing_eligible") or (geometry is not None and (geometry.get("type") != "Point" or not coordinate(geometry.get("coordinates")))):
            errors.append(f"place {place['id']}: invalid reference point")
    place_ids = {p["id"] for p in data.get("transport/named_places.json", {}).get("places", [])}
    for connection in data.get("transport/named_places.json", {}).get("conceptual_connections", []):
        if connection.get("from_id") not in place_ids or connection.get("to_id") not in place_ids or connection.get("access") != "unverified" or connection.get("geometry") is not None or connection.get("routing_eligible") is not False:
            errors.append("conceptual connection must remain unverified and nonspatial")
    for route in catalog.get("routes", []):
        ids = route.get("leg_ids", [])
        directions = route.get("directions", [])
        if not ids or any(i not in legs for i in ids) or not directions:
            errors.append(f"route {route['id']}: invalid catalog legs/directions")
        for direction in directions:
            if any(p not in route.get("patterns", []) or p not in patterns or patterns[p].get("classification") == "operational_vehicle_movement" for p in direction):
                errors.append(f"route {route['id']}: invalid passenger direction")
        if route.get("vehicle_type") == "multileg":
            if len(ids) < 2 or len(directions) != 1 or any(len(d) != len(ids) for d in directions) or route.get("transfer_count") != len(ids)-1 or route.get("total_fare") is not None or route.get("total_duration_minutes") is not None or route.get("pedestrian_access") != "unresolved" or route.get("authorization") != "unconfirmed":
                errors.append(f"route {route['id']}: incomplete journey gates")
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
    places = _index_by_id(data, "transport/named_places.json", "places")
    endpoints = {**terminals, **places}

    for pattern in data.get("transport/service_patterns.json", {}).get("patterns", []):
        pid = pattern.get("id", "?")
        if pattern.get("route_id") and pattern["route_id"] not in routes:
            errors.append(f"pattern {pid}: route_id {pattern['route_id']} not found")
        origin = pattern.get("origin_id")
        if origin and origin not in endpoints:
            errors.append(f"pattern {pid}: origin_id {origin} not found in terminals")
        destination = pattern.get("destination_id")
        if destination and destination not in endpoints:
            errors.append(f"pattern {pid}: destination_id {destination} not found")

    for route in routes.values():
        rid = route.get("id", "?")
        _check_terminal_ref(route, rid, "origin_id", endpoints, errors)
        _check_terminal_ref(route, rid, "destination_id", endpoints, errors)
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
