# Automotive Production Digital Twin - Backend (Phase 1)

Deterministic Discrete-Event Simulation (DES) core for automotive manufacturing line digital twin.

## Overview

The simulation core models a 6-station sequential automotive assembly line with 5 finite-capacity buffers:

```
[ Inflow ] -> [ S1 ] -> (B12) -> [ S2 ] -> (B23) -> [ S3 ] -> (B34) -> [ S4 ] -> (B45) -> [ S5 ] -> (B56) -> [ S6 ] -> [ Outflow ]
```

### Stations
1. **S1 (FRAMING)**: Robotic Underbody & Side Ring Spot Welding (Nominal ~52.0s)
2. **S2 (PAINT)**: Electrocoat, Primer & Clearcoat Robot Cells (Nominal ~54.0s)
3. **S3 (CHASSIS MARRIAGE)**: Decking & Automated Multi-Spindle (Nominal ~54.0s)
4. **S4 (POWERTRAIN)**: High-Voltage Harness & Drive Inverter Assembly (Nominal ~51.0s)
5. **S5 (INTERIOR & WIRING)**: Cockpit Module, Harness Loom & Acoustic Lining (Nominal ~53.0s)
6. **S6 (FINAL INSPECTION)**: Optical ADAS Calibration, EOL Tester & Roll Bench (Nominal ~55.0s)

### Buffers
- **B12, B23, B34, B45, B56**: Finite capacity (default: 5 vehicles).

### Natural Flow Dynamics (No Hardcoded Conditionals)
- **Starvation**: When an upstream buffer is empty, the downstream station transitions to `STARVED`.
- **Blocking**: When a downstream buffer reaches capacity (e.g. 5 vehicles), the upstream station transitions to `BLOCKED` until a slot is freed.
- **Machine Downtime & Recovery**: Supports failure probability and repair time distributions, transitioning machines through `DOWN` / `MAINTENANCE` states.

---

## Directory Structure

```
backend/
├── config/
│   ├── __init__.py
│   └── factory_config.py          # Baseline takt time, station parameters, sensor configs
├── models/
│   ├── __init__.py
│   ├── enums.py                   # StationId, BufferId, MachineState, EventType
│   ├── states.py                  # FactoryState, StationState, BufferState, VehicleState, TelemetryState
│   └── events.py                  # FactoryEvent with full queue/buffer context
├── simulation/
│   ├── __init__.py
│   ├── buffer.py                  # SimPy bounded buffer
│   ├── station.py                 # Discrete-event station with push/pull & downtime
│   ├── vehicle_generator.py       # Takt-time feeder
│   └── engine.py                  # Simulation orchestrator
├── twin/
│   ├── __init__.py
│   └── digital_twin.py            # High-level DigitalTwin / FactorySimulator API
├── tests/
│   ├── __init__.py
│   ├── test_normal_production.py
│   ├── test_blocking_starvation.py
│   ├── test_downtime_recovery.py
│   └── test_throughput_metrics.py
├── cli.py                         # 60-minute CLI demo runner
└── requirements.txt
```

---

## Installation & Setup

```bash
cd backend
pip install -r requirements.txt
```

---

## Running the Unit Tests

```bash
python -m pytest backend/tests -v
```

---

## Running the CLI Demo

Run 60 simulated minutes:
```bash
python -m backend.cli --duration 60
```

Export event log to CSV / JSON:
```bash
python -m backend.cli --duration 60 --export-csv --export-json
```
