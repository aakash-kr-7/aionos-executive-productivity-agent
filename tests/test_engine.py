from app.engine import brief

def test_core_commitments():
    cs=brief('2026-09-23')
    assert len(cs)==5
    assert any(c.subject=='Updated vendor list' and c.action_type=='my_action' for c in cs)
    assert any(c.subject=='Mumbai office lease renewal' and c.action_type=='unclear_ownership' for c in cs)

def test_vendor_deadline_is_wed_morning():
    c=next(c for c in brief() if c.subject=='Updated vendor list')
    assert 'Wednesday' in c.deadline_label

def test_lease_never_invents_owner():
    c=next(c for c in brief() if 'lease' in c.subject.lower())
    assert c.owner is None
    assert c.status=='ambiguous'

def test_completed_meridian():
    c=next(c for c in brief() if 'Meridian' in c.subject)
    assert c.status=='completed'
