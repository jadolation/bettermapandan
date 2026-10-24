"""Transport data package for BetterMapandan Commuter.

V0 phase: evidence inventory, schema validation, and routing-eligibility gates.
All records begin as unverified and reference-only; routing eligibility is an
explicit validated field, never inferred from a marker or source URL.
"""

VERIFICATION_STATUSES = {
    "unverified",
    "maintainer_confirmed",
    "operator_confirmed",
    "authority_confirmed",
    "withdrawn",
}

PUBLICATION_STATUSES = {
    "draft",
    "reference_only",
    "published",
    "withdrawn",
}

SOURCE_TYPES = {
    "maintainer_provided",
    "maintainer_local_observation",
    "government_municipal_ordinance",
    "government_service_record",
    "government_official",
    "open_street_map",
    "operator_schedule",
    "authority_direct",
    "field_survey",
}

FARE_RATE_KINDS = {
    "official_verified",
    "locally_reported_range",
    "calculated_estimate",
    "unknown",
}

DEPARTURE_MODELS = {
    "scheduled",
    "frequency_based",
    "fill_and_go",
    "unknown",
}

TRICYCLE_SERVICE_TYPES = {
    "shared_passing",
    "arkila",
}

GEOJSON_COORD_ORDER = "longitude, latitude"

DEFAULT_SNAP_THRESHOLD_M = 30
MANUAL_SNAP_MAX_M = 150
