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
                        "organization_name": {"type": "string"},
                        "crossref": {"type": "object"}
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
    },
    "fdp_disclosures.json": {
        "type": "object",
        "required": ["meta", "sre", "sef", "ldrrmf", "bids", "dev_fund"],
        "properties": {
            "meta": {"type": "object"},
            "sre": {"type": "array"},
            "sef": {"type": "array"},
            "ldrrmf": {"type": "array"},
            "cash_flows": {"type": "array"},
            "cash_advances": {"type": "array"},
            "trust_fund": {"type": "array"},
            "lgsf": {"type": "array"},
            "dev_fund": {"type": "array"},
            "bids": {"type": "array"},
            "manpower": {"type": "array"},
            "indebtedness": {"type": "array"},
            "budget": {"type": "array"},
            "budget_book": {"type": "array"},
            "spp": {"type": "array"},
            "app": {"type": "array"},
            "gad": {"type": "array"},
            "fund_matrix": {"type": "array"},
            "spa": {"type": "array"}
        }
    },
    "coa-project-findings.json": {
        "type": "object",
        "required": ["project_names"],
        "properties": {
            "contract_number_formats": {"type": "array"},
            "contractor_names": {"type": "array"},
            "project_names": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["project_title", "cost", "fund_source", "status"],
                    "properties": {
                        "project_title": {"type": "string"},
                        "cost": {"type": "number"},
                        "fund_source": {"type": "string"},
                        "status": {"type": "string"}
                    }
                }
            },
            "procurement_section_observations": {"type": "array"},
            "infrastructure_section_observations": {"type": "array"},
            "disallowed_disallowance_findings": {"type": "array"},
            "philgeps_records": {"type": "array"},
            "peso_amounts_near_project_names": {"type": "array"}
        }
    },
    "entities/projects.json": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["project_id", "canonical_name", "project_type",
                         "municipality", "province", "barangay", "fiscal_year",
                         "provenance"],
            "properties": {
                "project_id": {"type": "string"},
                "canonical_name": {"type": "string"},
                "project_type": {"type": "string"},
                "municipality": {"type": "string"},
                "province": {"type": "string"},
                "barangay": {"type": "array"},
                "fiscal_year": {"type": ["integer", "null"]},
                "provenance": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["source"], "properties": {"source": {"type": "string"}, "record_role": {"type": "string", "enum": ["project_record", "fund_record", "bid_record", "contract_record", "audit_record", "infrastructure_record"]}, "source_as_of": {"type": "string"}}}}
            }
        }
    },
    "entities/contracts.json": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["contract_id", "title", "award_amount", "award_date",
                         "organization", "source_record_id", "provenance"],
            "properties": {
                "contract_id": {"type": "string"},
                "title": {"type": "string"},
                "awardee_id": {"type": ["string", "null"]},
                "award_amount": {"type": "number"},
                "award_date": {"type": "string"},
                "provenance": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["source"], "properties": {"source": {"type": "string"}, "record_role": {"type": "string", "enum": ["project_record", "fund_record", "bid_record", "contract_record", "audit_record", "infrastructure_record"]}, "source_as_of": {"type": "string"}}}}
            }
        }
    },
    "entities/contractors.json": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["contractor_id", "canonical_name", "source_names",
                         "contract_count", "provenance"],
            "properties": {
                "contractor_id": {"type": "string"},
                "canonical_name": {"type": "string"},
                "source_names": {"type": "array", "minItems": 1},
                "provenance": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["source"], "properties": {"source": {"type": "string"}, "record_role": {"type": "string", "enum": ["project_record", "fund_record", "bid_record", "contract_record", "audit_record", "infrastructure_record"]}, "source_as_of": {"type": "string"}}}}
            }
        }
    },
    "entities/funds.json": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["fund_id", "period", "figures", "provenance"],
            "properties": {
                "fund_id": {"type": "string"},
                "period": {"type": "string"},
                "figures": {"type": "object"},
                "provenance": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["source"], "properties": {"source": {"type": "string"}, "record_role": {"type": "string", "enum": ["project_record", "fund_record", "bid_record", "contract_record", "audit_record", "infrastructure_record"]}, "source_as_of": {"type": "string"}}}}
            }
        }
    },
    "entities/audit-findings.json": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["finding_id", "title", "status", "provenance"],
            "properties": {
                "finding_id": {"type": "string"},
                "title": {"type": "string"},
                "provenance": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["source"], "properties": {"source": {"type": "string"}, "record_role": {"type": "string", "enum": ["project_record", "fund_record", "bid_record", "contract_record", "audit_record", "infrastructure_record"]}, "source_as_of": {"type": "string"}}}}
            }
        }
    },
    "entities/bids.json": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["bid_id", "project", "periods", "provenance"],
            "properties": {
                "bid_id": {"type": "string"},
                "project": {"type": "string"},
                "bidder": {"type": "string"},
                "periods": {"type": "array"},
                "provenance": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["source"], "properties": {"source": {"type": "string"}, "record_role": {"type": "string", "enum": ["project_record", "fund_record", "bid_record", "contract_record", "audit_record", "infrastructure_record"]}, "source_as_of": {"type": "string"}}}}
            }
        }
    },
    "relationships.json": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["id", "from", "to", "type", "confidence", "evidence"],
            "properties": {
                "id": {"type": "string"},
                "from": {"type": "string"},
                "to": {"type": "string"},
                "type": {"type": "string",
                         "enum": ["awarded_to", "has_contract", "has_bid", "resulted_in",
                                  "contractor_identity"]},
                "confidence": {"type": "string",
                               "enum": ["explicit", "strong", "probable",
                                        "possible", "unmatched"]},
                "evidence": {"type": "array", "minItems": 1}
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
