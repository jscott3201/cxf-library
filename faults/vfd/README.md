# VFD Fault Rules

Variable frequency drive fault detection rules (`VFD-FC-*`). Source
grounding: HVAC FDD Reference v1.0 ch.15 (Variable Frequency Drives —
adapted authority; see each card's Deviations section). Application-agnostic:
the same two rules serve fan and pump drives, with the process-variable pair
bound per application.

Point dictionary: [`points/vfd.points.json`](../../points/vfd.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| VFD-FC-050 | Command vs feedback deviation | 2 | rule | **verified** |
| VFD-FC-051 | At minimum speed with load unsatisfied | 3 | rule | **verified** |

Severity and method per the reference's ch.15 cards (its §5.8.8 index carries
no severity column).

## Relationships

- Both rules share the vfd-pump-faults playbook (which also covers the
  future PMP family).
