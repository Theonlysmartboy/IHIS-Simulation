# Comprehensive Scientific Analysis and Thesis-Ready Documentation
**Project:** Integrated Health Information System (IHIS) Simulation and Dashboard  
**Target Focus:** "Development and Simulation-Based Validation of an Interoperable Health Information System (IHIS) Model for Resource-Constrained Settings"

---

# 1. IMPLEMENTED ALGORITHMS

This section analyzes the computational algorithms explicitly coded within the IHIS project, defining their purposes, operational steps, mathematical foundations, and academic relevance.

## 1.1 M/M/c Analytical Queueing Solver (Erlang-C Engine)
* **Algorithm Name:** Erlang-C Analytical Solver
* **Purpose:** Computes steady-state queue performance metrics to mathematically predict system bottlenecks under baseline, surge, and horizontally scaled conditions.
* **Mathematical Basis:** Continuous-time Markov chains representing an $M/M/c$ queuing system. It models arrivals as a Poisson process (exponential inter-arrival times) and service times as exponentially distributed.
* **Inputs:** 
  - $\lambda$ (Arrival Rate in transactions per second, Float)
  - $\mu$ (Service Rate per server node in transactions per second, Float)
  - $c$ (Number of active parallel server nodes, Integer)
* **Outputs:** 
  - $\rho$ (System Utilisation, Float)
  - $P_Q$ (Probability of Queueing/Waiting, Float)
  - $W_q$ (Average Queue Waiting Time in milliseconds, Float)
  - $T_r$ (Average System Response Time in milliseconds, Float)
  - $L_q$ (Average Queue Length, Float)
  - $S$ (System Stability, Boolean)
* **Complexity Implications:** $\mathcal{O}(c)$ due to the summation required to calculate the Poisson denominator. Excellent scalability suitable for interactive execution.
* **Healthcare Relevance:** Represents the operational capability of a centralized or federated Health Information Exchange (HIE) regional repository processing incoming FHIR payloads from numerous primary care clinics.
* **Thesis Relevance:** Directly supports System Design and Evaluation. It acts as the mathematical control to validate the empirical discrete-event simulation model.
* **Exact Source File/Function:** `dashboard/simulation.py` -> `erlang_c()`

## 1.2 SimPy Discrete-Event Queueing Simulator
* **Algorithm Name:** SimPy-driven M/M/c Discrete-Event Simulator (DES) with Stochastic Failures
* **Purpose:** Dynamically models transaction-level processing, resource contention, queuing delays, and hardware/network failure scenarios over a continuous time horizon.
* **Mathematical Basis:** Monte Carlo simulation utilizing pseudo-random number generators drawing from exponential distributions for arrival and service durations, uniform distributions for downtime intervals, and Bernoulli trials for failure triggers.
* **Inputs:** 
  - $\lambda$ (Mean arrival rate, Float)
  - $c$ (Server capacity/concurrency limit, Integer)
  - $T$ (Simulation duration, Float)
  - $\mu$ (Mean service rate per node, default=20 TPS, Float)
  - $p_{\text{fail}}$ (Probability of network/transaction failure, default=0.005, Float)
* **Outputs:** 
  - Empirical distribution of response times ($T_r$, List of Floats)
  - Empirical distribution of queue wait times ($W_q$, List of Floats)
  - $N_{\text{completed}}$ (Total successfully completed transactions, Integer)
  - $N_{\text{failed}}$ (Total failed transactions, Integer)
  - $D_{\text{total}}$ (Total system downtime in seconds, Float)
* **Complexity Implications:** $\mathcal{O}(N)$ where $N$ is the number of stochastically generated arrival events. Highly representative of physical server workloads.
* **Healthcare Relevance:** Models real-world network instability, power outages, and resource constraints typical in low- and middle-income country (LMIC) health facilities.
* **Thesis Relevance:** Supports the Methodology and Results chapters by simulating complex, non-deterministic workflows that are mathematically intractable when incorporating random failures.
* **Exact Source File/Function:** `dashboard/simulation.py` -> `run_simpy_scenario()`

## 1.3 Schema-Constraint FHIR Resource Validator
* **Algorithm Name:** FHIR Structural and Required Field Validator
* **Purpose:** Evaluates whether incoming JSON payloads conform to mandatory HL7 FHIR R4 schema specifications prior to database persistence.
* **Mathematical Basis:** Deterministic validation against schema requirement sets.
* **Inputs:** 
  - `resource` (Parsed JSON dictionary, Dict)
* **Outputs:** 
  - `is_valid` (Compliance status, Boolean)
* **Complexity Implications:** $\mathcal{O}(M)$ where $M$ is the number of mandatory fields evaluated. Highly efficient.
* **Healthcare Relevance:** Ensures semantic and structural interoperability across different vendor EHR modules mapping to the national HIE repository.
* **Thesis Relevance:** Serves as the primary mechanism for quantifying "Data Quality" and "FHIR Compliance Rate" within the HIE pipeline, supporting the Interoperability Evaluation objective.
* **Exact Source File/Function:** `dashboard/fhir_parser.py` -> `validate_fhir_resource()`

---

# 2. MATHEMATICAL MODELS AND FORMULAE

This section provides the rigorous mathematical models implemented in the simulation engine. All equations are presented in LaTeX notation alongside plain-text formats.

## 2.1 Traffic Intensity ($a$)
Measures the total offered load to the server cluster.

* **LaTeX:**
  $$a = \frac{\lambda}{\mu}$$
* **Plain Text:**
  `a = lambda / mu`
* **Variables:**
  - $\lambda$ (`arrival_rate`): Incoming transaction rate (transactions/second).
  - $\mu$ (`service_rate`): Average processing speed of a single server node (transactions/second).
* **Code Implementation:** `dashboard/simulation.py` -> line 75: `a = lam / mu`
* **Interpretation:** If $a > c$, the system receives more work than the collective cluster can process, indicating immediate instability.

## 2.2 Server Cluster Utilisation ($\rho$)
Represents the average fraction of time that the server nodes are busy.

* **LaTeX:**
  $$\rho = \frac{\lambda}{c \cdot \mu}$$
* **Plain Text:**
  `rho = lambda / (c * mu)`
* **Variables:**
  - $c$ (`num_servers`): Number of active server nodes in the HIE cluster.
* **Code Implementation:** `dashboard/simulation.py` -> line 76: `rho = lam / (c * mu)`
* **Interpretation:** $\rho$ must remain strictly less than 1.0 ($\rho < 1.0$) for system stability. If $\rho \ge 1.0$, the queue grows infinitely.

## 2.3 Erlang-C Probability of Waiting ($P_Q$)
Calculates the exact probability that an arriving transaction will find all servers busy and must queue.

* **LaTeX:**
  $$P_Q = \frac{\frac{a^c}{c!} \cdot \frac{1}{1-\rho}}{\sum_{k=0}^{c-1} \frac{a^k}{k!} + \frac{a^c}{c!} \cdot \frac{1}{1-\rho}}$$
* **Plain Text:**
  `P_Q = ((a^c / c!) * (1 / (1 - rho))) / ( sum(a^k / k! for k in 0..c-1) + ((a^c / c!) * (1 / (1 - rho))) )`
* **Variables:**
  - $a$: Traffic intensity.
  - $c$: Number of server nodes.
  - $\rho$: Server cluster utilisation.
* **Code Implementation:** `dashboard/simulation.py` -> lines 90-93:
  ```python
  numerator = (a ** c / math.factorial(c)) * (1 / (1 - rho))
  poisson_sum = sum((a ** k) / math.factorial(k) for k in range(c))
  denominator = poisson_sum + numerator
  prob_waiting = numerator / denominator
  ```
* **Interpretation:** High values of $P_Q$ indicate that clinic workstations will experience immediate delays prior to transaction processing.

## 2.4 Average Queue Waiting Time ($W_q$)
Predicts the mean duration a FHIR resource remains buffered in the queue before server acquisition.

* **LaTeX:**
  $$W_q = \frac{P_Q}{(c \cdot \mu) - \lambda}$$
* **Plain Text:**
  `W_q = P_Q / ((c * mu) - lambda)`
* **Code Implementation:** `dashboard/simulation.py` -> lines 95-97:
  ```python
  spare_capacity = (c * mu) - lam
  avg_queue_wait_s = prob_waiting / spare_capacity
  avg_queue_wait_ms = avg_queue_wait_s * 1000
  ```
* **Interpretation:** Measures latency introduced strictly by resource contention.

## 2.5 Average Response Time ($T_r$)
Calculates total operational latency (waiting time in queue + transmission and processing service time).

* **LaTeX:**
  $$T_r = W_q + \frac{1}{\mu}$$
* **Plain Text:**
  `T_r = W_q + (1 / mu)`
* **Code Implementation:** `dashboard/simulation.py` -> lines 98-99:
  ```python
  avg_response_time_s = avg_queue_wait_s + (1 / mu)
  avg_response_time_ms = avg_response_time_s * 1000
  ```
* **Interpretation:** This is the primary indicator evaluated against the HIE SLA threshold ($\le 200$ ms).

## 2.6 Wait Time Reduction Percentage ($\Delta W_q$)
Quantifies the performance improvement gained by scaling servers during peak load.

* **LaTeX:**
  $$\Delta W_q = \frac{W_{q,\text{baseline}} - W_{q,\text{scaled}}}{W_{q,\text{baseline}}} \cdot 100$$
* **Plain Text:**
  `wait_reduction = ((s1_avg_wait - s3_avg_wait) / s1_avg_wait) * 100`
* **Code Implementation:** `dashboard/simulation.py` -> line 196:
  ```python
  wait_reduction = ((s1_avg_wait - s3_avg_wait) / s1_avg_wait * 100) if s1_avg_wait > 0 else 0
  ```

---

# 3. SIMULATION ENGINE ANALYSIS

The system's simulation architecture is designed around two layers: the analytical Erlang-C solver (for static, immediate mathematical bounds) and a stochastically driven SimPy discrete-event simulation model (for time-series, empirical verification).

```
 +-----------------------------------------------------------------------------------+
 |                             Discrete-Event Generator                              |
 +-----------------------------------------------------------------------------------+
                                           |
                                           v  (Inter-arrival: Exp(lambda))
 +-----------------------------------------------------------------------------------+
 |                             System Queue Buffer                                   |
 +-----------------------------------------------------------------------------------+
                                           |
                                           v  (Server Acquisition: Resource Request)
 +---------------------------------------------------+
 |           Server Node Cluster (c Nodes)           |
 +---------------------------------------------------+
   |                                               |
   v (Service: Exp(mu))                            v (Network Failure: 0.5% rate)
 +-----------------------+                       +-----------------------------------+
 | Completed Transaction |                       | Failed Transaction (Bernoulli)    |
 +-----------------------+                       +-----------------------------------+
                                                   |
                                                   v (Downtime: Uniform(5ms, 15ms))
                                                 +-----------------------------------+
                                                 | System Recovery Phase             |
                                                 +-----------------------------------+
```

### 3.1 Event Lifecycle and Clock Handling
In `run_simpy_scenario`, the simulation utilizes SimPy's virtual clock `env.now`. Time units are modeled in seconds.
1. **Initiation:** The simulation scheduler schedules the event generator loop (`generator()`) at time `0`.
2. **Poisson Arrival Schedule:** The generator loop executes a non-blocking timeout: `yield env.timeout(random.expovariate(arrival_rate))`. This advances the virtual clock directly to the next arrival time according to a homogeneous Poisson process.
3. **Transaction Spawn:** Upon expiration, the process triggers a `fhir_transaction` thread in the simulation environment.
4. **Queue Entry:** The transaction requests access to one of the $c$ parallel server slots: `with cluster.request() as req: yield req`.
5. **Server Processing:** Once allocated, the virtual thread delays by a service time drawn from an exponential distribution with $\mu=20$: `yield env.timeout(random.expovariate(20))`.
6. **Failure Injection:** During the inter-arrival step, a stochastic failure checker assesses if a hardware or connectivity drop occurs based on a Bernoulli distribution ($p = 0.005$). If true, a failure penalty is applied by calling `yield env.timeout(random.uniform(0.005, 0.015))`, simulating network reconnection or query retry overheads.

### 3.2 Implemented Logic vs. Theoretical Assumptions
- **Implemented Logic:** Active thread-level resource locking via `simpy.Resource(env, capacity=num_servers)`, finite runtime limits, explicit tracking of failed states, and uniform recovery penalties.
- **Theoretical Assumptions:** The analytical Erlang-C solver assumes absolute steady-state conditions, infinite queue buffers, no server dropouts, and absolute system uptime ($100\%$). The dual-layer design allows the research to benchmark empirical operational realities (SimPy) against idealized mathematical theory (Erlang-C).

---

# 4. FHIR AND INTEROPERABILITY IMPLEMENTATION

This section covers how the application operationalizes HL7 FHIR (Fast Healthcare Interoperability Resources) data models.

## 4.1 Schema Validation Specifications
The HIE validator (`dashboard/fhir_parser.py`) enforces structural completeness. The system parses structural attributes using a required-keys verification lookup:

| FHIR Resource | Primary Key | Required Structural Keys | Codeable Concept Verification |
|---|---|---|---|
| **Patient** | `id` | `resourceType` | Marital Status (System-Coded mapping) |
| **Encounter** | `id` | `resourceType`, `status` | Encounter Class & Type mapping |
| **Observation**| `id` | `resourceType`, `status`, `code` | LOINC Code mapping |
| **Condition** | `id` | `resourceType`, `code` | ICD-10 & SNOMED CT terminology codes |
| **Medication** | `id` | `resourceType`, `status`, `medicationCodeableConcept` | RxNorm & SNOMED CT terminology codes |

## 4.2 Codeable Concept Extraction & Mapping Workflows
The database parser extracts standardized terminology from standard nested FHIR JSON elements. This is implemented in the `get_coding` function:
1. **Extraction:** Standard FHIR codeable concepts organize mappings within a `"coding"` JSON array.
2. **Dynamic Vocabulary Search:** The function iterates through available codings. If a `system_prefix` parameter is provided (e.g. `"snomed"`, `"loinc"`, or `"icd"`), it matches the URI system key.
3. **Resolution:** If a prefix match is resolved, it returns a key-value tuple representing the medical code and its display name: `(code, display)`. If no prefix matches, it falls back to the first available coding pair in the array to preserve data fidelity.

---

# 5. SCALABILITY IMPLEMENTATION

The simulation executes horizontal scaling analysis dynamically by evaluating the impact of increasing server allocations on queuing delays under high load conditions.

```
 +------------------------------------------------------------------------------------+
 |                    Baseline Scenario (Scenario 1)                                  |
 |                    Offered Load: lambda = 48 TPS                                   |
 |                    Allocated Servers: c = 3                                        |
 |                    System Status: Stable (rho = 80.0%)                             |
 +------------------------------------------------------------------------------------+
                                           |
                                           v  (Surge Trigger: Load increased by 150%)
 +------------------------------------------------------------------------------------+
 |                    Peak Surge Scenario (Scenario 2)                                |
 |                    Offered Load: lambda = 72 TPS                                   |
 |                    Allocated Servers: c = 3                                        |
 |                    System Status: UNSTABLE (rho = 120.0%)                          |
 +------------------------------------------------------------------------------------+
                                           |
                                           v  (Scale Trigger: Servers added [c + 2])
 +------------------------------------------------------------------------------------+
 |                    Horizontally Scaled Scenario (Scenario 3)                       |
 |                    Offered Load: lambda = 72 TPS                                   |
 |                    Allocated Servers: c = 5                                        |
 |                    System Status: Stable (rho = 72.0%)                             |
 +------------------------------------------------------------------------------------+
```

### 5.1 Dynamic Scaling Logic
The horizontal scaling execution is implemented in `run_full_simulation()` (`dashboard/simulation.py`):
1. **Baseline Load Evaluation (Scenario 1):** Measures HIE latency under a standard load (default = 48 TPS) allocated to $c$ servers (default = 3).
2. **Surge Modeling (Scenario 2):** Simulates a sudden $150\%$ surge in patient visits (e.g., during epidemic outbreaks or morning peak registration hours). The arrival rate increases to $\lambda_{\text{surge}} = 1.5 \cdot \lambda_{\text{baseline}}$ (72 TPS). Because $c \cdot \mu = 3 \cdot 20 = 60$ TPS, the offered load (72 TPS) exceeds server capacity, resulting in system instability ($\rho = 1.2$).
3. **Horizontal Scaling Execution (Scenario 3):** Dynamically scales the HIE infrastructure by provisioning two additional nodes ($c_{\text{scaled}} = c + 2$). The system calculates new queuing states. At $c=5$, cluster processing capacity increases to $100$ TPS, restoring system stability ($\rho = 0.72$ or $72\%$) and reducing latencies back to safe SLA bounds.

---

# 6. PERFORMANCE EVALUATION LOGIC

The simulation engine evaluates the physical infrastructure against key performance indicators (KPIs) mapped from real-world HIE deployment specifications.

```
+------------------------------------------------------------------------------+
|                      Performance Evaluation Workflow                         |
+------------------------------------------------------------------------------+
  |
  |-- [1] Database Resource Query
  |   `--> Total Records, Valid FHIR Records, System Ratios
  |
  |-- [2] Stochastic Event Generation
  |   `--> SimPy Transaction Simulation over continuous time
  |
  |-- [3] Empirical Parameter Calculation
  |   `--> Mean/p95 Response Times, Availability %, Failure Rates, TPS
  |
  |-- [4] Thesis SLA Threshold Comparison
  |   `--> Check against response time (<=200ms) and availability (>=99.5%)
  |
  +-- [5] Final Evaluation Model Persistence (MySQL DB Write)
```

1. **Throughput ($TPS$):** Calculated stochastically as the total completed transactions divided by the virtual simulation timeframe:
   $$\text{Throughput} = \frac{N_{\text{completed}}}{T_{\text{simulation}}}$$
2. **Availability Percentage ($A$):** Models HIE system availability by deducting stochastically simulated network/database downtime from the system uptime window:
   $$A = \frac{T_{\text{simulation}} - D_{\text{total}}}{T_{\text{simulation}}} \cdot 100$$
3. **Failure Rate ($F_{\%}$):** Calculated as the proportion of failed transactions resulting from simulated dropped packages or connection interruptions:
   $$F_{\%} = \frac{N_{\text{failed}}}{N_{\text{completed}} + N_{\text{failed}}} \cdot 100$$
4. **SLA Validation:** Compares computed KPIs against thesis target parameters (Response Time $\le 200$ ms, Uptime $\ge 99.5\%$, Throughput $\ge 50$ TPS, Failure Rate $\le 1\%$, FHIR Compliance $\ge 98\%$) to produce a pass/fail compliance assessment.

---

# 7. ARCHITECTURAL IMPLEMENTATION

This section describes the modular architecture of the IHIS Simulation system and how it represents a local HIE implementation.

```
 +------------------------+      +------------------------+      +------------------------+
 |   Synthea FHIR Files   |      | HAPI FHIR Server API   |      |   DHIS2 Indicators     |
 +------------------------+      +------------------------+      +------------------------+
              |                               |                               |
              +-----------------------+-------+-------------------------------+
                                      |
                                      v
                       +-------------------------------+
                       |       Ingestion Layer         |
                       |    (dashboard/fhir_parser.py)  |
                       +-------------------------------+
                                      |
                                      v
                       +-------------------------------+
                       |      Local MySQL DB           |
                       |    (dashboard/db.py)          |
                       +-------------------------------+
                               |               ^
        (Read counts to drive  |               | (Persist simulation
         simulation runs)      v               |  results & performance logs)
                       +-------------------------------+
                       |      Simulation Engine        |
                       |  (dashboard/simulation.py)    |
                       +-------------------------------+
                                      |
                                      v
                       +-------------------------------+
                       |      Flask Dashboard UI       |
                       |    (dashboard/app.py)         |
                       +-------------------------------+
```

The system is structured into four core layers:
1. **Ingestion and Normalization Layer (`fhir_parser.py`):** Handles parsing, semantic field extraction, and structural checking of input JSON records. It acts as the system's "interoperability gateway."
2. **Persistence Layer (`db.py`):** Uses SQLAlchemy mapped to a local MySQL instance. Tables are designed using standard foreign key constraints to model relational medical records (Patient, Encounter, Observation, Condition, Medication).
3. **Discrete-Event Simulation Layer (`simulation.py`):** Drives performance evaluation and capacity forecasting. By reading actual resource counts from the DB, it seeds the arrival rates and profiles of the simulation, ensuring the simulation is backed by clinical data volumes.
4. **Presentation and Management Layer (`app.py`):** A Flask-based web application that serves as the controller, executing simulations, exposing data ingestion endpoints, querying indicator metrics, and rendering results.

---

# 8. METRICS GENERATED BY THE SYSTEM

The simulation produces concrete metrics to quantify the performance and interoperability of the IHIS system.

### Table 8.1: Simulation Metrics Mapped to Technical Meanings
| Metric ID | UI Display Name | Data Type | Formula/Origin | Operational Meaning in Healthcare |
|---|---|---|---|---|
| `total_resources` | Total Uploaded Resources | Integer | Sum of all DB records | Represents the cumulative processing workload in the database cache. |
| `fhir_compliance_pct` | FHIR Compliance Rate | Float | `(valid / total) * 100` | Quantifies syntactic interoperability. Low percentages indicate high data mapping errors. |
| `utilisation` | Server Utilisation | Float | $\rho = \frac{\lambda}{c \cdot \mu}$ | Shows HIE hardware utilization under load. |
| `avg_response_ms` | Average Response Time | Float | Mean of empirical SimPy run | Represents the latency felt by a clinician retrieving a patient record. |
| `avg_queue_wait_ms` | Average Waiting Delay | Float | Mean of SimPy wait times | Represents delays caused strictly by network/database congestion. |
| `throughput_tps` | System Throughput | Float | Completed requests per second | Measures HIE transaction bandwidth. |
| `availability_pct` | System Uptime | Float | $\frac{T - D}{T} \cdot 100$ | Quantifies HIE resilience against power cuts or network failures. |
| `failure_rate_pct` | Transaction Drop Rate | Float | $\frac{N_{\text{failed}}}{N_{\text{total}}} \cdot 100$ | Measures network reliability and data transmission success. |

---

# 9. THESIS CHAPTER MAPPING

This section maps the codebase components to their appropriate locations in a master's dissertation.

### Table 9.1: Project Mapping to Thesis Structure
| Code File / Concept | Proposed Thesis Chapter | Proposed Subsection | Recommended Placement |
|---|---|---|---|
| **Erlang-C Equations** | Chapter 3 (Methodology) | 3.4 Mathematical Modeling of HIE Queues | Methodology |
| **SimPy Engine Workflow** | Chapter 3 (Methodology) | 3.5 Discrete-Event Simulation Framework | Methodology |
| **FHIR Ingestion Pipeline**| Chapter 4 (System Design) | 4.2 Data Ingestion & Parser Architecture | System Design |
| **MySQL Relational Schema**| Chapter 4 (System Design) | 4.4 Persistence Layer & DB Entity Relations | System Design |
| **HAPI & DHIS2 API Connect**| Chapter 4 (System Design) | 4.5 External Integrations & Federated Sync | System Design |
| **Dynamic Scaling Scenarios**| Chapter 5 (Evaluation) | 5.3 Stress Testing and Capacity Scaling | Evaluation / Results |
| **SimPy vs Erlang Results**| Chapter 6 (Results) | 6.2 Simulation Empirical Validation | Results |
| **LMIC Performance Review**| Chapter 7 (Discussion) | 7.2 Feasibility and System Sustainability | Discussion |

---

# 10. THESIS-READY TECHNICAL WRITEUPS

These write-ups are drafted in a formal academic tone, ready for direct copy-pasting into your dissertation.

## 10.1 Chapter 3 (Methodology) - Queuing Model Specification
> "To model the transaction pipelines of the proposed Integrated Health Information System (IHIS) architecture, we establish an analytical M/M/c queuing framework. The model treats incoming clinic transactions as a Poisson process characterized by a mean arrival rate $\lambda$. The centralized HIE gateway cluster is modeled as a set of $c$ parallel, homogeneous servers. Each individual server node processes incoming transactions at a service rate $\mu$, where service times follow an exponential distribution. 
>
> The traffic intensity is calculated as $a = \lambda/\mu$, and the overall system utilization is defined as $\rho = a/c$. To prevent queue overflow and system instability, the system must satisfy the condition $\rho < 1.0$. The probability that a transaction must queue upon arrival is computed via the classical Erlang-C formula. From this probability, we derive the average queue waiting time $W_q$ and the total system response time $T_r$ (composed of queuing wait time plus active processing time). This analytical model provides the baseline bounds against which empirical, non-deterministic discrete-event simulation workloads are validated."

## 10.2 Chapter 4 (System Design) - FHIR Validation and Processing Logic
> "Semantic and structural interoperability within the IHIS repository is enforced through an automated FHIR parsing and validation engine. When a Synthea-generated or HAPI-sourced JSON document is submitted, the ingestion engine inspects the envelope to ensure the `resourceType` matches recognized standard profiles (Patient, Encounter, Observation, Condition, MedicationRequest). For each resource, the system enforces a strict key-matching protocol, verifying mandatory structural attributes such as unique identifier fields, clinical statuses, and terminology codes. 
>
> In addition to structural validation, the engine extracts standardized clinical vocabularies. For instance, diagnostic statements are checked for ICD-10 and SNOMED CT identifiers, while observations are resolved to LOINC codes. This extraction uses a prefix-matching algorithm that scans nested codeable concepts and maps them to clean database columns. Payloads passing validation are flagged as compliant, while malformed records are marked as non-compliant for diagnostic audit logging, ensuring the HIE database acts as a source of clean, validated clinical records."

## 10.3 Chapter 5 (Evaluation) - Empirical Simulation Setup
> "To evaluate system performance under non-idealized operating environments, we developed a discrete-event simulation model using the SimPy framework. While analytical queuing models assume perfect uptime, real-world deployments in low- and middle-income countries (LMICs) face frequent resource constraints, network volatility, and server hardware interruptions. 
>
> The simulation engine addresses these factors by introducing stochastic failure events modeled via a Bernoulli distribution. With a failure probability $p = 0.005$, the system simulates temporary database lockups or network packet drops, applying a uniform recovery penalty between 5ms and 15ms. The simulation advances using a virtual clock where incoming transactions are modeled stochastically as competing threads requesting access to the server cluster resource. This empirical environment allows us to measure non-deterministic performance indicators, including 95th percentile response times, transaction failure rates, and empirical system availability, capturing the operational dynamics of an active HIE deployment."

---

# 11. PSEUDOCODE EXTRACTIONS

These pseudocode blocks represent the core logic of the application's processing layers, structured clearly for direct placement in your dissertation's appendix or implementation sections.

### Algorithm 11.1: Erlang-C Mathematical Queuing Solver
```text
================================================================================
Algorithm: ERLANG_C_SOLVER
================================================================================
Inputs:
  lam          : Float   (Arrival rate, transactions per second)
  mu           : Float   (Service rate per server node)
  c            : Integer (Number of active parallel server nodes)

Outputs:
  A dictionary containing:
    utilisation          : Float   (System resource usage ratio)
    system_stable        : Boolean (True if system can handle the load)
    prob_waiting         : Float   (Probability of queuing, P_Q)
    avg_queue_wait_ms    : Float   (Expected queuing latency in ms)
    avg_response_time_ms : Float   (Expected total HIE latency in ms)

Steps:
  1. Calculate traffic intensity:
     a = lam / mu
  
  2. Calculate system utilisation:
     rho = lam / (c * mu)
  
  3. If rho >= 1.0 Then:
       // System is overloaded and unstable
       Return {
         utilisation: rho,
         system_stable: False,
         prob_waiting: 1.0,
         avg_queue_wait_ms: Infinity,
         avg_response_time_ms: Infinity
       }
     EndIf
  
  4. Compute Erlang-C Poisson summation:
     poisson_sum = Sum of (a^k / k!) for k from 0 to (c - 1)
  
  5. Compute Erlang-C queue probability components:
     numerator = (a^c / c!) * (1 / (1 - rho))
     denominator = poisson_sum + numerator
     P_Q = numerator / denominator
  
  6. Calculate expected latency indicators:
     spare_capacity = (c * mu) - lam
     W_q = P_Q / spare_capacity
     T_r = W_q + (1 / mu)
  
  7. Return computed parameters:
       Return {
         utilisation: rho,
         system_stable: True,
         prob_waiting: P_Q,
         avg_queue_wait_ms: W_q * 1000,
         avg_response_time_ms: T_r * 1000
       }
================================================================================
```

### Algorithm 11.2: SimPy Discrete-Event Simulator with Failures
```text
================================================================================
Algorithm: DISCRETE_EVENT_SIMULATOR
================================================================================
Inputs:
  arrival_rate : Float   (Poisson arrival rate, lambda)
  num_servers  : Integer (Server node capacity, c)
  sim_duration : Float   (Total execution timeframe in seconds, T)
  service_rate : Float   (Default = 20 TPS, mu)

Outputs:
  A dictionary containing:
    avg_response : Float   (Mean empirical response time in ms)
    avg_wait     : Float   (Mean empirical queuing wait in ms)
    completed    : Integer (Total completed transactions)
    failed       : Integer (Total failed transactions)
    availability : Float   (Empirical system uptime percentage)

Steps:
  1. Initialize SimPy Environment:
     env = CreateSimPyEnvironment()
  
  2. Initialize HIE Server Resource:
     cluster = CreateSimPyResource(env, capacity=num_servers)
  
  3. Initialize tracking metrics:
     response_times = EmptyList()
     wait_times = EmptyList()
     completed_count = 0
     failed_count = 0
     total_downtime = 0.0
  
  4. Define FHIR Transaction Process (env, resource_id):
       t_arrival = env.current_time
       
       // Request server slot from cluster resource
       With cluster.request() As request:
         Yield request // Block thread until a server is free
         
         t_allocated = env.current_time
         queuing_delay = t_allocated - t_arrival
         Record queuing_delay in wait_times
         
         // Generate processing duration
         service_duration = GenerateExponentialRandom(rate=service_rate)
         Yield env.timeout(service_duration) // Block thread during processing
         
         t_completion = env.current_time
         total_latency = t_completion - t_arrival
         Record total_latency in response_times
         completed_count = completed_count + 1
       EndWith
  
  5. Define Transaction Generator Loop (env):
       While env.current_time < sim_duration:
         // Schedule next arrival
         inter_arrival_delay = GenerateExponentialRandom(rate=arrival_rate)
         Yield env.timeout(inter_arrival_delay)
         
         // Spawn active transaction thread
         StartProcess(FHIR_Transaction(env))
         
         // Stochastic network failure injection (p=0.005)
         If GenerateUniformRandom(0, 1) < 0.005 Then:
           failed_count = failed_count + 1
           failure_downtime = GenerateUniformRandom(0.005, 0.015)
           total_downtime = total_downtime + failure_downtime
           Yield env.timeout(failure_downtime) // System downtime delay
         EndIf
       EndWhile
  
  6. Execute Simulation:
     RunEnvironment(env, until=sim_duration)
  
  7. Compute Summary Metrics:
     avg_resp = Mean(response_times) * 1000
     avg_wait = Mean(wait_times) * 1000
     uptime_pct = ((sim_duration - total_downtime) / sim_duration) * 100
     
     Return {
       avg_response: avg_resp,
       avg_wait: avg_wait,
       completed: completed_count,
       failed: failed_count,
       availability: uptime_pct
     }
================================================================================
```

---

# 12. IMPORTANT CODE REFERENCES

To maintain academic integrity and support easy citation in your implementation chapters, the table below maps core system features to their exact file paths, class/function entry points, and line numbers.

### Table 12.1: Key Architectural Code References
| System Submodule | Target File Path | Primary Function / Class | Line Range | Functional Contribution |
|---|---|---|---|---|
| **Erlang-C Core Solver** | `dashboard/simulation.py` | `erlang_c()` | 70 - 111 | Solves $M/M/c$ analytical formulas. |
| **DES Simulator Engine** | `dashboard/simulation.py` | `run_simpy_scenario()` | 114 - 153 | Drives stochastic SimPy events. |
| **HIE Simulation Controller** | `dashboard/simulation.py` | `run_full_simulation()` | 156 - 305 | Coordinates baseline, surge, and scaled runs. |
| **FHIR Structure Check** | `dashboard/fhir_parser.py` | `validate_fhir_resource()` | 28 - 34 | Performs key verification on profiles. |
| **Standard Terminology Map**| `dashboard/fhir_parser.py` | `get_coding()` | 47 - 57 | Parses LOINC, SNOMED, and RxNorm codes. |
| **Bulk SQL Ingestion Handler**| `dashboard/fhir_parser.py` | `parse_synthea_bundle() -> bulk_upsert()` | 204 - 220 | Executes dialect-aware database bulk-upsert. |
| **DB Normalisation Helper**| `dashboard/db.py` | `init_db()` | 22 - 48 | Configures MySQL connection pooling. |
| **Flask Route Coordinator**| `dashboard/app.py` | `upload()`, `simulate()` | 100 - 141 | Exposes core application API routing. |

---

# 13. RESEARCH CONTRIBUTION MAPPING

This section maps the codebase features to the main objectives of your thesis.

### Table 13.1: Code Implementation Mapped to Research Contributions
| Implemented Code Feature | Core Thesis Objective Mapped | Scientific / Research Contribution |
|---|---|---|
| **Stochastic Failure Injection (`run_simpy_scenario`)** | **LMIC Feasibility Assessment** | Validates HIE operational robustness under typical resource-constrained settings (e.g. electrical power cuts, network drops). |
| **Dialect-Aware Bulk Ingestion (`fhir_parser.py`)** | **HIE High-Performance Design** | Demonstrates database-portable, high-speed ingestion strategies, reducing overhead for high-volume clinical deployments. |
| **Dynamic Scaling Scenarios (`run_full_simulation`)** | **System Scalability Analysis** | Validates the effectiveness of horizontal scaling strategies in mitigating HIE congestion during high registration periods. |
| **HAPI FHIR Integration (`fhir_server.py`)** | **Interoperability Standards Integration**| Evaluates HIE parser compliance against active public sandbox endpoints (HAPI FHIR R4). |
| **DHIS2 Indicators Query (`dhis2.py`)** | **Public Health Data Aggregation** | Connects clinical transactional operations to secondary national public health indicator aggregation models. |

---

# 14. IMPLEMENTATION VS THEORY ALIGNMENT

This final section discusses how the software implementation aligns with and validates key theoretical concepts in health informatics.

### 14.1 Federated HIE and Interoperability Workflows
- **Theoretical Conception:** A federated Health Information Exchange (HIE) aggregates patient health data on demand from diverse point-of-care clinics, maintaining strict compliance with terminology standards (LOINC, SNOMED CT) and data schemas (HL7 FHIR R4).
- **Code Realization:** The ingestion layer (`dashboard/fhir_parser.py`) accepts standard FHIR Bundle payloads. The code validates these payloads against structural constraints, parses clinical registries, maps standard terminologies through the `get_coding()` function, and persists records using a structured MySQL schema. This implementation demonstrates how to build a high-performance local HIE gateway that bridges point-of-care clinical transactions with central health repositories.

### 14.2 Mathematical Queueing Theory Validation
- **Theoretical Conception:** Centralized server capacities can be modeled using the Erlang-C formula to establish baseline requirements for handling clinic transaction volumes without introducing unacceptable latency.
- **Code Realization:** The application provides a direct empirical test of queuing theory. By running a stochastically driven SimPy discrete-event simulation alongside the analytical Erlang-C solver, the system validates mathematical predictions. The simulation introduces real-world variables like random connectivity dropouts, demonstrating how empirical latencies align with theoretical equations and providing a validated framework for capacity planning in digital health deployments.
