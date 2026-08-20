# CHW Fault Rules

Chilled-water plant fault detection rules (`CHW-*`). CHW-0001..0006 originate
in HVAC FDD Reference v1.0 ch.13 or close its cited approach-rule gaps.
CHW-0007..0009 are library-authored control/protection extensions grounded in
public plant guidance and verified graph precedents. The family now separates
efficiency and reset performance from per-machine tracking, proof, and cycling.

Point dictionary: [`points/chw.points.json`](../../points/chw.points.json).
Supplementary deep-read sources (paraphrase-and-cite only, per the licensing
rule): G36 cooling-plant AFDD document, ASHRAE RP-1043 chiller FDD review,
and the chiller-plant entries in the project’s internal research triage (licensed sources; not distributed).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| CHW-0001 | Chiller efficiency (kW/ton) degradation | 3 | statistical | **verified** |
| CHW-0002 | CHWST reset not functioning | 3 | statistical | **verified** |
| CHW-0003 | CHW loop DP reset not functioning | 3 | statistical | **verified** |
| CHW-0004 | Chilled water low delta-T syndrome | 3 | rule | **verified** |
| CHW-0005 | Chiller condenser approach high | 3 | rule | **verified** |
| CHW-0006 | Chiller evaporator approach high | 3 | rule | **verified** |
| CHW-0007 | Chilled-water supply temperature tracking failure | 3 | rule | **verified** |
| CHW-0008 | Chiller proof-of-operation failure | 2 | rule | **verified** |
| CHW-0009 | Chiller short-cycling | 2 | rule | **verified** |

Severity and method per the reference's ch.13 cards. CHW-0005/CHW-0006 are
the approach pair resolving the reference's dangling CHW-FC-008/009 playbook
citations (mentioned there, never defined): condenser side and evaporator
side of the same verify step, tube-side discriminators for CHW-0001.

## Relationships

- **CHW-0002/CHW-0003** are the plant-side siblings of AHU-0023/AHU-0024 (SAT/DSP
  reset) — same detector shape (setpoint range flat over a window while the
  load moves), same RetuningOpps lineage, and the same CLU-02-style "reset
  never programmed" root cause one system further upstream.
- **CHW-0004 (low delta-T)** is the plant-level symptom of coil-side
  defects the library already detects locally: fouled/leaking coil valves
  (FCU-0004, AHU-0014), three-way bypass, dirty filters — tied together
  by cluster CLU-06 (trigger CHW-0001).
- **CHW-0001**'s baseline follows the HP-0001 host-fitted pattern — the
  reference specifies a Ridge regression over load/CWST/CHWST; the graph
  carries the fitted coefficients as set_param placeholders.
- **CHW-0007** complements CHW-0001/0005/0006: tracking direction is useful
  evidence during an approach or efficiency finding, so none suppresses it.
- **CHW-0008 stays relationship-only.** Its fail-to-start direction makes
  tracking non-evaluable, but its unexpected-run direction can still be loaded
  and meaningfully fail tracking. Current metadata cannot encode only one lane.
- **CHW-0009 and CHW-0007 are related** because low-load overshoot can produce
  cycling, but neither implies the other and no graph state is shared.

## Per-machine binding boundaries

| Point | CHW-0007 | CHW-0008 | CHW-0009 | Plant/loop use |
|---|---|---|---|---|
| `chiller_cmd` | — | Final command for this machine | — | Plant enable or cooling demand is invalid |
| `chiller_status` | This machine | This machine, independent proof | This machine | A fleet OR hides lag-machine starts |
| `chiller_load` | This machine | — | — | A documented plant maximum remains valid only for plant-level gates such as CHW-0004 |
| `chwst` / `chwst_sp` | Same controllable leaving-water target | — | — | Common header is conditional, not automatically per-machine |

On parallel plants, prefer each chiller's evaporator outlet plus the final
active target delivered to its controller. A mixed-header measurement/setpoint
may be used for CHW-0007 only when the deployment proves the staged machine(s)
actually control that same point. An OR of statuses or maximum of loads is not
a weaker per-machine proxy; it changes the question.

## Ontology and cluster decision

The PR 04 point additions pin ASHRAE 223 to the inspected public-review
artifact `1.0.0-ppr.2.1` (SHA-256
`1f156f9938c0be430d2216e01e31bb183c438ba318d8d4a23d2f074ebcd6f573`),
replacing the former unverified `v1.0.0-2026` label. The migration also
replaces legacy `Water`/`Refrigerant` and free-text aspect shorthands with
artifact-defined local names such as `Water-ChilledWater`, `Fluid-Water`,
`Constituent-Refrigerant`, and `Aspect-Setpoint`. Brick 1.4.4 provides exact
generic `Start_Stop_Command` and `Run_Status` classes on a `Chiller`.

CLU-06 is not broadened. Tracking, proof, and cycling improve diagnosis but do
not share one trigger/fix with the existing efficiency-reset-approach cluster.
