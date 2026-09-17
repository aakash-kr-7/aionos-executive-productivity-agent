"""Stage 4 — Temporal Normalization.

Resolves relative deadline phrases ("end of day tomorrow", "Wednesday
morning", "Thursday 9:30 AM") against the signal's own timestamp and the
exercise week (Sep 21–25 2026).

Produces absolute ISO-8601 deadlines and tracks revision history when later
signals in the same topic change the deadline.
"""
from __future__ import annotations
import re
from datetime import date, timedelta
from typing import Optional
from .extract import CandidateCommitment


DAY_NAMES = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2,
    'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6,
}

TIME_OF_DAY = {
    'morning': '09:00', 'afternoon': '14:00',
    'evening': '18:00', 'eod': '17:00', 'end of day': '17:00',
}


def _week_start(exercise_week: list[str]) -> date:
    return date.fromisoformat(exercise_week[0])


def _signal_date(timestamp: str) -> date:
    """Extract a date from an ISO timestamp string."""
    return date.fromisoformat(timestamp[:10])


def _day_name_to_date(day_name: str, week_start: date) -> Optional[date]:
    """Convert a day name to a date within the exercise week."""
    offset = DAY_NAMES.get(day_name.lower())
    if offset is not None:
        return week_start + timedelta(days=offset)
    return None


def resolve_deadline(phrase: str, signal_ts: str, week_start: date) -> Optional[str]:
    """Resolve a deadline phrase to an absolute ISO-8601 datetime string.

    Returns None if the phrase cannot be resolved.
    """
    if not phrase:
        return None

    phrase_lower = phrase.lower().strip()
    sig_date = _signal_date(signal_ts)

    # ---- Explicit time like "9:30 AM Thursday", "3:00 PM", or "3 PM" ----
    explicit_time: Optional[str] = None
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)\b', phrase, re.IGNORECASE)
    if not time_match:
        time_match = re.search(r'(\d{1,2}):(\d{2})', phrase)
    if time_match:
        hour = int(time_match.group(1))
        minute = time_match.group(2) if (len(time_match.groups()) >= 2 and time_match.group(2)) else '00'
        ampm = (time_match.group(3) or '').upper() if len(time_match.groups()) >= 3 and time_match.group(3) else ''
        if ampm == 'PM' and hour < 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        explicit_time = f'{hour:02d}:{minute}'

    # ---- Day name ----
    target_date: Optional[date] = None
    for day_name in DAY_NAMES:
        if day_name in phrase_lower:
            target_date = _day_name_to_date(day_name, week_start)
            break

    # ---- "tomorrow" ----
    if 'tomorrow' in phrase_lower:
        target_date = sig_date + timedelta(days=1)

    # ---- "today" ----
    if 'today' in phrase_lower and target_date is None:
        target_date = sig_date

    # ---- "this week" / "this friday" ----
    if 'this week' in phrase_lower or 'this friday' in phrase_lower:
        target_date = week_start + timedelta(days=4)  # Friday

    # ---- Month + day: "25 September" / "September 25" ----
    month_day = re.search(r'(\d{1,2})\s*(?:September|Sep)', phrase, re.IGNORECASE)
    if not month_day:
        month_day = re.search(r'(?:September|Sep)\s*(\d{1,2})', phrase, re.IGNORECASE)
    if month_day and target_date is None:
        day_num = int(month_day.group(1))
        target_date = date(week_start.year, 9, day_num)

    if target_date is None:
        return None

    # ---- Time of day ----
    if explicit_time is None:
        for tod_phrase, tod_time in TIME_OF_DAY.items():
            if tod_phrase in phrase_lower:
                explicit_time = tod_time
                break

    if explicit_time is None:
        # "end of day" check
        if 'end of day' in phrase_lower or 'eod' in phrase_lower:
            explicit_time = '17:00'
        elif 'morning' in phrase_lower:
            explicit_time = '09:00'
        elif 'evening' in phrase_lower:
            explicit_time = '18:00'
        elif 'afternoon' in phrase_lower:
            explicit_time = '14:00'
        else:
            explicit_time = '17:00'  # default to end of day

    return f'{target_date.isoformat()}T{explicit_time}'


def _make_label(deadline: str, phrase: str) -> str:
    """Create a human-readable deadline label."""
    d = date.fromisoformat(deadline[:10])
    day_name = d.strftime('%A')
    time_part = deadline[11:]

    label_parts: list[str] = [day_name]

    if time_part == '09:00':
        label_parts.append('morning')
    elif time_part == '17:00':
        label_parts.append('end of day')
    elif time_part == '18:00':
        label_parts.append('evening')
    elif time_part not in ('14:00',):
        # Specific time
        h, m = int(time_part[:2]), int(time_part[3:5])
        am_pm = 'AM' if h < 12 else 'PM'
        display_h = h if h <= 12 else h - 12
        if display_h == 0:
            display_h = 12
        label_parts.append(f'{display_h}:{m:02d} {am_pm}')
    else:
        label_parts.append('afternoon')

    # Add date for clarity
    label_parts.append(f'(Sep {d.day})')

    return ' '.join(label_parts)


def resolve_deadlines(
    candidates: list[CandidateCommitment],
    exercise_week: list[str],
) -> tuple[list[CandidateCommitment], list[dict]]:
    """Resolve deadline phrases on all candidates to absolute datetimes.

    Mutates candidates in-place by adding ``_resolved_deadline`` and
    ``_deadline_label`` attributes.
    """
    ws = _week_start(exercise_week)
    resolved_count = 0

    for cand in candidates:
        dl = resolve_deadline(cand.deadline_phrase, cand.source_signal.timestamp, ws)
        if dl:
            cand._resolved_deadline = dl  # type: ignore[attr-defined]
            cand._deadline_label = _make_label(dl, cand.deadline_phrase or '')  # type: ignore[attr-defined]
            resolved_count += 1
        else:
            cand._resolved_deadline = None  # type: ignore[attr-defined]
            cand._deadline_label = None  # type: ignore[attr-defined]

    log = [{
        'stage': 'temporal',
        'resolved_count': resolved_count,
        'total_with_phrases': sum(1 for c in candidates if c.deadline_phrase),
        'detail': f'Resolved {resolved_count} deadline phrases to absolute datetimes',
    }]
    return candidates, log
