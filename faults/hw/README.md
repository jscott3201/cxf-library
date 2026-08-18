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
| HW-FC-053 | HW loop low delta-T | 3 | rule | **verified** |
| HW-FC-054 | HW loop DP too high (pump speed vs mild OAT) | 3 | rule | **verified** |
| HW-FC-055 | HW loop DP reset not functioning | 3 | statistical | **verified** |
| HW-FC-056 | HW supply temperature too high at low load | 3 | rule | **verified** |
| HW-FC-057 | HWS temperature reset not functioning | 3 | statistical | **verified** |

Severity and method for FC-050–052 per the reference's ch.14 cards.
FC-053–057 are **library-authored** rules grounded in PNNL-27338's hot-water
distribution measure-identification algorithms (§4; deep-read memo in
`_research/local/deep-reads/pnnl-27338-rcx-measures.md`) — the reference's
ch.14 specifies only three rules, so these five extend the family under the
same numbering with explicit non-reference sourcing; severities are
library-assigned by analogy to the AHU/CHW siblings.

## Relationships

- **HW-FC-050** is the boiler member of the short-cycling family
  (AHU-FC-004, RTU-FC-050, FCU-FC-001, HP-FC-051's frequency branch) and
  inherits its edge-counter idiom and Nyquist band discipline.
- **HW-FC-051** follows the HP-FC-050 host-fitted baseline pattern
  (efficiency vs firing rate, single regressor).
- **HW-FC-052** is the heating-plant cousin of AHU-FC-052's after-hours
  operation — equipment running when conditions say it cannot be useful;
  Scope 1 emissions make it unusually consequential per kWh.
