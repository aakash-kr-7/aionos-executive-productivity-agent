"""Data models for the Executive Productivity Agent.

Pydantic schemas for the API boundary. Internal pipeline stages use
lightweight dataclasses; conversion to these models happens at output time.
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

SourceType = Literal['meeting', 'email', 'calendar', 'voice_note']
ActionType = Literal['my_action', 'waiting_on_other', 'unclear_ownership', 'informational']
CommitmentStatus = Literal[
    'open', 'completed', 'overdue', 'due_today', 'upcoming', 'ambiguous',
    'stale',  # kept as alias for backward-compat; pipeline uses 'overdue'
]


class Evidence(BaseModel):
    """A single piece of source evidence backing a commitment."""
    source_id: str
    source_type: SourceType
    date: str
    title: str
    excerpt: str


class DeadlineRevision(BaseModel):
    """One revision in a commitment's deadline history."""
    revised_at: str
    previous_deadline: Optional[str] = None
    new_deadline: str
    source_id: str
    reason: Optional[str] = None


class ReconciliationRecord(BaseModel):
    """Metadata about how a commitment was reconciled across sources."""
    merged_signal_count: int
    source_types_involved: list[str]
    merge_rationale: str


class Commitment(BaseModel):
    """A single reconciled, classified, status-resolved commitment."""
    id: str
    subject: str
    action: str
    action_type: ActionType
    owner: Optional[str] = None
    owner_display: Optional[str] = None
    counterparty: Optional[str] = None
    deadline: Optional[str] = None
    deadline_label: Optional[str] = None
    deadline_history: list[DeadlineRevision] = []
    status: CommitmentStatus = 'open'
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence]
    rationale: list[str]
    extraction_trace: list[str] = []
    reconciliation: Optional[ReconciliationRecord] = None


class QueryRequest(BaseModel):
    question: str
    as_of: str = '2026-09-23'


class QueryResponse(BaseModel):
    answer: str
    commitments: list[Commitment]
    evidence: list[Evidence]
    interpretation: list[str]
    audit_id: str


class PipelineResult(BaseModel):
    """Full output from a pipeline run."""
    commitments: list[Commitment]
    pipeline_log: list[dict] = []
    signal_count: int = 0
    candidate_count: int = 0
    reconciled_count: int = 0
