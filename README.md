# AIONOS Executive Productivity Agent

A grounded, defensible, multi-stage agentic system for **Assignment 1 — Executive Productivity Agent** from the AIONOS Agentic AI Factory assessment.

Turns heterogeneous, multi-modal business inputs into a prioritized daily action brief for **Arjun Malhotra, VP Sales (Veridian Corp)** during the exercise week of **21–25 September 2026**.

---

## What It Does

1. **Executive Commitments**: Identifies promises and obligations explicitly made by Arjun (`my_action`).
2. **Action Separation**: Strictly distinguishes **My Actions** (executive-owned) from **Waiting on Others** (counterparty-owned).
3. **Deadlines & Overdue Detection**: Resolves relative phrases to absolute ISO-8601 datetimes and dynamically tracks overdue status as the date advances.
4. **Cross-Source Deduplication**: Reconciles repeated mentions across email threads, meeting transcripts, voice notes, and calendar constraints into 5 canonical commitments.
5. **Ownership Gating**: Preserves explicit ambiguity (`unclear_ownership`) and refuses to invent missing ownership (e.g. the Mumbai office lease renewal).
6. **Timeline Simulation**: Supports simulated dates across the entire exercise week (Sep 21–25, 2026), dynamically updating state machines.
7. **Grounded Q&A**: Answers executive questions (`What did I promise Raghav?`, `What needs action today?`, `Who owns the Mumbai lease?`) with provenance links and audit events.
8. **Audit Trail & Provenance**: Links every conclusion back to source signal IDs with exact quotes and confidence scores.

---

## Pipeline Architecture

The system executes an explicit 8-stage perception-to-action pipeline:

```text
RAW SOURCES (Data Pack)
   │
   ▼
[Stage 1: Ingestion & Normalization]    → 70 NormalizedSignal objects
   │
   ▼
[Stage 2: Signal Extraction]            → 34 CandidateCommitment objects (regex intent detectors + voice segmentation)
   │
   ▼
[Stage 3: Entity & Person Resolution]   → Canonical people directory mapping
   │
   ▼
[Stage 4: Temporal Normalization]       → Relative phrases to absolute ISO datetimes
   │
   ▼
[Stage 5: Cross-Source Reconciliation]  → 5 ReconciledGroup clusters (Jaccard + Containment)
   │
   ▼
[Stage 6: Ownership Classification]     → my_action vs waiting_on_other vs unclear_ownership (don't assume)
   │
   ▼
[Stage 7: Deadline & Status Engine]     → Dynamic status (due_today, overdue, completed, upcoming, ambiguous) + slippage tracking
   │
   ▼
[Stage 8: Prioritization & Scoring]     → Urgency ordering + calibrated confidence scores (0.70–0.99)
   │
   ├───────────────────────────────┐
   ▼                               ▼
Daily Brief API              Grounded Q&A Agent
/api/brief, /api/pipeline-trace  Directional person & temporal router
```

Full architectural specifications, data schemas, and mathematical formulas are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).  
A senior reviewer evaluation defense is provided in [docs/DEFENSIBILITY.md](docs/DEFENSIBILITY.md).

---

## Canonical Commitments Summary (as of Wed 23 Sep 2026)

| Subject | Action Type | Owner | Counterparty | Deadline | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Updated vendor list** | `my_action` | Arjun Malhotra | Raghav Sethi | Wed morning (Sep 23) | `due_today` |
| **Meridian logistics call** | `my_action` | Arjun Malhotra | Priya Nair | Wed 3:00 PM (Sep 23) | `completed` |
| **Q3 campaign deck review** | `waiting_on_other` | Neha Kapoor | Neha Kapoor | Thu 9:30 AM (Sep 24) | `upcoming` |
| **July expense variance report** | `waiting_on_other` | Divya Rao | Divya Rao | Wed evening (Sep 23) | `completed` |
| **Mumbai office lease renewal** | `unclear_ownership` | *Unassigned* | Facilities / Stakeholders | Fri end of day (Sep 25) | `ambiguous` |

---

## Quickstart

### 1. Installation

Python 3.10+ is recommended.

```bash
# Clone or navigate to the repository
cd AIONOS_Executive_Productivity_Agent

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Application

```bash
# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```

Open your browser to: **http://127.0.0.1:8000**

### 3. One-Command Demo

```bash
python run_demo.py
```

---

## API Endpoints

- `GET /api/brief?date=YYYY-MM-DD` — Daily brief with commitments, metrics, and owner breakdown.
- `GET /api/commitments?date=YYYY-MM-DD` — Canonical reconciled commitments.
- `GET /api/pipeline-trace?date=YYYY-MM-DD` — Live pipeline audit log detailing signal counts and stage transitions.
- `GET /api/sources` — Authoritative data pack source registry and people directory.
- `GET /api/audit` — Immutable log of grounded Q&A events and matched commitment IDs.
- `POST /api/query` — Grounded Q&A assistant (`{"question": "What did I promise Raghav?", "as_of": "2026-09-23"}`).
- `GET /api/health` — Service health and architecture metadata.

---


## Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Formal specification of all 8 pipeline stages, dataclass schemas, similarity formulas, and state machines.
- **[docs/DEFENSIBILITY.md](docs/DEFENSIBILITY.md)**: Ruthless senior reviewer defense covering agentic criteria, non-invention of ownership, and grounding guarantees.
- **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)**: 15-minute live demonstration walkthrough and reviewer Q&A preparation.
- **[docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md)**: Grounding constraints and data pack boundaries.
