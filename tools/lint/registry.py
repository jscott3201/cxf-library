#!/usr/bin/env python3
"""Lint faults/registry.json against the fault dirs (SCHEMA.md "Layout").

Checks, per the general-namespace contract:
  - every fault dir has exactly one registry row and vice versa (bijection)
  - ids match `{EQUIP}-{NNNN}` and their directory / frontmatter id
  - per family, numbers are contiguous from 0001 (IDs are never reused,
    so a gap means a deleted rule — which the library does not do)
  - name/method/status in the registry match the card frontmatter
  - legacy_id values are unique and either the old `{EQUIP}-FC-{NNN}` form
    or null (rules authored after the 2026-08-18 renumbering)
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ID_RE = re.compile(r"^([A-Z]+)-(\d{4})$")
LEGACY_RE = re.compile(r"^[A-Z]+-FC-\d{3}$")

failures = []

registry = json.loads((REPO / "faults" / "registry.json").read_text(encoding="utf-8"))
rows = {r["id"]: r for r in registry.get("rules", [])}
if len(rows) != len(registry.get("rules", [])):
    failures.append("registry: duplicate ids")

dirs = {d.name: d for d in REPO.glob("faults/*/*") if (d / "card.md").is_file()}

for missing in sorted(set(dirs) - set(rows)):
    failures.append(f"{dirs[missing]}: fault dir has no registry row")
for stale in sorted(set(rows) - set(dirs)):
    failures.append(f"registry: row {stale} has no fault dir")

legacy_seen = {}
by_family = {}
for fid, row in sorted(rows.items()):
    m = ID_RE.match(fid)
    if not m:
        failures.append(f"registry: {fid} does not match {{EQUIP}}-{{NNNN}}")
        continue
    fam, num = m.group(1), int(m.group(2))
    by_family.setdefault(fam, []).append(num)
    if row.get("family") != fam.lower():
        failures.append(f"registry: {fid} family field {row.get('family')} != {fam.lower()}")
    legacy = row.get("legacy_id")
    if legacy is not None:
        if not LEGACY_RE.match(legacy):
            failures.append(f"registry: {fid} legacy_id {legacy} is not an old-form code")
        if legacy in legacy_seen:
            failures.append(f"registry: legacy_id {legacy} duplicated on {legacy_seen[legacy]} and {fid}")
        legacy_seen[legacy] = fid
    d = dirs.get(fid)
    if not d:
        continue
    text = (d / "card.md").read_text(encoding="utf-8")
    for field in ("id", "name", "method", "status"):
        m_f = re.search(rf"^{field}:\s*(.+)$", text, re.M)
        card_val = m_f.group(1).strip().strip('"') if m_f else None
        want = fid if field == "id" else row.get(field)
        if card_val != want:
            failures.append(f"{d}/card.md: {field} `{card_val}` != registry `{want}`")

for fam, nums in sorted(by_family.items()):
    expect = list(range(1, len(nums) + 1))
    if sorted(nums) != expect:
        failures.append(f"registry: {fam} numbers {sorted(nums)} not contiguous from 0001")

if failures:
    print("\n".join(failures))
    sys.exit(1)
print(f"registry lint: {len(rows)} rules OK")
