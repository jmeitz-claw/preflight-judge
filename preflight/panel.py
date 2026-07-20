"""panel — an adversarial pre-flight judge panel for expensive candidate work.

Before you spend money/compute running N candidate experiments (A/B ideas,
agent hypotheses, model-eval configs, backtests, marketing tests), submit them
here. Each candidate is cross-examined by a panel of *perspective-diverse*
judges — each trying to REFUTE the candidate's claimed effect from a different
angle — and only the survivors advance to the expensive stage.

It never runs your experiment and never promotes anything. It only DEMOTES weak
candidates so your budget is spent on ideas that already survived scrutiny.

DESIGN — perspective-diverse verify (not N identical refuters). Four lenses:
  1. BootstrapStability (CRITICAL) — is the effect a resampling artifact of a
     few lucky samples? The claimed-direction bootstrap bound must clear the null.
  2. TemporalRobustness (CRITICAL) — does the effect persist across time, or was
     it one regime? Chronological split; both halves must agree in direction.
  3. Redundancy (CRITICAL) — is this candidate a near-duplicate nested inside a
     broader sibling that already carries the same signal? Keep the parent.
  4. PracticalHaircut (ADVISORY) — after a real-world cost haircut, is the effect
     still worth acting on? Flags thin-but-real; cannot kill on its own.

SURVIVAL RULE — a candidate survives iff no CRITICAL judge refutes it AND fewer
than a majority of all judges refute it. Deterministic: the bootstrap PRNG is
seeded from the candidate id, so the same candidate on the same data always gets
the same verdict (reproducible in CI and audits). Pure stdlib.

DATA MODEL
  observation : {"value": float, "ts"?: comparable, "id"?: hashable}
  candidate   : {"id": str, "observations": [observation, ...],
                 "baseline"?: float = 0.0,
                 "direction"?: "auto"|"positive"|"negative" = "auto"}
The claimed effect is mean(value) - baseline.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Set

from .config import PanelConfig


# ---------------------------------------------------------------------------
# small stdlib stats
# ---------------------------------------------------------------------------

def percentile(values: Sequence[float], pct: float) -> float:
    """Linear-interpolation percentile (pct in [0,100]). Empty ⇒ 0.0."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    rank = (pct / 100.0) * (len(s) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return s[lo]
    frac = rank - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _values(obs: Sequence[Dict[str, Any]]) -> List[float]:
    return [float(o["value"]) for o in obs if o.get("value") is not None]


def _effect(obs: Sequence[Dict[str, Any]], baseline: float) -> Optional[float]:
    vals = _values(obs)
    if not vals:
        return None
    return sum(vals) / len(vals) - baseline


def _claimed_dir(effect: float, direction: str) -> int:
    if direction == "positive":
        return 1
    if direction == "negative":
        return -1
    return 1 if effect >= 0 else -1


# ---------------------------------------------------------------------------
# result types
# ---------------------------------------------------------------------------

@dataclass
class Verdict:
    lens: str
    critical: bool
    refuted: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PanelResult:
    candidate_id: str
    survived: bool
    n: int
    effect: float
    verdicts: List[Verdict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    def refuted_lenses(self) -> List[str]:
        return [v.lens for v in self.verdicts if v.refuted]


# ---------------------------------------------------------------------------
# judges — a judge that cannot evaluate PASSES (refuted=False); the panel never
# kills on insufficient data, only on positive evidence of a flaw.
# ---------------------------------------------------------------------------

def judge_bootstrap_stability(cand: Dict[str, Any], cfg: PanelConfig) -> Verdict:
    lens = "bootstrap_stability"
    obs = cand["observations"]
    baseline = float(cand.get("baseline", 0.0) or 0.0)
    vals = _values(obs)
    if len(vals) < 2:
        return Verdict(lens, True, False, "insufficient samples to resample — pass")
    effect = sum(vals) / len(vals) - baseline
    d = _claimed_dir(effect, cand.get("direction", "auto"))
    n = len(vals)
    rng = random.Random(f"boot::{cand['id']}::{n}")
    effects: List[float] = []
    for _ in range(cfg.bootstrap_samples):
        acc = 0.0
        for _ in range(n):
            acc += vals[rng.randrange(n)]
        effects.append(acc / n - baseline)
    if d > 0:
        lb = percentile(effects, cfg.bootstrap_lb_pctile)
        refuted = lb <= 0.0
        reason = (f"bootstrap {cfg.bootstrap_lb_pctile:.0f}%ile lower bound "
                  f"{lb:+.4f} {'crosses' if refuted else 'clears'} the null")
    else:
        ub = percentile(effects, 100.0 - cfg.bootstrap_lb_pctile)
        refuted = ub >= 0.0
        reason = (f"bootstrap {100.0-cfg.bootstrap_lb_pctile:.0f}%ile upper bound "
                  f"{ub:+.4f} {'crosses' if refuted else 'clears'} the null")
    return Verdict(lens, True, refuted, reason)


def judge_temporal_robustness(cand: Dict[str, Any], cfg: PanelConfig) -> Verdict:
    lens = "temporal_robustness"
    obs = [o for o in cand["observations"] if o.get("ts") is not None and o.get("value") is not None]
    baseline = float(cand.get("baseline", 0.0) or 0.0)
    if len(obs) < 2 * cfg.temporal_min_half_n:
        return Verdict(lens, True, False,
                       f"fewer than {2*cfg.temporal_min_half_n} timestamped samples — skip")
    ordered = sorted(obs, key=lambda o: o["ts"])
    mid = len(ordered) // 2
    h1 = _effect(ordered[:mid], baseline)
    h2 = _effect(ordered[mid:], baseline)
    overall = _effect(ordered, baseline)
    if h1 is None or h2 is None or overall is None:
        return Verdict(lens, True, False, "insufficient values in a half — pass")
    s = 1 if overall >= 0 else -1

    def agrees(x: float) -> bool:
        return (x > 0 and s > 0) or (x < 0 and s < 0)

    refuted = not (agrees(h1) and agrees(h2))
    reason = (f"halves {h1:+.4f} / {h2:+.4f} vs overall {overall:+.4f} — "
              f"{'disagree' if refuted else 'agree'} in direction")
    return Verdict(lens, True, refuted, reason)


def judge_redundancy(cand: Dict[str, Any], siblings: List[Dict[str, Any]], cfg: PanelConfig) -> Verdict:
    lens = "redundancy"
    my_ids = {o["id"] for o in cand["observations"] if o.get("id") is not None}
    if not my_ids:
        return Verdict(lens, True, False, "no sample ids — redundancy not evaluable — pass")
    for sib in siblings:
        if sib["id"] == cand["id"]:
            continue
        sib_ids = {o["id"] for o in sib["observations"] if o.get("id") is not None}
        if len(sib_ids) <= len(my_ids):
            continue  # only a strictly-broader sibling can subsume this one
        overlap = len(my_ids & sib_ids) / len(my_ids)
        if overlap >= cfg.redundancy_subset_frac:
            return Verdict(lens, True, True,
                           f"{overlap*100:.0f}% of samples nested in broader candidate "
                           f"'{sib['id']}' — redundant, keep the parent")
    return Verdict(lens, True, False, "not subsumed by a broader candidate — pass")


def judge_practical_haircut(cand: Dict[str, Any], cfg: PanelConfig) -> Verdict:
    lens = "practical_haircut"
    obs = cand["observations"]
    baseline = float(cand.get("baseline", 0.0) or 0.0)
    effect = _effect(obs, baseline)
    if effect is None:
        return Verdict(lens, False, False, "no values — pass")
    net = abs(effect) - cfg.effect_haircut
    refuted = net < cfg.practical_floor
    reason = (f"|effect| {abs(effect):.4f} − haircut {cfg.effect_haircut:.4f} = {net:.4f} "
              f"{'<' if refuted else '≥'} floor {cfg.practical_floor:.4f}")
    return Verdict(lens, False, refuted, reason)  # advisory: critical=False


# ---------------------------------------------------------------------------
# the panel
# ---------------------------------------------------------------------------

def screen_candidate(cand: Dict[str, Any], siblings: List[Dict[str, Any]],
                     cfg: Optional[PanelConfig] = None) -> PanelResult:
    """Cross-examine one candidate against the panel. `siblings` are the other
    candidates in the batch (used only by the redundancy lens)."""
    cfg = cfg or PanelConfig.default()
    obs = cand["observations"]
    effect = _effect(obs, float(cand.get("baseline", 0.0) or 0.0)) or 0.0
    verdicts = [
        judge_bootstrap_stability(cand, cfg),
        judge_temporal_robustness(cand, cfg),
        judge_redundancy(cand, siblings, cfg),
        judge_practical_haircut(cand, cfg),
    ]
    critical_refuted = sum(1 for v in verdicts if v.critical and v.refuted)
    total_refuted = sum(1 for v in verdicts if v.refuted)
    survived = critical_refuted == 0 and total_refuted < cfg.majority(len(verdicts))
    if survived:
        summary = f"SURVIVED (effect {effect:+.4f}, n={len(_values(obs))})"
    else:
        killed = [v.lens for v in verdicts if v.refuted]
        summary = f"REFUTED by {killed}"
    return PanelResult(cand["id"], survived, len(_values(obs)), effect, verdicts, summary)


def screen(candidates: List[Dict[str, Any]], cfg: Optional[PanelConfig] = None) -> List[PanelResult]:
    """Screen a whole batch. Returns one :class:`PanelResult` per candidate,
    in input order. Redundancy is evaluated across the batch."""
    cfg = cfg or PanelConfig.default()
    return [screen_candidate(c, candidates, cfg) for c in candidates]


def survivors(candidates: List[Dict[str, Any]], cfg: Optional[PanelConfig] = None) -> List[Dict[str, Any]]:
    """Convenience: return only the candidate dicts that survived the panel."""
    keep = {r.candidate_id for r in screen(candidates, cfg) if r.survived}
    return [c for c in candidates if c["id"] in keep]
