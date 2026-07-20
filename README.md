# preflight-judge

**Refute weak candidate experiments before you pay to run them.** A read-only,
dependency-free adversarial panel: hand it N candidate experiments (A/B ideas,
agent hypotheses, model-eval configs, backtests, marketing tests) with cheap
pilot data, and it tells you which are worth the expensive full run — killing the
ones whose apparent effect is a fluke, a one-time regime, or a duplicate.

The market is flooded with tools that help you *generate more* AI output. This is
the opposite: a rigorous, cheap **refutation layer** that makes you run *less*.
The ROI is obvious — kill 60% of your runs before they cost you a cent.

> It refutes; it never runs your experiment. `screen()` is pure and
> side-effect-free — it returns verdicts, you decide what to run.

Extracted and generalized from a production trading system's adversarial
proposal-screening gate.

## The idea: perspective-diverse verify

Instead of one reviewer (or N identical ones), each candidate faces a panel of
**distinct failure lenses** — diversity catches failure modes redundancy can't:

| Lens | Asks | Kills? |
|------|------|--------|
| **bootstrap_stability** | Is the effect a resampling artifact of a few lucky samples? | ✅ critical |
| **temporal_robustness** | Does it persist across time, or was it one regime? | ✅ critical |
| **redundancy** | Is this just a narrower duplicate of a broader candidate? | ✅ critical |
| **practical_haircut** | After real-world cost, is the effect still worth acting on? | advisory (flags, can't kill alone) |

**Survival rule:** a candidate survives iff **no critical lens refutes it** *and*
fewer than a majority of all lenses refute it. Deterministic — the bootstrap PRNG
is seeded from the candidate id, so the same candidate on the same data always
gets the same verdict (reproducible in CI and audits).

## Install

```bash
pip install -e .
python -m preflight.selftest
```

Stdlib-only. No numpy, no pandas, nothing to pin.

## Quick start

```python
from preflight import screen, survivors, PanelConfig

candidates = [
    {"id": "variant-A", "baseline": 0.20,
     "observations": [{"value": 1, "ts": 0, "id": "a0"}, {"value": 0, "ts": 1, "id": "a1"}, ...]},
    {"id": "variant-B", "observations": [...]},
]

for r in screen(candidates):
    print(r.candidate_id, r.survived, r.summary)
    for v in r.verdicts:
        print("  ", "✗" if v.refuted else "·", v.lens, v.reason)

# or just keep the ones worth the expensive run:
worth_it = survivors(candidates)
```

## Data model

- **observation**: `{"value": float, "ts"?: comparable, "id"?: hashable}`
  - `value` — the per-sample numeric outcome (reward, conversion 0/1, score, lift).
  - `ts` — optional sort key; enables the temporal lens (skipped if absent).
  - `id` — optional sample id; enables the redundancy lens (skipped if absent).
- **candidate**: `{"id": str, "observations": [observation, ...], "baseline"?: float = 0.0, "direction"?: "auto"|"positive"|"negative"}`
  - The claimed effect is `mean(value) − baseline`.

Every threshold is a field on `PanelConfig` (`bootstrap_samples`,
`bootstrap_lb_pctile`, `temporal_min_half_n`, `redundancy_subset_frac`,
`effect_haircut`, `practical_floor`). `PanelConfig.strict()` refutes more
aggressively.

## Where it fits

- **A/B & growth** — screen variants from a cheap pilot before a costly full test.
- **LLM agent swarms** — screen proposed hypotheses before spending tokens deep-diving each.
- **ML/eval** — triage eval configs / fine-tune candidates before expensive runs.
- **Quant/backtests** — refute overfit signals before they consume OOS budget.

See [`examples/`](examples/).

## CLI

```bash
cat candidates.json | python -m preflight.cli screen
python -m preflight.cli selftest
```

## Testing

```bash
python -m preflight.selftest         # zero-dependency planted-scenario checks
python -m pytest tests/              # full unittest suite
```

## License

MIT. It's a screening heuristic, not a proof — it reduces wasted runs, it doesn't
guarantee the survivors are real.
