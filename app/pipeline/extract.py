"""Stage 2 — Signal Extraction → Commitment Candidates.

Scans each NormalizedSignal using deterministic, regex-based pattern
extractors to identify commitment candidates.  Patterns detect:

  - First-person promises ("I'll …", "I told X I'd …")
  - Requests / follow-ups ("can you …", "following up")
  - Deliveries ("attached", "sent as promised")
  - Confirmations ("confirmed", "see you at")
  - Schedule changes ("shifting to …", "let's say …")
  - Ambiguity flags ("not sure who", "don't assume")
  - Obligations / reminders ("requires", "needs … by")

Voice notes are split at topic boundaries so multi-topic memos produce
separate candidates.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional
from .ingest import NormalizedSignal


@dataclass
class CandidateCommitment:
    """A single extracted commitment candidate from a source signal."""
    candidate_id: str
    topic_tokens: list[str]
    action_phrase: str
    signal_type: str  # promise | request | delivery | confirmation | scheduling | ambiguity_flag | obligation
    source_signal: NormalizedSignal
    mentioned_people: list[str]
    deadline_phrase: Optional[str]
    confidence: float
    extraction_rationale: str
    segment_text: str


# ── Stop words for topic-token extraction ──────────────────────────────
_STOP = frozenset(
    'i me my we our you your he she it they the a an is are was were be been '
    'being have has had do does did will would could should may might can shall '
    'need to of in for on with at by from as into about that this but and or '
    'not no if so just also then than too very think get got going ll d ve s t '
    'up out still said saying know want see let make take come go back one re '
    'done told send check ahead instead quick note self remind end day sure '
    'thing someone anyone whoever something ready actually heads say more than '
    'think believe suppose got pulled really guess safely doable tight works '
    'good no worries whenever chance propose apologies delay understand '
    'understood exactly needed thank yes am pm'.split()
)

# ── Pattern tables (regex, rationale) ──────────────────────────────────
PROMISE_PATTERNS: list[tuple[str, str]] = [
    (r"I told \w+ I['\u2019]d\s+.{5,60}", 'Reported first-person promise'),
    (r"I['\u2019]ll get (?:that |it )?to\s+.{3,30}", 'Promise to deliver to someone'),
    (r"I['\u2019]ll have .{5,60} ready", 'Promise to prepare/deliver'),
    (r"I['\u2019]ll\s+\w+.{5,60}", 'First-person future commitment'),
    (r"I need to \w+.{5,60}", 'First-person obligation'),
    (r"I owe \w+", 'Acknowledged debt/obligation'),
    (r"\b(?:I\s+)?will (?:send|have|get|deliver|provide|share|prioritize)\b.{3,60}", 'First-person future action promise'),
    (r"\b(?:will|shall)\s+(?:send|have|get|deliver|provide|share)\b.{3,60}", 'Future action promise'),
    (r"\bremind me\b", 'Self-reminder indicating pending obligation'),
    (r"\bneed to (?:get|send|lock|finish|complete|prepare)\b.{3,60}", 'Self-obligation'),
]

REQUEST_PATTERNS: list[tuple[str, str]] = [
    (r"[Cc]an you \w+.{5,60}", 'Direct request'),
    (r"[Cc]an I get .{5,60}", 'Request with possible deadline'),
    (r"[Ff]ollowing up\b", 'Follow-up request'),
    (r"[Jj]ust checking\b", 'Follow-up check'),
    (r"\bstill (?:good|on) for\b", 'Confirmation request'),
]

DELIVERY_PATTERNS: list[tuple[str, str]] = [
    (r"\b[Rr]eport attached\b", 'Report delivery'),
    (r"\b[Dd]eck is ready\b", 'Deliverable completion'),
    (r"\b[Ss]ent as promised\b", 'Confirmed delivery'),
    (r"\b[Aa]ttach(?:ed|ing)\b.{0,30}(?:draft|report|deck|document|file)?", 'Delivery via attachment'),
    (r"\bexactly what I needed\b", 'Receipt acknowledgment'),
]

CONFIRMATION_PATTERNS: list[tuple[str, str]] = [
    (r"\b[Cc]onfirmed\b", 'Explicit confirmation'),
    (r"\b[Ss]ee you at\b", 'Meeting confirmation'),
    (r"\bworks (?:on our end|for (?:me|us))\b", 'Schedule acceptance'),
]

SCHEDULING_PATTERNS: list[tuple[str, str]] = [
    (r"[Ss]hifting .{3,40} to .{5,30}", 'Schedule change'),
    (r"[Hh]ow about .{5,30}", 'Schedule proposal'),
    (r"[Ll]et['\u2019]s say .{5,30}", 'Schedule proposal'),
    (r"[Tt]argeting .{5,30}", 'Schedule target'),
    (r"[Rr]ealistically .{5,40} (?:is )?safer", 'Schedule revision'),
]

AMBIGUITY_PATTERNS: list[tuple[str, str]] = [
    (r"[Nn]ot sure (?:who|whose)\b", 'Ownership uncertainty'),
    (r"\bdon['\u2019]t assume\b", 'Explicit non-assignment directive'),
    (r"\bhasn['\u2019]t been assigned\b", 'Unassigned flag'),
    (r"\bstill unowned\b", 'Unowned flag'),
    (r"\bhaven['\u2019]t seen anyone pick it up\b", 'Unassigned observation'),
    (r"\bdon['\u2019]t think it['\u2019]s (?:me|been)\b", 'Ownership denial'),
    (r"\b[Nn]ot on my end\b", 'Ownership denial'),
    (r"\bsomeone needs to own\b", 'Ownership gap'),
    (r"\bflag it\b", 'Ambiguity flagging directive'),
]

OBLIGATION_PATTERNS: list[tuple[str, str]] = [
    (r"\b[Rr]equires .{5,60}", 'External requirement/obligation'),
    (r"\b[Rr]eminder:", 'Reminder of existing obligation'),
    (r"\bneeds to be\b.{3,60}", 'Stated need/requirement'),
    (r"\bstill pending\b", 'Pending status'),
    (r"\b[Dd]eadline is\b", 'Deadline statement'),
]

DEADLINE_PHRASES: list[str] = [
    r"\b\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)\s*(?:on\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|tomorrow|today)?\b",
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|tomorrow|today)\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)\b",
    r"(?:by |before |targeting )?(?:end of day\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|tomorrow|today)(?:\s*\([A-Za-z]+\))?\s*(?:morning|afternoon|evening|EOD|end of day)?",
    r"\b(?:first thing\s+)?(?:tomorrow|today)\s+(?:morning|afternoon|evening|EOD|end of day)\b",
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|tomorrow|today)\s+(?:morning|afternoon|evening|EOD|end of day)\b",
    r"\b(?:tomorrow\s*\([A-Za-z]+\)\s*(?:morning|afternoon|evening|EOD|end of day)?)\b",
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday),?\s*\d{1,2}\s*(?:September|Sep)(?:,?\s*end of day)?",
    r"\bthis (?:week|Friday)\b",
    r"\b(?:Wednesday|Thursday|Friday)\s+(?:morning|evening|afternoon)\b",
    r"\bend of day\b",
]


# ── Extraction helpers ─────────────────────────────────────────────────

def _extract_topic_tokens(text: str) -> list[str]:
    """Extract significant words from text for topic identification."""
    clean = re.sub(r"[^\w\s-]", ' ', text.lower())
    return [w for w in clean.split() if w not in _STOP and len(w) >= 3]


def _extract_people(text: str, people_names: list[str]) -> list[str]:
    """Find people mentioned in text by name or first name."""
    found: list[str] = []
    text_lower = text.lower()
    for name in people_names:
        first = name.split()[0].lower()
        if name.lower() in text_lower or first in text_lower:
            if name not in found:
                found.append(name)
    return found


def _extract_deadline_phrase(text: str) -> Optional[str]:
    """Extract the first deadline-related phrase from text."""
    for pattern in DEADLINE_PHRASES:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def _match_patterns(text: str, patterns: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """Return (signal_type_ignored, matched_text, rationale) for each match."""
    results: list[tuple[str, str, str]] = []
    for pattern, rationale in patterns:
        m = re.search(pattern, text)
        if m:
            results.append(('', m.group(0), rationale))
    return results


def _segment_voice_note(text: str) -> list[str]:
    """Split a voice note into topic segments at natural boundaries."""
    segments = re.split(r'\.\s+[Aa]lso\s+', text)
    result: list[str] = []
    for seg in segments:
        result.append(seg.strip())
    return [s for s in result if len(s) >= 15]


# ── Main extraction entry point ───────────────────────────────────────

def extract(signals: list[NormalizedSignal], people_names: list[str]
            ) -> tuple[list[CandidateCommitment], list[dict]]:
    """Extract commitment candidates from normalized signals.

    Returns (candidates, log_entries).
    """
    candidates: list[CandidateCommitment] = []
    log: list[dict] = []
    cidx = 0

    for signal in signals:
        # Calendar constraints are used for corroboration, not primary extraction
        if signal.is_constraint:
            continue

        # Voice notes may contain multiple topics
        if signal.source_type == 'voice_note':
            segments = _segment_voice_note(signal.raw_text)
        else:
            segments = [signal.raw_text]

        for segment in segments:
            detections: list[tuple[str, str, str]] = []  # (type, matched, rationale)

            for signal_type, patterns in [
                ('ambiguity_flag', AMBIGUITY_PATTERNS),
                ('obligation', OBLIGATION_PATTERNS),
                ('promise', PROMISE_PATTERNS),
                ('delivery', DELIVERY_PATTERNS),
                ('confirmation', CONFIRMATION_PATTERNS),
                ('request', REQUEST_PATTERNS),
                ('scheduling', SCHEDULING_PATTERNS),
            ]:
                for _pat, matched_text, rat in _match_patterns(segment, patterns):
                    detections.append((signal_type, matched_text, rat))

            if not detections:
                continue

            # Determine primary signal type by priority order
            type_priority = {
                'ambiguity_flag': 0, 'promise': 1, 'obligation': 2,
                'delivery': 3, 'confirmation': 4, 'request': 5, 'scheduling': 6,
            }
            detections.sort(key=lambda d: type_priority.get(d[0], 99))
            primary_type = detections[0][0]

            topic_tokens = _extract_topic_tokens(segment)
            mentioned = _extract_people(segment, people_names)
            deadline_phrase = _extract_deadline_phrase(segment)

            all_rationales = [f'{d[0]}: {d[2]} (matched: "{d[1][:60]}")' for d in detections]
            confidence = 0.85 if len(detections) == 1 else min(0.95, 0.80 + 0.03 * len(detections))

            candidates.append(CandidateCommitment(
                candidate_id=f'cand_{cidx:04d}',
                topic_tokens=topic_tokens,
                action_phrase=segment[:250],
                signal_type=primary_type,
                source_signal=signal,
                mentioned_people=mentioned,
                deadline_phrase=deadline_phrase,
                confidence=confidence,
                extraction_rationale='; '.join(all_rationales),
                segment_text=segment,
            ))
            cidx += 1

    type_counts: dict[str, int] = {}
    for c in candidates:
        type_counts[c.signal_type] = type_counts.get(c.signal_type, 0) + 1

    log.append({
        'stage': 'extract',
        'total_signals_processed': sum(1 for s in signals if not s.is_constraint),
        'candidates_produced': len(candidates),
        'signal_type_breakdown': type_counts,
        'detail': f'Extracted {len(candidates)} commitment candidates from {sum(1 for s in signals if not s.is_constraint)} non-calendar signals',
    })
    return candidates, log
