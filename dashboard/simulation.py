"""
Simulation engine that runs M/M/c queuing model against real uploaded data.
Uses actual resource counts from the database to drive the simulation.
"""

import math
import random
import time
import numpy as np
import simpy
from .db import (
    get_session, Patient, Encounter, Observation,
    Condition, Medication, SimulationRun, UploadBatch
)

RANDOM_SEED = 42
SERVICE_RATE_PER_NODE = 20  # mu: requests/second per server

# Acceptance thresholds from thesis Table 3.1
THRESHOLDS = {
    "avg_response_time_ms": 200,
    "p95_response_time_ms": 1000,
    "throughput_tps": 50,
    "availability_pct": 99.5,
    "transaction_failure_rate": 0.01,
    "fhir_validation_rate": 0.98,
}


def get_data_summary():
    """Get counts of all uploaded resources from the database."""
    session = get_session()
    try:
        patients = session.query(Patient).count()
        encounters = session.query(Encounter).count()
        observations = session.query(Observation).count()
        conditions = session.query(Condition).count()
        medications = session.query(Medication).count()
        total = patients + encounters + observations + conditions + medications

        valid_patients = session.query(Patient).filter(Patient.fhir_valid == True).count()
        valid_encounters = session.query(Encounter).filter(Encounter.fhir_valid == True).count()
        valid_observations = session.query(Observation).filter(Observation.fhir_valid == True).count()
        valid_conditions = session.query(Condition).filter(Condition.fhir_valid == True).count()
        valid_medications = session.query(Medication).filter(Medication.fhir_valid == True).count()
        valid_total = valid_patients + valid_encounters + valid_observations + valid_conditions + valid_medications

        batches = session.query(UploadBatch).filter(UploadBatch.status == "completed").count()

        from dashboard.db import Dhis2Data
        dhis2_count = session.query(Dhis2Data).count()

        return {
            "patients": patients,
            "encounters": encounters,
            "observations": observations,
            "conditions": conditions,
            "medications": medications,
            "dhis2_indicators": dhis2_count,
            "total": total,
            "valid_total": valid_total,
            "fhir_compliance_pct": round(valid_total / total * 100, 2) if total > 0 else 0,
            "batches": batches,
            "has_data": total > 0 or dhis2_count > 0,
        }
    finally:
        session.close()


def erlang_c(arrival_rate: float, service_rate: float, num_servers: int) -> dict:
    """M/M/c queuing model using the Erlang-C formula."""
    lam = arrival_rate
    mu = service_rate
    c = num_servers
    a = lam / mu
    rho = lam / (c * mu)

    if rho >= 1.0:
        return {
            "traffic_intensity": round(a, 4),
            "utilisation": round(rho, 4),
            "system_stable": False,
            "prob_waiting": 1.0,
            "avg_queue_wait_ms": float("inf"),
            "avg_response_time_ms": float("inf"),
            "throughput_tps": 0,
            "queue_length": float("inf"),
        }

    numerator = (a ** c / math.factorial(c)) * (1 / (1 - rho))
    poisson_sum = sum((a ** k) / math.factorial(k) for k in range(c))
    denominator = poisson_sum + numerator
    prob_waiting = numerator / denominator

    spare_capacity = (c * mu) - lam
    avg_queue_wait_s = prob_waiting / spare_capacity
    avg_queue_wait_ms = avg_queue_wait_s * 1000
    avg_response_time_s = avg_queue_wait_s + (1 / mu)
    avg_response_time_ms = avg_response_time_s * 1000
    avg_queue_length = lam * avg_queue_wait_s

    return {
        "traffic_intensity": round(a, 4),
        "utilisation": round(rho, 4),
        "system_stable": True,
        "prob_waiting": round(prob_waiting, 4),
        "avg_queue_wait_ms": round(avg_queue_wait_ms, 2),
        "avg_response_time_ms": round(avg_response_time_ms, 2),
        "avg_queue_length": round(avg_queue_length, 4),
        "spare_capacity": round(spare_capacity, 4),
    }


def run_simpy_scenario(arrival_rate, num_servers, sim_duration=100):
    """Run a SimPy discrete-event simulation for an M/M/c queue."""
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    results = {
        "response_times_ms": [],
        "queue_wait_times_ms": [],
        "completed": 0,
        "failed": 0,
        "downtime_s": 0,
    }

    def fhir_transaction(env, cluster, res):
        arrival = env.now
        with cluster.request() as req:
            yield req
            wait = env.now - arrival
            service = random.expovariate(SERVICE_RATE_PER_NODE)
            yield env.timeout(service)
            total = env.now - arrival
            res["response_times_ms"].append(total * 1000)
            res["queue_wait_times_ms"].append(wait * 1000)
            res["completed"] += 1

    def generator(env, cluster, res):
        while True:
            inter = random.expovariate(arrival_rate)
            yield env.timeout(inter)
            env.process(fhir_transaction(env, cluster, res))
            if random.random() < 0.005:
                res["failed"] += 1
                res["downtime_s"] += random.uniform(0.005, 0.015)

    env = simpy.Environment()
    cluster = simpy.Resource(env, capacity=num_servers)
    env.process(generator(env, cluster, results))
    env.run(until=sim_duration)

    return results


def run_full_simulation(arrival_rate=48, num_servers=3):
    """
    Run the full simulation against real data in the database.

    Uses actual FHIR resource counts for compliance metrics,
    and M/M/c queuing model for performance metrics.
    """
    data = get_data_summary()
    if not data["has_data"]:
        return {"error": "No data uploaded. Please upload Synthea FHIR bundles first."}

    mu = SERVICE_RATE_PER_NODE

    # Scenario 1: Baseline
    s1_queuing = erlang_c(arrival_rate, mu, num_servers)
    s1_sim = run_simpy_scenario(arrival_rate, num_servers)
    s1_avg_resp = float(np.mean(s1_sim["response_times_ms"])) if s1_sim["response_times_ms"] else 0
    s1_p95_resp = float(np.percentile(s1_sim["response_times_ms"], 95)) if s1_sim["response_times_ms"] else 0
    s1_avg_wait = float(np.mean(s1_sim["queue_wait_times_ms"])) if s1_sim["queue_wait_times_ms"] else 0
    s1_tps = s1_sim["completed"] / 100
    s1_total = s1_sim["completed"] + s1_sim["failed"]
    s1_fail_rate = (s1_sim["failed"] / s1_total * 100) if s1_total > 0 else 0
    s1_avail = ((100 - s1_sim["downtime_s"]) / 100) * 100

    # Scenario 2: Surge (same servers, higher load)
    surge_rate = int(arrival_rate * 1.5)
    s2_queuing = erlang_c(surge_rate, mu, num_servers)

    # Scenario 3: Horizontal Scaling (surge load, more servers)
    scaled_servers = num_servers + 2
    s3_queuing = erlang_c(surge_rate, mu, scaled_servers)
    s3_sim = run_simpy_scenario(surge_rate, scaled_servers)
    s3_avg_resp = float(np.mean(s3_sim["response_times_ms"])) if s3_sim["response_times_ms"] else 0
    s3_avg_wait = float(np.mean(s3_sim["queue_wait_times_ms"])) if s3_sim["queue_wait_times_ms"] else 0
    s3_tps = s3_sim["completed"] / 100
    s3_total = s3_sim["completed"] + s3_sim["failed"]
    s3_fail_rate = (s3_sim["failed"] / s3_total * 100) if s3_total > 0 else 0
    s3_avail = ((100 - s3_sim["downtime_s"]) / 100) * 100

    # Wait reduction
    wait_reduction = ((s1_avg_wait - s3_avg_wait) / s1_avg_wait * 100) if s1_avg_wait > 0 else 0

    # Scaling table
    scaling_table = []
    for c in range(num_servers, num_servers + 5):
        m = erlang_c(surge_rate, mu, c)
        scaling_table.append({
            "servers": c,
            "total_capacity_tps": c * mu,
            "utilisation": m["utilisation"],
            "prob_waiting": m.get("prob_waiting", 1.0),
            "avg_queue_wait_ms": m["avg_queue_wait_ms"] if m["system_stable"] else None,
            "avg_response_time_ms": m["avg_response_time_ms"] if m["system_stable"] else None,
            "system_stable": m["system_stable"],
        })

    # FHIR compliance from real data
    session = get_session()
    try:
        fhir_systems = []
        for model, name, fmt in [
            (Patient, "Patient Records", "HL7 FHIR R4"),
            (Encounter, "Encounter Records", "HL7 FHIR R4"),
            (Observation, "Lab Observations", "LOINC coded"),
            (Condition, "Diagnoses", "ICD-10 / SNOMED"),
            (Medication, "Medications", "RxNorm coded"),
        ]:
            total = session.query(model).count()
            valid = session.query(model).filter(model.fhir_valid == True).count()
            rate = round(valid / total * 100, 2) if total > 0 else 0
            fhir_systems.append({
                "system_name": name,
                "data_format": fmt,
                "total_resources": total,
                "valid_resources": valid,
                "compliance_rate_pct": rate,
                "passes_threshold": rate >= 98.0,
            })

        # Save simulation run
        run = SimulationRun(
            total_patients=data["patients"],
            total_encounters=data["encounters"],
            total_observations=data["observations"],
            total_conditions=data["conditions"],
            total_medications=data["medications"],
            total_resources=data["total"],
            fhir_valid_count=data["valid_total"],
            fhir_compliance_pct=data["fhir_compliance_pct"],
            arrival_rate=arrival_rate,
            service_rate=mu,
            num_servers=num_servers,
            utilisation=s1_queuing["utilisation"],
            system_stable=s1_queuing["system_stable"],
            avg_response_ms=round(s1_avg_resp, 2),
            avg_queue_wait_ms=round(s1_avg_wait, 2),
            throughput_tps=round(s1_tps, 2),
            availability_pct=round(s1_avail, 2),
            failure_rate_pct=round(s1_fail_rate, 2),
        )
        session.add(run)
        session.commit()
        run_id = run.id
    finally:
        session.close()

    return {
        "run_id": run_id,
        "data_summary": data,
        "thresholds": THRESHOLDS,
        "scenario_1": {
            "name": "Baseline Load",
            "arrival_rate": arrival_rate,
            "num_servers": num_servers,
            "avg_response_ms": round(s1_avg_resp, 2),
            "p95_response_ms": round(s1_p95_resp, 2),
            "avg_queue_wait_ms": round(s1_avg_wait, 2),
            "throughput_tps": round(s1_tps, 2),
            "availability_pct": round(s1_avail, 2),
            "failure_rate_pct": round(s1_fail_rate, 2),
            "utilisation": s1_queuing["utilisation"],
            "system_stable": s1_queuing["system_stable"],
            "transactions_completed": s1_sim["completed"],
            "transactions_failed": s1_sim["failed"],
        },
        "scenario_2": {
            "name": "Peak Surge",
            "arrival_rate": surge_rate,
            "num_servers": num_servers,
            "utilisation": s2_queuing["utilisation"],
            "system_stable": s2_queuing["system_stable"],
            "avg_response_ms": s2_queuing["avg_response_time_ms"] if s2_queuing["system_stable"] else None,
        },
        "scenario_3": {
            "name": "Horizontal Scaling",
            "arrival_rate": surge_rate,
            "num_servers": scaled_servers,
            "avg_response_ms": round(s3_avg_resp, 2),
            "avg_queue_wait_ms": round(s3_avg_wait, 2),
            "throughput_tps": round(s3_tps, 2),
            "availability_pct": round(s3_avail, 2),
            "failure_rate_pct": round(s3_fail_rate, 2),
            "utilisation": s3_queuing["utilisation"],
            "system_stable": s3_queuing["system_stable"],
            "wait_reduction_pct": round(wait_reduction, 2),
        },
        "scaling_table": scaling_table,
        "fhir_systems": fhir_systems,
        "fhir_compliance_pct": data["fhir_compliance_pct"],
    }
