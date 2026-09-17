"""FastAPI service for the Executive Productivity Agent.

Endpoints:
  GET  /                   → dashboard UI
  GET  /api/health         → health check
  GET  /api/brief          → daily brief with metrics
  GET  /api/commitments    → reconciled commitment list
  GET  /api/sources        → source registry
  GET  /api/audit          → query audit trail
  GET  /api/pipeline-trace → full pipeline extraction audit log
  POST /api/query          → grounded Q&A
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .engine import brief, pipeline_result, DATA
from .agent import answer
from .models import QueryRequest

app = FastAPI(
    title='AIONOS Executive Productivity Agent',
    version='2.0.0',
    description='Grounded daily action intelligence — Assignment 1',
)

STATIC = Path(__file__).parent.parent / 'static'
app.mount('/static', StaticFiles(directory=STATIC), name='static')

# Persistent audit log (JSONL)
AUDIT_FILE = Path(__file__).parent.parent / 'data' / 'audit.jsonl'
AUDIT: list[dict] = []


def _validate_date(date_str: str) -> str:
    """Validate and return an ISO date string."""
    try:
        date.fromisoformat(date_str)
        return date_str
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail=f'Invalid date format: {date_str!r}. Expected YYYY-MM-DD.')


@app.get('/')
def root():
    return FileResponse(STATIC / 'index.html')


@app.get('/api/health')
def health():
    return {
        'status': 'ok',
        'agent': 'Executive Productivity Agent',
        'version': '2.0.0',
        'source_boundary': 'Assignment 1 Data Pack only',
        'pipeline': 'multi-stage extraction (ingest → extract → resolve → temporal → reconcile → classify → status → prioritize)',
    }


def _generate_executive_summary(as_of: str, commitments: list, meetings: list) -> str:
    """Construct an information-dense executive briefing tailored to the as_of date."""
    overdue = [c for c in commitments if c.status == 'overdue']
    due_today = [c for c in commitments if c.status == 'due_today']
    ambiguous = [c for c in commitments if c.status == 'ambiguous']
    waiting = [c for c in commitments if c.action_type == 'waiting_on_other']
    important_meetings = [m for m in meetings if m['title'] != 'Blocked']

    parts = []
    if overdue:
        subjects = ', '.join(f'"{c.subject}"' for c in overdue)
        parts.append(f"URGENT: You have {len(overdue)} overdue commitment(s) requiring immediate resolution: {subjects}.")
    if due_today:
        actions = '; '.join(f'{c.action}' for c in due_today)
        parts.append(f"Action required today: {actions}.")
    if important_meetings:
        mtg_str = ', '.join(f"{m['title']} ({m['start']}–{m['end']})" for m in important_meetings)
        parts.append(f"Today's key schedule includes {mtg_str}.")
    if ambiguous:
        lease = next((c for c in ambiguous if 'lease' in c.subject.lower()), None)
        if lease:
            parts.append(f"Ownership Alert: {lease.subject} ({lease.deadline_label or 'Friday'}) remains completely unassigned across stakeholders. Leadership directive: flag it, do not assume.")
    completed_dependencies = [c for c in waiting if c.status == 'completed']
    pending_dependencies = [c for c in waiting if c.status != 'completed']
    if completed_dependencies:
        dep_str = ', '.join(f"{c.owner_display} delivered {c.subject}" for c in completed_dependencies)
        parts.append(f"Received deliverables: {dep_str}.")
    if pending_dependencies:
        dep_str = ', '.join(f"{c.subject} from {c.owner_display} ({c.deadline_label or 'pending'})" for c in pending_dependencies)
        parts.append(f"Tracking dependencies: {dep_str}.")

    return ' '.join(parts) if parts else "All commitments are on schedule with no urgent blockers."


@app.get('/api/brief')
def get_brief(date: str = Query('2026-09-23')):
    date = _validate_date(date)
    cs = brief(date)
    user_name = DATA['metadata']['user']['name']
    user_cal = next((c for c in DATA['calendars'] if c['person'] == user_name), None)
    meetings = []
    if user_cal:
        meetings = [
            {'date': ev[0], 'start': ev[1], 'end': ev[2], 'title': ev[3]}
            for ev in user_cal['events'] if ev[0] == date
        ]
    summary = _generate_executive_summary(date, cs, meetings)
    return {
        'as_of': date,
        'user': DATA['metadata']['user'],
        'executive_summary': summary,
        'meetings': meetings,
        'commitments': cs,
        'metrics': {
            'my_actions': sum(c.action_type == 'my_action' and c.status != 'completed' for c in cs),
            'waiting_on_others': sum(c.action_type == 'waiting_on_other' for c in cs),
            'unclear_ownership': sum(c.action_type == 'unclear_ownership' for c in cs),
            'completed': sum(c.status == 'completed' for c in cs),
            'overdue': sum(c.status == 'overdue' for c in cs),
            'stale': sum(c.status == 'overdue' for c in cs),
            'due_today': sum(c.status == 'due_today' for c in cs),
            'upcoming': sum(c.status == 'upcoming' for c in cs),
        },
    }


@app.get('/api/commitments')
def commitments(date: str = Query('2026-09-23')):
    date = _validate_date(date)
    return {'commitments': brief(date)}


@app.get('/api/sources')
def sources():
    return {
        'people': DATA['metadata']['people'],
        'source_types': ['meeting', 'calendar', 'email', 'voice_note'],
        'email_threads': len(DATA['emails']),
        'voice_notes': len(DATA['voice_notes']),
        'calendar_people': len(DATA['calendars']),
    }


@app.get('/api/audit')
def audit():
    return {'events': AUDIT}


@app.get('/api/pipeline-trace')
def pipeline_trace(date: str = Query('2026-09-23')):
    """Return the full pipeline extraction audit log."""
    date = _validate_date(date)
    result = pipeline_result(date)
    return {
        'as_of': date,
        'signal_count': result.signal_count,
        'candidate_count': result.candidate_count,
        'reconciled_count': result.reconciled_count,
        'commitment_count': len(result.commitments),
        'stages': result.pipeline_log,
    }


@app.post('/api/query')
def query(req: QueryRequest):
    _validate_date(req.as_of)
    result = answer(req)
    event = {
        'id': result.audit_id,
        'type': 'grounded_query',
        'question': req.question,
        'as_of': req.as_of,
        'matched_commitments': [c.id for c in result.commitments],
    }
    AUDIT.append(event)
    # Persist to JSONL
    try:
        with open(AUDIT_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event) + '\n')
    except OSError:
        pass  # non-critical
    return result
