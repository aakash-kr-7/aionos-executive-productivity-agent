from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health():
    r=client.get('/api/health'); assert r.status_code==200; assert r.json()['status']=='ok'

def test_query_raghav():
    r=client.post('/api/query',json={'question':'What did I promise Raghav?','as_of':'2026-09-23'})
    assert r.status_code==200
    j=r.json(); assert any(c['subject']=='Updated vendor list' for c in j['commitments'])
    assert 'Raghav' in j['answer'] or 'vendor list' in j['answer']
