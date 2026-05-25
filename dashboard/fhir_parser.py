"""
FHIR Bundle Parser for Synthea-generated JSON files.
Extracts Patient, Encounter, Observation, Condition, MedicationRequest resources.
Uses bulk inserts for performance with remote databases.
"""

import json
import uuid
from datetime import datetime, timezone
from .db import (
    get_session, UploadBatch, Patient, Encounter,
    Observation, Condition, Medication
)
from sqlalchemy.dialects.postgresql import insert as pg_insert


FHIR_REQUIRED = {
    "Patient": ["id", "resourceType"],
    "Encounter": ["id", "resourceType", "status"],
    "Observation": ["id", "resourceType", "status", "code"],
    "Condition": ["id", "resourceType", "code"],
    "MedicationRequest": ["id", "resourceType", "status", "medicationCodeableConcept"],
}

SUPPORTED_TYPES = set(FHIR_REQUIRED.keys())


def validate_fhir_resource(resource: dict) -> bool:
    rtype = resource.get("resourceType", "")
    required = FHIR_REQUIRED.get(rtype, [])
    for field in required:
        if field not in resource or resource[field] is None:
            return False
    return True


def extract_reference_id(ref: str) -> str:
    if not ref:
        return ""
    if "urn:uuid:" in ref:
        return ref.replace("urn:uuid:", "")
    if "/" in ref:
        return ref.split("/")[-1]
    return ref


def get_coding(codeable_concept: dict, system_prefix: str = "") -> tuple:
    if not codeable_concept:
        return "", ""
    codings = codeable_concept.get("coding", [])
    for coding in codings:
        sys = coding.get("system", "")
        if not system_prefix or system_prefix in sys:
            return coding.get("code", ""), coding.get("display", "")
    if codings:
        return codings[0].get("code", ""), codings[0].get("display", "")
    return "", ""


def parse_synthea_bundle(file_content: str, filename: str) -> dict:
    """
    Parse a Synthea FHIR Bundle JSON and store resources in the database.
    Uses bulk inserts for speed with remote Postgres.
    """
    data = json.loads(file_content)

    if data.get("resourceType") != "Bundle":
        return {"error": f"Not a FHIR Bundle (got {data.get('resourceType', 'unknown')})"}

    entries = data.get("entry", [])
    if not entries:
        return {"error": "Bundle has no entries"}

    session = get_session()
    try:
        batch = UploadBatch(filename=filename, total_resources=0)
        session.add(batch)
        session.flush()
        bid = batch.id

        # Collect rows in memory first
        patients, encounters, observations, conditions, medications = [], [], [], [], []
        counts = {"Patient": 0, "Encounter": 0, "Observation": 0, "Condition": 0, "MedicationRequest": 0, "other": 0}
        valid_count = 0
        invalid_count = 0
        now = datetime.now(timezone.utc)

        for entry in entries:
            resource = entry.get("resource", {})
            rtype = resource.get("resourceType", "")

            if rtype not in SUPPORTED_TYPES:
                counts["other"] += 1
                continue

            is_valid = validate_fhir_resource(resource)
            rid = resource.get("id", "")
            if not rid:
                rid = extract_reference_id(entry.get("fullUrl", ""))
            if not rid:
                rid = str(uuid.uuid4())

            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1

            if rtype == "Patient":
                name = resource.get("name", [{}])[0] if resource.get("name") else {}
                address = resource.get("address", [{}])[0] if resource.get("address") else {}
                patients.append({
                    "id": rid, "batch_id": bid,
                    "given_name": " ".join(name.get("given", [])),
                    "family_name": name.get("family", ""),
                    "birth_date": resource.get("birthDate", ""),
                    "gender": resource.get("gender", ""),
                    "address_city": address.get("city", ""),
                    "address_country": address.get("country", ""),
                    "marital_status": get_coding(resource.get("maritalStatus"))[1],
                    "fhir_valid": is_valid,
                    "raw_json": json.dumps(resource)[:5000],
                    "created_at": now,
                })
                counts["Patient"] += 1

            elif rtype == "Encounter":
                enc_class = resource.get("class", {})
                enc_type = resource.get("type", [{}])[0] if resource.get("type") else {}
                period = resource.get("period", {})
                subject = resource.get("subject", {}).get("reference", "")
                encounters.append({
                    "id": rid, "batch_id": bid,
                    "patient_id": extract_reference_id(subject),
                    "encounter_class": enc_class.get("code", "") if isinstance(enc_class, dict) else str(enc_class),
                    "encounter_type": get_coding(enc_type)[1] if isinstance(enc_type, dict) else "",
                    "period_start": period.get("start", ""),
                    "period_end": period.get("end", ""),
                    "status": resource.get("status", ""),
                    "fhir_valid": is_valid,
                    "created_at": now,
                })
                counts["Encounter"] += 1

            elif rtype == "Observation":
                code_val, code_display = get_coding(resource.get("code"))
                vq = resource.get("valueQuantity", {})
                subject = resource.get("subject", {}).get("reference", "")
                encounter = resource.get("encounter", {}).get("reference", "") if resource.get("encounter") else ""
                observations.append({
                    "id": rid, "batch_id": bid,
                    "patient_id": extract_reference_id(subject),
                    "encounter_id": extract_reference_id(encounter),
                    "loinc_code": code_val,
                    "display": (code_display or "")[:500],
                    "value_quantity": vq.get("value") if vq else None,
                    "value_unit": vq.get("unit", "") if vq else "",
                    "value_string": str(resource.get("valueString", "") or resource.get("valueCodeableConcept", ""))[:500],
                    "status": resource.get("status", ""),
                    "fhir_valid": is_valid,
                    "created_at": now,
                })
                counts["Observation"] += 1

            elif rtype == "Condition":
                code_val, code_display = get_coding(resource.get("code"))
                snomed_code, _ = get_coding(resource.get("code"), "snomed")
                icd_code, _ = get_coding(resource.get("code"), "icd")
                subject = resource.get("subject", {}).get("reference", "")
                clinical = resource.get("clinicalStatus", {})
                cs_code, _ = get_coding(clinical)
                conditions.append({
                    "id": rid, "batch_id": bid,
                    "patient_id": extract_reference_id(subject),
                    "icd10_code": icd_code or code_val,
                    "snomed_code": snomed_code or code_val,
                    "display": (code_display or "")[:500],
                    "clinical_status": cs_code,
                    "onset_date": resource.get("onsetDateTime", ""),
                    "fhir_valid": is_valid,
                    "created_at": now,
                })
                counts["Condition"] += 1

            elif rtype == "MedicationRequest":
                med = resource.get("medicationCodeableConcept", {})
                code_val, code_display = get_coding(med)
                rxnorm, _ = get_coding(med, "rxnorm")
                snomed, _ = get_coding(med, "snomed")
                subject = resource.get("subject", {}).get("reference", "")
                medications.append({
                    "id": rid, "batch_id": bid,
                    "patient_id": extract_reference_id(subject),
                    "rxnorm_code": rxnorm or code_val,
                    "snomed_code": snomed or "",
                    "medication_name": (code_display or "")[:500],
                    "status": resource.get("status", ""),
                    "authored_on": resource.get("authoredOn", ""),
                    "fhir_valid": is_valid,
                    "created_at": now,
                })
                counts["MedicationRequest"] += 1

        # Bulk insert with ON CONFLICT DO NOTHING
        def bulk_upsert(model, rows):
            if not rows:
                return
            stmt = pg_insert(model.__table__).values(rows).on_conflict_do_nothing(index_elements=["id"])
            session.execute(stmt)

        bulk_upsert(Patient, patients)
        bulk_upsert(Encounter, encounters)
        bulk_upsert(Observation, observations)
        bulk_upsert(Condition, conditions)
        bulk_upsert(Medication, medications)

        total = sum(v for k, v in counts.items() if k != "other")
        batch.total_resources = total
        batch.valid_resources = valid_count
        batch.invalid_resources = invalid_count
        batch.status = "completed"
        session.commit()

        return {
            "batch_id": batch.id,
            "filename": filename,
            "total_resources": total,
            "valid": valid_count,
            "invalid": invalid_count,
            "compliance_pct": round((valid_count / total * 100), 2) if total > 0 else 0,
            "counts": counts,
            "status": "completed",
        }

    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()
