#!/usr/bin/env python3
"""JSON Schema validation for BetterMapandan data files."""
import json
from pathlib import Path

try:
    import jsonschema
except ImportError:
    jsonschema = None

SCHEMAS = {
    "barangays.json": {
        "type": "object",
        "required": ["barangays"],
        "properties": {
            "barangays": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["slug", "name", "punong_barangay"],
                    "properties": {
                        "slug": {"type": "string"},
                        "name": {"type": "string"},
                        "pop2024": {"type": "string"},
                        "pop2020": {"type": "string"},
                        "landUse": {"type": "string"},
                        "history": {"type": "string"},
                        "punong_barangay": {"type": "string"},
                        "kagawads": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "position": {"type": "string"},
                                    "email": {"type": ["string", "null"]},
                                    "contact": {"type": ["string", "null"]}
                                }
                            }
                        },
                        "officials": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["name", "position"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "position": {"type": "string"},
                                    "email": {"type": ["string", "null"]},
                                    "contact": {"type": ["string", "null"]}
                                }
                            }
                        },
                        "facebook": {"type": ["string", "null"]},
                        "phone": {"type": ["string", "null"]},
                        "photo": {"type": ["string", "null"]}
                    }
                }
            }
        }
    },
    "services.json": {
        "type": "object",
        "required": ["services"],
        "properties": {
            "services": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["slug", "name", "category"],
                    "properties": {
                        "slug": {"type": "string"},
                        "name": {"type": "string"},
                        "category": {"type": "string"},
                        "description": {"type": "string"},
                        "requirements": {"type": "array", "items": {"type": "string"}},
                        "procedure": {"type": "array", "items": {"type": "string"}},
                        "fees": {"type": ["string", "number", "null"]},
                        "office": {"type": "string"},
                        "contact": {"type": "string"},
                        "source": {"type": "string"}
                    }
                }
            }
        }
    },
    "legislative.json": {
        "type": "object",
        "properties": {
            "ordinances": {"type": "array"},
            "resolutions": {"type": "array"},
            "executive_issuances": {"type": "array"}
        }
    },
    "procurement.json": {
        "type": "object",
        "required": ["contracts"],
        "properties": {
            "contracts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["title", "awardee", "amount", "award_date"],
                    "properties": {
                        "title": {"type": "string"},
                        "awardee": {"type": "string"},
                        "amount": {"type": "number"},
                        "award_date": {"type": "string"},
                        "status": {"type": "string"},
                        "business_category": {"type": "string"},
                        "reference_id": {"type": "string"},
                        "contract_no": {"type": "string"},
                        "organization_name": {"type": "string"}
                    }
                }
            }
        }
    },
    "dpwh.json": {
        "type": "object",
        "required": ["projects"],
        "properties": {
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["project_name", "contractor", "contract_amount", "status"],
                    "properties": {
                        "transaction_id": {"type": "string"},
                        "contract_id": {"type": "string"},
                        "project_name": {"type": "string"},
                        "category": {"type": "string"},
                        "executing_agency": {"type": "string"},
                        "contractor": {"type": "string"},
                        "contractor_id": {"type": "string"},
                        "approved_budget": {"type": "number"},
                        "contract_amount": {"type": "number"},
                        "accomplishment_percent": {"type": "number"},
                        "status": {"type": "string"},
                        "fiscal_year": {"type": ["integer", "null"]},
                        "source_of_funds": {"type": "string"},
                        "contract_effectivity_date": {"type": ["string", "null"]},
                        "contract_expiry_date": {"type": ["string", "null"]},
                        "actual_start_date": {"type": ["string", "null"]},
                        "actual_completion_date": {"type": ["string", "null"]},
                        "barangay_location": {"type": "string"},
                        "latitude": {"type": ["number", "null"]},
                        "longitude": {"type": ["number", "null"]},
                        "project_components": {"type": "array"},
                        "bidders": {"type": "array"},
                        "procurement_activities": {"type": "array"},
                        "source_document_url": {"type": "string"},
                        "crossref": {"type": "object"}
                    }
                }
            }
        }
    }
}


def validate_all(data_dir: Path) -> list:
    """Validate all JSON data files in *data_dir* against their schemas."""
    errors = []
    if jsonschema is None:
        print("WARNING: jsonschema not installed; skipping validation")
        return errors

    for filename, schema in SCHEMAS.items():
        path = data_dir / filename
        if not path.exists():
            errors.append(f"Missing data file: {path}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"Malformed JSON in {filename}: {e}")
            continue
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation failed for {filename}: {e.message}")

    return errors
