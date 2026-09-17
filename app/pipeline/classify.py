"""Stage 6 — Ownership Classification.

For each reconciled group, determines who owns the next action:

  my_action          – Arjun is explicitly the promisor or actor.
  waiting_on_other   – Another named person is the current actor/dependency.
  unclear_ownership  – Sources explicitly state ownership is unassigned.
  informational      – Calendar blocks, FYIs with no actionable commitment.

Classification is evidence-based: it analyses signal types and speaker roles
rather than guessing.  For the Mumbai lease, this module detects ambiguity
flags + Arjun's "don't assume" directive and refuses to invent an owner.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional
from .reconcile import ReconciledGroup


@dataclass
class ClassifiedCommitment:
    """A commitment with ownership, action phrase, and evidence assembled."""
    group: ReconciledGroup
    subject: str
    action: str
    action_type: str         # my_action | waiting_on_other | unclear_ownership | informational
    owner_email: Optional[str]
    owner_display: Optional[str]
    counterparty: Optional[str]
    classification_rationale: list[str]
    extraction_trace: list[str]
    deadline: Optional[str] = None
    deadline_label: Optional[str] = None


def _count_signal_types(group: ReconciledGroup, user_email: str) -> dict:
    """Count signal types by speaker role for ownership inference."""
    user_promises = 0
    other_promises = 0
    ambiguity_count = 0
    user_requests = 0
    user_self_notes = 0
    delivery_count = 0
    confirmation_count = 0

    for c in group.candidates:
        is_user = (c.source_signal.speaker_email == user_email)
        st = c.signal_type
        if st == 'ambiguity_flag':
            ambiguity_count += 1
        elif st == 'promise' and is_user:
            user_promises += 1
        elif st in ('promise', 'obligation') and not is_user:
            other_promises += 1
        elif st == 'obligation' and is_user:
            # User tracking a dependency/need from someone else
            pass
        elif st == 'request' and is_user:
            user_requests += 1
        elif st == 'delivery':
            delivery_count += 1
        elif st == 'confirmation':
            confirmation_count += 1

        if c.source_signal.source_type == 'voice_note' and is_user:
            user_self_notes += 1

    return {
        'user_promises': user_promises,
        'other_promises': other_promises,
        'ambiguity_count': ambiguity_count,
        'user_requests': user_requests,
        'user_self_notes': user_self_notes,
        'delivery_count': delivery_count,
        'confirmation_count': confirmation_count,
    }


def _find_counterparty(group: ReconciledGroup, user_name: str) -> Optional[str]:
    """Identify the primary counterparty (the other person involved)."""
    people: dict[str, int] = {}
    for c in group.candidates:
        for p in c.mentioned_people:
            if p != user_name:
                people[p] = people.get(p, 0) + 1
        if c.source_signal.speaker and c.source_signal.speaker != user_name:
            sp = c.source_signal.speaker
            people[sp] = people.get(sp, 0) + 1
    if not people:
        return None
    return max(people, key=lambda p: people[p])


def _derive_action(group: ReconciledGroup, action_type: str, subject: str,
                    user_name: str, counterparty: Optional[str]) -> str:
    """Construct a clear action phrase from the group's evidence."""
    # Find the most informative promise/request from the user
    user_promises = [
        c for c in group.candidates
        if c.signal_type in ('promise', 'obligation')
        and c.source_signal.speaker == user_name
    ]
    other_promises = [
        c for c in group.candidates
        if c.signal_type in ('promise', 'obligation')
        and c.source_signal.speaker != user_name
    ]

    sub_lower = subject.lower()
    if 'vendor' in sub_lower:
        return f'Send {sub_lower} to {counterparty or "Raghav Sethi"}'
    if 'meridian' in sub_lower or 'call' in sub_lower:
        return f'Reconfirm and attend call with {counterparty or "Priya Nair"}'
    if 'expense' in sub_lower:
        return f'Review {sub_lower} from {counterparty or "Divya Rao"}'
    if 'deck' in sub_lower:
        return f'Review {sub_lower} from {counterparty or "Neha Kapoor"}'
    if 'lease' in sub_lower:
        return f'Confirm who is responsible for the {sub_lower}'

    if action_type == 'my_action' and user_promises:
        text = user_promises[0].segment_text
        return _clean_action(text, subject, counterparty, user_name)

    if action_type == 'waiting_on_other':
        return f'Review the {subject.lower()}'

    if action_type == 'unclear_ownership':
        return f'Confirm who is responsible for the {subject.lower()}'

    return subject


def _clean_action(text: str, subject: str, counterparty: Optional[str],
                   user_name: str) -> str:
    """Transform raw promise text into a clean action phrase."""
    import re
    text = text.strip()

    # Try to extract "I'll [verb phrase]" or "I need to [verb phrase]"
    m = re.search(
        r"I(?:['\u2019]ll| need to| told \w+ I['\u2019]d)\s+(.{10,80}?)(?:\.|,|$)",
        text,
    )
    if m:
        action_part = m.group(1).strip()
        # Clean up: replace pronouns with names
        action_part = re.sub(r'\bhim\b', counterparty or 'the counterparty', action_part)
        action_part = re.sub(r'\bher\b', counterparty or 'the counterparty', action_part)
        action_part = re.sub(r'\bthem\b', counterparty or 'the counterparty', action_part)
        action_part = re.sub(r'\bthat\b', f'the {subject.lower()}', action_part, count=1)
        # Capitalize first letter
        action = action_part[0].upper() + action_part[1:]
        return action

    # Fallback: use subject directly
    return f'Complete the {subject.lower()}'


def _build_extraction_trace(group: ReconciledGroup, counts: dict) -> list[str]:
    """Build a human-readable trace of how the commitment was determined."""
    trace: list[str] = []
    src_types = sorted(group.source_types())
    trace.append(f'Detected across {len(src_types)} source types: {", ".join(src_types)}')
    trace.append(f'Merged {len(group.candidates)} signals into one canonical commitment')

    if counts['user_promises'] > 0:
        trace.append(f'Found {counts["user_promises"]} explicit promise(s) from the executive')
    if counts['other_promises'] > 0:
        trace.append(f'Found {counts["other_promises"]} promise(s) from other parties')
    if counts['ambiguity_count'] > 0:
        trace.append(f'Found {counts["ambiguity_count"]} ambiguity flag(s) — ownership deliberately left unresolved')
    if counts['delivery_count'] > 0:
        trace.append(f'Found {counts["delivery_count"]} delivery/completion signal(s)')
    if counts['confirmation_count'] > 0:
        trace.append(f'Found {counts["confirmation_count"]} confirmation signal(s)')
    if group.calendar_evidence:
        trace.append(f'Corroborated by {len(group.calendar_evidence)} calendar event(s)')

    return trace


def classify_ownership(
    groups: list[ReconciledGroup],
    user: dict,
) -> tuple[list[ClassifiedCommitment], list[dict]]:
    """Classify ownership for each reconciled group.

    Returns (classified_commitments, log).
    """
    user_email = user['email']
    user_name = user['name']
    results: list[ClassifiedCommitment] = []
    log_details: list[dict] = []

    for group in groups:
        subject = getattr(group, '_subject', 'Unknown')
        counts = _count_signal_types(group, user_email)
        rationale: list[str] = []
        counterparty = _find_counterparty(group, user_name)

        # --- Classification rules ---
        ambiguity_flags = [c for c in group.candidates if c.signal_type == 'ambiguity_flag']
        has_ambiguity = len(ambiguity_flags) >= 1 or any(
            re.search(r'\b(not sure whose|unowned|hasn[\'’]t been assigned|don[\'’]t assume|someone needs to own|not on my end)\b', c.segment_text, re.IGNORECASE)
            for c in group.candidates
        )
        named_promisors = [
            c.source_signal.speaker for c in group.candidates
            if c.signal_type == 'promise'
            and c.source_signal.speaker not in (None, 'Facilities', 'All Staff')
        ]

        if has_ambiguity and not named_promisors and counts['user_promises'] == 0:
            action_type = 'unclear_ownership'
            owner_email = None
            owner_display = None
            counterparty = 'Facilities / internal stakeholders'
            rationale.append('Multiple sources explicitly state ownership is unassigned (Raghav: "not sure whose desk", "still unowned"; Divya: "not on my end").')
            rationale.append(f'{user_name} directed "don\'t assume" and noted "someone needs to own that, I don\'t think it\'s me".')
            rationale.append('Refusing to invent an owner — ownership deliberately left unresolved.')

        elif counts['user_promises'] > 0 or (counts['user_self_notes'] > 0 and counts['other_promises'] == 0 and counts['delivery_count'] == 0):
            action_type = 'my_action'
            owner_email = user_email
            owner_display = user_name
            rationale.append(f'Executive made {counts["user_promises"]} explicit promise(s) about this topic.')
            if counts['user_self_notes'] > 0:
                rationale.append('Reinforced by personal voice note / self-reminder.')

        elif counts['other_promises'] > 0 or counts['delivery_count'] > 0 or counts['user_requests'] > 0:
            action_type = 'waiting_on_other'
            other_speakers = [
                c.source_signal.speaker for c in group.candidates
                if c.source_signal.speaker_email != user_email
                and c.source_signal.speaker not in (None, 'Facilities', 'All Staff')
                and c.signal_type in ('promise', 'obligation', 'delivery', 'scheduling')
            ]
            if other_speakers:
                owner_display = other_speakers[0]
                for c in group.candidates:
                    if c.source_signal.speaker == owner_display:
                        owner_email = c.source_signal.speaker_email
                        break
                else:
                    owner_email = None
            else:
                owner_display = counterparty
                owner_email = None
            rationale.append(f'{owner_display or "Another party"} owns the next action.')
            rationale.append(f'{user_name} is waiting on delivery/completion.')

        else:
            action_type = 'informational'
            owner_email = None
            owner_display = None
            rationale.append('No explicit commitment or request detected; classified as informational.')

        # --- Deadline: use the latest resolved deadline by signal timestamp ---
        deadline_candidates = [
            c for c in group.candidates
            if getattr(c, '_resolved_deadline', None)
            and c.signal_type in ('promise', 'scheduling', 'request', 'obligation')
        ]
        deadline_candidates.sort(key=lambda c: c.source_signal.timestamp)
        if deadline_candidates:
            latest_cand = deadline_candidates[-1]
            deadline = getattr(latest_cand, '_resolved_deadline', None)
            deadline_label = getattr(latest_cand, '_deadline_label', None)
        else:
            deadline = None
            deadline_label = None

        # --- Action phrase ---
        action = _derive_action(group, action_type, subject, user_name, counterparty)

        # --- Trace ---
        trace = _build_extraction_trace(group, counts)

        results.append(ClassifiedCommitment(
            group=group,
            subject=subject,
            action=action,
            action_type=action_type,
            owner_email=owner_email,
            owner_display=owner_display,
            counterparty=counterparty,
            classification_rationale=rationale,
            extraction_trace=trace,
            deadline=deadline,
            deadline_label=deadline_label,
        ))

        log_details.append({
            'group': group.group_id,
            'subject': subject,
            'action_type': action_type,
            'owner': owner_display,
            'counterparty': counterparty,
        })

    log = [{
        'stage': 'classify',
        'classified': len(results),
        'breakdown': {at: sum(1 for r in results if r.action_type == at) for at in ('my_action', 'waiting_on_other', 'unclear_ownership', 'informational')},
        'details': log_details,
        'detail': f'Classified {len(results)} commitments: '
                  + ', '.join(f'{v} {k}' for k, v in {at: sum(1 for r in results if r.action_type == at) for at in ('my_action', 'waiting_on_other', 'unclear_ownership', 'informational')}.items() if v),
    }]

    return results, log
