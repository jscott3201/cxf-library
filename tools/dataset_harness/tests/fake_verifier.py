#!/usr/bin/env python3
"""Original test double for the cxf-verify JSON trace contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] != "--trace-json":
        print("expected --trace-json <fault-dir> <vectors.json>", file=sys.stderr)
        return 2
    vectors = json.loads(Path(sys.argv[3]).read_text())
    step = vectors["clock"]["step_s"]
    horizon = vectors["clock"]["horizon_s"]
    count = int(horizon // step) + 1
    trace = {
        "schema": "cxf-library/replay-trace/v1",
        "clock": {"step_s": step},
        "scenarios": [
            {
                "name": scenario["name"],
                "samples": [
                    {"t": index * step, "outputs": {"yFault": False}}
                    for index in range(count)
                ],
            }
            for scenario in vectors["scenarios"]
        ],
    }
    print(json.dumps(trace, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
