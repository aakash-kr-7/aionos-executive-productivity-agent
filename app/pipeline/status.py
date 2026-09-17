"""Stage 7 — Deadline & Status Engine.

Calculates commitment status **dynamically relative to as_of**:

  completed  – Evidence of delivery/confirmation exists
  overdue    – as_of > deadline and no completion evidence
  due_today  – deadline falls on as_of date
  upcoming   – deadline is after as_of
  ambiguous  – ownership is unclear (regardless of deadline)
  open       – no deadline or not yet resolved

Also tracks deadline slippage (revision history) within each group.
"""
from __future__ import annotations
from datetime import date, datetime
from .classify import ClassifiedCommitment
from ..models import DeadlineRevision


def _parse_date(dt_str: str) -> date:
    return date.fromisoformat(dt_str[:10])


def _has_completion_evidence(cc: ClassifiedCommitment) -> bool:
    """Check if the group has delivery or confirmation signals."""
    for c in cc.group.candidates:
        if c.signal_type in ('delivery', 'confirmation'):
            return True
    return False


def _completion_date(cc: ClassifiedCommitment) -> str | None:
    """Return the timestamp of the earliest completion signal."""
    for c in cc.group.candidates:
        if c.signal_type in ('delivery', 'confirmation'):
            return c.source_signal.timestamp
    return None


def _build_deadline_history(cc: ClassifiedCommitment) -> list[DeadlineRevision]:
    """Build the deadline revision history from scheduling/promise signals."""
    revisions: list[DeadlineRevision] = []
    previous: str | None = None

    # Collect all candidates with resolved deadlines, sorted by timestamp
    deadline_candidates = [
        c for c in cc.group.candidates
        if getattr(c, '_resolved_deadline', None) and c.signal_type in ('promise', 'scheduling', 'request', 'obligation')
    ]
    deadline_candidates.sort(key=lambda c: c.source_signal.timestamp)

    for c in deadline_candidates:
        new_dl = getattr(c, '_resolved_deadline', None)
        if new_dl and new_dl != previous:
            revisions.append(DeadlineRevision(
                revised_at=c.source_signal.timestamp[:10],
                previous_deadline=previous,
                new_deadline=new_dl,
                source_id=c.source_signal.source_id,
                reason=c.segment_text[:120] if previous else 'Initial deadline',
            ))
            previous = new_dl

    return revisions


def compute_status(
    classified: list[ClassifiedCommitment],
    as_of: str,
) -> tuple[list[ClassifiedCommitment], list[dict]]:
    """Compute dynamic status for each classified commitment.

    Mutates commitments in-place with ``_status`` and ``_deadline_history``.
    Returns (classified, log).
    """
    as_of_date = _parse_date(as_of)
    log_details: list[dict] = []

    for cc in classified:
        # Build deadline history
        cc._deadline_history = _build_deadline_history(cc)  # type: ignore[attr-defined]

        # Ambiguous ownership → always ambiguous status
        if cc.action_type == 'unclear_ownership':
            cc._status = 'ambiguous'  # type: ignore[attr-defined]
            log_details.append({'subject': cc.subject, 'status': 'ambiguous', 'reason': 'ownership unclear'})
            continue

        # Check for completion evidence
        completed = _has_completion_evidence(cc)
        comp_date = _completion_date(cc)

        if completed:
            # Completion evidence exists — but only count it if as_of >= completion date
            if comp_date and _parse_date(comp_date) <= as_of_date:
                cc._status = 'completed'  # type: ignore[attr-defined]
                log_details.append({'subject': cc.subject, 'status': 'completed', 'reason': f'completion evidence on {comp_date[:10]}'})
                continue

        # Deadline-based status
        if cc.deadline:
            dl_date = _parse_date(cc.deadline)
            if as_of_date > dl_date:
                cc._status = 'overdue'  # type: ignore[attr-defined]
                log_details.append({'subject': cc.subject, 'status': 'overdue', 'reason': f'deadline {cc.deadline} passed as of {as_of}'})
            elif as_of_date == dl_date:
                cc._status = 'due_today'  # type: ignore[attr-defined]
                log_details.append({'subject': cc.subject, 'status': 'due_today', 'reason': f'deadline {cc.deadline} is today'})
            else:
                cc._status = 'upcoming'  # type: ignore[attr-defined]
                log_details.append({'subject': cc.subject, 'status': 'upcoming', 'reason': f'deadline {cc.deadline} is after {as_of}'})
        else:
            cc._status = 'open'  # type: ignore[attr-defined]
            log_details.append({'subject': cc.subject, 'status': 'open', 'reason': 'no deadline resolved'})

    log = [{
        'stage': 'status',
        'as_of': as_of,
        'statuses': {s: sum(1 for cc in classified if getattr(cc, '_status', '') == s) for s in ('completed', 'overdue', 'due_today', 'upcoming', 'ambiguous', 'open')},
        'details': log_details,
        'detail': f'Computed status for {len(classified)} commitments as of {as_of}',
    }]

    return classified, log
