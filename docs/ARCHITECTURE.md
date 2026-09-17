# Architecture & Process Flow

## 1. Source ingestion

The supplied data pack is represented in `data/source_data.json` as four source classes: meeting, email, calendar, and voice note. Each source receives a stable source ID.

## 2. Normalization

Messages are normalized into evidence objects with source type, date, title, and short excerpt. Calendar events are retained as temporal constraints, not treated as commitments by themselves.

## 3. Commitment extraction

The assessment dataset is intentionally small. The prototype uses auditable extraction rules for explicit first-person commitments, explicit requests, dependency handoffs, and unresolved ownership. This avoids pretending a general LLM is certain where the source is ambiguous.

## 4. Reconciliation

Multiple mentions are merged into one canonical commitment. Example: the updated vendor list appears in the leadership sync, two later Arjun emails, and his personal voice note. The UI shows one action with four evidence references.

## 5. Ownership gate

The system distinguishes:

- `my_action`: Arjun is explicitly the actor.
- `waiting_on_other`: another named person is the current actor/dependency.
- `unclear_ownership`: the sources explicitly do not establish an owner.

For the Mumbai lease, the source says it is unassigned and Arjun says “don’t assume”; therefore the system does not assign Facilities as owner even though Divya believes it typically sits there.

## 6. Deadline engine

The exercise week is fixed to 21–25 September 2026. Explicit relative phrases are resolved against the source timestamp and later messages can supersede earlier target dates. The latest evidence wins only when the source explicitly changes the deadline; otherwise the earlier commitment remains.

## 7. Brief generation

The daily brief ranks attention by state: stale commitments, ambiguous ownership, and open Arjun actions. This is prioritization of workflow state, not an invented business priority.

## 8. Q&A

Questions are classified with simple intent rules and resolved against canonical commitments. Responses include interpretation text and evidence. Unknown questions return a grounded “not found” answer rather than hallucinating.

## 9. Auditability

Each Q&A creates an audit event with a generated system ID, question, as-of date, and matched commitment IDs. System metadata is separate from business source data.
