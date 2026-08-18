# SYS Fault Rules

System-level and cross-equipment rules (`SYS-*`). Two populations share
this chapter:

- **Reference ch.16 rules** (SYS-0001–057): cross-equipment waste and
  schedule faults, fully specified in HVAC FDD Reference v1.0 ch.16
  (pdf pages 138–147). All eight are verified — this completed the
  reference's entire fully-specified fault set.
- **Sensor-health rules** (SYS-0005 + SYS-0009/SYS-0010): the library's
  cross-equipment sensor-integrity family per the accepted design
  (internal sensor-health design note, local-only). SYS-0005 is BOTH — the
  reference's own paired-sensor cross-validation card is exactly the
  redundancy-pair bias rule, so it keeps its reference number (decided
  2026-08-17; numbering is adjustable as the library grows).

These rules bind **role points** (`points/sys.points.json`) — the documented
exception to the canonical-name convention: one graph, many bindings, with
the host's instance configuration recording each binding. That same record
drives the `adjudicates` NO_EVAL fan-out (SCHEMA.md frontmatter table).

Point dictionary: [`points/sys.points.json`](../../points/sys.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| SYS-0001 | CHW flow with no cooling demand | 3 | rule | **verified** |
| SYS-0002 | HW flow with no heating demand | 3 | rule | **verified** |
| SYS-0003 | Lighting on with no occupancy | 4 | rule | **verified** |
| SYS-0004 | Exhaust fan running during unoccupied hours | 3 | rule | **verified** |
| SYS-0005 | Sensor drift via cross-validation (paired sensors) | 3 | rule | **verified** |
| SYS-0006 | Virtual sensor drift detection | 3 | statistical | **verified** |
| SYS-0007 | Zone heating active during summer / warm weather | 3 | rule | **verified** |
| SYS-0008 | Exhaust fan schedule misalignment with AHU | 3 | rule | **verified** |
| SYS-0009 | Sensor flatline while equipment active | 3 | rule | **verified** |
| SYS-0010 | Sensor spike / rate-of-change violation | 3 | rule | **verified** |

All severities/methods are re-verified against the chapter text (SYS-0003
is severity 4/info per the chapter, correcting the provisional row).
SYS-0009/SYS-0010 are library-authored (design doc + public sources: Yang et
al. 2008, Liao et al. 2021, Dey & Dong 2016). Naming note: the sys
dictionary's host-derived schedule boolean is `occ_scheduled`; the ahu
dictionary spells the same concept `occ_schedule` — a known inconsistency,
left in place because renaming a bound point churns verified content IDs.

## Relationships

- **SYS-0005/SYS-0006/SYS-0009/SYS-0010** are meta-rules: their `adjudicates` frontmatter names
  the role point they judge, and hosts treat an active fault as NO_EVAL for
  every rule consuming the bound point. Spike detection builds on
  `Discrete.UnitDelay` (previous-tick comparison), flatline on
  `Discrete.Sampler` — `Reals.Derivative` is deliberately avoided at BAS tick
  rates (its k/T are input pins and it over-reads ramp rates by 1 + dt/T;
  design doc §4).
- **SYS-0005** is CLU-09's (Sensor Integrity Failure) trigger with
  SYS-0006/SYS-0009/SYS-0010 as members; `playbooks/sensor-drift.md` is the family
  playbook. SYS-0006 adjudicates a single accused sensor
  (`invalid_while_active`); the pair rule SYS-0005 stays `ambiguous`.
- **SYS-0006 and SYS-0008** expose secondary boundary outputs that are
  **sub-condition/direction flags** (`yBias`/`yNoise`,
  `yExhaustWithoutSupply`/`ySupplyWithoutExhaust`), NOT the library's usual
  `y...Ok` evaluability flags — false on these never means NO_EVAL
  (SCHEMA.md, outputs contract).
- **AHU-0028 / RTU-0003** are the precedent physical-plausibility rules
  the design doc §2 leans on: envelope checks that already ship without
  violating the fault-given-valid-data stance.
