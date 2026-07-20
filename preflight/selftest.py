"""Dependency-free self-tests with planted scenarios.

Run: `python -m preflight.selftest`

Planted truths the panel must get right:
  - a genuine, stable, persistent effect SURVIVES
  - a null / coin-flip effect is REFUTED by bootstrap
  - a regime effect (strong early, gone/reversed late) is REFUTED by temporal
  - a candidate nested inside a broader sibling is REFUTED by redundancy
  - a thin-but-real effect is FLAGGED (advisory) but NOT killed
  - verdicts are deterministic across runs
"""
from __future__ import annotations

from .config import PanelConfig
from .panel import screen, screen_candidate, survivors


def _series(values, start_ts=0, prefix="s"):
    return [{"value": v, "ts": start_ts + i, "id": f"{prefix}{i}"} for i, v in enumerate(values)]


def run() -> int:
    failures = []

    def check(name, cond):
        if not cond:
            failures.append(name)

    cfg = PanelConfig.default()

    # --- genuine effect: strong, uniform, persistent → survives ---
    genuine = {"id": "genuine", "observations": _series([1.0] * 40 + [0.0] * 5, prefix="g")}
    r = screen_candidate(genuine, [genuine], cfg)
    check("genuine survives", r.survived)
    check("genuine positive effect", r.effect > 0)

    # --- null effect: zero-centered noise (mean 0) → bootstrap refutes (bound crosses 0) ---
    null = {"id": "null", "observations": _series(([1.0, -1.0] * 30), prefix="n")}
    r = screen_candidate(null, [null], cfg)
    check("null refuted", not r.survived)
    check("null killed by bootstrap", "bootstrap_stability" in r.refuted_lenses())

    # --- regime effect: strongly positive first half, reversed second half ---
    regime = {"id": "regime",
              "observations": _series([1.0] * 20, start_ts=0, prefix="ra")
                            + _series([-1.0] * 20, start_ts=100, prefix="rb"),
              "baseline": 0.0}
    r = screen_candidate(regime, [regime], cfg)
    check("regime refuted", not r.survived)
    check("regime killed by temporal", "temporal_robustness" in r.refuted_lenses())

    # --- redundancy: child cohort fully nested inside a broader parent ---
    parent = {"id": "parent", "observations": _series([1.0] * 60, prefix="p")}
    child = {"id": "child", "observations": [parent["observations"][i] for i in range(40)]}
    res = {x.candidate_id: x for x in screen([parent, child], cfg)}
    check("child refuted redundant", not res["child"].survived
          and "redundancy" in res["child"].refuted_lenses())
    check("parent survives", res["parent"].survived)

    # --- practical haircut: real but thin effect flagged (advisory), not killed ---
    thin_cfg = PanelConfig(effect_haircut=0.02, practical_floor=0.03)
    # strong-signal so bootstrap/temporal pass; small MEAN so it's economically thin:
    thin = {"id": "thin", "observations": _series([0.03] * 200, prefix="t")}
    r = screen_candidate(thin, [thin], thin_cfg)
    check("thin flagged by haircut", "practical_haircut" in r.refuted_lenses())
    check("thin still survives (advisory only)", r.survived)

    # --- negative-direction effect survives when consistently negative ---
    neg = {"id": "neg", "observations": _series([-1.0] * 40, prefix="ng"), "direction": "negative"}
    r = screen_candidate(neg, [neg], cfg)
    check("negative effect survives", r.survived and r.effect < 0)

    # --- determinism: same candidate, same verdicts across runs ---
    a = screen_candidate(genuine, [genuine], cfg).to_dict()
    b = screen_candidate(genuine, [genuine], cfg).to_dict()
    check("deterministic", a == b)

    # --- survivors() convenience filters correctly ---
    batch = [genuine, null, regime]
    kept = {c["id"] for c in survivors(batch, cfg)}
    check("survivors filters", kept == {"genuine"})

    # --- insufficient data never refutes (1 sample passes all critical) ---
    tiny = {"id": "tiny", "observations": [{"value": 1.0, "id": "z0"}]}
    r = screen_candidate(tiny, [tiny], cfg)
    check("tiny not refuted on thin data", r.survived)

    if failures:
        print(f"SELFTEST FAILED ({len(failures)}): {failures}")
        return 1
    print("SELFTEST OK — all planted scenarios classified correctly")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run())
