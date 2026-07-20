"""Example: screen A/B / experiment candidates before paying to run them at scale.

You have several candidate variants, each with a cheap pilot sample of a numeric
outcome (conversion, reward, latency-improvement, eval score). The panel tells
you which are worth a full, expensive run — and refutes the ones whose apparent
lift is a fluke, a one-week regime, or a duplicate of another variant.

`value` is the per-sample outcome; `baseline` is the control/null you compare to.
"""
from preflight import screen, PanelConfig

# Pilot samples per candidate. In reality these come from your pilot run.
candidates = [
    # Real, stable lift over a 0.20 control conversion rate.
    {"id": "variant-A", "baseline": 0.20,
     "observations": [{"value": v, "ts": i, "id": f"a{i}"}
                      for i, v in enumerate([1.0] * 34 + [0.0] * 6)]},

    # No real lift — noise around the control.
    {"id": "variant-B", "baseline": 0.20,
     "observations": [{"value": v, "ts": i, "id": f"b{i}"}
                      for i, v in enumerate(([1.0, 0.0, 0.0, 0.0, 0.0] * 12))]},

    # Looked great early, decayed later (novelty effect) — a regime, not a lift.
    {"id": "variant-C", "baseline": 0.20,
     "observations": [{"value": v, "ts": i, "id": f"c{i}"}
                      for i, v in enumerate([1.0] * 20 + [0.0] * 20)]},
]

cfg = PanelConfig(effect_haircut=0.0, practical_floor=0.0)
for r in screen(candidates, cfg):
    tag = "RUN IT" if r.survived else "skip"
    print(f"[{tag:6}] {r.candidate_id:10} effect={r.effect:+.3f} n={r.n}  {r.summary}")
    for v in r.verdicts:
        mark = "✗" if v.refuted else "·"
        print(f"           {mark} {v.lens}: {v.reason}")
