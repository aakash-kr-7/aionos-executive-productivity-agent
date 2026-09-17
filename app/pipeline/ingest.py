"""Stage 1 — Ingestion & Normalization.

Reads the raw source_data.json structure (meeting statements, email threads,
calendar events, voice notes) and produces a flat list of NormalizedSignal
objects with a uniform schema regardless of source type.

Every piece of text in the data pack receives a unique signal_id for
end-to-end traceability.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NormalizedSignal:
    """A single atomic unit of source information."""
    signal_id: str
    source_id: str
    source_type: str            # meeting | email | calendar | voice_note
    timestamp: str              # ISO-ish datetime string
    speaker: Optional[str]      # display name of speaker/sender
    speaker_email: Optional[str]
    recipients: list[str]       # email addresses (empty for meetings/voice)
    raw_text: str
    thread_id: Optional[str]    # groups email messages into threads
    title: str                  # source-level title (meeting title, thread subject …)
    is_constraint: bool = False # True for calendar events (not commitments themselves)


def _find_email(name: str, people: list[dict]) -> Optional[str]:
    """Look up an email address by display name."""
    for p in people:
        if p['name'] == name:
            return p['email']
    return None


def _email_to_name(email: str, people: list[dict]) -> str:
    """Convert an email address to a display name."""
    for p in people:
        if p['email'] == email:
            return p['name']
    # Fallback: humanize the local part
    local = email.split('@')[0]
    return local.replace('.', ' ').replace('_', ' ').title()


def ingest(data: dict) -> tuple[list[NormalizedSignal], list[dict]]:
    """Ingest all sources and return (signals, log_entries).

    The log entries record what was ingested from each source type,
    giving the audit trail its first stage of provenance.
    """
    signals: list[NormalizedSignal] = []
    log: list[dict] = []
    people = data['metadata']['people']
    user = data['metadata']['user']
    idx = 0

    # ---- Meeting transcript ----
    meeting = data.get('meeting')
    if meeting:
        for si, stmt in enumerate(meeting.get('statements', [])):
            speaker_email = _find_email(stmt['speaker'], people)
            signals.append(NormalizedSignal(
                signal_id=f'sig_{idx:04d}',
                source_id=meeting['source_id'],
                source_type='meeting',
                timestamp=meeting['date'] + 'T09:00',
                speaker=stmt['speaker'],
                speaker_email=speaker_email,
                recipients=[],
                raw_text=stmt['text'],
                thread_id=None,
                title=meeting['title'],
            ))
            idx += 1
        log.append({
            'stage': 'ingest', 'source': 'meeting',
            'signals': len(meeting.get('statements', [])),
            'detail': f"Ingested {len(meeting.get('statements', []))} statements from '{meeting['title']}'",
        })

    # ---- Calendar events ----
    cal_count = 0
    for cal in data.get('calendars', []):
        person_email = _find_email(cal['person'], people)
        for event in cal['events']:
            date_str, start, end, title = event
            signals.append(NormalizedSignal(
                signal_id=f'sig_{idx:04d}',
                source_id=f"calendar_{cal['person'].lower().replace(' ', '_')}",
                source_type='calendar',
                timestamp=f'{date_str}T{start}',
                speaker=cal['person'],
                speaker_email=person_email,
                recipients=[],
                raw_text=f'{start}\u2013{end} {title}',
                thread_id=None,
                title=f"{cal['person']} calendar",
                is_constraint=True,
            ))
            idx += 1
            cal_count += 1
    log.append({
        'stage': 'ingest', 'source': 'calendar',
        'signals': cal_count,
        'detail': f'Ingested {cal_count} calendar events across {len(data.get("calendars", []))} people',
    })

    # ---- Email threads ----
    email_count = 0
    for thread in data.get('emails', []):
        for mi, msg in enumerate(thread['messages']):
            ts, sender, recipient, text = msg
            signals.append(NormalizedSignal(
                signal_id=f'sig_{idx:04d}',
                source_id=f"email_{thread['thread']}_{mi}",
                source_type='email',
                timestamp=ts,
                speaker=_email_to_name(sender, people),
                speaker_email=sender,
                recipients=[r.strip() for r in recipient.split(',')],
                raw_text=text,
                thread_id=thread['thread'],
                title=thread['subject'],
            ))
            idx += 1
            email_count += 1
    log.append({
        'stage': 'ingest', 'source': 'email',
        'signals': email_count,
        'detail': f'Ingested {email_count} messages across {len(data.get("emails", []))} threads',
    })

    # ---- Voice notes ----
    for vn in data.get('voice_notes', []):
        signals.append(NormalizedSignal(
            signal_id=f'sig_{idx:04d}',
            source_id=vn['source_id'],
            source_type='voice_note',
            timestamp=vn['date'],
            speaker=user['name'],
            speaker_email=user['email'],
            recipients=[],
            raw_text=vn['text'],
            thread_id=None,
            title=vn['title'],
        ))
        idx += 1
    log.append({
        'stage': 'ingest', 'source': 'voice_note',
        'signals': len(data.get('voice_notes', [])),
        'detail': f"Ingested {len(data.get('voice_notes', []))} voice notes",
    })

    return signals, log
