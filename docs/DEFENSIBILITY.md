# AIONOS Agentic AI Factory — Architecture Defensibility Document

**Assignment 1**: Executive Productivity Agent  
**Candidate Evaluation**: Senior Reviewer Defense  
**Executive Context**: Arjun Malhotra, VP Sales (Veridian Corp)  
**Timeline**: Exercise Week: 21–25 September 2026  

---

## 1. Executive Summary: Why This Is an Agent, Not a CRUD Dashboard

A CRUD dashboard with NLP simply receives unstructured text, passes it to an API or database, and performs keyword lookups or uncontrolled LLM completions. Such systems fail in executive contexts because they:
1. Hallucinate missing facts (e.g. inventing an owner for an unassigned lease).
2. Conflate mentions across sources into duplicate tasks.
3. Fail to track deadline revisions when discussions slip across multiple days.
4. Cannot separate what the executive owes from what the executive is waiting on.

This codebase implements an **agentic perception-to-action pipeline**:

```text
RAW SIGNALS → EXTRACT → RESOLVE → TEMPORAL → RECONCILE → CLASSIFY → STATUS ENGINE → PRIORITIZE
```

### Key Agentic Properties
1. **Multi-Source Corroboration**: Combines 4 distinct modalities (leadership sync meeting transcript, 5 email threads, 2 personal voice memos, and calendar events) into 5 canonical commitments.
2. **Dynamic World-State Modeling**: Evaluates commitment status relative to any `as_of` simulation date. On Wednesday, the vendor list is `due_today`; on Thursday, it dynamically transitions to `overdue`.
3. **Epistemic Humility (Ambiguity Preservation)**: Explicitly detects when ownership is unassigned and refuses to invent an owner.
4. **Causal Slippage Tracking**: Maintains an immutable revision history for each commitment, explaining *why* and *when* deadlines shifted.
5. **Grounded Bounded Q&A**: Answers executive questions with strict provenance citing signal IDs, excerpts, and audit events.

---

## 2. Core Requirements Compliance Matrix

| Requirement | Implementation in Pipeline | Code Location | Verification Test |
| :--- | :--- | :--- | :--- |
| **1. Identify executive commitments** | First-person promise extractors (`will send`, `I told X I'd`, `I need to reconfirm`) identify actions Arjun explicitly committed to. | `app/pipeline/extract.py` | `test_stage2_signal_types_extracted` |
| **2. Separate 'my actions' from 'waiting on others'** | Ownership classifier checks speaker roles: Arjun's promises &rarr; `my_action`; counterparties' promises &rarr; `waiting_on_other`. | `app/pipeline/classify.py` | `test_stage6_ownership_classification_and_refusal` |
| **3. Detect deadlines & overdue items** | Resolves relative phrases to absolute datetimes; dynamic status engine flags items where `as_of > deadline`. | `app/pipeline/temporal.py`<br>`app/pipeline/status.py` | `test_stage7_dynamic_status_across_week` |
| **4. Deduplicate across sources** | Clusters email threads, voice notes, and meeting turns using Jaccard token overlap + counterparty similarity. | `app/pipeline/reconcile.py` | `test_stage5_reconciliation_exact_groups` |
| **5. Flag unclear ownership** | Detects uncertainty patterns (`not sure whose desk`, `don't assume`, `still unowned`); preserves `owner = None`. | `app/pipeline/classify.py` | `test_lease_never_invents_owner` |
| **6. Produce a useful daily brief** | Urgency-ranked action queue with calibrated confidence, metrics ribbon, and filterable views. | `app/pipeline/prioritize.py`<br>`app/main.py` | `test_brief_as_of_wednesday` |
| **7. Allow grounded questions** | Intent-routed Q&A agent supporting person queries, temporal queries, status filters, and topic matching. | `app/agent.py` | `test_query_raghav_promise`<br>`test_query_today_actions` |

---

## 3. Deep Dive: Non-Invention of Ownership (The Mumbai Lease)

### The Problem
In standard LLM or naive NLP solutions, when prompted with "Who owns the Mumbai lease?", models routinely guess "Facilities" or "Divya Rao" because Facilities sent reminders and Divya commented on it.

### Ground Truth in Data Pack
1. **Email 1** (Facilities &rarr; All Staff): Automated broadcast notification that signature is required.
2. **Meeting turn 3** (Raghav): *"The Mumbai office renewal paperwork needs someone to sign off this week. Not sure whose desk that's on right now."*
3. **Meeting turn 4** (Divya): *"I think that's supposed to be Facilities, but I haven't seen anyone pick it up."*
4. **Meeting turn 5** (Arjun): *"Okay, flag it, don't assume."*
5. **Voice Note 1** (Arjun): *"Also still haven't heard back on the Mumbai lease thing, someone needs to own that, I don't think it's me."*
6. **Email 2** (Raghav): *"Don't think it's been assigned."*
7. **Email 3** (Divya): *"Not on my end — I believe this typically sits with Facilities directly, not us."*
8. **Email 4** (Raghav): *"This is now one day out and still unowned — can you confirm who's handling it?"*

### Pipeline Resolution
`classify_ownership` in `app/pipeline/classify.py`:
```python
if has_ambiguity and not named_promisors and counts['user_promises'] == 0:
    action_type = 'unclear_ownership'
    owner_email = None
    owner_display = None
    counterparty = 'Facilities / internal stakeholders'
    rationale.append('Multiple sources explicitly state ownership is unassigned.')
    rationale.append('Arjun directed "don\'t assume" — ownership intentionally left unresolved.')
```
The output model produces:
- `owner`: `None`
- `owner_display`: `None`
- `status`: `'ambiguous'`
- `action_type`: `'unclear_ownership'`
- Response to *"Who owns the Mumbai lease?"*:
  > "Ownership is intentionally not assigned: the source material says the item is unowned and the executive explicitly said not to assume."

---

## 4. Deep Dive: Dynamic Temporal Reasoning & Slippage Tracking

The system tracks commitments across the 5 days of the exercise week (`2026-09-21` to `2026-09-25`).

### Case Study: Updated Vendor List
1. **Mon 21 Sep 09:00** (Meeting): Arjun promises: *"I'll get that to him by end of day tomorrow"* &rarr; Deadline: `2026-09-22T17:00`.
2. **Mon 21 Sep 17:40** (Email): Arjun emails Raghav: *"Running behind, will send first thing tomorrow morning instead"* &rarr; Deadline: `2026-09-22T09:00`.
3. **Tue 22 Sep 18:30** (Email): Arjun emails Raghav: *"got pulled into board prep — will send by tomorrow (Wednesday) morning for sure"* &rarr; Deadline: `2026-09-23T09:00`.
4. **Wed 23 Sep 08:45** (Email): Raghav follows up: *"Just checking — still good for this morning?"* (Arjun has not delivered).

### Observed System Behavior by `as_of` Date
- **As of Sep 21**: Status = `upcoming` (Target: Tuesday).
- **As of Sep 22**: Status = `upcoming` (Target: Wednesday morning).
- **As of Sep 23**: Status = `due_today` (Target: Wednesday morning, today).
- **As of Sep 24**: Status = `overdue` (Target was Wednesday morning, no completion evidence exists).
- **As of Sep 25**: Status = `overdue`.

Every slippage event is preserved in `c.deadline_history` with source signal ID, revised date, and excerpt.

---

## 5. Confidence Score Calibration

Confidence scores are not random numbers; they are computed via an auditable evidence scoring function:

$$\text{Score} = \text{clamp}\Big(0.75 + \min(0.15, (N_{\text{sources}} - 1) \cdot 0.05) + \min(0.08, (N_{\text{signals}} - 1) \cdot 0.02) + B_{\text{cal}} - P_{\text{ambiguity}}, 0.70, 0.99\Big)$$

- High corroboration commitments (e.g. Meridian Call across email, meeting, voice note, and calendar) score **0.96**.
- Ambiguous items with unassigned ownership incur a penalty and score **0.85**, accurately reflecting uncertainty.

---

## 6. Audit Trail & Reproducibility

Every Q&A interaction generates an audit record:
```json
{
  "id": "audit-371f60d8d0",
  "type": "grounded_query",
  "question": "What did I promise Raghav?",
  "as_of": "2026-09-23",
  "matched_commitments": ["4c67ed5b60"]
}
```
Records are appended to `data/audit.jsonl` and accessible via `GET /api/audit`.
All pipeline stages can be inspected in real time via `GET /api/pipeline-trace`.
