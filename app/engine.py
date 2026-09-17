"""Engine — thin orchestration wrapper around the pipeline.

Loads the supplied data pack once at import time and provides
``brief(as_of)`` as the primary entry point used by the API layer.
"""
from __future__ import annotations
import json
from pathlib import Path
from .models import Commitment, PipelineResult
from .pipeline import run_pipeline

DATA = json.loads(
    (Path(__file__).parent.parent / 'data' / 'source_data.json')
    .read_text(encoding='utf-8')
)
PEOPLE = {p['email']: p['name'] for p in DATA['metadata']['people']}

# Cache to avoid re-running pipeline for identical inputs
_cache: dict[str, PipelineResult] = {}


def _pipeline(as_of: str = '2026-09-23') -> PipelineResult:
    """Run the pipeline, with a simple in-process cache."""
    if as_of not in _cache:
        _cache[as_of] = run_pipeline(DATA, as_of)
    return _cache[as_of]


def brief(as_of: str = '2026-09-23') -> list[Commitment]:
    """Return prioritized commitments for the daily brief."""
    return _pipeline(as_of).commitments


def pipeline_result(as_of: str = '2026-09-23') -> PipelineResult:
    """Return the full pipeline result including audit log."""
    return _pipeline(as_of)
