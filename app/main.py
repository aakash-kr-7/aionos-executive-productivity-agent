from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .engine import brief, DATA
from .agent import answer
from .models import QueryRequest

app=FastAPI(title='AIONOS Executive Productivity Agent',version='1.0.0')
STATIC=Path(__file__).parent.parent/'static'
app.mount('/static', StaticFiles(directory=STATIC), name='static')
AUDIT=[]

@app.get('/')
def root(): return FileResponse(STATIC/'index.html')

@app.get('/api/health')
def health(): return {'status':'ok','agent':'Executive Productivity Agent','source_boundary':'Assignment 1 Data Pack only'}

@app.get('/api/brief')
def get_brief(date: str=Query('2026-09-23')):
    cs=brief(date)
    return {'as_of':date,'user':DATA['metadata']['user'],'commitments':cs,'metrics':{
        'my_actions':sum(c.action_type=='my_action' and c.status!='completed' for c in cs),
        'waiting_on_others':sum(c.action_type=='waiting_on_other' for c in cs),
        'unclear_ownership':sum(c.action_type=='unclear_ownership' for c in cs),
        'completed':sum(c.status=='completed' for c in cs),
        'stale':sum(c.status=='stale' for c in cs)}}

@app.get('/api/commitments')
def commitments(): return {'commitments':brief('2026-09-23')}

@app.get('/api/sources')
def sources():
    return {'people':DATA['metadata']['people'],'source_types':['meeting','calendar','email','voice_note'],'email_threads':len(DATA['emails']),'voice_notes':len(DATA['voice_notes']),'calendar_people':len(DATA['calendars'])}

@app.get('/api/audit')
def audit(): return {'events':AUDIT}

@app.post('/api/query')
def query(req: QueryRequest):
    result=answer(req)
    AUDIT.append({'id':result.audit_id,'type':'grounded_query','question':req.question,'as_of':req.as_of,'matched_commitments':[c.id for c in result.commitments]})
    return result
