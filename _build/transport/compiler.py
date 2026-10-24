"""Compile transport reference data into a browser-loadable bundle.

Produces a single minified JSON artifact containing terminals and tricycle
stands for the V1.0 commuter directory. Routing graph outputs are added in
later phases. The bundle is generated once per build, before locale rendering.
"""
import json
from html import escape
from pathlib import Path

from _build.transport.validation import load_transport_data, validate_records


def reported_fare_summary(legs):
    """Sum applicable, bounded reported leg fares, never promote a subtotal."""
    known = [leg for leg in legs if leg["fare"].get("amount") is not None
             and leg["fare"].get("rate_kind") == "locally_reported_range"]
    subtotal = {"min": sum(leg["fare"]["amount"]["min"] for leg in known),
                "max": sum(leg["fare"]["amount"]["max"] for leg in known), "currency": "PHP"} if known else None
    complete = bool(legs) and len(known) == len(legs)
    return {"complete": complete, "amount": subtotal if complete else None,
            "known_subtotal": subtotal, "unknown_leg_ids": [leg["id"] for leg in legs if leg not in known],
            "basis": "reported_ranges_not_official_or_service_guarantee"}


def reference_bundle():
    """Public reference projection; no operator, licensing or routing claims."""
    data = load_transport_data()
    errors = validate_records(data)
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
    public_fields = ("id", "pattern_id", "name", "classification", "geometry_status", "geometry_review", "verification_status", "publication_status", "routing_eligible", "endpoint", "profile", "retrieved_at", "attribution", "distance_m", "distance_comparison", "snap_offsets_m", "warnings", "response_checksum", "supplied_waypoints", "snapped_waypoints", "derived_waypoints", "endpoint_caveat", "unrouted_endpoint")
    shapes = [{"type": "Feature", "geometry": f["geometry"], "properties": {**{k: f["properties"][k] for k in public_fields if k in f["properties"]}, "legs": [{k: leg[k] for k in ("sequence", "distance_m", "road_names")} for leg in f["properties"]["legs"]]}} for f in data["transport/route_shapes.geojson"]["features"] if f["properties"]["classification"] == "passenger_candidate" and not f["properties"].get("stale") and not f["properties"].get("withheld")]
    available = {f["properties"]["pattern_id"] for f in shapes}
    legs = {leg["id"]: leg for leg in data["transport/routes.json"]["legs"]}
    fare_index = {f["id"]: f for f in fares}
    catalog = [{**{k: r[k] for k in ("id", "vehicle_type", "origin_id", "destination_id", "directions", "explanation_key", "transfer_count") if k in r}, "routing_eligible": False,
                "legs": [{**legs[i], "fare": {k: fare_index[legs[i]["fare_id"]].get(k) for k in ("amount", "rate_kind", "source_type")}} for i in r["leg_ids"]]}
               for r in data["transport/routes.json"]["routes"]]
    for route in catalog:
        route["fare_summary"] = reported_fare_summary(route["legs"])
    modes = {"place-guam-pickup": "tricycle", "place-manaoag-waiting": "minibus",
             "place-meditek-manaoag": "minibus", "place-sm-entry": "minibus",
             "place-calasiao": "jeepney", "place-sta-barbara": "tricycle",
             "place-border-arch": "transfer", "place-gmt-tuliao": "transfer"}
    observations = [{"type": "Feature", "id": p["id"], "geometry": p["geometry"],
                     "properties": {"id": p["id"], "name": p["name"], "transport_type": modes[p["id"]], "fares": [], "observed_only": True}}
                    for p in data["transport/named_places.json"]["places"] if p["id"] in modes and p.get("geometry")]
    return {"schema_version": 4, "features": features, "observations": observations, "shapes": shapes, "catalog": catalog, "patterns": [{"id": p["id"], "name": p["name"], "classification": p["classification"], "available": p["id"] in available} for p in data["transport/route_waypoints.json"]["patterns"] if p["classification"] == "passenger_candidate"]}


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
    routes = []
    for route in bundle["catalog"]:
        rows = []
        for leg in route["legs"]:
            amount = leg["fare"]["amount"]
            fare = f"PHP {amount['min']}-{amount['max']}" if amount else labels["unknown_fare"]
            driving = f"{leg['driving_km']} km / {leg['driving_minutes']} min" if leg["driving_km"] is not None else labels["unknown_driving"]
            modes = labels["vehicle_unknown"] if len(leg["vehicle_types"]) > 1 else labels[leg["vehicle_types"][0]]
            rows.append('<li>' + escape(labels[leg["label_key"]]) + ': ' + escape(modes + '; ' + fare) + '<br>' + escape(labels["driving"] + ': ' + driving) + '</li>')
        explanation = '<p>' + escape(labels[route["explanation_key"]]) + '</p>' if route.get("explanation_key") else ''
        summary = route["fare_summary"]
        amount = summary["amount"] or summary["known_subtotal"]
        fares = labels["reported_range"] if summary["complete"] else labels["incomplete_fare"]
        if amount:
            fares += f": PHP {amount['min']}-{amount['max']}"
        if not summary["complete"]:
            fares += " + " + labels["unknown_fare"]
        alternate = '<p>' + escape(labels["alternate_driving"]) + '</p>' if any(leg.get("alternate_driving_note_minutes") for leg in route["legs"]) else ''
        routes.append('<fieldset class="passenger-geometry" data-route="' + escape(route["id"]) + '" data-type="' + escape(route["vehicle_type"]) + '"><legend>' + escape(labels[route["id"]]) + '</legend><p class="fare-summary">' + escape(fares) + '</p><details><summary>' + escape(labels["trip_details"]) + '</summary>' + explanation + '<ul>' + ''.join(rows) + '</ul>' + alternate + '<p>' + escape(labels["waiting_unknown"]) + '</p><p>' + escape(labels["fare_caveat"]) + '</p>' + ('<p>' + escape(labels["return_unconfirmed"]) + '</p>' if len(route["directions"]) > 1 else '') + '</details></fieldset>')
    return {"COMMUTER_DIRECTORY": "".join(cards),
            "COMMUTER_ROUTES": "".join(routes),
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
