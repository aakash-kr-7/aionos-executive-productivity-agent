from __future__ import annotations
import re, uuid
from .engine import brief
from .models import QueryResponse, QueryRequest, Commitment, Evidence


def answer(req: QueryRequest):
    cs=brief(req.as_of)
    q=req.question.lower().strip()
    chosen=[]
    interpretation=[]
    if 'promise' in q or 'promised' in q or 'commit' in q:
        names={'raghav':'Raghav Sethi','neha':'Neha Kapoor','divya':'Divya Rao','priya':'Priya Nair'}
        target=next((v for k,v in names.items() if k in q),None)
        if target=='Raghav Sethi':
            chosen=[c for c in cs if c.counterparty=='Raghav Sethi']
            interpretation.append('Interpreted the question as asking for Arjun-owned commitments involving Raghav Sethi.')
        elif target:
            chosen=[c for c in cs if c.counterparty==target or c.owner_display==target]
            interpretation.append(f'Interpreted the question as asking for commitments involving {target}.')
        else:
            chosen=[c for c in cs if c.action_type=='my_action']
            interpretation.append('No specific person was named, so returned Arjun-owned actions.')
    elif 'today' in q or 'action' in q or 'do i need' in q:
        chosen=[c for c in cs if c.action_type in ('my_action','unclear_ownership') and c.status not in ('completed',)]
        interpretation.append(f'Used the supplied data-pack timeline with as-of date {req.as_of}.')
    elif 'waiting' in q or 'others' in q:
        chosen=[c for c in cs if c.action_type=='waiting_on_other']
        interpretation.append('Interpreted “waiting on others” as actions whose next external/internal dependency is owned by someone other than Arjun.')
    elif 'lease' in q or 'mumbai' in q:
        chosen=[c for c in cs if 'lease' in c.subject.lower()]
        interpretation.append('Matched the Mumbai lease renewal topic and preserved the unresolved ownership state.')
    else:
        terms=set(re.findall(r'[a-z]{3,}',q))
        chosen=[c for c in cs if terms & set(re.findall(r'[a-z]{3,}',(c.subject+' '+c.action).lower()))]
        interpretation.append('Topic-matched the question against reconciled commitments; no unsupported facts were added.')
    if not chosen:
        text='I could not ground that question in the supplied data pack.'
    else:
        lines=[]
        for c in chosen:
            state={'stale':'stale / still open','open':'open','completed':'completed','ambiguous':'ambiguous ownership'}[c.status]
            owner=c.owner_display or 'owner not established'
            deadline=c.deadline_label or 'no explicit deadline'
            lines.append(f'• {c.action} — {state}; owner: {owner}; deadline: {deadline}.')
        text='\n'.join(lines)
        if any(c.action_type=='unclear_ownership' for c in chosen):
            text+='\n\nOwnership is intentionally not assigned: the source material says the item is unowned and explicitly says not to assume.'
    audit_id='audit-'+uuid.uuid4().hex[:10]
    evidence=[]
    seen=set()
    for c in chosen:
        for e in c.evidence:
            if e.source_id not in seen:
                evidence.append(e); seen.add(e.source_id)
    return QueryResponse(answer=text,commitments=chosen,evidence=evidence,interpretation=interpretation,audit_id=audit_id)
