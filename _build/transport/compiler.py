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
                                        **{k: props[k] for k in ("classification", "location_description", "source_type", "source_note", "verification_status", "routing_eligible", "linked_routes") if k in props},
                                        "fares": [{"id": f["id"], "amount": f["amount"]} for f in applicable]}})
    public_fields = ("id", "pattern_id", "name", "classification", "geometry_status", "geometry_review", "verification_status", "publication_status", "routing_eligible", "endpoint", "profile", "retrieved_at", "attribution", "distance_m", "distance_comparison", "snap_offsets_m", "warnings", "response_checksum", "supplied_waypoints", "snapped_waypoints", "derived_waypoints", "endpoint_caveat", "unrouted_endpoint")
    shapes = [{"type": "Feature", "geometry": f["geometry"], "properties": {**{k: f["properties"][k] for k in public_fields if k in f["properties"]}, "legs": [{k: leg[k] for k in ("sequence", "distance_m", "road_names")} for leg in f["properties"]["legs"]]}} for f in data["transport/route_shapes.geojson"]["features"] if f["properties"]["classification"] == "passenger_candidate" and not f["properties"].get("stale") and not f["properties"].get("withheld")]
    available = {f["properties"]["pattern_id"] for f in shapes}
    legs = {leg["id"]: leg for leg in data["transport/routes.json"]["legs"]}
    fare_index = {f["id"]: f for f in fares}
    catalog = [{**{k: r[k] for k in ("id", "vehicle_type", "origin_id", "destination_id", "directions", "explanation_key", "subtitle_key", "transfer_count", "service_verification_status", "evidence_source", "evidence_note", "source_type", "pedestrian_access", "authorization", "public_signboard_text", "last_updated", "created_date", "source_url") if k in r}, "routing_eligible": False,
                "legs": [{**legs[i], "fare": {k: fare_index[legs[i]["fare_id"]].get(k) for k in ("amount", "rate_kind", "source_type")}} for i in r["leg_ids"]]}
               for r in data["transport/routes.json"]["routes"] if r.get("public_catalog", True)]
    for route in catalog:
        route["fare_summary"] = reported_fare_summary(route["legs"])
    modes = {"place-guam-pickup": "tricycle", "place-manaoag-waiting": "minibus",
             "place-town-plaza": "tricycle", "place-firetree-roundabout-manaoag": "minibus",
             "place-tuliao-jeep": "jeepney", "place-tuliao-tricycle": "tricycle",
             "place-meditek-manaoag": "minibus", "place-sm-entry": "minibus",
             "place-calasiao": "jeepney", "place-sta-barbara": "tricycle",
             "place-border-arch": "transfer", "place-gmt-tuliao": "transfer"}
    observations = [{"type": "Feature", "id": p["id"], "geometry": p["geometry"],
                     "properties": {"id": p["id"], "name": p["name"], "transport_type": modes[p["id"]], "fares": [], "observed_only": True,
                                    **{k: p[k] for k in ("classification", "source_type", "verification_status", "routing_eligible", "notes") if k in p}}}
                    for p in data["transport/named_places.json"]["places"] if p["id"] in modes and p.get("geometry")]
    # Explicit source observations for each reported leg, never nearest-place inference.
    leg_places = {
        "leg-manaoag": ["place-firetree-roundabout-manaoag", "place-manaoag-waiting"],
        "leg-manaoag-sm": ["place-meditek-manaoag", "place-sm-entry"],
        "leg-guam": ["place-guam-pickup", "place-town-plaza"],
        "leg-border-arch": ["place-border-arch"],
        "leg-tuliao": ["place-border-arch", "place-gmt-tuliao"],
        "leg-calasiao": ["place-tuliao-jeep", "place-calasiao"],
        "leg-sta-barbara": ["place-tuliao-tricycle", "place-sta-barbara"],
    }
    spatial_ids = {f["id"] for f in features + observations}
    for route in catalog:
        ids = [route["origin_id"], route["destination_id"]]
        ids += [place for leg in route["legs"] for place in leg_places.get(leg["id"], [])]
        route["marker_ids"] = list(dict.fromkeys(i for i in ids if i in spatial_ids))
    for feature in features + observations:
        props = feature["properties"]
        props["catalog_route_ids"] = [r["id"] for r in catalog if props["id"] in r["marker_ids"] or r["id"] in props.get("linked_routes", [])]
    endpoint_ids = {r[k] for r in catalog for k in ("origin_id", "destination_id")}
    place_names = {p["id"]: p["name"] for p in data["transport/named_places.json"]["places"] if p["id"] in endpoint_ids}
    direction_source = data["transport/directions.json"]
    directions = {c["pattern_id"]: {**c, "steps": [{**direction_source["step_defaults"], **step} for step in c["steps"]]}
                  for c in direction_source["collections"]}
    # Older street-only reports are independent direction records, not turn instructions.
    for pattern in data["transport/service_patterns.json"]["patterns"]:
        if pattern["id"] in {"mini-mapandan-dagupan-outbound", "mini-dagupan-mapandan-return", "jeep-mapandan-mangaldan", "jeep-mangaldan-mapandan"}:
            directions[pattern["id"]] = {"pattern_id": pattern["id"], "notes": ["street_sequence_only"], "steps": [
                {**direction_source["step_defaults"], "sequence": i, "instruction_type": "reported_street",
                 "instruction_text": street, "original_source": street, "street_name": street,
                 "distance_m": None, "waypoint": None}
                for i, street in enumerate(pattern["reported_streets"], 1)]}
    return {"schema_version": 5, "direction_steps": directions, "direction_limitations": direction_source["limitations"], "features": features, "observations": observations, "place_names": place_names, "shapes": shapes, "catalog": catalog, "patterns": [{"id": p["id"], "name": p["name"], "classification": p["classification"], "available": p["id"] in available} for p in data["transport/route_waypoints.json"]["patterns"] if p["classification"] == "passenger_candidate"]}


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
        "reset_lines", "uncertainty", "coverage")}
    routes = []
    for route in bundle["catalog"]:
        summary = route["fare_summary"]
        amount = summary["amount"] or summary["known_subtotal"]
        fares = labels["reported_range"] if summary["complete"] else labels["incomplete_fare"]
        if amount:
            fares += f": PHP {amount['min']}-{amount['max']}"
        if not summary["complete"]:
            fares += " + " + labels["unknown_fare"]
        modes = " / ".join(dict.fromkeys(labels[mode] for leg in route["legs"] for mode in leg["vehicle_types"]))
        rides = f'{len(route["legs"])} {labels["rides"]} / {route.get("transfer_count", 0)} {labels["transfers"]}'
        routes.append('<button type="button" class="passenger-geometry route-select" aria-pressed="false" aria-controls="commuter-info" data-route="' + escape(route["id"]) + '" data-type="' + escape(route["vehicle_type"]) + '"><strong>' + escape(labels[route["id"]]) + '</strong><span class="route-chips">' + escape(modes + " / " + rides) + '</span><span class="fare-summary">' + escape(fares) + '</span></button>')
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
