"""Stage 8 — Prioritization & Output Conversion.

Sorts commitments by attention urgency and converts the internal
ClassifiedCommitment dataclasses into final Pydantic Commitment models
for the API boundary.

Priority order (highest attention first):
  overdue > ambiguous > due_today > upcoming > open > waiting > completed > informational
"""
from __future__ import annotations
import hashlib
from ..models import Commitment, Evidence, DeadlineRevision, ReconciliationRecord
from .classify import ClassifiedCommitment


STATUS_PRIORITY = {
    'overdue': 0,
    'ambiguous': 1,
    'due_today': 2,
    'upcoming': 3,
    'open': 4,
    'completed': 5,
}

TYPE_PRIORITY = {
    'my_action': 0,
    'unclear_ownership': 1,
    'waiting_on_other': 2,
    'informational': 3,
}


def _cid(subject: str) -> str:
    """Generate a deterministic commitment ID from the subject."""
    return hashlib.sha1(subject.lower().encode()).hexdigest()[:10]


def _build_evidence(cc: ClassifiedCommitment) -> list[Evidence]:
    """Assemble evidence list from the group's candidates, context, and calendar signals."""
    evidence: list[Evidence] = []
    seen_ids: set[str] = set()

    # Primary evidence: candidate signals
    for c in cc.group.candidates:
        sig = c.source_signal
        if sig.source_id not in seen_ids:
            evidence.append(Evidence(
                source_id=sig.source_id,
                source_type=sig.source_type,
                date=sig.timestamp[:10],
                title=sig.title,
                excerpt=c.segment_text[:200],
            ))
            seen_ids.add(sig.source_id)

    # Calendar corroboration
    for cal in cc.group.calendar_evidence:
        if cal.source_id not in seen_ids:
            evidence.append(Evidence(
                source_id=cal.source_id,
                source_type='calendar',
                date=cal.timestamp[:10],
                title=cal.title,
                excerpt=cal.raw_text,
            ))
            seen_ids.add(cal.source_id)

    # Sort by date for readability
    evidence.sort(key=lambda e: e.date)
    return evidence


def _build_reconciliation(cc: ClassifiedCommitment) -> ReconciliationRecord:
    """Build reconciliation metadata."""
    return ReconciliationRecord(
        merged_signal_count=len(cc.group.candidates),
        source_types_involved=sorted(cc.group.source_types()),
        merge_rationale=(
            f'Merged {len(cc.group.candidates)} signals from '
            f'{", ".join(sorted(cc.group.source_types()))} '
            f'into one canonical commitment via topic/person similarity'
        ),
    )


def _compute_confidence(cc: ClassifiedCommitment) -> float:
    """Compute a calibrated confidence score based on evidence strength."""
    source_types = cc.group.source_types()
    evidence_count = len(cc.group.candidates)
    has_calendar = bool(cc.group.calendar_evidence)
    has_ambiguity = cc.action_type == 'unclear_ownership'

    base = 0.75
    source_bonus = min(0.15, (len(source_types) - 1) * 0.05)
    evidence_bonus = min(0.08, (evidence_count - 1) * 0.02)
    calendar_bonus = 0.03 if has_calendar else 0.0
    ambiguity_penalty = 0.10 if has_ambiguity else 0.0

    return round(min(0.99, base + source_bonus + evidence_bonus + calendar_bonus - ambiguity_penalty), 2)


def prioritize(classified: list[ClassifiedCommitment]) -> list[Commitment]:
    """Sort by urgency and convert to Pydantic Commitment models."""

    def sort_key(cc: ClassifiedCommitment):
        status = getattr(cc, '_status', 'open')
        return (
            STATUS_PRIORITY.get(status, 4),
            TYPE_PRIORITY.get(cc.action_type, 3),
            cc.deadline or '9999',
        )

    classified.sort(key=sort_key)

    commitments: list[Commitment] = []
    for cc in classified:
        status = getattr(cc, '_status', 'open')
        deadline_history = getattr(cc, '_deadline_history', [])

        commitments.append(Commitment(
            id=_cid(cc.subject),
            subject=cc.subject,
            action=cc.action,
            action_type=cc.action_type,
            owner=cc.owner_email,
            owner_display=cc.owner_display,
            counterparty=cc.counterparty,
            deadline=cc.deadline,
            deadline_label=cc.deadline_label,
            deadline_history=deadline_history,
            status=status,
            confidence=_compute_confidence(cc),
            evidence=_build_evidence(cc),
            rationale=cc.classification_rationale,
            extraction_trace=cc.extraction_trace,
            reconciliation=_build_reconciliation(cc),
        ))

    return commitments
