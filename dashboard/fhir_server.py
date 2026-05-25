"""
Fetch FHIR resources from the public HAPI FHIR R4 test server.
https://hapi.fhir.org/baseR4
"""

import requests
import uuid
from datetime import datetime, timezone
from .db import (
    get_session, UploadBatch, Patient, Encounter,
    Observation, Condition, Medication
)
from .fhir_parser import validate_fhir_resource, extract_reference_id

HAPI_BASE = "https://hapi.fhir.org/baseR4"
RESOURCE_TYPES = ["Patient", "Encounter", "Observation", "Condition", "MedicationRequest"]
COUNT_PER_TYPE = 20


def fetch_from_hapi():
    """Fetch sample FHIR resources from the public HAPI server."""
    session = get_session()
    try:
        batch = UploadBatch(
            filename="HAPI FHIR Test Server",
            total_resources=0,
            status="processing"
        )
        session.add(batch)
        session.flush()

        counts = {rt: 0 for rt in RESOURCE_TYPES}
        valid_count = 0
        invalid_count = 0

        for rtype in RESOURCE_TYPES:
            url = f"{HAPI_BASE}/{rtype}?_count={COUNT_PER_TYPE}&_format=json"
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                bundle = resp.json()
            except Exception as e:
                continue

            entries = bundle.get("entry", [])
            for entry in entries:
                resource = entry.get("resource", {})
                if resource.get("resourceType") != rtype:
                    continue

                rid = resource.get("id", str(uuid.uuid4()))
                is_valid = validate_fhir_resource(resource)
                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

                # Use unique IDs to avoid collisions with existing data
                unique_id = f"hapi-{rid}"

                if rtype == "Patient":
                    name = resource.get("name", [{}])[0]
                    given = " ".join(name.get("given", []))
                    family = name.get("family", "")
                    addr = (resource.get("address") or [{}])[0]
                    obj = Patient(
                        id=unique_id, batch_id=batch.id,
                        given_name=given, family_name=family,
                        birth_date=resource.get("birthDate", ""),
                        gender=resource.get("gender", ""),
                        address_city=addr.get("city", ""),
                        address_country=addr.get("country", ""),
                        fhir_valid=is_valid
                    )
                    session.merge(obj)

                elif rtype == "Encounter":
                    subj = resource.get("subject", {}).get("reference", "")
                    enc_class = resource.get("class", {})
                    if isinstance(enc_class, dict):
                        enc_class = enc_class.get("code", "")
                    period = resource.get("period", {})
                    obj = Encounter(
                        id=unique_id, batch_id=batch.id,
                        patient_id=extract_reference_id(subj),
                        encounter_class=str(enc_class),
                        period_start=period.get("start", ""),
                        period_end=period.get("end", ""),
                        status=resource.get("status", ""),
                        fhir_valid=is_valid
                    )
                    session.merge(obj)

                elif rtype == "Observation":
                    code = resource.get("code", {}).get("coding", [{}])[0]
                    vq = resource.get("valueQuantity", {})
                    obj = Observation(
                        id=unique_id, batch_id=batch.id,
                        patient_id=extract_reference_id(
                            resource.get("subject", {}).get("reference", "")
                        ),
                        loinc_code=code.get("code", ""),
                        display=code.get("display", ""),
                        value_quantity=vq.get("value"),
                        value_unit=vq.get("unit", ""),
                        status=resource.get("status", ""),
                        fhir_valid=is_valid
                    )
                    session.merge(obj)

                elif rtype == "Condition":
                    code = resource.get("code", {}).get("coding", [{}])[0]
                    obj = Condition(
                        id=unique_id, batch_id=batch.id,
                        patient_id=extract_reference_id(
                            resource.get("subject", {}).get("reference", "")
                        ),
                        icd10_code=code.get("code", ""),
                        display=code.get("display", ""),
                        clinical_status=str(
                            resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
                        ),
                        fhir_valid=is_valid
                    )
                    session.merge(obj)

                elif rtype == "MedicationRequest":
                    med_cc = resource.get("medicationCodeableConcept", {})
                    med_code = (med_cc.get("coding") or [{}])[0]
                    obj = Medication(
                        id=unique_id, batch_id=batch.id,
                        patient_id=extract_reference_id(
                            resource.get("subject", {}).get("reference", "")
                        ),
                        rxnorm_code=med_code.get("code", ""),
                        medication_name=med_code.get("display", med_cc.get("text", "")),
                        status=resource.get("status", ""),
                        fhir_valid=is_valid
                    )
                    session.merge(obj)

                counts[rtype] += 1

        total = sum(counts.values())
        batch.total_resources = total
        batch.valid_resources = valid_count
        batch.invalid_resources = invalid_count
        batch.status = "completed"
        session.commit()

        compliance = round(valid_count / total * 100, 2) if total > 0 else 0

        return {
            "source": "HAPI FHIR Test Server",
            "total_resources": total,
            "valid_resources": valid_count,
            "invalid_resources": invalid_count,
            "compliance_pct": compliance,
            "counts": counts,
        }

    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()
