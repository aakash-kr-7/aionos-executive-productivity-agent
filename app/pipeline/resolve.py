"""Stage 3 — Entity & Person Resolution.

Resolves names ("Arjun", "Raghav", "Priya"), email addresses, and
organisational references ("Facilities", "All Staff") to canonical person
records from the data pack's people directory.
"""
from __future__ import annotations
from .extract import CandidateCommitment


def _build_lookup(people_list: list[dict]) -> dict[str, dict]:
    """Build a fast lookup table: lowercase first-name, full name, and email → person record."""
    lookup: dict[str, dict] = {}
    for p in people_list:
        lookup[p['email'].lower()] = p
        lookup[p['name'].lower()] = p
        first = p['name'].split()[0].lower()
        if first not in lookup:  # avoid overwriting if two people share a first name
            lookup[first] = p
    # Org aliases
    lookup['all'] = {'name': 'All Staff', 'role': 'Internal distribution list', 'email': 'all'}
    lookup['all staff'] = lookup['all']
    return lookup


def resolve_people(
    candidates: list[CandidateCommitment],
    people_list: list[dict],
) -> tuple[list[CandidateCommitment], list[dict]]:
    """Resolve mentioned people names to canonical records.

    Mutates candidates in-place by normalising their ``mentioned_people``
    to canonical full names, and returns a log entry.
    """
    lookup = _build_lookup(people_list)
    resolved_count = 0

    for cand in candidates:
        resolved: list[str] = []
        for name in cand.mentioned_people:
            key = name.lower().strip()
            if key in lookup:
                resolved.append(lookup[key]['name'])
                resolved_count += 1
            else:
                resolved.append(name)  # keep original if unresolved
        cand.mentioned_people = list(dict.fromkeys(resolved))  # dedup, preserve order

        # Also resolve the speaker
        sp = cand.source_signal.speaker
        if sp:
            sp_key = sp.lower().strip()
            if sp_key in lookup:
                cand.source_signal.speaker = lookup[sp_key]['name']

    log = [{
        'stage': 'resolve',
        'resolved_count': resolved_count,
        'detail': f'Resolved {resolved_count} person references across {len(candidates)} candidates',
    }]
    return candidates, log
