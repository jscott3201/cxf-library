# HW Fault Rules

Hot water / boiler plant fault detection rules (`HW-FC-*`). Source grounding:
HVAC FDD Reference v1.0 ch.14 (pdf pages 124–127) — the three most impactful
boiler plant problems: short-cycling, combustion efficiency degradation, and
the missing OAT lockout the chapter calls one of the simplest, highest-ROI
fixes in the whole catalog (>25% prevalence, 100% of plant energy wasted
while active).

Point dictionary: [`points/hw.points.json`](../../points/hw.points.json).
Supplementary deep-read sources per `_research/local/paper-triage.md`
(G36 heating-plant AFDD document, FEMP O&M guide, PNNL-13890) —
paraphrase-and-cite only.

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| HW-FC-050 | Boiler short-cycling | 2 | rule | **verified** |
| HW-FC-051 | Boiler efficiency degradation | 3 | statistical | **verified** |
| HW-FC-052 | Boiler/HW pump on above OAT lockout | 3 | rule | **verified** |

Severity and method per the reference's ch.14 cards.

## Relationships

- **HW-FC-050** is the boiler member of the short-cycling family
  (AHU-FC-004, RTU-FC-050, FCU-FC-001, HP-FC-051's frequency branch) and
  inherits its edge-counter idiom and Nyquist band discipline.
- **HW-FC-051** follows the HP-FC-050 host-fitted baseline pattern
  (efficiency vs firing rate, single regressor).
- **HW-FC-052** is the heating-plant cousin of AHU-FC-052's after-hours
  operation — equipment running when conditions say it cannot be useful;
  Scope 1 emissions make it unusually consequential per kWh.
