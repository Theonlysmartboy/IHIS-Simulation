# IHIS Simulation

Integrated Health Information System simulation and dashboard.
Upload Synthea FHIR patient data, run M/M/c queuing model, view performance results.

## Requirements

To run this project locally, you need:
- **Python 3.8+**
- **MySQL Server** installed and running locally (e.g. MySQL Community Server, XAMPP, or WampServer)
- **Java 17+** (Optional, only required if you want to generate new Synthea patient data)

## Database Setup

Before running the application, you must create a MySQL database and user. Open your MySQL CLI or a database management tool (like MySQL Workbench, phpMyAdmin, or DBeaver) and run the following commands:

```sql
-- 1. Create the database with proper utf8mb4 character set support
CREATE DATABASE ihis_simulation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. Create a local developer user (Optional, or use root)
CREATE USER 'ihis'@'localhost' IDENTIFIED BY 'ihis_dev';
GRANT ALL PRIVILEGES ON ihis_simulation.* TO 'ihis'@'localhost';
FLUSH PRIVILEGES;
```

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

### 4. Set up database environment variables

Create a `.env` file in the project root:

```
DATABASE_URL=mysql+pymysql://ihis:ihis_dev@localhost/ihis_simulation
```

*(Alternatively, use `DATABASE_URL=mysql+pymysql://root:password@localhost/ihis_simulation` matching your root credentials).*

All database tables are created automatically on the first start of the application.

### 5. Start the server

```bash
python dashboard/app.py
```

Open http://localhost:5000 in your browser.

## Getting FHIR Test Data

You have two options:

### Option A: Use pre-generated samples (local only)

Sample batches are in `data/samples/`. Go to http://localhost:5000/samples, pick a batch, and click **Import**.

### Option B: Generate your own with Synthea

Requires Java 17+. Download the Synthea JAR:

https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar

Place it in the project root and run:

```bash
java -jar synthea-with-dependencies.jar -p 50 -s 42 --exporter.fhir.export true
```

Generated files will be in `output/fhir/`. Upload them via the **Upload** button in the dashboard.

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
- **SimSQL (MySQL)** SQL-based data simulation layer for FHIR operations
- **Synthea** synthetic FHIR R4 patient data generation
- **Standards** HL7 FHIR R4, ICD-10, LOINC, RxNorm, SNOMED CT

## Troubleshooting MySQL Connection Issues

- **Authentication plugin 'caching_sha2_password' cannot be loaded**: Modern MySQL installations use caching_sha2_password by default. Make sure the `cryptography` library is installed (`pip install cryptography`), which allows `PyMySQL` to safely authenticate using modern credentials.
- **Access Denied**: Double-check the username and password in the `.env` database URL. Make sure the user has been granted privileges on the database `ihis_simulation` and that `FLUSH PRIVILEGES;` was run.
- **Can't connect to local MySQL server**: Ensure the MySQL server service is actually running on your computer.
