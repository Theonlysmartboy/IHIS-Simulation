# IHIS Simulation

Integrated Health Information System simulation and dashboard.
Upload Synthea FHIR patient data, run M/M/c queuing model, view performance results.

## Run Postgres with Docker (optional)

If you don't have Postgres installed, spin one up in Docker Desktop:

```bash
docker compose up -d
```

Then set this in your `.env`:

```
DATABASE_URL=postgresql://ihis:ihis_dev@localhost:5432/ihis
```

To stop: `docker compose down`

## Installation

### 1. Extract and open

Extract the ZIP, then `cd` into the folder:

```bash
cd IHIS-Simulation
```

### 2. Create virtual environment

```bash
python -m venv venv
```

Activate it:

- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up database

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://user:pass@host/dbname
```

Tables are created automatically on first run.

### 5. Start the server

```bash
python dashboard/app.py
```

Open http://localhost:5000

## Getting FHIR Test Data

You have two options:

### Option A: Use pre-generated samples (local only)

Sample batches are in `data/samples/`. Go to http://localhost:5000/samples, pick a batch, and click Import.

### Option B: Generate your own with Synthea

Requires Java 17+. Download the Synthea JAR:

https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar

Place it in the project root and run:

```bash
java -jar synthea-with-dependencies.jar -p 50 -s 42 --exporter.fhir.export true
```

Generated files will be in `output/fhir/`. Upload them via the Upload button in the dashboard.

Full Synthea setup guide: https://github.com/synthetichealth/synthea/wiki/Basic-Setup-and-Running

## Scenarios

| # | Name | Tests |
|---|------|-------|
| 1 | Baseline Load | Latency, Availability, Throughput |
| 2 | Peak Surge | Stability (expected: unstable) |
| 3 | Horizontal Scaling | Scalability, Wait Reduction |

## Acceptance Thresholds

| Metric | Threshold |
|--------|-----------|
| Average Response Time | ≤ 200ms |
| System Availability | ≥ 99.5% |
| Throughput | ≥ 50 TPS |
| Transaction Failure Rate | ≤ 1% |
| FHIR Validation Compliance | ≥ 98% |

## Stack

- **Flask** web dashboard with Chart.js
- **SimPy** discrete-event simulation (M/M/c queuing model, Erlang-C)
- **SimSQL (PostgreSQL)** SQL-based data simulation layer for FHIR operations
- **Synthea** synthetic FHIR R4 patient data generation
- **Standards** HL7 FHIR R4, ICD-10, LOINC, RxNorm, SNOMED CT
