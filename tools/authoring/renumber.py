#!/usr/bin/env python3
"""One-shot migration: {FAM}-FC-{NNN} fault IDs -> the general {FAM}-{NNNN} namespace.

Renumbers each family contiguously from 0001 in current numeric order,
rewrites every tracked text reference (including composite shorthand like
SYS-FC-058/059), renames the fault dirs via `git mv`, and writes
faults/registry.json — the library-wide fault-code map, carrying each
rule's legacy FC code.

Dry run by default (prints the mapping); --write executes.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OLD_ID = re.compile(r"([A-Z]+)-FC-(\d{3})")
# Composite shorthand: SYS-FC-058/059, TOWER-FC-050/051/052
COMPOSITE = re.compile(r"([A-Z]+)-FC-(\d{3})((?:/\d{3})+)")
TEXT_SUFFIXES = {".md", ".json", ".jsonld", ".svg", ".py", ".yml", ".yaml", ".toml", ".rs"}


def build_mapping():
    mapping = {}
    for fam_dir in sorted((REPO / "faults").iterdir()):
        if not fam_dir.is_dir():
            continue
        olds = sorted(
            (d.name for d in fam_dir.iterdir() if OLD_ID.fullmatch(d.name)),
            key=lambda n: int(n.rsplit("-", 1)[1]),
        )
        for i, old in enumerate(olds, start=1):
            fam = old.split("-")[0]
            mapping[old] = f"{fam}-{i:04d}"
    return mapping


def expand_composites(text: str) -> str:
    """SYS-FC-058/059 -> SYS-FC-058/SYS-FC-059 so the plain map covers it."""
    def repl(m):
        fam, first, rest = m.group(1), m.group(2), m.group(3)
        parts = [f"{fam}-FC-{first}"] + [f"{fam}-FC-{n}" for n in rest.strip("/").split("/")]
        return "/".join(parts)
    return COMPOSITE.sub(repl, text)


def rewrite(text: str, mapping: dict) -> str:
    text = expand_composites(text)
    return OLD_ID.sub(lambda m: mapping.get(m.group(0), m.group(0)), text)


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    return [REPO / p for p in out if Path(p).suffix in TEXT_SUFFIXES]


def write_registry(mapping: dict):
    entries = []
    for old, new in sorted(mapping.items(), key=lambda kv: kv[1]):
        fam = new.split("-")[0].lower()
        card = REPO / "faults" / fam / new / "card.md"
        text = card.read_text(encoding="utf-8")
        name = re.search(r"^name:\s*(.+)$", text, re.M).group(1).strip().strip('"')
        status = re.search(r"^status:\s*(\S+)", text, re.M).group(1)
        method = re.search(r"^method:\s*(\S+)", text, re.M).group(1)
        entries.append({
            "id": new, "family": fam, "name": name,
            "method": method, "status": status, "legacy_id": old,
        })
    registry = {"schema": "cxf-library/registry/v1", "rules": entries}
    (REPO / "faults" / "registry.json").write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )


def main():
    write = "--write" in sys.argv
    mapping = build_mapping()
    fams = {}
    for old, new in mapping.items():
        fams.setdefault(old.split("-")[0], []).append((old, new))
    for fam in sorted(fams):
        pairs = sorted(fams[fam], key=lambda p: p[1])
        print(f"{fam}: {len(pairs)} rules  {pairs[0][0]} -> {pairs[0][1]}  ...  {pairs[-1][0]} -> {pairs[-1][1]}")
    if not write:
        for old, new in sorted(mapping.items(), key=lambda kv: kv[1]):
            print(f"  {old:>14} -> {new}")
        print("\ndry run — pass --write to execute")
        return

    for f in tracked_files():
        orig = f.read_text(encoding="utf-8")
        new = rewrite(orig, mapping)
        if new != orig:
            f.write_text(new, encoding="utf-8")
    for old, new in mapping.items():
        fam = old.split("-")[0].lower()
        subprocess.run(
            ["git", "mv", f"faults/{fam}/{old}", f"faults/{fam}/{new}"],
            cwd=REPO, check=True,
        )
    write_registry(mapping)
    print(f"\nrenamed {len(mapping)} rules; wrote faults/registry.json")


if __name__ == "__main__":
    main()
