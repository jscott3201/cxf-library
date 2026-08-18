# TOWER Fault Rules

Cooling tower rules (`TOWER-FC-*`) — the library's first **fully
library-authored family**: no HVAC FDD Reference chapter covers towers, and
three deep-read sources (BEE 2006; PNNL-13890; DOE/PNNL O&M Best Practices
3.0) corroborate mechanisms but publish no approach/range fault magnitudes.
The family's quantitative grounding is therefore the committed 4-climate
simulation study (tools/simharness README, "Tower groundwork"): healthy
approach spans 1.6–13.3 °C un-gated purely on VFD fan modulation — which is
why the approach rule is **fan-at-capacity gated** — while range holds a
stable healthy band (p50 2.2–3.2 °C) across climates. Approach/range bands
ship as commissioning placeholders with CTI/ASHRAE fault-side corroboration
recorded as pending on each card; the fan short-cycling threshold is the
family's one literature-backed number (4–5 starts/hour, DOE/PNNL O&M
guides).

Point dictionary: [`points/tower.points.json`](../../points/tower.points.json)
— note the loop-side semantics (tower-leaving = cold = *entering* condenser
water) and the `oa_wetbulb` host psychrometric obligation.

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| TOWER-FC-050 | Tower approach high at fan capacity | 3 | rule | **verified** |
| TOWER-FC-051 | Tower range collapse | 3 | rule | **verified** |
| TOWER-FC-052 | Tower fan short-cycling | 3 | rule | **verified** |

## Relationships

- **CLU-10 (Condenser-Side Degradation)**: TOWER-FC-050 is the trigger,
  TOWER-FC-051 and CHW-FC-054 (chiller condenser approach) the members;
  `playbooks/cooling-tower-performance.md` is the family playbook.
  CHW-FC-054 is the tube-side vs fill-side discriminator: tower approach
  normal + condenser approach high → clean the tubes, not the fill.
- **TOWER-FC-052** stays outside CLU-10 — a drive/control fault, not the
  degradation syndrome; it shares the playbook's control-side steps.
- The pending primary sources when they are acquired: a CTI/ASHRAE tower
  chapter for approach/range fault bands, ASHRAE RP-1043 for the chiller
  condenser-approach threshold.
