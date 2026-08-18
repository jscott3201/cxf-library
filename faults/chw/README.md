# CHW Fault Rules

Chilled water plant fault detection rules (`CHW-FC-*`). Source grounding:
HVAC FDD Reference v1.0 ch.13 (pdf pages 118–123). Chiller plants are the
largest single energy consumers in most commercial buildings, so small
efficiency losses are expensive: the chapter's own arithmetic puts 0.1 kW/ton
above baseline at roughly 15% excess chiller energy, and both reset faults
sit above 30% prevalence in PNNL's 151-building study.

Point dictionary: [`points/chw.points.json`](../../points/chw.points.json).
Supplementary deep-read sources (paraphrase-and-cite only, per the licensing
rule): G36 cooling-plant AFDD document, ASHRAE RP-1043 chiller FDD review,
and the chiller-plant entries in the project’s internal research triage (licensed sources; not distributed).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| CHW-FC-050 | Chiller efficiency (kW/ton) degradation | 3 | statistical | **verified** |
| CHW-FC-051 | CHWST reset not functioning | 3 | statistical | **verified** |
| CHW-FC-052 | CHW loop DP reset not functioning | 3 | statistical | **verified** |
| CHW-FC-053 | Chilled water low delta-T syndrome | 3 | rule | **verified** |

Severity and method per the reference's ch.13 cards.

## Relationships

- **CHW-FC-051/052** are the plant-side siblings of AHU-FC-057/058 (SAT/DSP
  reset) — same detector shape (setpoint range flat over a window while the
  load moves), same RetuningOpps lineage, and the same CLU-02-style "reset
  never programmed" root cause one system further upstream.
- **CHW-FC-053 (low delta-T)** is the plant-level symptom of coil-side
  defects the library already detects locally: fouled/leaking coil valves
  (FCU-FC-004, AHU-FC-014), three-way bypass, dirty filters — tied together
  by cluster CLU-06 (trigger CHW-FC-050).
- **CHW-FC-050**'s baseline follows the HP-FC-050 host-fitted pattern — the
  reference specifies a Ridge regression over load/CWST/CHWST; the graph
  carries the fitted coefficients as set_param placeholders.
