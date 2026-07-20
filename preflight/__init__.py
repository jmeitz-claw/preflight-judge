"""preflight-judge — an adversarial pre-flight panel that refutes weak candidate
experiments before you spend money/compute running them.

    from preflight import screen, survivors, PanelConfig

    candidates = [
        {"id": "prompt-A", "observations": [{"value": 1, "ts": 1, "id": "s1"}, ...]},
        {"id": "prompt-B", "observations": [...]},
    ]
    for r in screen(candidates):
        print(r.candidate_id, r.survived, r.summary)

    # or just keep the ones worth running:
    keep = survivors(candidates)

Perspective-diverse judges (bootstrap stability, temporal robustness, redundancy,
practical haircut), deterministic, pure stdlib. It refutes; it never runs your
experiment.
"""
from .config import PanelConfig
from .panel import (
    Verdict,
    PanelResult,
    screen,
    screen_candidate,
    survivors,
    percentile,
    judge_bootstrap_stability,
    judge_temporal_robustness,
    judge_redundancy,
    judge_practical_haircut,
)

__version__ = "0.1.0"

__all__ = [
    "PanelConfig",
    "Verdict",
    "PanelResult",
    "screen",
    "screen_candidate",
    "survivors",
    "percentile",
    "judge_bootstrap_stability",
    "judge_temporal_robustness",
    "judge_redundancy",
    "judge_practical_haircut",
    "__version__",
]
