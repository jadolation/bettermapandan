"""Compile transport reference data into a browser-loadable bundle.

Produces a single minified JSON artifact containing terminals and tricycle
stands for the V1.0 commuter directory. Routing graph outputs are added in
later phases. The bundle is generated once per build, before locale rendering.
"""
import json
from html import escape
from pathlib import Path

from _build.transport.validation import load_transport_data, validate_shapes


def reference_bundle():
    """Public reference projection; no operator, licensing or routing claims."""
    data = load_transport_data()
    errors = validate_shapes(data)
    if errors:
        raise ValueError("; ".join(errors))
    features = []
    fares = data["transport/fares.json"]["fares"]
    for feature in (data["transport/terminals.geojson"]["features"] +
                    data["transport/tricycle_stands.geojson"]["features"]):
        props = feature["properties"]
        applicable = [fare for fare in fares if (
            fare.get("route_id") in props.get("linked_routes", []) or
            fare.get("vehicle_type") == props["transport_type"])]
        features.append({"type": "Feature", "id": props["id"],
                         "geometry": feature["geometry"],
                         "properties": {"id": props["id"], "name": props["name"],
                                        "transport_type": props["transport_type"],
                                        "fares": [{"id": f["id"], "amount": f["amount"]} for f in applicable]}})
    public_fields = ("id", "pattern_id", "name", "classification", "geometry_status", "geometry_review", "verification_status", "publication_status", "routing_eligible", "endpoint", "profile", "retrieved_at", "attribution", "distance_m", "distance_comparison", "snap_offsets_m", "warnings", "response_checksum", "supplied_waypoints", "snapped_waypoints")
    shapes = [{"type": "Feature", "geometry": f["geometry"], "properties": {**{k: f["properties"][k] for k in public_fields if k in f["properties"]}, "legs": [{k: leg[k] for k in ("sequence", "distance_m", "road_names")} for leg in f["properties"]["legs"]]}} for f in data["transport/route_shapes.geojson"]["features"] if f["properties"]["classification"] == "passenger_candidate" and not f["properties"].get("stale") and not f["properties"].get("withheld")]
    available = {f["properties"]["pattern_id"] for f in shapes}
    return {"schema_version": 2, "features": features, "shapes": shapes, "patterns": [{"id": p["id"], "name": p["name"], "classification": p["classification"], "available": p["id"] in available} for p in data["transport/route_waypoints.json"]["patterns"] if p["classification"] == "passenger_candidate"]}


def commuter_placeholders(locale):
    """Build accessible HTML and script-safe data from the same seven records."""
    from _build.gis import script_json
    labels = locale["commuter"]
    bundle = reference_bundle()
    cards = []
    for feature in bundle["features"]:
        props = feature["properties"]
        name = labels[props["id"]]
        fare_html = "".join(
            '<li>' + escape(labels[fare["id"]]) + ': PHP ' +
            str(fare["amount"]["min"]) + '-' + str(fare["amount"]["max"]) + '</li>'
            for fare in props["fares"])
        cards.append(
            '<article class="transport-card" data-id="' + escape(props["id"]) +
            '" data-type="' + escape(props["transport_type"]) + '"><h3>' + escape(name) +
            '</h3><p>' + escape(labels[props["transport_type"]]) + '</p><ul>' + fare_html +
            '</ul><button hidden type="button" ' +
            'class="transport-select" aria-controls="commuter-info">' + escape(labels["select"]) +
            ': ' + escape(name) + '</button></article>')
    labels = {k: v for k, v in labels.items() if k not in (
        "mini-dagupan-turnaround", "operational", "snap_offsets", "distance_difference",
        "geometry_details", "reset_lines", "uncertainty", "coverage")}
    return {"COMMUTER_DIRECTORY": "".join(cards),
            "COMMUTER_DATA": script_json({**bundle, "labels": labels}),
            **{"C_" + key.upper(): escape(value, quote=True) for key, value in labels.items()}}


def compile_transport_reference(root):
    """Compile transport reference data into a single browser-ready JSON bundle.

    Writes to <root>/assets/data/transport-reference.min.json.
    Returns the relative output path within assets/data/.
    """
    bundle = reference_bundle()
    output = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    out_file = Path(root) / "assets" / "data" / "transport-reference.min.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(output, encoding="utf-8")
    return "assets/data/transport-reference.min.json"
