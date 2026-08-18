#!/usr/bin/env python3
"""Lint fault-ID band placement against the SCHEMA.md numbering contract.

Enforced (the direction that is checkable):
  - 100-149 requires method: statistical (advanced statistical band)
  - 150-199 requires method: ml (reserved)
  - frontmatter id matches the directory name

Deliberately NOT enforced: statistical rules may live in 050-099 — the
expansion band admits any method (13 reference-derived statistical rules
ship there); only the 100+ bands constrain method.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

failures = []
for card in sorted(REPO.glob("faults/*/*/card.md")):
    text = card.read_text(encoding="utf-8")
    fid = card.parent.name
    m_id = re.search(r"^id:\s*(\S+)", text, re.M)
    m_method = re.search(r"^method:\s*(\S+)", text, re.M)
    if not m_id or m_id.group(1) != fid:
        failures.append(f"{card}: frontmatter id {m_id.group(1) if m_id else '(missing)'} != dir {fid}")
        continue
    num = int(fid.rsplit("-", 1)[1])
    method = m_method.group(1) if m_method else "(missing)"
    if 100 <= num <= 149 and method != "statistical":
        failures.append(f"{card}: id {fid} is in the advanced-statistical band (100-149) but method is {method}")
    if 150 <= num <= 199 and method != "ml":
        failures.append(f"{card}: id {fid} is in the ML band (150-199) but method is {method}")
    if num > 199:
        failures.append(f"{card}: id {fid} is outside all defined bands (001-199)")

if failures:
    print("\n".join(failures))
    sys.exit(1)
print(f"id-band lint: {len(list(REPO.glob('faults/*/*/card.md')))} cards OK")
