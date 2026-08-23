# Predicting Bottleneck Propagation in Vehicle Assembly Lines

> **From detecting bottlenecks to predicting where, when, and how the next bottleneck will emerge.**

A predictive AI system for vehicle assembly lines that combines a **Discrete Event Simulation (DES) Digital Twin**, **Graph Attention Networks (GATv2)**, and a **Temporal Transformer** to forecast bottleneck propagation before it becomes visible on the physical production line.

## 🌐 Project Website

**Live Demo / Website:** [ADD YOUR WEBSITE LINK HERE]

---

## 👥 Team

| Member           | Institution | Stream                                | Graduation |
| ---------------- | ----------- | ------------------------------------- | ---------- |
| Afifah Khan      | IIT Patna   | Electrical & Communication            | 2028       |
| Sanskruti Shetti | IIT Patna   | Metallurgical & Materials Engineering | 2027       |

---

## 🚨 Problem Statement

A vehicle assembly line is a coupled system where multiple stations interact through finite-capacity buffers.

Each station continuously produces signals such as:

* Cycle time
* Utilization
* Arrival/departure rate
* Queue and WIP
* Buffer occupancy
* Machine health
* Downtime
* Vehicle history

When a station loses capacity, its processing rate falls below incoming flow. This causes:

```text
Capacity Loss
     ↓
Queue / WIP Growth
     ↓
Upstream Blocking
```

At the same time:

```text
Capacity Loss
     ↓
Reduced Departures
     ↓
Downstream Starvation
```

The bottleneck can also **shift dynamically** as the state of the production line changes.

Therefore, simply detecting the current bottleneck is not enough.

### The real question is:

> **Which station will become the next bottleneck, when will it happen, how severe will it be, and how much throughput will it impact?**

Our system is designed to answer these questions **before the bottleneck becomes visible**.

---

# 💡 Proposed Solution

We create a **digital representation of the physical production line** and continuously synchronize it with available production signals.

The system follows five major stages:

```text
Physical Production Line
          ↓
     Sparse Sensing
          ↓
      Digital Twin
          ↓
   Deviation Detection
          ↓
 GATv2 + Temporal Transformer
          ↓
 Bottleneck Prediction
          ↓
Counterfactual Simulation
          ↓
 Recommended Intervention
```

---

# 🏭 1. Physical Line → Digital Twin

The production line is represented as a **6-station directed graph** with finite-capacity buffers.

The Digital Twin synchronizes:

* Stations
* Vehicles
* Buffers
* WIP states
* Machine states

A **60-minute rolling state** is maintained using signals such as:

* Cycle time
* Utilization
* Flow
* Queue/WIP
* Buffer occupancy
* Machine state
* Downtime
* Health signals
* Vehicle history

---

# 📡 2. Sparse Sensing & State Estimation

Real-world production environments may contain:

* Missing sensor readings
* Incomplete machine signals
* Unreliable measurements

Instead of assuming perfect data, the system incorporates:

* State estimation
* Missingness masks
* Confidence scores

This allows the model to explicitly understand **how much information is actually available**.

---

# 🧠 3. Learn Deviation from Normal Behavior

The Digital Twin forward-simulates the expected production trajectory.

For each station:

```text
Deviation δᵢ(t)
=
Observedᵢ(t) − Expectedᵢ(t)
```

This deviation provides an early indicator of capacity degradation.

Rather than waiting until a station becomes an obvious bottleneck, the system looks for **deviations from expected behavior** that indicate an emerging constraint.

---

# 🤖 4. AI Prediction Engine

The prediction system combines two complementary models.

## GATv2 — Spatial Dependencies

The assembly line is represented as a graph where stations influence neighboring stations.

**GATv2 learns:**

* Inter-station dependencies
* Blocking propagation
* Starvation propagation
* Buffer interactions

This allows the model to understand **where disturbances propagate**.

## Temporal Transformer — Time Dependencies

The Temporal Transformer analyzes the historical evolution of the production line.

```text
60-minute history
        ↓
Temporal Transformer
        ↓
20-minute forecast
```

It learns how previous degradation patterns can lead to future bottlenecks.

### Combined Architecture

```text
                    Production State
                           │
                           ▼
                    Digital Twin
                           │
                  ┌────────┴────────┐
                  │                 │
              Graph State       Time Series
                  │                 │
                  ▼                 ▼
                GATv2       Temporal Transformer
                  │                 │
                  └────────┬────────┘
                           ▼
                    Multi-Task Head
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
     Bottleneck        Time-to-         Severity
     Probability       Bottleneck
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                 Queue / WIP / Throughput
                           │
                           ▼
                    Quality / Defect Risk
```

---

# 🎯 5. Multi-Task Prediction

The model does not produce a single binary bottleneck prediction.

It simultaneously predicts:

| Output                 | Purpose                                       |
| ---------------------- | --------------------------------------------- |
| Bottleneck probability | Likelihood of a station becoming a bottleneck |
| Severity               | Expected impact of the bottleneck             |
| Time-to-bottleneck     | How soon the bottleneck will occur            |
| Queue / WIP            | Expected accumulation                         |
| Throughput             | Expected production impact                    |
| Defect risk × vehicle  | Potential quality impact                      |

### Example Prediction

```text
Station: S3
Bottleneck Probability: 87%
Time-to-Bottleneck: 14 min
```

---

# 🔍 Explainability

The system also explains **why a station is predicted to become a bottleneck**.

Example:

```text
WHY S3?

Cycle-time deviation    → 31%
Queue growth            → 25%
Upstream pressure       → 18%
Machine health          → 15%
Neighbor state          → 11%
```

This makes the prediction more actionable for production engineers instead of treating the AI as a black box.

---

# 🌊 Bottleneck Propagation

The system explicitly models how a local degradation can propagate through the production line.

Example:

```text
S2
 │
 ▼
S3  ← Emerging Bottleneck
 │
 ▼
S4
```

Possible propagation:

```text
S2 BLOCKED
     ↓
    S3
     ↓
S4 STARVED
```

This allows the system to reason about the **system-wide consequences** of a local capacity degradation.

---

# 📊 Uncertainty Estimation

Predictions should not be treated as equally reliable, especially when sensor information is incomplete.

We use **Monte Carlo Dropout × 50** to estimate the prediction distribution and confidence.

```text
Prediction
     +
Uncertainty
     +
Sensor Availability
     ↓
Confidence Score
```

The system therefore recognizes that **uncertainty increases under sparse sensing**.

---

# 🔮 Counterfactual Simulation

Prediction alone is not enough.

Once a potential bottleneck is identified, the Digital Twin can test possible interventions before applying them to the real production line.

### Possible interventions

* No action
* Maintenance
* Resource reallocation
* Resequencing

Each intervention is simulated and compared using metrics such as:

```text
Throughput ↑
WIP ↓
Bottleneck Risk ↓
Quality Risk ↓
```

---

# 🛠️ Recommended Action

The system can recommend the intervention that produces the best simulated outcome.

### Example

```text
Predicted Bottleneck → S3

Recommended Action:
ADD OPERATOR → S3

Reason:
Best simulated production outcome
```

This transforms the system from a **prediction tool** into a **decision-support system**.

---

# 🧩 Complete System Pipeline

```text
┌─────────────────────────────┐
│     Physical Assembly Line  │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│       Sparse Sensor Data    │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│      State Estimation       │
│   + Missingness Mask        │
│   + Confidence Score        │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│        Digital Twin         │
│            DES              │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│    Observed vs Expected     │
│       Deviation δ(t)        │
└──────────────┬──────────────┘
               ↓
      ┌────────┴────────┐
      ↓                 ↓
┌───────────┐    ┌────────────────┐
│   GATv2   │    │    Temporal    │
│           │    │   Transformer  │
└─────┬─────┘    └───────┬────────┘
      └──────────┬───────┘
                 ↓
┌─────────────────────────────┐
│      Multi-Task Prediction  │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ Bottleneck • Severity       │
│ Time • WIP • Throughput     │
│ Quality Risk                │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ Counterfactual Simulation   │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│   Recommended Intervention  │
└─────────────────────────────┘
```

---

# 🚀 Key Innovation

Traditional manufacturing monitoring primarily focuses on:

> **"Where is the bottleneck right now?"**

Our approach focuses on:

> **"Where will the bottleneck emerge next, when will it happen, how severe will it be, and what should we do about it?"**

The key idea is to combine:

**Digital Twin + Graph AI + Temporal Forecasting + Uncertainty + Counterfactual Simulation**

to move from **reactive monitoring** toward **proactive production optimization**.

---

# 📈 Example End-to-End Scenario

Suppose station **S3** begins experiencing subtle cycle-time degradation.

The bottleneck is not yet visible.

```text
S3 Cycle Time ↑
      ↓
Deviation from Digital Twin ↑
      ↓
GATv2 detects increasing upstream pressure
      ↓
Temporal Transformer detects degradation trend
      ↓
Bottleneck Probability = 87%
      ↓
Time-to-Bottleneck = 14 min
      ↓
Counterfactual simulations
      ↓
"Add Operator → S3"
      ↓
Lower predicted WIP
Higher predicted throughput
Lower bottleneck risk
```

The intervention can therefore be evaluated **before the constraint becomes operationally severe**.

---

# 🌐 Demo

Explore the complete system through our website:

**[ADD WEBSITE URL]**

The website provides an interactive view of the proposed bottleneck prediction and intervention pipeline.

---

# 🎥 Demo Video

[ADD YOUR VIDEO / DEMO LINK HERE]

---

# 🧰 Technology Stack

### AI / Machine Learning

* GATv2
* Temporal Transformer
* Multi-task learning
* Monte Carlo Dropout

### Simulation

* Discrete Event Simulation (DES)
* Digital Twin
* Counterfactual Simulation

### Data

* Cycle time
* Utilization
* Flow
* Queue / WIP
* Buffer occupancy
* Machine health
* Downtime
* Vehicle history

---

# 📌 Project Status

🚧 **Prototype / Research Project**

The current system demonstrates the proposed architecture for proactive bottleneck prediction, uncertainty estimation, and intervention planning in assembly-line environments.

---

# 👩‍💻 Team

**Afifah Khan**
IIT Patna

**Sanskruti Shetti**
IIT Patna

---

## ⭐ Why This Matters

A production line should not have to **wait for a bottleneck to become visible** before taking action.

Our goal is to give manufacturing systems the ability to:

**Observe → Understand → Predict → Simulate → Act**

before production losses occur.
