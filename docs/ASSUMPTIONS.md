# Inputs, Sources & Assumptions

## Sources used

Only the uploaded Assignment 1 Data Pack is treated as business truth. It contains the people directory, one leadership-sync transcript, four calendars, five email threads, and two personal voice-note transcripts.

## Explicit source boundary

The data pack says: “Use only the material below as the source data for your agent. Do not invent information that isn’t grounded in one of these sources.”

## Assumptions made by the implementation

1. “Today” is resolved using the requested `as_of` date; the default demo date is 23 Sep 2026 because that is when the supplied voice note and latest vendor-list follow-up occur.
2. A calendar event can corroborate a commitment but does not independently create one unless another source establishes the action.
3. Later explicit changes in an email thread supersede earlier target dates for the same action.
4. “Waiting on others” means the current next step is explicitly owned by someone other than Arjun.
5. “Unclear ownership” is a first-class state; no owner is inferred from organizational habit.
6. System-generated commitment IDs and audit IDs are metadata, not source facts.

## Known limitation

This submission uses deterministic extraction rules because the supplied dataset is small and the assessment time limit is six hours. The architecture deliberately isolates this component so an LLM structured-output extractor can be plugged in without weakening the evidence and ownership gates.
