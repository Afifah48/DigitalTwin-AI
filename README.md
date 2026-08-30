# 🚗 DigitalTwin.AI

### Predict the bottleneck before it forms.

> **An AI-powered automotive manufacturing digital twin that moves factory operations from reactive monitoring to predictive, explainable, and simulation-driven intervention.**

DigitalTwin.AI is an end-to-end cyber-physical decision-support platform for automotive manufacturing. It combines a **discrete-event factory simulation**, **telemetry analytics**, **anomaly detection**, **bottleneck prediction**, **quality-risk estimation**, **explainable AI**, **uncertainty estimation**, **counterfactual simulation**, and **intervention optimization** into a single interactive command center.

Instead of waiting for a production bottleneck to occur, the system continuously analyzes factory behavior, predicts where degradation is heading, explains the contributing factors, evaluates possible interventions in a simulated twin, and recommends an action based on risk, throughput, queue pressure, cost, and operational disruption.

---

## 🎯 The Problem

Modern automotive production lines are highly interconnected.

A small degradation at one station can propagate through buffers and downstream stations, eventually causing:

* Increasing cycle times
* Buffer congestion
* Machine blocking
* Station starvation
* Reduced throughput
* Increased work-in-progress
* Quality exposure
* Bottleneck migration
* Production delays

Traditional factory monitoring is often **reactive**:

```text
Machine degrades
      ↓
Alarm appears
      ↓
Operator investigates
      ↓
Production is already affected
      ↓
Corrective action
```

DigitalTwin.AI changes the workflow to:

```text
Observe
   ↓
Synchronize
   ↓
Detect
   ↓
Predict
   ↓
Explain
   ↓
Simulate
   ↓
Optimize
   ↓
Intervene
```

The objective is simple:

> **Predict the trajectory. Explain the cause. Simulate the consequence. Intervene before the bottleneck arrives.**

---

# 🧠 What is DigitalTwin.AI?

DigitalTwin.AI creates a software representation of an automotive assembly line and combines it with analytical and predictive intelligence.

The digital twin models a sequential production line containing **six stations and finite-capacity buffers**. The simulation captures production flow, cycle times, queues, machine states, downtime, blocking, starvation, and throughput.

On top of this simulation layer, the platform adds multiple intelligence layers:

| Layer                     | Purpose                                  |
| ------------------------- | ---------------------------------------- |
| Digital Twin              | Simulates the manufacturing system       |
| Telemetry Analytics       | Understands current factory behavior     |
| Anomaly Detection         | Detects abnormal machine behavior        |
| Bottleneck Intelligence   | Predicts emerging bottlenecks            |
| Quality Intelligence      | Estimates vehicle quality risk           |
| Explainability            | Explains why a station is becoming risky |
| Uncertainty               | Quantifies prediction variability        |
| Counterfactual Simulation | Tests "what-if" interventions            |
| Optimization              | Selects high-value interventions         |
| Command Center            | Presents decisions to operators          |

---

# 🏭 Factory Digital Twin

The current simulation represents a six-stage automotive assembly line:

```text
                 FINITE-CAPACITY BUFFERS

[IN FLOW]
    │
    ▼
┌──────────────┐
│ S1 FRAMING   │
└──────────────┘
    │ B12
    ▼
┌──────────────┐
│ S2 PAINT     │
└──────────────┘
    │ B23
    ▼
┌────────────────────┐
│ S3 CHASSIS MARRIAGE│
└────────────────────┘
    │ B34
    ▼
┌────────────────────┐
│ S4 POWERTRAIN      │
└────────────────────┘
    │ B45
    ▼
┌────────────────────┐
│ S5 INTERIOR/WIRING │
└────────────────────┘
    │ B56
    ▼
┌────────────────────┐
│ S6 FINAL INSPECTION│
└────────────────────┘
    │
    ▼
 [OUT FLOW]
```

The backend defines five finite-capacity buffers, with the default capacity configured as five vehicles. The simulation naturally models **starvation**, **blocking**, and machine downtime/recovery rather than simply hard-coding a visual state.

---

# 🔧 Production Stations

### S1 — FRAMING

**Robotic Underbody & Side Ring Spot Welding**

* Baseline cycle time: ~52 seconds
* Robotic welding operations
* 64 sensors
* Downstream neighbor: S2

### S2 — PAINT

**Electrocoat, Primer & Clearcoat Robot Cells**

* Baseline cycle time: ~54 seconds
* 88 sensors
* Neighbors: S1, S3

### S3 — CHASSIS MARRIAGE

**Decking & Automated High-Torque Multi-Spindle**

* Baseline cycle time: ~54 seconds
* 112 sensors
* Neighbors: S2, S4
* Used as the default station for several analytical views

### S4 — POWERTRAIN

**High-Voltage Harness & Drive Inverter Assembly**

* Baseline cycle time: ~51 seconds
* 52 sensors
* Neighbors: S3, S5
* Used as the induced bottleneck in the optimizer demonstration

### S5 — INTERIOR & WIRING

**Cockpit Module, Harness Loom & Acoustic Lining**

* Baseline cycle time: ~53 seconds
* 28 sensors
* Neighbors: S4, S6
* Lower instrumentation confidence in parts of the prototype

### S6 — FINAL INSPECTION

**Optical ADAS Calibration, EOL Tester & Roll Bench**

* Baseline cycle time: ~55 seconds
* 96 sensors
* Downstream neighbor: S5

The station metadata, baseline cycle times, sensor counts, tooling, neighbors, and attention weights are defined in the backend factory-state layer.

---

# 🏗️ System Architecture

```text
                         ┌───────────────────────────┐
                         │       React Dashboard     │
                         │                           │
                         │  Factory Visualization    │
                         │  Bottleneck Prediction    │
                         │  Trajectory Analysis      │
                         │  Explainability           │
                         │  Uncertainty              │
                         │  What-If Simulation       │
                         │  Command Center           │
                         └─────────────┬─────────────┘
                                       │
                                  REST API
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │       FastAPI Backend      │
                         └─────────────┬─────────────┘
                                       │
             ┌─────────────────────────┼─────────────────────────┐
             │                         │                         │
             ▼                         ▼                         ▼
     ┌───────────────┐       ┌──────────────────┐      ┌─────────────────┐
     │ Factory State │       │ Analytics / ML    │      │ Decision Layer  │
     └───────┬───────┘       └────────┬─────────┘      └────────┬────────┘
             │                        │                         │
             ▼                        ▼                         ▼
     ┌───────────────┐       ┌──────────────────┐      ┌─────────────────┐
     │ Digital Twin  │       │ Anomaly Detection│      │ Recommendations │
     │ DES Simulator │       │ EWMA / CUSUM     │      │ Root Cause      │
     └───────┬───────┘       │ ML Models        │      │ Impact Analysis │
             │               └────────┬─────────┘      └─────────────────┘
             │                        │
             ▼                        ▼
     ┌──────────────────────────────────────────────────────────────┐
     │              Counterfactual + Optimization Engine            │
     │                                                              │
     │  Intervention → Twin Simulation → Risk/Throughput Evaluation │
     │                  → Multi-objective Ranking                   │
     └──────────────────────────────────────────────────────────────┘
```

---

# 🔄 End-to-End Intelligence Pipeline

## 1. Observe

The system ingests factory telemetry such as:

* Cycle time
* Utilization
* Queue length
* WIP
* Buffer occupancy
* Temperature
* Vibration
* Motor current
* Current variance
* Machine state

The backend loads station telemetry and vehicle-history datasets from Parquet files and maintains the active simulation episode in memory.

---

## 2. Synchronize

The dashboard periodically polls the backend for the latest factory state.

The React `FactorySimulationContext` refreshes factory information every two seconds and updates:

* Stations
* Vehicles
* Factory decision
* Explainability data
* Uncertainty data
* Trajectory data

If the backend is unavailable, the frontend falls back to cached/static factory data.

---

## 3. Detect Anomalies

The analytics layer contains multiple statistical and ML-oriented detection components.

### EWMA

Exponentially Weighted Moving Average is used for gradual drift detection.

Conceptually:

```text
S(t) = αx(t) + (1 - α)S(t-1)
```

This allows the system to identify sustained deviation from a baseline while smoothing noisy sensor measurements.

### CUSUM

CUSUM accumulates small persistent shifts instead of reacting to every individual noisy observation.

It supports:

* Positive shifts
* Negative shifts
* Detection thresholds
* Direction identification

This makes it useful for detecting persistent manufacturing process changes.

### ML-based anomaly models

The repository also contains anomaly-model components including:

* Feature engineering
* Isolation Forest
* LSTM autoencoder
* Anomaly model/service layers

These are organized under the backend anomaly-model subsystem.

---

# 🚨 Bottleneck Prediction

DigitalTwin.AI does not simply identify the station with the largest queue.

The bottleneck subsystem evaluates station behavior and propagation across the production network.

Relevant signals include:

```text
Cycle-time deviation
        +
Queue pressure
        +
Buffer occupancy
        +
Machine state
        +
Persistence
        +
Propagation
        +
Neighbor influence
        ↓
Bottleneck Risk
```

This allows the system to reason about an **emerging bottleneck**, rather than only reporting a bottleneck after production has already degraded.

---

# 🧬 Bottleneck Propagation

A production bottleneck rarely remains isolated.

For example:

```text
S3 degradation
      │
      ▼
B34 begins filling
      │
      ▼
S3 becomes constrained
      │
      ▼
S2 → blocked
      │
      ▼
Upstream congestion
```

At the same time:

```text
S4 slows down
      │
      ▼
B45 fills
      │
      ▼
S5 loses available capacity
      │
      ▼
Downstream starvation/blocking
```

The system therefore considers station relationships and propagation rather than treating each station independently.

---

# 📈 Trajectory Prediction

The `/api/trajectory` endpoint provides a rolling historical trajectory and a forward forecast.

The backend combines:

* Historical telemetry
* Current cycle time
* Station baseline
* Current degradation
* Forecast horizon

The current implementation exposes historical points and forecast points over a roughly **60-minute historical window and 20-minute forward horizon**.

Conceptually:

```text
Cycle Time
   │
   │                         ╭────── Forecast
   │                     ╭───╯
   │                 ╭───╯
   │             ╭───╯
   │        ─────╯
   │  Historical
   │
   └──────────────────────────────────► Time
             NOW        +20 min
```

This is one of the key ideas behind the project:

> **A factory should be managed according to where its trajectory is going, not only where it is now.**

---

# 🔬 Explainable AI

The dashboard contains an explainability workflow through the **"Why?"** interaction.

The backend `/api/explainability` endpoint computes:

* Feature attributions
* Spatial attention
* Station relationships
* Anomaly information
* Bottleneck information
* Change-point-related information

The explainability service receives telemetry, anomaly predictions, bottleneck information, and station relationships before generating the explanation.

Instead of:

```text
"Station S3 is risky."
```

the goal is to provide:

```text
S3 is becoming risky because:

Cycle-time deviation      ██████████
Queue pressure             ████████
Neighbor influence         ██████
Telemetry variance         ████
```

This makes predictions more useful for human operators.

---

# 🎲 Uncertainty Estimation

Predictions without uncertainty can be misleading.

DigitalTwin.AI therefore provides a Monte Carlo uncertainty view.

The backend generates:

* Multiple forward prediction passes
* Mean prediction
* Standard deviation
* Lower 90% prediction band
* Upper 90% prediction band
* Instrumentation confidence

The current uncertainty endpoint performs **50 Monte Carlo forward passes** across forecast horizons of:

```text
0 min
5 min
10 min
14 min
20 min
```

and returns a 90% prediction envelope.

Conceptually:

```text
Cycle Time
   │
   │                  ╭──────── Upper 90%
   │               ╭──╯
   │            ╭───┤
   │         ╭──╯   │
   │      ───┤ Mean │
   │   ╭─────╯      │
   │ ╭─╯             ╰──── Lower 90%
   │
   └──────────────────────────────►
          0   5   10   14   20 min
```

This helps distinguish:

> **"The model predicts degradation."**

from:

> **"The model predicts degradation, and here is how confident we are."**

---

# 🔮 Counterfactual Simulation

One of the core features of the system is the ability to ask:

> **What happens if we intervene?**

The counterfactual simulator creates two configurations:

```text
                 Same Initial Conditions
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        Baseline Twin         Modified Twin
              │                     │
              ▼                     ▼
        Simulation             Simulation
              │                     │
              └──────────┬──────────┘
                         ▼
                  Compare Results
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
    Throughput          Risk             Queue
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                   Intervention
                    Evaluation
```

The counterfactual simulator runs baseline and modified digital-twin simulations with the same seed, then calculates changes in throughput, bottleneck risk, queue length, WIP, affected stations, and confidence.

---

# 🛠️ Available Intervention Types

The optimizer currently evaluates several classes of intervention.

### 1. Cycle-Time Reduction

Reduce the baseline cycle time of a station.

Example:

```text
S4: 75s → 70s
```

### 2. Downtime Reduction

Reduce the failure probability of a station.

### 3. Buffer Expansion

Increase the capacity of a production buffer.

Example:

```text
B45: 5 → 7 vehicles
```

These actions are represented as counterfactual actions and applied to a copied factory configuration before simulation.

---

# 🧮 Multi-Objective Intervention Optimization

The system doesn't simply choose:

> "The intervention with the largest throughput."

Instead, the optimizer combines multiple objectives.

The current scoring framework considers:

```text
Risk Reduction
       +
Throughput Improvement
       +
Queue Reduction
       -
Intervention Cost
       -
Bottleneck Migration / Disruption
```

The optimizer generates feasible candidates, rejects actions exceeding the configured budget, simulates each candidate, scores them, and returns the best intervention plus alternatives.

This makes the recommendation closer to an operational decision:

```text
                    ┌───────────────┐
                    │ Candidate A   │
                    └───────┬───────┘
                            │
                    ┌───────────────┐
                    │ Candidate B   │
                    └───────┬───────┘
                            │
                    ┌───────────────┐
                    │ Candidate C   │
                    └───────┬───────┘
                            │
                            ▼
                   Multi-objective
                      evaluation
                            │
                            ▼
                    ┌───────────────┐
                    │ Best Action   │
                    └───────────────┘
```

---

# 🎯 Scenario Engine

The dashboard presents multiple scenarios:

### Scenario A — No Action

```text
Maintain the current state.
```

This represents the reactive baseline.

### Scenario B — Optimized Intervention

The highest-ranked intervention generated by the optimizer.

### Scenario C — Alternative Option 1

The next-best feasible intervention.

### Scenario D — Alternative Option 2

Another feasible intervention for comparison.

The `/api/scenarios` endpoint runs the optimizer and maps its results into the frontend scenario schema.

---

# 🚦 Decision Intelligence

The project also contains a dedicated decision layer that combines outputs from earlier phases.

The decision subsystem includes components for:

* Evidence aggregation
* Severity
* Root-cause analysis
* Impact analysis
* Recommendations
* Decision auditing
* Phase adapters
* Factory decision service

The backend exposes these decisions as part of the aggregated factory state.

The conceptual decision chain is:

```text
Telemetry
   ↓
Anomaly Detection
   ↓
Bottleneck Risk
   ↓
Quality Risk
   ↓
Root Cause
   ↓
Impact
   ↓
Recommended Action
```

---

# 🚗 Vehicle-Level Intelligence

The digital twin is not limited to station-level metrics.

The backend extracts vehicle-level information including:

* Vehicle ID
* Vehicle model
* Current station
* Progress
* Transit time
* Quality exposure
* Risk score
* Predicted defect probability
* QA routing requirement
* Complete station history

The dashboard includes a **Vehicle Inspector Drawer** for examining individual vehicles.

Example:

```text
Vehicle
   │
   ├── Current Station
   ├── Transit History
   ├── Cycle-Time Deviations
   ├── Quality Risk
   ├── Exposure Level
   └── QA Recommendation
```

This creates a link between:

**factory-level performance → station-level degradation → vehicle-level quality exposure**

---

# 🖥️ Frontend

The frontend is built using:

* React 19
* TypeScript
* Vite
* Tailwind CSS
* Lucide React
* Motion
* Google GenAI package

The project runs the Vite development server on port `3000`.

---

# 🎛️ Dashboard Views

The main React application supports multiple operating modes.

## LIVE FACTORY

Provides the primary factory-line visualization and predictive bottleneck information.

## SYNCHRONIZED

Combines the factory visualization with predictive and trajectory views.

## DIGITAL TWIN

Provides:

* Predictive bottleneck
* Digital twin graph
* Trajectory deviation
* Bottleneck migration

## COMMAND CENTER

Provides the higher-level operational decision interface.

These modes are routed through the main `App.tsx` component.

---

# 🧩 Main UI Components

The repository includes dedicated components for:

* `FactoryLineCanvas`
* `DigitalTwinGraphView`
* `PredictiveBottleneckCard`
* `BottleneckMigrationView`
* `TrajectoryDeviationChart`
* `CommandCenterMatrix`
* `ExplainabilityModal`
* `UncertaintyViewModal`
* `CounterfactualSimulationModal`
* `StationDetailDrawer`
* `VehicleInspectorDrawer`
* `SceneGuidedTourBar`
* `Header`

This keeps the dashboard modular rather than placing the entire interface inside a single component.

---

# 🎬 Guided Story Mode

The application includes a guided-tour concept for presenting the factory story.

Scenes can be:

* Selected
* Advanced
* Reversed
* Automatically played

The automatic tour advances approximately every 12 seconds.

This makes the application suitable not only as an engineering dashboard, but also as a **demo/pitch interface** for communicating the digital-twin workflow.

---

# 🔊 Interactive Soundscape

The frontend also includes an audio utility used for interface feedback.

Interactions such as:

* Clicking
* Selecting stations
* Opening analytical views
* Alerts
* Interventions

can trigger synthesized UI sounds.

Sound can be muted from the application state.

---

# 🔌 API

The backend uses **FastAPI**.

Default backend:

```text
http://localhost:8000
```

Interactive Swagger documentation:

```text
http://localhost:8000/docs
```

---

## API Endpoints

### `GET /api/factory-state`

Returns the aggregated factory state.

```text
GET /api/factory-state
```

Provides information including:

* Stations
* Vehicles
* Decision information
* Explainability
* Uncertainty
* Trajectory data

The frontend polls this endpoint periodically.

---

### `GET /api/explainability`

Returns explainability information for a station.

```text
GET /api/explainability?station_id=S3
```

Used by the dashboard's "Why?" workflow.

---

### `GET /api/uncertainty`

Returns Monte Carlo uncertainty information.

```text
GET /api/uncertainty?station_id=S3
```

Response includes:

```text
station_id
instrumentation_confidence
passes_count
passes
envelope
```

The frontend uses this data to render the uncertainty view.

---

### `GET /api/trajectory`

Returns historical and forecast trajectory information.

```text
GET /api/trajectory?station_id=S3
```

The frontend uses this endpoint for trajectory-deviation analysis.

---

### `GET /api/scenarios`

Runs the intervention optimization pipeline and returns scenario candidates.

```text
GET /api/scenarios
```

The endpoint:

1. Creates a factory configuration
2. Creates an induced S4 bottleneck scenario
3. Configures optimization objectives
4. Runs the optimizer
5. Returns baseline + optimized + alternative scenarios

The current demo configuration uses a 300-unit maximum budget and a 7200-second optimization simulation.

---

# 📊 Example API Workflow

```text
Frontend
   │
   ├── GET /api/factory-state
   │        ↓
   │     Current Factory State
   │
   ├── GET /api/trajectory
   │        ↓
   │     Historical + Forecast
   │
   ├── GET /api/explainability
   │        ↓
   │     Why is this happening?
   │
   ├── GET /api/uncertainty
   │        ↓
   │     How confident are we?
   │
   └── GET /api/scenarios
            ↓
        What should we do?
```

---

# 🐍 Backend Technology

The backend requirements include:

* **SimPy** — discrete-event simulation
* **Pydantic** — data validation/modeling
* **NumPy** — numerical computing
* **Pandas** — data processing
* **scikit-learn** — machine learning
* **Joblib** — model persistence
* **XGBoost** — gradient boosting
* **SHAP** — model explainability
* **PyTorch** — deep-learning models
* **PyArrow** — Parquet/data support
* **Pytest** — testing
* **FastAPI** — REST API
* **Uvicorn** — ASGI server
* **HTTPX** — HTTP testing/client support

These dependencies are specified in `backend/requirements.txt`.

---

# ⚛️ Frontend Technology

The frontend package uses:

* React 19
* React DOM
* TypeScript
* Vite
* Tailwind CSS
* Lucide React
* Motion
* Google GenAI SDK
* Express/Node tooling

The development server is configured to expose Vite on:

```text
0.0.0.0:3000
```

with the project scripts providing `dev`, `build`, `preview`, and TypeScript checking.

---

# 📁 Project Structure

```text
DigitalTwin-AI/
│
├── assets/
│   └── .aistudio/
│
├── backend/
│   │
│   ├── analytics/
│   │   ├── baseline.py
│   │   ├── buffer.py
│   │   ├── confidence.py
│   │   ├── cusum.py
│   │   ├── deviation.py
│   │   ├── ewma.py
│   │   ├── health.py
│   │   └── pipeline.py
│   │
│   ├── app/
│   │   ├── analytics/
│   │   ├── decision/
│   │   ├── explainability/
│   │   ├── models/
│   │   └── schemas/
│   │
│   ├── bottleneck/
│   │   ├── demo.py
│   │   ├── evaluator.py
│   │   ├── models.py
│   │   ├── persistence.py
│   │   ├── pipeline.py
│   │   ├── propagation.py
│   │   ├── ranking.py
│   │   ├── reasoning.py
│   │   └── risk.py
│   │
│   ├── config/
│   │   └── factory_config.py
│   │
│   ├── counterfactual/
│   │   ├── models.py
│   │   └── simulator.py
│   │
│   ├── data/
│   │   └── telemetry / historical datasets
│   │
│   ├── models/
│   │   ├── anomaly/
│   │   ├── decision/
│   │   ├── quality/
│   │   ├── enums.py
│   │   ├── events.py
│   │   └── states.py
│   │
│   ├── optimization/
│   │   ├── models.py
│   │   └── optimizer.py
│   │
│   ├── quality/
│   │   ├── calibration.py
│   │   ├── evaluator.py
│   │   ├── explain.py
│   │   ├── features.py
│   │   ├── models.py
│   │   ├── risk.py
│   │   ├── service.py
│   │   ├── temporal.py
│   │   └── training.py
│   │
│   ├── scenarios/
│   │   ├── base.py
│   │   ├── buffer_pressure.py
│   │   ├── capacity_loss.py
│   │   ├── composite.py
│   │   ├── degradation.py
│   │   ├── failure.py
│   │   ├── migration.py
│   │   ├── normal.py
│   │   ├── quality.py
│   │   ├── registry.py
│   │   ├── sensor.py
│   │   └── surge.py
│   │
│   ├── simulation/
│   │   ├── buffer.py
│   │   ├── engine.py
│   │   ├── station.py
│   │   └── vehicle_generator.py
│   │
│   ├── training/
│   │
│   ├── twin/
│   │   └── digital_twin.py
│   │
│   ├── api.py
│   ├── factory_state.py
│   ├── cli.py
│   ├── requirements.txt
│   └── tests/
│
├── docs/
│   └── episode_trajectories.png
│
├── src/
│   ├── components/
│   ├── context/
│   ├── data/
│   ├── services/
│   ├── types/
│   ├── utils/
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
│
├── .env.example
├── index.html
├── metadata.json
├── package.json
├── tsconfig.json
└── vite.config.ts
```

The repository currently contains separate frontend and backend concerns, with the backend itself split into simulation, analytics, bottleneck, quality, counterfactual, optimization, and decision subsystems.

---

# 🚀 Getting Started

## Prerequisites

Recommended environment:

```text
Python 3.10+
Node.js
npm
```

---

# 1. Clone the Repository

```bash
git clone https://github.com/Afifah48/DigitalTwin-AI.git
cd DigitalTwin-AI
```

---

# 2. Backend Setup

Create a Python virtual environment:

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

---

# 3. Start the FastAPI Backend

From the repository root:

```bash
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

---

# 4. Start the Frontend

Install Node dependencies:

```bash
npm install
```

Start Vite:

```bash
npm run dev
```

The application is configured to run on:

```text
http://localhost:3000
```

The frontend API service currently points to:

```text
http://localhost:8000
```

so the backend should be running before using dynamic dashboard features.

---

# 🧪 Running Tests

The backend includes unit tests covering areas such as:

* Normal production
* Blocking/starvation
* Downtime recovery
* Throughput metrics

The backend documentation specifies running tests with:

```bash
python -m pytest backend/tests -v
```

---

# 🧪 Running the Digital Twin Directly

The core digital twin exposes a simple API:

```python
from backend.twin.digital_twin import DigitalTwin

twin = DigitalTwin(seed=42)

state = twin.simulate(3600)

print(state)
```

The twin also supports:

```python
twin.reset()
twin.step_until(...)
twin.get_state()
twin.get_events()
twin.get_telemetry_snapshot()
```

and can export its event log to JSON or CSV.

---

# 📦 Event Logging

The digital twin records discrete events containing information such as:

```text
timestamp
event_type
station_id
buffer_id
vehicle_id
cycle_time
machine_state
queue_before
queue_after
buffer_before
buffer_after
```

These events can be exported for downstream analytics and ML dataset generation.

---

# 📊 Data Layer

The backend currently works with Parquet datasets including:

```text
station_telemetry.parquet
phase4_phase5_integration.parquet
vehicle_station_history.parquet
vehicle_quality.parquet
```

These datasets provide the telemetry, station-history, integration, and quality information used by the factory-state layer.

---

# 🔬 Prototype / Demo Scope

DigitalTwin.AI is currently a **research/demo prototype** rather than a production factory-control system.

The current repository uses simulated and prepared datasets to demonstrate the architecture and decision workflow.

Important prototype characteristics include:

* A controlled simulation environment
* A prepared active episode (`EP_0001`)
* Synthetic/simulated factory trajectories
* Demonstration bottleneck conditions
* Prepared quality-risk predictions
* Cached frontend fallback data
* Demo-specific optimization configuration

The repository explicitly describes the dashboard as simulated data / a concept prototype for a hackathon pitch.

---

# ⚠️ Current Implementation Notes

A few details are important for anyone extending the project.

### 1. Local API dependency

The frontend currently uses:

```text
http://localhost:8000
```

as its API base URL.

For deployment, this should be moved into an environment variable.

---

### 2. Development CORS

The FastAPI backend currently allows all origins:

```python
allow_origins=["*"]
```

This is convenient for development/hackathon usage but should be restricted for production deployment.

---

### 3. Demo-specific bottleneck

The scenario API deliberately modifies S4's baseline cycle time to create the demonstration bottleneck:

```text
S4 baseline cycle time = 75 seconds
```

This is intentional for the scenario/optimization demo rather than representing a universal factory configuration.

---

### 4. Counterfactual confidence

The scenario mapping currently exposes a fixed confidence value for some UI fields because the counterfactual result itself does not provide the same uncertainty representation as the dedicated uncertainty endpoint.

Therefore, the scenario confidence displayed by the frontend should not be interpreted as a statistically calibrated confidence interval.

---

# 🛡️ Safety & Deployment Considerations

Before deploying this system against real manufacturing infrastructure:

* Replace wildcard CORS
* Add authentication/authorization
* Validate all API inputs
* Move API URLs to environment configuration
* Protect operational telemetry
* Add audit logging
* Add model versioning
* Add proper uncertainty calibration
* Validate recommendations against real operational constraints
* Add human approval before physical intervention
* Separate simulation commands from real actuator commands
* Add monitoring and rollback mechanisms

The current project should be treated as a **decision-support prototype**, not an autonomous production-control system.

---

# 🔮 Future Roadmap

## Phase 1 — Real-Time Industrial Connectivity

Connect the digital twin to:

* OPC-UA
* MQTT
* PLC telemetry
* MES
* SCADA
* Industrial IoT sensors

---

## Phase 2 — Real-Time Digital Twin Synchronization

Replace prepared episode data with continuously synchronized factory state.

```text
Physical Factory
      ⇅
Industrial Data Layer
      ⇅
Digital Twin
```

---

## Phase 3 — Advanced Predictive Models

Improve:

* Remaining useful life prediction
* Time-to-bottleneck prediction
* Failure prediction
* Quality prediction
* Sequence forecasting

---

## Phase 4 — Calibrated Uncertainty

Introduce:

* Conformal prediction
* Bayesian models
* Deep ensembles
* Probabilistic forecasting

to provide better-calibrated prediction intervals.

---

## Phase 5 — Automated Root Cause Analysis

Build causal graphs connecting:

```text
Sensor
  ↓
Machine
  ↓
Station
  ↓
Buffer
  ↓
Downstream Station
  ↓
Vehicle
  ↓
Quality
```

---

## Phase 6 — Advanced Optimization

Extend the intervention optimizer to include:

* Workforce allocation
* Maintenance scheduling
* Production sequencing
* Buffer sizing
* Tool replacement
* Shift planning
* Multi-line optimization

---

## Phase 7 — Human-in-the-Loop Operations

Introduce explicit operator approval:

```text
AI Recommendation
       ↓
Impact Simulation
       ↓
Operator Review
       ↓
Approve / Reject
       ↓
Controlled Execution
```

---

# 💡 Why This Architecture Matters

Most manufacturing AI systems focus on a single prediction:

> "Will this machine fail?"

DigitalTwin.AI attempts to close the complete operational loop:

```text
             ┌──────────────┐
             │    OBSERVE   │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │ SYNCHRONIZE  │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │   PREDICT    │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │   EXPLAIN    │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │   SIMULATE   │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │   OPTIMIZE   │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │  INTERVENE   │
             └──────┬───────┘
                    │
                    └───────────────┐
                                    ▼
                              Observe Again
```

This creates a closed-loop **predictive operations architecture** rather than an isolated ML model.

---

# 🏆 Key Differentiators

### 🔮 Predictive rather than reactive

The system focuses on the future trajectory of the production line.

### 🧠 Explainable

Predictions are accompanied by feature/station-level explanations.

### 🎲 Uncertainty-aware

Monte Carlo simulations provide prediction envelopes rather than only point estimates.

### 🧪 What-if capable

Operators can test possible interventions inside the digital twin before acting.

### ⚙️ Optimization-driven

Interventions are ranked according to multiple operational objectives.

### 🔗 System-level reasoning

The system considers station interactions, queues, buffers, bottleneck migration, and downstream effects.

### 🚗 Vehicle-level visibility

Factory-level issues can be traced down to individual vehicle histories and quality exposure.

### 🖥️ Interactive command center

The frontend combines simulation, analytics, explanation, uncertainty, and intervention into one operational interface.

---

# 📚 Technology Stack

| Area            | Technology                       |
| --------------- | -------------------------------- |
| Frontend        | React                            |
| Language        | TypeScript                       |
| Build Tool      | Vite                             |
| Styling         | Tailwind CSS                     |
| UI Icons        | Lucide React                     |
| Animation       | Motion                           |
| Backend         | Python                           |
| API             | FastAPI                          |
| Server          | Uvicorn                          |
| Simulation      | SimPy                            |
| Data Processing | Pandas / NumPy                   |
| ML              | scikit-learn / XGBoost / PyTorch |
| Explainability  | SHAP                             |
| Data Format     | Apache Parquet                   |
| Validation      | Pydantic                         |
| Testing         | Pytest                           |
| Communication   | REST API                         |

The package manifests and backend requirements define the current dependency stack.

---

# 📜 License

Add your preferred open-source license here.

For example:

```text
MIT License
```

if the repository is intended to be released under MIT.

---

# 🤝 Contributing

Contributions are welcome.

A typical contribution workflow:

```bash
git checkout -b feature/your-feature
```

Make your changes, test them, and then open a pull request.

Suggested areas for contribution:

* Improved bottleneck models
* New anomaly detectors
* Better uncertainty calibration
* Additional factory scenarios
* Advanced optimization strategies
* Real industrial data adapters
* Visualization improvements
* API improvements
* Testing and benchmarking

---

# 👥 Team

**DigitalTwin.AI**

Built as an end-to-end predictive manufacturing intelligence prototype.

---

# ⭐ Project Vision

> **Factories should not wait for bottlenecks to happen. They should see them coming.**

DigitalTwin.AI aims to provide the intelligence layer between raw industrial telemetry and operational decisions:

```text
RAW DATA
   ↓
UNDERSTANDING
   ↓
PREDICTION
   ↓
EXPLANATION
   ↓
SIMULATION
   ↓
OPTIMIZATION
   ↓
DECISION
```

The ultimate goal is a manufacturing environment where operators can ask:

> **"What is going to happen?"**

> **"Why is it happening?"**

> **"What happens if we do nothing?"**

> **"What happens if we intervene?"**

> **"Which intervention gives us the best outcome?"**

—and receive those answers before the bottleneck reaches the production line.

---

## 🚀 Quick Reference

### Start Backend

```bash
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend

```bash
npm install
npm run dev
```

### Frontend

```text
http://localhost:3000
```

### Backend

```text
http://localhost:8000
```

### Swagger API

```text
http://localhost:8000/docs
```

### Main APIs

```text
GET /api/factory-state
GET /api/explainability?station_id=S3
GET /api/uncertainty?station_id=S3
GET /api/trajectory?station_id=S3
GET /api/scenarios
```

---

### Built around one idea:

# **Predict the bottleneck before it forms. 🚗⚙️🧠**
