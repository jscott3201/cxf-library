# FPB Fault Rules

Fan-powered terminal rules (`FPB-*`) cover series and parallel fan-powered VAV
terminal units, also called fan-powered boxes, fan-powered terminal units, or
FPUs. Ordinary VAV boxes remain in `vav`; fan coils remain in `fcu`.

Point dictionary: [`points/fpb.points.json`](../../points/fpb.points.json).
Brick 1.4.4 provides only generic `Terminal_Unit`; ASHRAE 223 PPR2.1 provides
exact `FanPoweredTerminal`. Series/parallel identity is deployment topology.

| Concern | Series FPB | Parallel FPB |
|---|---|---|
| Fan location | In the primary/discharge path, generally continuous when occupied | Parallel plenum-air branch, often heating/low-flow operation |
| Primary airflow | Through primary damper | Through primary damper |
| Reheat coil | Typically downstream of fan | In fan/reheat branch before mixing, per actual unit topology |
| Fan proof rule | Applicable when commanded | Applicable when commanded |
| Airflow tracking | Primary airflow only | Primary airflow only; does not prove fan-branch airflow |
| Reheat delta-T binding | Direct coil inlet/outlet | Must remain branch-local or use a validated derived point |

Excluded: ordinary single-duct VAV boxes without terminal fans, FCUs, induction
units without commanded fans, dual-duct boxes without explicit compatibility,
and electric-reheat-only units for the hydronic valve rule.

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| FPB-0001 | Terminal fan proof-of-operation failure | 2 | rule | **verified** |
| FPB-0002 | Primary airflow tracking failure | 3 | rule | **verified** |
| FPB-0003 | Reheat valve closed with unintended temperature rise | 3 | rule | **verified** |

## Source and validation posture

The [LBNL simulated FPU dataset](https://faultdetection.lbl.gov/dataset/simulated-fpu/)
(DOI 10.25984/1881324) documents PFPU/SFPU topology and publishes HVACSIM+
cases spanning 365 days at one-minute resolution, 109 points, fault-free cases,
and ten fault categories. It is a future validation source, not evidence for
the library-authored thresholds in this slice; the adapter is deferred to PR11.

## Relationships

- FPB-0001 supplies direction-sensitive fan-proof context; no whole-rule
  suppression is safe for FPB-0002/0003.
- FPB-0002 is the primary-stream sibling of VAV-0004 and relates upstream AHU
  static/reset signatures without claiming their causes.
- FPB-0003 is the coil-local sibling of FCU-0005/VAV-0009. It is not added to
  CLU-01 because a single AHU simultaneous-command repair cannot reliably clear
  a physically passing terminal valve.
