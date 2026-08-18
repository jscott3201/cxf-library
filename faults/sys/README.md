# SYS Fault Rules

System-level and cross-equipment rules (`SYS-FC-*`). Two populations share
this chapter:

- **Reference ch.16 rules** (SYS-FC-050–057): cross-equipment waste and
  schedule faults, fully specified in HVAC FDD Reference v1.0 ch.16
  (pdf pages 138–147). All eight are verified — this completed the
  reference's entire fully-specified fault set.
- **Sensor-health rules** (SYS-FC-054 + SYS-FC-100/101): the library's
  cross-equipment sensor-integrity family per the accepted design
  (`_research/fc100-sensor-health-design.md`). SYS-FC-054 is BOTH — the
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
| SYS-FC-050 | CHW flow with no cooling demand | 3 | rule | **verified** |
| SYS-FC-051 | HW flow with no heating demand | 3 | rule | **verified** |
| SYS-FC-052 | Lighting on with no occupancy | 4 | rule | **verified** |
| SYS-FC-053 | Exhaust fan running during unoccupied hours | 3 | rule | **verified** |
| SYS-FC-054 | Sensor drift via cross-validation (paired sensors) | 3 | rule | **verified** |
| SYS-FC-055 | Virtual sensor drift detection | 3 | statistical | **verified** |
| SYS-FC-056 | Zone heating active during summer / warm weather | 3 | rule | **verified** |
| SYS-FC-057 | Exhaust fan schedule misalignment with AHU | 3 | rule | **verified** |
| SYS-FC-100 | Sensor flatline while equipment active | 3 | rule | **verified** |
| SYS-FC-101 | Sensor spike / rate-of-change violation | 3 | rule | **verified** |

All severities/methods are re-verified against the chapter text (SYS-FC-052
is severity 4/info per the chapter, correcting the provisional row).
SYS-FC-100/101 are library-authored (design doc + public sources: Yang et
al. 2008, Liao et al. 2021, Dey & Dong 2016). Naming note: the sys
dictionary's host-derived schedule boolean is `occ_scheduled`; the ahu
dictionary spells the same concept `occ_schedule` — a known inconsistency,
left in place because renaming a bound point churns verified content IDs.

## Relationships

- **SYS-FC-054/055/100/101** are meta-rules: their `adjudicates` frontmatter names
  the role point they judge, and hosts treat an active fault as NO_EVAL for
  every rule consuming the bound point. Spike detection builds on
  `Discrete.UnitDelay` (previous-tick comparison), flatline on
  `Discrete.Sampler` — `Reals.Derivative` is deliberately avoided at BAS tick
  rates (its k/T are input pins and it over-reads ramp rates by 1 + dt/T;
  design doc §4).
- **SYS-FC-054** is CLU-09's (Sensor Integrity Failure) trigger with
  SYS-FC-055/100/101 as members; `playbooks/sensor-drift.md` is the family
  playbook. SYS-FC-055 adjudicates a single accused sensor
  (`invalid_while_active`); the pair rule SYS-FC-054 stays `ambiguous`.
- **SYS-FC-055 and SYS-FC-057** expose secondary boundary outputs that are
  **sub-condition/direction flags** (`yBias`/`yNoise`,
  `yExhaustWithoutSupply`/`ySupplyWithoutExhaust`), NOT the library's usual
  `y...Ok` evaluability flags — false on these never means NO_EVAL
  (SCHEMA.md, outputs contract).
- **AHU-FC-062 / RTU-FC-052** are the precedent physical-plausibility rules
  the design doc §2 leans on: envelope checks that already ship without
  violating the fault-given-valid-data stance.
