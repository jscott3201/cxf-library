# PMP Fault Rules

Hydronic pump fault detection rules (`PMP-*`). Source grounding: HVAC FDD
Reference v1.0 ch.15 "Pumps" (pdf pages 133–135) — two fully specified rules,
both protective: a pump burning energy while moving no water is wasting 100%
of its input and eating its seals and bearings at the same time. These are the
pump IDs the `vfd-pump-faults` playbook has cited since it was transcribed;
this family closes that dangling reference.

Point dictionary: [`points/pmp.points.json`](../../points/pmp.points.json).
Loop-agnostic: the same rules bind to CHW, HW, or condenser-water pumps.

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| PMP-0001 | Pump commanded on, no flow detected | 2 | rule | **verified** |
| PMP-0002 | Pump deadheading (high DP, low/no flow) | 2 | rule | **verified** |

Severity and method per the reference's ch.15 cards. Both are Phase 2,
Category PROTECTIVE — the savings line is 100% of pump energy while active,
plus avoided mechanical damage ($5K–$20K seal/bearing failures on -051).

## Relationships

- **PMP-0001 vs -051** differ in what they can see: -050 needs only
  cmd/status/flow and catches the broad "no useful work" condition;
  -051 adds the DP signature that distinguishes true deadheading (valves
  closed against a running pump) from impeller/coupling failure (DP low).
  Diagnosis order in the shared [vfd-pump-faults](../../playbooks/vfd-pump-faults.md)
  playbook follows that split.
- **VFD-0001/VFD-0002** watch the same drive from the electrical side; a
  deadheading pump at fixed speed shows normal VFD tracking — the families
  are complementary, not redundant.
