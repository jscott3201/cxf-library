# HW Fault Rules

Hot water / boiler plant fault detection rules (`HW-*`). Core source grounding:
HVAC FDD Reference v1.0 ch.14 (pdf pages 124–127) — the three most impactful
boiler plant problems: short-cycling, combustion efficiency degradation, and
the missing OAT lockout the chapter calls one of the simplest, highest-ROI
fixes in the whole catalog (>25% prevalence, 100% of plant energy wasted
while active).

Point dictionary: [`points/hw.points.json`](../../points/hw.points.json).
Supplementary deep-read sources per the project’s internal research triage (licensed sources; not distributed)
(G36 heating-plant AFDD document, FEMP O&M guide, PNNL-13890) —
paraphrase-and-cite only. HW-0010..0012 extend the family with regulation and
staging checks grounded in NIST regulation concepts, the LBNL simulated boiler
plant inventory, and verified library graph precedents. Their numeric settings
are explicitly classified; HW-0012's load/stage thresholds are adoption-blocking
placeholders rather than portable defaults.

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| HW-0001 | Boiler short-cycling | 2 | rule | **verified** |
| HW-0002 | Boiler efficiency degradation | 3 | statistical | **verified** |
| HW-0003 | Boiler/HW pump on above OAT lockout | 3 | rule | **verified** |
| HW-0004 | HW loop low delta-T | 3 | rule | **verified** |
| HW-0005 | HW loop DP too high (pump speed vs mild OAT) | 3 | rule | **verified** |
| HW-0006 | HW loop DP reset not functioning | 3 | statistical | **verified** |
| HW-0007 | HW supply temperature too high at low load | 3 | rule | **verified** |
| HW-0008 | HWS temperature reset not functioning | 3 | statistical | **verified** |
| HW-0009 | Boiler proof-of-operation failure | 2 | rule | **verified** |
| HW-0010 | Hot-water supply temperature tracking failure | 3 | rule | **verified** |
| HW-0011 | Hot-water temperature-control hunting | 3 | rule | **verified** |
| HW-0012 | Excess boiler stages at low plant load | 3 | rule | **verified** |

Severity and method for FC-050–052 per the reference's ch.14 cards.
FC-053–057 are **library-authored** rules grounded in PNNL-27338's hot-water
distribution measure-identification algorithms (§4; adapted via an internal
paraphrased deep-read digest, not distributed) — the reference's
ch.14 specifies only three rules, so these five extend the family under the
same numbering with explicit non-reference sourcing; severities are
library-assigned by analogy to the AHU/CHW siblings.

## Relationships

- **HW-0001** is the boiler member of the short-cycling family
  (AHU-0004, RTU-0001, FCU-0001, HP-0002's frequency branch) and
  inherits its edge-counter idiom and Nyquist band discipline.
- **HW-0002** follows the HP-0001 host-fitted baseline pattern
  (efficiency vs firing rate, single regressor).
- **HW-0003** is the heating-plant cousin of AHU-0018's after-hours
  operation — equipment running when conditions say it cannot be useful;
  Scope 1 emissions make it unusually consequential per kWh.
- **HW-0010** mirrors CHW-0007's strict two-sided hydronic tracking form, but
  gates on firing plus established circulation and compares a coherent plant
  header with its final active target.
- **HW-0011** adapts VFD-0004's dual mean-crossing/MAD regulation topology to
  capacity-normalized boiler firing and HWS error. Its counts require a fixed
  60 s exercised tick and a complete 1800 s warm-up.
- **HW-0012** uses a native integer firing-unit count and a host-derived 0..1
  useful-load fraction. `yLoadOk` is an evaluability output; fleet membership,
  capacity basis, and the allowed staging map are commissioning obligations.
- No Boiler Control Instability cluster is created. Cycling, hunting, tracking,
  and over-staging can co-occur, but they do not share a reliable first trigger
  or one repair that clears all members.
