"""Example: an LLM research/agent swarm proposes hypotheses; screen them before
spending tokens/compute deep-diving each one.

Each candidate hypothesis carries a batch of cheap scored trials (`value` = a
per-trial success/score from a quick probe). Only survivors earn the expensive
deep run — so the compute budget goes to ideas that already survived scrutiny.
"""
from preflight import screen, survivors

candidates = [
    # A hypothesis that consistently helps across probes.
    {"id": "use-scratchpad",
     "observations": [{"value": v, "ts": i, "id": f"sp{i}"}
                      for i, v in enumerate([1.0] * 36 + [0.0] * 4)]},

    # A hypothesis whose "gain" is really just noise.
    {"id": "verbose-prompts",
     "observations": [{"value": v, "ts": i, "id": f"vp{i}"}
                      for i, v in enumerate([1.0, -1.0] * 20)]},

    # A near-duplicate of use-scratchpad (same trials, re-labeled) — redundant.
    {"id": "scratchpad-v2",
     "observations": [{"value": 1.0, "ts": i, "id": f"sp{i}"} for i in range(30)]},
]

print("Full verdicts:")
for r in screen(candidates):
    print(f"  {r.candidate_id:16} survived={r.survived}  {r.summary}")

print("\nWorth the expensive deep run:")
for c in survivors(candidates):
    print(f"  → {c['id']}")
