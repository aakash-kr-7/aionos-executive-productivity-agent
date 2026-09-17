from __future__ import annotations
import json, re, hashlib
from datetime import date, datetime
from pathlib import Path
from .models import Commitment, Evidence

DATA = json.loads((Path(__file__).parent.parent / 'data' / 'source_data.json').read_text(encoding='utf-8'))
PEOPLE = {p['email']: p['name'] for p in DATA['metadata']['people']}
PEOPLE.update({'All':'All Staff','facilities@veridian-corp.example':'Facilities'})


def ev(source_id, source_type, d, title, excerpt):
    return Evidence(source_id=source_id, source_type=source_type, date=d[:10], title=title, excerpt=excerpt)


def cid(subject):
    return hashlib.sha1(subject.lower().encode()).hexdigest()[:10]


def build_commitments():
    out=[]
    # Canonical commitments are deliberately explicit: this is a small assessment dataset and explicit rules make the demo auditable.
    vendor_e=[
        ev('meeting_leadership_sync','meeting','2026-09-21','Leadership Sync','Arjun: I told Raghav I’d send him the updated vendor list. I’ll get that to him by end of day tomorrow.'),
        ev('email_vendor_list_2','email','2026-09-21','Vendor List','Running behind, will send first thing tomorrow morning instead.'),
        ev('email_vendor_list_4','email','2026-09-22','Vendor List','Sorry, got pulled into board prep — will send by tomorrow (Wednesday) morning for sure.'),
        ev('voice_note_1','voice_note','2026-09-21','Personal voice memo — Monday 21 Sep','Need to get Raghav that vendor list... remind me.')]
    out.append(Commitment(id=cid('vendor list'),subject='Updated vendor list',action='Send the updated vendor list to Raghav Sethi',action_type='my_action',owner='arjun.malhotra@veridian-corp.example',owner_display='Arjun Malhotra',counterparty='Raghav Sethi',deadline='2026-09-23T09:00',deadline_label='Wednesday morning',status='stale',confidence=.99,evidence=vendor_e,rationale=['Explicit first-person promise in the leadership sync.','Repeated by Arjun in email and voice note.','Latest evidence on Wed 23 Sep at 08:45 asks whether it is still happening this morning.']))

    deck_e=[
        ev('email_campaign_deck_1','email','2026-09-21','Q3 Campaign Deck','Still targeting Wednesday for your review.'),
        ev('email_campaign_deck_2','email','2026-09-22','Q3 Campaign Deck','Shifting the review to Thursday morning instead of Wednesday.'),
        ev('email_campaign_deck_4','email','2026-09-23','Q3 Campaign Deck','Let’s say 9:30 AM Thursday, before your board prep block.'),
        ev('calendar_arjun_deck','calendar','2026-09-24','Arjun calendar','09:00–10:00 Board Prep Session')]
    out.append(Commitment(id=cid('campaign deck review'),subject='Q3 campaign deck review',action='Review the Q3 campaign deck',action_type='waiting_on_other',owner='neha.kapoor@veridian-corp.example',owner_display='Neha Kapoor',counterparty='Arjun Malhotra',deadline='2026-09-24T09:30',deadline_label='Thursday 9:30 AM',status='open',confidence=.98,evidence=deck_e,rationale=['Neha owns delivery of the deck; Arjun owns the review.','The latest thread fixes the review at Thursday 9:30 AM.','The calendar contains a matching Deck Review with Arjun.']))

    call_e=[
        ev('meeting_leadership_sync','meeting','2026-09-21','Leadership Sync','Arjun: I need to reconfirm the new time with their team myself.'),
        ev('email_call_reschedule_1','email','2026-09-21','Call Reschedule','Can you propose a new time? We’re flexible Tuesday–Thursday afternoons.'),
        ev('email_call_reschedule_2','email','2026-09-22','Call Reschedule','How about Wednesday 3:00 PM?'),
        ev('email_call_reschedule_3','email','2026-09-22','Call Reschedule','Wednesday 3 PM works on our end, confirmed.'),
        ev('email_call_reschedule_5','email','2026-09-23','Call Reschedule','Yes, confirmed, see you at 3.'),
        ev('calendar_meridian','calendar','2026-09-23','Arjun calendar','15:00–15:30 Call — Meridian Logistics')]
    out.append(Commitment(id=cid('meridian call'),subject='Meridian Logistics call',action='Reconfirm / lock the Meridian Logistics call time with Priya Nair',action_type='my_action',owner='arjun.malhotra@veridian-corp.example',owner_display='Arjun Malhotra',counterparty='Priya Nair',deadline='2026-09-23T15:00',deadline_label='Wednesday 3:00 PM',status='completed',confidence=.99,evidence=call_e,rationale=['Arjun explicitly says he owes the time and needs to lock it in.','Priya confirms Wednesday 3 PM.','Arjun reconfirms at 2:00 PM and the calendar has the 3:00 PM call.']))

    expense_e=[
        ev('meeting_leadership_sync','meeting','2026-09-21','Leadership Sync','Divya: I’ll have it ready Wednesday evening.'),
        ev('email_expense_variance_2','email','2026-09-22','Expense Variance Report','Can I get it by Wednesday evening instead? Want time to review before Thursday.'),
        ev('email_expense_variance_4','email','2026-09-23','Expense Variance Report','Report attached, sent as promised.'),
        ev('voice_note_2','voice_note','2026-09-23','Personal voice memo — Wednesday 23 Sep','Expense variance report from Divya needs to be in my hands by Wednesday evening.')]
    out.append(Commitment(id=cid('expense variance'),subject='July expense variance report',action='Review the July expense variance report before board prep',action_type='my_action',owner='arjun.malhotra@veridian-corp.example',owner_display='Arjun Malhotra',counterparty='Divya Rao',deadline='2026-09-24T09:00',deadline_label='Before Thursday board prep',status='open',confidence=.98,evidence=expense_e,rationale=['Divya delivered the report Wednesday evening.','Arjun explicitly wanted time to review it before Thursday.','Thursday 9:00–10:00 AM is the Board Prep Session, making the stated review dependency time-sensitive.']))

    lease_e=[
        ev('meeting_leadership_sync','meeting','2026-09-21','Leadership Sync','Arjun: Okay, flag it, don’t assume.'),
        ev('email_mumbai_lease_1','email','2026-09-21','Mumbai Office Lease Renewal','Requires an authorized signature by Friday, 25 September.'),
        ev('email_mumbai_lease_2','email','2026-09-22','Mumbai Office Lease Renewal','Has anyone confirmed who’s signing off? Don’t think it’s been assigned.'),
        ev('email_mumbai_lease_3','email','2026-09-23','Mumbai Office Lease Renewal','Not on my end — I believe this typically sits with Facilities directly, not us.'),
        ev('email_mumbai_lease_4','email','2026-09-24','Mumbai Office Lease Renewal','Signature is still pending. Deadline is Friday, 25 September, end of day.'),
        ev('email_mumbai_lease_5','email','2026-09-24','Mumbai Office Lease Renewal','This is now one day out and still unowned — can you confirm who’s handling it?'),
        ev('voice_note_1','voice_note','2026-09-21','Personal voice memo — Monday 21 Sep','Someone needs to own that, I don’t think it’s me.')]
    out.append(Commitment(id=cid('mumbai lease'),subject='Mumbai office lease renewal',action='Confirm who is authorized to sign off on the Mumbai office lease renewal',action_type='unclear_ownership',owner=None,owner_display=None,counterparty='Facilities / internal stakeholders',deadline='2026-09-25T17:00',deadline_label='Friday 25 Sep, end of day',status='ambiguous',confidence=.99,evidence=lease_e,rationale=['The deadline and pending signature are explicit.','The sources explicitly say ownership has not been assigned.','Divya says she believes it typically sits with Facilities, but Arjun said not to assume.']))

    # Informational/closed items can still be surfaced in the audit graph.
    return out


def brief(as_of='2026-09-23'):
    commitments=build_commitments()
    d=date.fromisoformat(as_of)
    def key(c):
        urgency=0
        if c.status=='stale': urgency=-3
        elif c.action_type=='unclear_ownership': urgency=-2
        elif c.status=='open': urgency=-1
        return (urgency,c.deadline or '9999')
    commitments=sorted(commitments,key=key)
    return commitments
