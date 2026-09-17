from typing import Literal, Optional
from pydantic import BaseModel, Field

SourceType = Literal['meeting', 'email', 'calendar', 'voice_note']
ActionType = Literal['my_action', 'waiting_on_other', 'unclear_ownership', 'informational']

class Evidence(BaseModel):
    source_id: str
    source_type: SourceType
    date: str
    title: str
    excerpt: str

class Commitment(BaseModel):
    id: str
    subject: str
    action: str
    action_type: ActionType
    owner: Optional[str] = None
    owner_display: Optional[str] = None
    counterparty: Optional[str] = None
    deadline: Optional[str] = None
    deadline_label: Optional[str] = None
    status: Literal['open', 'completed', 'stale', 'ambiguous'] = 'open'
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence]
    rationale: list[str]

class QueryRequest(BaseModel):
    question: str
    as_of: str = '2026-09-23'

class QueryResponse(BaseModel):
    answer: str
    commitments: list[Commitment]
    evidence: list[Evidence]
    interpretation: list[str]
    audit_id: str
