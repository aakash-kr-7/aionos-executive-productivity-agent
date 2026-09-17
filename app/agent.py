"""Grounded Q&A agent boundary.

Replaces the original keyword-matching if/elif chain with structured
intent classification that:

  - Detects person-scoped queries (with promisor/promisee directionality)
  - Detects temporal queries (today, overdue, this week)
  - Detects status queries (waiting, completed)
  - Detects topic queries (lease, vendor list, …)
  - Falls back to full-text token overlap search

Every response includes:
  - Interpretation of how the query was parsed
  - Evidence chain from the data pack
  - Audit ID for traceability

The agent is still deterministic (no LLM dependency) but uses structured
decomposition instead of raw string matching.
"""
from __future__ import annotations
import re
import uuid
from .engine import brief, DATA
from .models import QueryResponse, QueryRequest, Commitment, Evidence


# ── Person directory (built from data pack) ───────────────────────────
_PEOPLE = {
    p['name'].split()[0].lower(): p['name']
    for p in DATA['metadata']['people']
}
_USER = DATA['metadata']['user']['name']


def _detect_person(q: str) -> str | None:
    """Find a person reference in the query."""
    q_lower = q.lower()
    for key, full_name in _PEOPLE.items():
        if key in q_lower or full_name.lower() in q_lower:
            return full_name
    return None


def _detect_direction(q: str) -> str | None:
    """Detect promise direction: outgoing (I→X) vs incoming (X→me)."""
    q_lower = q.lower()
    outgoing = any(p in q_lower for p in [
        'did i promise', 'what did i promise', 'i promised', 'i committed',
        'i owe', 'what do i owe', 'did i commit',
    ])
    incoming = any(p in q_lower for p in [
        'promise me', 'promised me', 'owe me', 'waiting for',
        'did .* promise', 'committed to me',
    ])
    if outgoing:
        return 'outgoing'
    if incoming:
        return 'incoming'
    # Heuristic: "What did I promise X?" pattern
    if re.search(r'\bi\b.*\bpromise\b', q_lower):
        return 'outgoing'
    if re.search(r'\bpromise\b.*\b(raghav|neha|divya|priya)\b', q_lower):
        return 'outgoing'
    return None


def _detect_time_scope(q: str) -> str | None:
    """Detect temporal scope in the query."""
    q_lower = q.lower()
    if 'today' in q_lower or 'right now' in q_lower:
        return 'today'
    if 'overdue' in q_lower or 'late' in q_lower or 'missed' in q_lower:
        return 'overdue'
    if 'this week' in q_lower or 'week' in q_lower:
        return 'this_week'
    return None


def _detect_status_filter(q: str) -> str | None:
    """Detect status-based filters."""
    q_lower = q.lower()
    if 'waiting' in q_lower or 'others' in q_lower or 'blocked' in q_lower:
        return 'waiting'
    if 'completed' in q_lower or 'done' in q_lower or 'finished' in q_lower:
        return 'completed'
    if 'pending' in q_lower or 'open' in q_lower:
        return 'open'
    return None


def _extract_topic_tokens(q: str) -> set[str]:
    """Extract significant tokens from the query for topic matching."""
    stop = {'what', 'did', 'about', 'the', 'need', 'action', 'today',
            'promise', 'promised', 'commit', 'committed', 'waiting',
            'others', 'who', 'how', 'when', 'where', 'why', 'does',
            'should', 'can', 'tell', 'show', 'give', 'find', 'are',
            'any', 'all', 'my', 'for', 'with', 'from', 'that', 'this',
            'has', 'have', 'had', 'been', 'was', 'were', 'will', 'would'}
    return set(re.findall(r'[a-z]{3,}', q.lower())) - stop


def _topic_match_score(tokens: set[str], commitment: Commitment) -> float:
    """Score how well query tokens match a commitment."""
    target = set(re.findall(r'[a-z]{3,}', (commitment.subject + ' ' + commitment.action).lower()))
    if not tokens or not target:
        return 0.0
    return len(tokens & target) / max(len(tokens), 1)


def answer(req: QueryRequest) -> QueryResponse:
    """Answer a grounded question against the reconciled commitments."""
    cs = brief(req.as_of)
    q = req.question.strip()
    chosen: list[Commitment] = []
    interpretation: list[str] = []

    # ── Parse intent ──────────────────────────────────────────────
    person = _detect_person(q)
    direction = _detect_direction(q)
    time_scope = _detect_time_scope(q)
    status_filter = _detect_status_filter(q)
    topic_tokens = _extract_topic_tokens(q)

    # ── Apply filters ─────────────────────────────────────────────

    # 1. Person + direction queries
    if person and direction == 'outgoing':
        # "What did I promise Raghav?" → my_action items with this counterparty
        chosen = [c for c in cs if c.action_type == 'my_action' and c.counterparty == person]
        interpretation.append(
            f'Interpreted as: outgoing commitments from {_USER} to {person}.'
        )
    elif person and direction == 'incoming':
        # "What did Raghav promise me?" → waiting_on_other where owner is that person
        chosen = [c for c in cs if c.action_type == 'waiting_on_other' and c.owner_display == person]
        interpretation.append(
            f'Interpreted as: incoming commitments from {person} to {_USER}.'
        )
    elif person:
        # General person query — all commitments involving this person
        chosen = [c for c in cs if c.counterparty == person or c.owner_display == person]
        interpretation.append(
            f'Interpreted as: all commitments involving {person}.'
        )

    # 2. Time-scoped queries
    elif time_scope == 'today':
        chosen = [
            c for c in cs
            if c.action_type in ('my_action', 'unclear_ownership')
            and c.status not in ('completed',)
        ]
        interpretation.append(
            f'Used the supplied data-pack timeline with as-of date {req.as_of}. '
            f'Returned actionable items (my_action + unclear_ownership) that are not completed.'
        )
    elif time_scope == 'overdue':
        chosen = [c for c in cs if c.status == 'overdue']
        interpretation.append('Filtered for overdue commitments.')

    # 3. Status queries
    elif status_filter == 'waiting':
        chosen = [c for c in cs if c.action_type == 'waiting_on_other']
        interpretation.append(
            'Interpreted "waiting on others" as actions whose next dependency '
            'is owned by someone other than the executive.'
        )
    elif status_filter == 'completed':
        chosen = [c for c in cs if c.status == 'completed']
        interpretation.append('Filtered for completed commitments.')

    # 4. Topic matching (fallback)
    else:
        # Score each commitment against query tokens
        scored = [(c, _topic_match_score(topic_tokens, c)) for c in cs]
        scored.sort(key=lambda x: x[1], reverse=True)
        threshold = 0.3
        chosen = [c for c, score in scored if score >= threshold]
        if not chosen and scored and scored[0][1] > 0:
            # Take the best match even if below threshold
            chosen = [scored[0][0]]
        interpretation.append(
            'Topic-matched the question against reconciled commitments; '
            'no unsupported facts were added.'
        )

    # ── Build response ────────────────────────────────────────────
    if not chosen:
        text = (
            'I could not ground that question in the supplied data pack. '
            'Try asking about specific people (Raghav, Neha, Divya, Priya), '
            'topics (vendor list, lease, campaign deck), or status (waiting, overdue, today).'
        )
    else:
        lines: list[str] = []
        for c in chosen:
            status_label = {
                'overdue': 'OVERDUE',
                'due_today': 'due today',
                'upcoming': 'upcoming',
                'completed': 'completed',
                'ambiguous': 'ambiguous ownership',
                'open': 'open',
            }.get(c.status, c.status)
            owner = c.owner_display or 'owner not established'
            deadline = c.deadline_label or 'no explicit deadline'
            lines.append(
                f'\u2022 {c.action} \u2014 {status_label}; owner: {owner}; deadline: {deadline}.'
            )
        text = '\n'.join(lines)
        if any(c.action_type == 'unclear_ownership' for c in chosen):
            text += (
                '\n\nOwnership is intentionally not assigned: the source material '
                'says the item is unowned and the executive explicitly said not to assume.'
            )

    audit_id = 'audit-' + uuid.uuid4().hex[:10]

    # Collect unique evidence
    evidence: list[Evidence] = []
    seen: set[str] = set()
    for c in chosen:
        for e in c.evidence:
            if e.source_id not in seen:
                evidence.append(e)
                seen.add(e.source_id)

    return QueryResponse(
        answer=text,
        commitments=chosen,
        evidence=evidence,
        interpretation=interpretation,
        audit_id=audit_id,
    )
