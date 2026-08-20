# TOWER Fault Rules

Cooling tower rules (`TOWER-*`) are fully library-authored: no HVAC FDD
Reference chapter covers towers. BEE, DOE/PNNL, NREL, ASHRAE, SPX, and EVAPCO
sources corroborate the mechanisms and safety constraints, but they do not
publish portable executable limits for approach/range degradation, loaded-fan
overcooling, proof timing, or basin thermal response. Each card therefore
labels adopted values and site/OEM adoption blockers explicitly.

The first batch's quantitative grounding remains the committed 4-climate
simulation study (`tools/simharness` README, "Tower groundwork"): healthy
approach spans 1.6–13.3 °C un-gated purely on VFD fan modulation, which is why
TOWER-0001 is fan-at-capacity gated, while range holds a stable healthy band.
TOWER-0003's 4–5 starts/hour mechanism is literature-backed. TOWER-0004..0006
add per-fan proof, loaded-fan overcooling, and an explicitly site/OEM-governed
wet-basin freeze watchdog.

Point dictionary: [`points/tower.points.json`](../../points/tower.points.json)
— note the loop-side semantics (tower-leaving = cold = *entering* condenser
water), the `oa_wetbulb` host psychrometric obligation, and provisional 223
topology for basin points.

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| TOWER-0001 | Tower approach high at fan capacity | 3 | rule | **verified** |
| TOWER-0002 | Tower range collapse | 3 | rule | **verified** |
| TOWER-0003 | Tower fan short-cycling | 3 | rule | **verified** |
| TOWER-0004 | Tower fan proof-of-operation failure | 2 | rule | **verified** |
| TOWER-0005 | Condenser water overcooling with fan energy | 3 | rule | **verified** |
| TOWER-0006 | Cooling-tower basin freeze-protection failure | 2 | rule | **verified** |

## Relationships

- **CLU-10 (Condenser-Side Degradation)**: TOWER-0001 is the trigger,
  TOWER-0002 and CHW-0005 (chiller condenser approach) the members;
  `playbooks/cooling-tower-performance.md` is the family playbook.
  CHW-0005 is the tube-side vs fill-side discriminator: tower approach
  normal + condenser approach high → clean the tubes, not the fill.
- **TOWER-0003** stays outside CLU-10 — a drive/control fault, not the
  degradation syndrome; it shares the playbook's control-side steps.
- **TOWER-0004 and TOWER-0005** stay outside CLU-10. Proof disagreement and
  overcooling control waste do not share the cluster's degradation repair
  contract. TOWER-0004 is direction-sensitive proof context for TOWER-0005;
  no static whole-rule suppression is safe.
- **TOWER-0006** stays independent and synthetic-only. It applies only to a
  wet, filled basin with monitored heater/equivalent protection and configured
  site/OEM limits. A basin heater is not protection for external piping.
- The pending primary sources when they are acquired: a CTI/ASHRAE tower
  chapter for approach/range fault bands, ASHRAE RP-1043 for the chiller
  condenser-approach threshold.
