"""Transport data schemas for Better Mapandan Commuter."""
SCHEMAS = {
    "transport/route_waypoints.json": {
        "type": "object", "required": ["schema_version", "source_type", "transcription_date", "verification_status", "patterns"],
        "properties": {"source_type": {"const": "maintainer_provided"}, "verification_status": {"const": "unverified"}, "patterns": {"type": "array", "minItems": 1, "maxItems": 100, "items": {"type": "object", "required": ["id", "name", "classification"], "oneOf": [{"required": ["coordinates"]}, {"required": ["reverse_of"]}], "properties": {
            "endpoint_caveat": {"type": "string", "minLength": 1},
            "unrouted_endpoint": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "number"}},
            "bearings": {"type": "array", "items": {"type": "string", "pattern": "^(|[0-9]+,[0-9]+)$"}},
            "derived_waypoints": {"type": "array", "items": {"type": "object", "required": ["index", "osm_node", "source", "kind"], "properties": {"index": {"type": "integer", "minimum": 0}, "osm_node": {"type": "integer"}, "source": {"type": "string"}, "kind": {"const": "osm_derived_not_user_input"}}}},
            "sparse_segments": {"type": "array", "items": {"type": "object", "required": ["osm_way", "osm_nodes", "source", "coordinates"]}}
        }}}}
    },
    "transport/generation_report.json": {"type": "object", "required": ["schema_version", "endpoint", "profile", "retrieved_at", "patterns"], "properties": {"patterns": {"type": "array", "items": {"type": "object", "required": ["pattern_id", "input_hash", "status", "warnings"], "properties": {"status": {"enum": ["candidate", "withheld"]}}}}}},
    "transport/manifest.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "data_version"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "data_version": {"type": "string"},
            "coverage": {"type": "string"},
            "terminals": {"type": "string"},
            "stops": {"type": "string"},
            "tricycle_stands": {"type": "string"},
            "routes_file": {"type": "string"},
            "service_patterns_file": {"type": "string"},
            "route_shapes": {"type": "string"},
            "stop_occurrences": {"type": "string"},
            "tricycle_zones": {"type": "string"},
            "tricycle_rules": {"type": "string"},
            "fares": {"type": "string"},
            "schedules": {"type": "string"},
            "travel_time_profiles": {"type": "string"},
            "transfer_rules": {"type": "string"},
            "named_places": {"type": "string"},
            "operators": {"type": "string"},
            "road_graph_source": {"type": "string"},
            "manifest_version": {"type": "integer"}
        }
    },

    "transport/coverage.json": {
        "type": "object",
        "required": ["schema_version", "as_of", "supported_corridors"],
        "properties": {
            "schema_version": {"type": "integer"},
            "as_of": {"type": "string"},
            "description": {"type": "string"},
            "supported_corridors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "mode", "origin_id", "destination_id", "routing_eligible"],
                    "properties": {
                        "id": {"type": "string"},
                        "mode": {"type": "string"},
                        "origin_id": {"type": "string"},
                        "destination_id": {"type": "string"},
                        "status": {"type": "string"},
                        "routing_eligible": {"type": "boolean"},
                        "notes": {"type": "string"}
                    }
                }
            },
            "verified_pedestrian_access": {"type": "object"},
            "supported_tricycle_areas": {"type": "object"},
            "unsupported_areas": {"type": "array"},
            "supported_optimization_methods": {"type": "object"},
            "known_source_limitations": {"type": "array"},
            "last_validated": {"type": "string"},
            "validation_notes": {"type": "string"}
        }
    },

    "transport/sources.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "sources"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "type", "title", "retrieved", "republication_permitted"],
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "retrieved": {"type": "string"},
                        "license": {"type": ["string", "null"]},
                        "license_notes": {"type": "string"},
                        "notes": {"type": "string"},
                        "url": {"type": ["string", "null"]},
                        "republication_permitted": {"type": "boolean"}
                    }
                }
            }
        }
    },

    "transport/terminals.geojson": {
        "type": "object",
        "required": ["schema_version", "type", "features"],
        "properties": {
            "schema_version": {"type": "integer"},
            "type": {"const": "FeatureCollection"},
            "generated_at": {"type": "string"},
            "features": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "id", "geometry", "properties"],
                    "properties": {
                        "type": {"const": "Feature"},
                        "id": {"type": "string"},
                        "geometry": {
                            "type": "object",
                            "required": ["type", "coordinates"],
                            "properties": {
                                "type": {"const": "Point"},
                                "coordinates": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "minItems": 2,
                                    "maxItems": 2
                                }
                            }
                        },
                        "properties": {
                            "type": "object",
                            "required": ["id", "name", "transport_type", "source_type", "verification_status", "publication_status", "routing_eligible", "review_date"],
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "transport_type": {"type": "string"},
                                "classification": {"type": "string"},
                                "location_description": {"type": "string"},
                                "original_coordinate_representation": {"type": "string"},
                                "latitude": {"type": "number"},
                                "longitude": {"type": "number"},
                                "source_type": {"type": "string"},
                                "verification_status": {"type": "string"},
                                "publication_status": {"type": "string"},
                                "routing_eligible": {"type": "boolean"},
                                "review_date": {"type": "string"},
                                "reviewer": {"type": "string"},
                                "source_note": {"type": "string"},
                                "linked_routes": {"type": "array", "items": {"type": "string"}},
                                "linked_operators": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    }
                }
            }
        }
    },

    "transport/tricycle_stands.geojson": {
        "type": "object",
        "required": ["schema_version", "type", "features"],
        "properties": {
            "schema_version": {"type": "integer"},
            "type": {"const": "FeatureCollection"},
            "generated_at": {"type": "string"},
            "features": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "id", "geometry", "properties"],
                    "properties": {
                        "type": {"const": "Feature"},
                        "id": {"type": "string"},
                        "geometry": {"type": ["object", "null"]},
                        "properties": {
                            "type": "object",
                            "required": ["id", "name", "transport_type", "source_type", "verification_status", "publication_status", "routing_eligible", "review_date"],
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "transport_type": {"const": "tricycle"},
                                "classification": {"type": "string"},
                                "location_description": {"type": "string"},
                                "source_type": {"type": "string"},
                                "verification_status": {"type": "string"},
                                "publication_status": {"type": "string"},
                                "routing_eligible": {"type": "boolean"},
                                "review_date": {"type": "string"},
                                "reviewer": {"type": "string"},
                                "linked_routes": {"type": "array", "items": {"type": "string"}},
                                "linked_operators": {"type": "array", "items": {"type": "string"}},
                                "todas": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    }
                }
            }
        }
    },

    "transport/stops.geojson": {
        "type": "object",
        "required": ["schema_version", "type", "features"],
        "properties": {
            "schema_version": {"type": "integer"},
            "type": {"const": "FeatureCollection"},
            "generated_at": {"type": "string"},
            "features": {"type": "array"}
        }
    },

    "transport/routes.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "routes", "legs"],
        "properties": {
            "legs": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["id", "label_key", "vehicle_types", "fare_id", "driving_km", "driving_minutes"], "properties": {"id": {"type": "string"}, "vehicle_types": {"type": "array", "minItems": 1, "items": {"enum": ["minibus", "jeepney", "tricycle"]}}, "driving_km": {"type": ["number", "null"], "exclusiveMinimum": 0}, "driving_minutes": {"type": ["number", "null"], "exclusiveMinimum": 0}}}},
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "routes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name", "vehicle_type", "origin_id", "destination_id", "routing_eligible", "directions", "leg_ids"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "public_signboard_text": {"type": ["string", "null"]},
                        "public_catalog": {"type": "boolean", "description": "Whether this reference is offered as a public selectable journey; omitted means visible."},
                        "subtitle_key": {"type": "string"},
                        "vehicle_type": {"type": "string"},
                        "origin_id": {"type": "string"},
                        "destination_id": {"type": "string"},
                        "patterns": {"type": "array", "items": {"type": "string"}},
                        "directions": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "array", "minItems": 1, "items": {"type": "string"}}},
                        "leg_ids": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"type": "string"}},
                        "operating_status": {"type": "string"},
                        "service_verification_status": {"type": "string"},
                        "evidence_source": {"type": "string"},
                        "evidence_note": {"type": "string"},
                        "direction_handling": {"type": "string"},
                        "boarding_alighting_rules": {"type": "string"},
                        "routing_eligible": {"type": "boolean"},
                        "publication_status": {"type": "string"},
                        "created_date": {"type": "string"},
                        "last_updated": {"type": "string"},
                        "source_url": {"type": ["string", "null"]}
                    }
                }
            }
        }
    },

    "transport/service_patterns.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "patterns"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "patterns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "route_id", "direction", "vehicle_type", "routing_eligible"],
                    "properties": {
                        "id": {"type": "string"},
                        "route_id": {"type": ["string", "null"]},
                        "direction": {"type": "string"},
                        "vehicle_type": {"type": "string"},
                        "origin_id": {"type": "string"},
                        "destination_id": {"type": ["string", "null"]},
                        "classification": {"type": "string"},
                        "reported_streets": {"type": "array", "items": {"type": "string"}},
                        "driving_reference_distance_km": {"type": ["number", "null"]},
                        "driving_reference_duration_minutes": {"type": ["number", "null"]},
                        "driving_reference_basis": {"type": "string"},
                        "geometry_source": {"type": "string"},
                        "geometry_verified": {"type": "boolean"},
                        "routing_eligible": {"type": "boolean"},
                        "default_passenger_routing_eligible": {"type": ["boolean", "null"]},
                        "operating_status": {"type": "string"},
                        "boarding_alighting_rules": {"type": "string"},
                        "notes": {"type": ["string", "null"]},
                        "created_date": {"type": "string"},
                        "last_updated": {"type": "string"}
                    }
                }
            }
        }
    },

    "transport/route_shapes.geojson": {
        "type": "object",
        "required": ["type", "features"],
        "properties": {
            "type": {"const": "FeatureCollection"},
            "features": {"type": "array", "maxItems": 100, "items": {
                "type": "object", "required": ["type", "id", "geometry", "properties"],
                "properties": {
                    "type": {"const": "Feature"}, "id": {"type": "string"},
                    "geometry": {"type": "object", "required": ["type", "coordinates"], "properties": {"type": {"const": "LineString"}, "coordinates": {"type": "array", "minItems": 2, "maxItems": 50000, "items": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "number"}}}}},
                    "properties": {"type": "object", "required": ["id", "pattern_id", "geometry_status", "verification_status", "publication_status", "routing_eligible", "input_hash", "supplied_waypoints", "snapped_waypoints", "snap_offsets_m", "legs", "distance_m", "warnings", "endpoint", "profile", "retrieved_at", "response_checksum", "classification", "attribution", "max_snap_m"], "properties": {
                        "geometry_status": {"enum": ["candidate", "verified"]},
                        "publication_status": {"const": "reference_only"}, "routing_eligible": {"const": False},
                        "classification": {"enum": ["passenger_candidate", "operational_vehicle_movement"]},
                        "distance_m": {"type": "number", "exclusiveMinimum": 0},
                        "max_snap_m": {"type": "number", "exclusiveMinimum": 0, "maximum": 30},
                        "response_checksum": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                        "warnings": {"type": "array", "items": {"type": "string"}},
                        "legs": {"type": "array", "minItems": 1}, "snap_offsets_m": {"type": "array", "items": {"type": "number", "minimum": 0, "maximum": 30}}
                    }}
                }
            }}
        }
    },

    "transport/stop_occurrences.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "occurrences"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "occurrences": {"type": "array"}
        }
    },

    "transport/tricycle_zones.geojson": {
        "type": "object",
        "required": ["type", "features"],
        "properties": {
            "type": {"const": "FeatureCollection"},
            "features": {"type": "array"}
        }
    },

    "transport/tricycle_rules.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "rules"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "rules": {"type": "array"}
        }
    },

    "transport/fares.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "fares"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "fares": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "fare_type", "rate_kind", "amount", "verification_status"],
                    "properties": {
                        "id": {"type": "string"},
                        "route_id": {"type": ["string", "null"]},
                        "vehicle_type": {"type": ["string", "null"]},
                        "service_type": {"type": ["string", "null"]},
                        "fare_type": {"type": "string"},
                        "rate_kind": {"type": "string"},
                        "amount": {
                            "type": ["object", "null"],
                            "required": ["min", "max", "currency"],
                            "properties": {
                                "min": {"type": "number"},
                                "max": {"type": "number"},
                                "currency": {"type": "string"}
                            }
                        },
                        "basis": {"type": ["string", "null"]},
                        "notes": {"type": "string"},
                        "effective_date": {"type": ["string", "null"]},
                        "issuing_authority": {"type": ["string", "null"]},
                        "source_reference": {"type": "string"},
                        "verification_status": {"type": "string"},
                        "applicable_concessions": {"type": "array"},
                        "created_date": {"type": "string"},
                        "last_updated": {"type": "string"}
                    }
                }
            },
            "known_uncertainties": {"type": "array"}
        }
    },

    "transport/schedules.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "schedules"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "schedules": {"type": "array"},
            "notes": {"type": "string"}
        }
    },

    "transport/travel_time_profiles.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "profiles"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "profiles": {"type": "array"},
            "notes": {"type": "string"}
        }
    },

    "transport/transfer_rules.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "rules"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "rules": {"type": "array"},
            "notes": {"type": "string"}
        }
    },

    "transport/named_places.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "places"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "places": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name", "source_type", "verification_status"],
                    "properties": {
                        "id": {"type": "string"},
                        "route_id": {"type": ["string", "null"]},
                        "route_pattern_id": {"type": ["string", "null"]},
                        "name": {"type": "string"},
                        "address": {"type": "string"},
                        "geometry": {"type": ["object", "null"]},
                        "classification": {"type": "string"},
                        "source_type": {"type": "string"},
                        "verification_status": {"type": "string"},
                        "notes": {"type": "string"},
                        "review_date": {"type": "string"},
                        "reviewer": {"type": "string"}
                    }
                }
            },
            "relationships_to_resolve": {"type": "array", "items": {"type": "string"}},
            "conceptual_connections": {"type": "array", "items": {"type": "object", "required": ["id", "from_id", "to_id", "observation_separation_m", "access", "geometry", "routing_eligible"], "properties": {"access": {"const": "unverified"}, "geometry": {"type": "null"}, "routing_eligible": {"const": False}, "observation_separation_m": {"type": "number", "minimum": 0}}}}
        }
    },

    "transport/operators.json": {
        "type": "object",
        "required": ["schema_version", "generated_at", "operators"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "operators": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name", "transport_type", "verification_status"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "transport_type": {"type": "string"},
                        "todas": {"type": "array", "items": {"type": "string"}},
                        "verification_status": {"type": "string"},
                        "source_note": {"type": "string"},
                        "linked_terminal_ids": {"type": "array", "items": {"type": "string"}},
                        "linked_route_ids": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "notes": {"type": "string"}
        }
    },

    "transport/road_graph_source.geojson": {
        "type": "object",
        "required": ["schema_version", "features"],
        "properties": {
            "schema_version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "type": {"const": "FeatureCollection"},
            "features": {"type": "array"},
            "notes": {"type": "string"},
            "input_policy": {"type": "array", "items": {"type": "string"}},
            "access_policy": {"type": "string"}
        }
    }
}
