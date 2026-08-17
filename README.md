# cxf-library

Private library of CXF JSON control programs and CDL-based fault detection
rules for the [open-control engine](https://github.com/jscott3201/open-control-engine).

Each fault rule is a CDL composite block stored as CXF JSON-LD the engine loads
directly, paired with a human/machine fault card and executable test vectors.
Grounded in ASHRAE Guideline 36-2021 and the HVAC FDD Reference v1.0 (PNNL/LBNL
research consolidation), with point semantics tagged in Brick and ASHRAE 223P.

- **`SCHEMA.md`** — the normative layout and file contracts. Read this first.
- **`faults/<equip>/<FAULT-ID>/`** — one folder per rule: `card.md`,
  `rule.cxf.jsonld`, `vectors.json`.
- **`points/`** — canonical point dictionary (Brick + 223P tags).
- **`playbooks/`**, **`clusters/`** — remediation workflows and fault syndromes.
- **`tools/verify`** — engine-backed conformance runner:
  `cargo run --manifest-path tools/verify/Cargo.toml -- faults/ahu/AHU-FC-050`
  (requires a sibling checkout of `open-control`).
- **`_research/`** — source digests (CDL/CXF specs, FDD reference, repo landscape).

First pass in progress: air handling units (`faults/ahu/`), worked rule by rule.
