# ERV Fault Rules

Energy recovery ventilator fault detection rules (`ERV-*`). Source
grounding: HVAC FDD Reference v1.0 ch.15 (Energy Recovery — adapted
authority; see each card's Deviations section). One statistical
effectiveness rule and one protective frost rule.

Point dictionary: [`points/erv.points.json`](../../points/erv.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| ERV-0001 | Sensible effectiveness degradation | 3 | statistical | **verified** |
| ERV-0002 | Frost protection not engaging | 2 | rule | **verified** |

Severity and method per the reference's ch.15 cards (its §5.8.8 index carries
no severity column). ERV-0001 computes sensible effectiveness from three
ERV-local temperatures with a ΔT evaluability gate (the AHU-0021 pattern on
a different ratio); ERV-0002 is a protective sequence-watchdog.

## Relationships

- ERV-0001 carries the erv-effectiveness playbook; ERV-0002's remediation
  is folded into the same document.
