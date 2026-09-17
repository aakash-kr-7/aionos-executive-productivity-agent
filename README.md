# AIONOS Executive Productivity Agent

A polished, locally runnable prototype for **Assignment 1 — Executive Productivity Agent** from the AIONOS Agentic AI Factory assessment.

## What it does

The agent turns the supplied messy executive inputs into a grounded daily action brief for **Arjun Malhotra, VP Sales**.

It:

- extracts commitments made by Arjun
- separates **My Actions** from **Waiting on Others**
- detects deadlines, overdue items, and stale commitments
- reconciles/deduplicates repeated actions across meeting notes, email, calendar and voice notes
- flags unclear ownership without inventing an owner
- understands the supplied Sep 21–25, 2026 timeline
- answers grounded questions such as `What did I promise Raghav?`
- exposes source evidence for every conclusion
- keeps an audit trail of extraction, reconciliation, and answer generation
- provides deterministic fallbacks so the demo works with **no API keys**

## Source boundary

The implementation uses only the supplied Assignment 1 Data Pack as business source data. The data pack explicitly says not to invent information outside those sources. System-generated IDs, timestamps, scores, UI labels and processing metadata are not business facts and are labelled as system metadata where relevant.

## Architecture

```text
                 SUPPLIED DATA PACK
       ┌──────────────┬──────────────┐
       │ transcript   │ calendars    │
       │ emails       │ voice notes  │
       └──────┬───────┴───────┬──────┘
              │ normalize      │
              ▼                ▼
       Source Registry → Evidence Store
              │
              ▼
      Commitment Extraction Engine
              │
              ▼
       Reconciliation / Dedup
              │
       ┌──────┴──────────┐
       │                 │
       ▼                 ▼
  Ownership Gate    Deadline Engine
       │                 │
       └──────┬──────────┘
              ▼
        Action Brief API
              │
       ┌──────┴──────────────┐
       ▼                     ▼
   Q&A / Retrieval       Audit Trail
       │                     │
       └──────────┬──────────┘
                  ▼
             Web Dashboard
```

## Run

Python 3.10+ recommended.

```bash
cd aionos_exec_agent
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

### One-command demo

```bash
python run_demo.py
```

This starts the API and opens the browser where supported.

## API

- `GET /api/brief?date=2026-09-23` — daily brief
- `GET /api/commitments` — reconciled commitments
- `GET /api/sources` — normalized source registry
- `GET /api/audit` — audit events
- `POST /api/query` — grounded Q&A
- `GET /api/health` — health check

## Grounding behavior

Every commitment has evidence references. Q&A responses are generated from the canonical commitment/evidence graph rather than free-form invention. If ownership is unresolved, the system says so. If the supplied sources conflict or are insufficient, the answer explicitly reports the ambiguity.

## AI layer

The core prototype is deterministic so it is reliable in a six-hour assessment environment. `app/agent.py` contains the agent orchestration boundary. An optional LLM adapter can be added behind the same interface for classification/paraphrase, while the source-of-truth reconciliation and safety gates remain deterministic.

## Tests

```bash
pytest -q
```

## Demo script

See `docs/DEMO_SCRIPT.md` for a 15-minute walkthrough and defence questions.
