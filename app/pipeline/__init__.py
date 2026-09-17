"""Executive Productivity Agent — Multi-stage extraction pipeline.

Pipeline stages:
  1. ingest     — Normalize raw sources into signals
  2. extract    — Detect commitment candidates via pattern matching
  3. resolve    — Map names/emails to canonical person records
  4. temporal   — Resolve relative deadline phrases to absolute datetimes
  5. reconcile  — Cross-source deduplication and merge
  6. classify   — Ownership classification (my_action / waiting / unclear)
  7. status     — Dynamic status calculation relative to as_of date
  8. prioritize — Sort by attention urgency and produce final output

Every stage returns a log entry for the full pipeline audit trail.
The pipeline is fully deterministic — same input + as_of → same output.
"""
from __future__ import annotations
from ..models import PipelineResult
from .ingest import ingest
from .extract import extract
from .resolve import resolve_people
from .temporal import resolve_deadlines
from .reconcile import reconcile
from .classify import classify_ownership
from .status import compute_status
from .prioritize import prioritize


def run_pipeline(data: dict, as_of: str = '2026-09-23') -> PipelineResult:
    """Execute the full extraction pipeline and return structured results.

    Parameters
    ----------
    data : dict
        The parsed source_data.json content.
    as_of : str
        ISO date string determining the "current" day for status calculations.
    """
    pipeline_log: list[dict] = []
    people_list = data['metadata']['people']
    people_names = [p['name'] for p in people_list]
    user = data['metadata']['user']
    exercise_week = data['metadata']['exercise_week']

    # Stage 1: Ingest
    signals, ingest_log = ingest(data)
    pipeline_log.extend(ingest_log)

    # Stage 2: Extract
    candidates, extract_log = extract(signals, people_names)
    pipeline_log.extend(extract_log)

    # Stage 3: Resolve people
    candidates, resolve_log = resolve_people(candidates, people_list)
    pipeline_log.extend(resolve_log)

    # Stage 4: Temporal normalization
    candidates, temporal_log = resolve_deadlines(candidates, exercise_week)
    pipeline_log.extend(temporal_log)

    # Stage 5: Reconciliation / deduplication
    groups, reconcile_log = reconcile(candidates, signals)
    pipeline_log.extend(reconcile_log)

    # Stage 6: Ownership classification
    classified, classify_log = classify_ownership(groups, user)
    pipeline_log.extend(classify_log)

    # Stage 7: Status calculation
    with_status, status_log = compute_status(classified, as_of)
    pipeline_log.extend(status_log)

    # Stage 8: Prioritization and output conversion
    commitments = prioritize(with_status)

    return PipelineResult(
        commitments=commitments,
        pipeline_log=pipeline_log,
        signal_count=len(signals),
        candidate_count=len(candidates),
        reconciled_count=len(groups),
    )
