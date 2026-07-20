"""Command-line entry point.

    # screen a batch of candidates (JSON list on stdin) → verdicts as JSON
    cat candidates.json | python -m preflight.cli screen
    python -m preflight.cli screen --file candidates.json

    python -m preflight.cli selftest
"""
from __future__ import annotations

import json
import sys

from .panel import screen


def _cmd_screen(argv) -> int:
    if len(argv) >= 2 and argv[0] == "--file":
        with open(argv[1]) as f:
            candidates = json.load(f)
    else:
        data = sys.stdin.read().strip()
        if not data:
            print("ERROR: expected a JSON list of candidates on stdin or --file <path>",
                  file=sys.stderr)
            return 2
        candidates = json.loads(data)
    results = [r.to_dict() for r in screen(candidates)]
    print(json.dumps(results, indent=2))
    return 0 if all(r["survived"] for r in results) else 1


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "screen":
        return _cmd_screen(rest)
    if cmd == "selftest":
        from .selftest import run
        return run()
    print(f"unknown command: {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
