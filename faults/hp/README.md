# HP Fault Rules

Heat pump fault detection rules (`HP-*`). Source grounding: HVAC FDD
Reference v1.0 ch.11 (Heat Pumps — adapted authority; see each card's
Deviations section). Heat pumps extend the RTU fault set with defrost cycle
monitoring and reversing-valve diagnostics; refrigerant undercharge is the
most frequent fault (Barandier 2023).

Point dictionary: [`points/hp.points.json`](../../points/hp.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| HP-0001 | COP degradation vs baseline | 3 | statistical | **verified** |
| HP-0002 | Defrost cycle anomaly | 3 | rule | **verified** |
| HP-0003 | Reversing valve fault | 2 | rule | **verified** |
| HP-0004 | Refrigerant undercharge (superheat/subcooling divergence) | 3 | rule | **verified** |
| HP-0005 | Refrigerant overcharge (subcooling high) | 3 | rule | **verified** |
| HP-0006 | Reversing-valve internal bypass leakage | 3 | rule | **verified** |

Severity and method per the reference's ch.11 cards (its §5.8.4 index carries
no severity column). HP-0001's COP-vs-OAT baseline is host-fitted: the host
runs the 14-day learning regression and writes the slope/intercept as rule
parameters via `set_param` (R² > 0.6 precondition); the graph evaluates the
fitted line — the library's first host-learned baseline.

## Relationships

- HP-0001/HP-0002/HP-0003 share the heat-pump-faults playbook.
- RTU-0001 (compressor short-cycling) applies to HP equipment per its
  reference card; an HP instance would add defrost handling and is not yet
  scaffolded.

## Refrigerant-side family (library-authored, batch 17)

HP-0004/HP-0005/HP-0006 are grounded in NIST SP 1087 (2008) via the adapt-tier
program — the library's first refrigerant-side rules, built on the
suction/liquid-line temperatures and host-derived saturation temperatures
(P-T lookup) landed in `points/hp.points.json`. All three replace the
source's conditions-regressed no-fault baseline with fixed commissioning
placeholders (named simplification, RTU-0002 precedent). Wiring notes:
a charge cluster (HP-0004 trigger → HP-0001 member) and
`HP-0001 suppressed_by: [HP-0004]` are recorded candidates, left
unwired pending a decision on cross-family suppression conventions.
