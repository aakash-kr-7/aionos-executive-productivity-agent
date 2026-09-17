# Architecture & Pipeline Design Specification

## System Overview

The **AIONOS Executive Productivity Agent** transforms unstructured, multi-modal executive artifacts (meeting transcripts, email threads, calendar constraints, voice notes) into a grounded, prioritized daily action brief for **Arjun Malhotra, VP Sales**.

Rather than relying on a brittle prompt or opaque end-to-end LLM call, this system implements an **explicit, deterministic, 8-stage agentic pipeline**. Every stage has clear schema boundaries, typed dataclass interfaces, calibrated confidence scores, and an immutable audit log.

```text
                               RAW SOURCES (Data Pack)
                   ┌─────────────────────────────────────────────┐
                   │ Meeting Sync  •  Emails  •  Voice  •  Cals  │
                   └──────────────────────┬──────────────────────┘
                                          │ Stage 1
                                          ▼
                                     INGESTION
                         Produces: NormalizedSignal[] (70 signals)
                                          │ Stage 2
                                          ▼
                                 SIGNAL EXTRACTION
                    Regex intent extractors + voice note segmentation
                        Produces: CandidateCommitment[] (34 cands)
                                          │ Stage 3
                                          ▼
                              ENTITY & PERSON RESOLUTION
                   Resolves names, emails, and aliases to canonical directory
                                          │ Stage 4
                                          ▼
                                TEMPORAL NORMALIZATION
                     Resolves relative phrases to absolute ISO-8601
                                          │ Stage 5
                                          ▼
                        CROSS-SOURCE RECONCILIATION & DEDUP
                     Thread clustering + Jaccard token/person overlap
                          Produces: ReconciledGroup[] (5 groups)
                                          │ Stage 6
                                          ▼
                              OWNERSHIP CLASSIFICATION
                    Evidence-based gating (my_action vs waiting vs unclear)
                     Refusal to invent ownership for unassigned items
                                          │ Stage 7
                                          ▼
                               DEADLINE & STATUS ENGINE
                    Dynamic evaluation relative to as_of date + slippage
                                          │ Stage 8
                                          ▼
                          PRIORITIZATION & CONFIDENCE SCORING
                     Urgency sort + evidence weighting → Final API models
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
            DAILY BRIEF API                               GROUNDED Q&A
       /api/brief, /api/pipeline-trace           Multi-scope intent parser
                   │                                             │
                   └──────────────────────┬──────────────────────┘
                                          ▼
                                EXECUTIVE DASHBOARD
                      Real-time date simulation (21–25 Sep 2026)
```

---

## The 8 Pipeline Stages

### Stage 1: Ingestion & Normalization (`app/pipeline/ingest.py`)
- **Input**: Raw `source_data.json` dict.
- **Output**: Flat list of 70 `NormalizedSignal` dataclass instances.
- **Schema**:
  - `signal_id`: Deterministic unique identifier (e.g. `sig_email_vendor_list_0000`).
  - `source_type`: `meeting | email | calendar | voice_note`.
  - `source_id`: Source container ID.
  - `timestamp`: Normalized ISO-8601 string.
  - `speaker`: Canonical speaker name or sender.
  - `speaker_email`: Canonical email address.
  - `recipients`: List of recipient emails.
  - `title`: Subject, meeting title, or memo title.
  - `raw_text`: Exact message body or speech transcript.
  - `is_constraint`: Boolean flag for calendar events (used as corroborating temporal constraints, not primary commitment sources).

### Stage 2: Signal Extraction → Candidates (`app/pipeline/extract.py`)
- **Input**: `NormalizedSignal[]` and canonical person names.
- **Output**: `CandidateCommitment[]` (34 candidates).
- **Voice Note Segmentation**: Voice notes are split on topic transition boundaries (e.g., `.\s+Also\s+`), ensuring multi-topic memos (such as Memo 1 containing vendor list + Mumbai lease) are never conflated into a single candidate.
- **Intent Extraction**: Applies deterministic regex tables covering 7 communicative acts:
  - `promise`: Explicit first-person commitments ("I'll get that to him", "will send by tomorrow morning").
  - `request`: Explicit asks and follow-ups ("can you send", "following up", "can I get it by").
  - `delivery`: Handoff and attachment events ("report attached", "deck is ready", "sent as promised").
  - `confirmation`: Acceptance and scheduling agreements ("confirmed", "Wednesday 3 PM works", "see you at 3").
  - `scheduling`: Target shifts and revisions ("shifting to Thursday", "how about Wednesday 3 PM").
  - `ambiguity_flag`: Explicit ownership gaps ("not sure whose desk", "don't assume", "still unowned", "someone needs to own").
  - `obligation`: Reminders and external constraints ("requires authorized signature", "deadline is Friday").

### Stage 3: Entity & Person Resolution (`app/pipeline/resolve.py`)
- **Input**: `CandidateCommitment[]` and `data['metadata']['people']`.
- **Output**: Canonicalized candidates where first names, full names, email addresses, and organizational aliases (`All Staff`, `Facilities`) map to the authoritative people directory:
  - `Arjun Malhotra` (`arjun.malhotra@veridian-corp.example`, VP Sales)
  - `Neha Kapoor` (`neha.kapoor@veridian-corp.example`, Head of Marketing)
  - `Raghav Sethi` (`raghav.sethi@veridian-corp.example`, Head of Operations)
  - `Divya Rao` (`divya.rao@veridian-corp.example`, Finance Director)
  - `Priya Nair` (`priya.nair@meridianlogistics.example`, External Partner)

### Stage 4: Temporal Normalization (`app/pipeline/temporal.py`)
- **Input**: Candidates and exercise week calendar (`2026-09-21` to `2026-09-25`).
- **Output**: Adds `_resolved_deadline` (ISO datetime) and human-readable `_deadline_label`.
- **Resolution Rules**:
  - `end of day tomorrow` from Sep 21 &rarr; `2026-09-22T17:00` ("Tuesday end of day (Sep 22)").
  - `first thing tomorrow morning` from Sep 21 &rarr; `2026-09-22T09:00` ("Tuesday morning (Sep 22)").
  - `tomorrow (Wednesday) morning` from Sep 22 &rarr; `2026-09-23T09:00` ("Wednesday morning (Sep 23)").
  - `Wednesday 3:00 PM` &rarr; `2026-09-23T15:00` ("Wednesday 3:00 PM (Sep 23)").
  - `Wednesday evening` &rarr; `2026-09-23T18:00` ("Wednesday evening (Sep 23)").
  - `Thursday 9:30 AM` &rarr; `2026-09-24T09:30` ("Thursday 9:30 AM (Sep 24)").
  - `Friday, 25 September` &rarr; `2026-09-25T17:00` ("Friday end of day (Sep 25)").

### Stage 5: Cross-Source Reconciliation & Deduplication (`app/pipeline/reconcile.py`)
- **Input**: Candidates and all normalized signals.
- **Output**: Exactly 5 canonical `ReconciledGroup` objects.
- **Algorithm**:
  1. **Thread Seeding**: Candidates belonging to known email threads seed the 5 canonical commitment clusters.
  2. **Conversational Flow Enrichment**: Meeting remarks that are short reactions ("Okay, flag it, don't assume", "Noted") inherit topic tokens from their immediate conversational turn.
  3. **Composite Similarity Matching**: Ungrouped candidates (meeting turns, voice note segments) match an existing cluster via:
     $$\text{Score} = \max(J_{\text{tokens}}, 0.5 \cdot J_{\text{tokens}} + 0.5 \cdot J_{\text{counterparty}}, 0.6 \cdot \text{Containment})$$
     - Executive exclusion: Arjun Malhotra (the user) is excluded from counterparty similarity to prevent false cross-topic mergers.
     - Mandatory token overlap: Candidates with zero topic overlap cannot merge into an unrelated group.
  4. **Calendar Corroboration**: Calendar events match groups by title token overlap to provide temporal constraint backing.

### Stage 6: Ownership Classification (`app/pipeline/classify.py`)
- **Input**: `ReconciledGroup[]` and user profile.
- **Output**: `ClassifiedCommitment[]`.
- **Classification Taxonomy**:
  1. `my_action`: Executive made explicit promises or obligations to deliver (`user_promises > 0`).
     - *Updated vendor list*: Arjun promised Raghav.
     - *Meridian logistics call*: Arjun promised Priya to reconfirm/schedule.
  2. `waiting_on_other`: Another named individual promised the deliverable (`other_promises > 0`).
     - *Q3 campaign deck review*: Neha promised draft delivery.
     - *July expense variance report*: Divya promised report delivery.
  3. `unclear_ownership`: Ambiguity flags detected and no individual accepted ownership.
     - *Mumbai office lease renewal*: Raghav flagged "not sure whose desk", Divya stated "not on my end", Arjun directed "don't assume" and noted "someone needs to own that, I don't think it's me". **Ownership remains explicitly `None`**.
- **Deadline History**: Sorts deadline-bearing signals chronologically to build a full `DeadlineRevision[]` history, explaining why and when deadlines shifted.

### Stage 7: Deadline & Status Engine (`app/pipeline/status.py`)
- **Input**: `ClassifiedCommitment[]` and `as_of` date string.
- **Output**: Mutates commitments with dynamic `_status` relative to `as_of`:
  - `ambiguous`: Ownership is unassigned (`unclear_ownership`).
  - `completed`: Completion evidence (delivery/confirmation) occurred on or before `as_of`.
  - `due_today`: `as_of == deadline_date`.
  - `overdue`: `as_of > deadline_date` and deliverable has not been completed.
  - `upcoming`: `as_of < deadline_date`.

### Stage 8: Prioritization & Confidence (`app/pipeline/prioritize.py`)
- **Input**: `ClassifiedCommitment[]`.
- **Output**: Final Pydantic `Commitment[]` models.
- **Urgency Ordering**:
  1. Overdue commitments (`overdue`)
  2. Ambiguous / unowned items requiring immediate executive clarification (`ambiguous`)
  3. Items due today (`due_today`)
  4. Upcoming commitments (`upcoming`)
  5. Completed items (`completed`)
- **Confidence Calibration**: Computed from evidence diversity and depth:
  $$\text{Confidence} = \text{clamp}(0.75 + \text{Bonus}_{\text{sources}} + \text{Bonus}_{\text{signals}} + \text{Bonus}_{\text{calendar}} - \text{Penalty}_{\text{ambiguity}}, 0.70, 0.99)$$

---

## Dynamic State Progression (Sep 21–25, 2026)

| Commitment | Mon 21 Sep | Tue 22 Sep | Wed 23 Sep | Thu 24 Sep | Fri 25 Sep |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Updated vendor list** | `upcoming` | `upcoming` | `due_today` | `overdue` | `overdue` |
| **Meridian logistics call** | `upcoming` | `upcoming` | `completed` | `completed` | `completed` |
| **July expense variance report** | `upcoming` | `upcoming` | `completed` | `completed` | `completed` |
| **Q3 campaign deck review** | `upcoming` | `upcoming` | `upcoming` | `completed` | `completed` |
| **Mumbai office lease renewal** | `ambiguous` | `ambiguous` | `ambiguous` | `ambiguous` | `ambiguous` |
