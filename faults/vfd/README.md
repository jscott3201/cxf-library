# VFD Fault Rules

Variable frequency drive fault detection rules (`VFD-*`). Source
grounding: HVAC FDD Reference v1.0 ch.15, PNNL VFD O&amp;M guidance, NIST's
generic faulty-regulation work, and verified library hunting precedents (see
each card's Deviations section). Application-agnostic: the same five rules serve
fan, pump, and other process drives, with the process-variable pair bound per
application.

Point dictionary: [`points/vfd.points.json`](../../points/vfd.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| VFD-0001 | Command vs feedback deviation | 2 | rule | **verified** |
| VFD-0002 | At minimum speed with load unsatisfied | 3 | rule | **verified** |
| VFD-0003 | At maximum speed with load unsatisfied | 3 | rule | **verified** |
| VFD-0004 | VFD process-loop hunting | 3 | rule | **verified** |
| VFD-0005 | VFD not in remote automatic control | 2 | rule | **verified** |

VFD-0001/0002 severity and method follow the reference's ch.15 cards. The three
library-authored expansion rules classify their adopted thresholds and source
adaptations on-card.

## Relationships

- All five rules share the `vfd-pump-faults` playbook.
- VFD-0001 suppresses the speed-limit and hunting rules when speed feedback is
  not trustworthy. VFD-0005 suppresses those same-drive automatic-loop rules
  while remote automatic authority is absent.
- No drive-control cluster is declared: mode, tracking, capacity, and tuning
  findings are peer symptoms without one causal trigger whose correction should
  clear the rest.
