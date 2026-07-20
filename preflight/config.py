"""Configuration for the adversarial pre-flight judge panel.

Every knob the panel uses is a field on :class:`PanelConfig`, so an integrator
tunes strictness without editing judge code. The defaults are deliberately
conservative: the panel only ever DEMOTES candidates, and it never refutes on
insufficient data — only on positive evidence of a flaw.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class PanelConfig:
    # --- Bootstrap stability (critical) ------------------------------------
    bootstrap_samples: int = 2000        # resamples per candidate (seeded → deterministic)
    bootstrap_lb_pctile: float = 5.0     # claimed-direction bound must clear the null at this %ile

    # --- Temporal robustness (critical) ------------------------------------
    temporal_min_half_n: int = 15        # below this per half, skip (don't refute on noise)

    # --- Redundancy / duplication (critical) -------------------------------
    redundancy_subset_frac: float = 0.90 # child ⊆ parent at this sample-overlap ⇒ redundant

    # --- Practical-significance haircut (advisory) -------------------------
    # After subtracting `effect_haircut` (a per-decision cost), the effect must
    # still beat `practical_floor` to be worth acting on. Both default to 0, so
    # this judge is silent until you tell it what "worth it" means for you.
    effect_haircut: float = 0.0
    practical_floor: float = 0.0

    def majority(self, n_judges: int) -> int:
        """Number of refutals that constitutes a majority of `n_judges`."""
        return n_judges // 2 + 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def default(cls) -> "PanelConfig":
        return cls()

    @classmethod
    def strict(cls) -> "PanelConfig":
        """Tighter bounds — more candidates get refuted."""
        return cls(bootstrap_samples=4000, bootstrap_lb_pctile=10.0, temporal_min_half_n=10)
