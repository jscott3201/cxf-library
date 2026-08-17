# HP Fault Rules

Heat pump fault detection rules (`HP-FC-*`). Source grounding: HVAC FDD
Reference v1.0 ch.11 (Heat Pumps — adapted authority; see each card's
Deviations section). Heat pumps extend the RTU fault set with defrost cycle
monitoring and reversing-valve diagnostics; refrigerant undercharge is the
most frequent fault (Barandier 2023).

Point dictionary: [`points/hp.points.json`](../../points/hp.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| HP-FC-050 | COP degradation vs baseline | 3 | statistical | **verified** |
| HP-FC-051 | Defrost cycle anomaly | 3 | rule | **verified** |
| HP-FC-052 | Reversing valve fault | 2 | rule | **verified** |

Severity and method per the reference's ch.11 cards (its §5.8.4 index carries
no severity column). HP-FC-050's COP-vs-OAT baseline is host-fitted: the host
runs the 14-day learning regression and writes the slope/intercept as rule
parameters via `set_param` (R² > 0.6 precondition); the graph evaluates the
fitted line — the library's first host-learned baseline.

## Relationships

- HP-FC-050/051/052 share the heat-pump-faults playbook.
- RTU-FC-050 (compressor short-cycling) applies to HP equipment per its
  reference card; an HP instance would add defrost handling and is not yet
  scaffolded.
