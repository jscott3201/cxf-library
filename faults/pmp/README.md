# PMP Fault Rules

Hydronic pump fault detection rules (`PMP-*`). PMP-0001/PMP-0002 originate in
the HVAC FDD Reference v1.0 ch.15; the later proof, cycling, stopped-flow, and
expected-power rules are library-authored extensions grounded in verified graph
precedents and public pump-system guidance. The family covers direct proof,
hydraulic delivery, protective cycling, and baseline electrical performance
without claiming a universal pump curve.

Point dictionary: [`points/pmp.points.json`](../../points/pmp.points.json).
Loop-agnostic: the same rules bind to CHW, HW, or condenser-water pumps.

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| PMP-0001 | Pump commanded on, no flow detected | 2 | rule | **verified** |
| PMP-0002 | Pump deadheading (high DP, low/no flow) | 2 | rule | **verified** |
| PMP-0003 | Pump proof-of-operation failure | 2 | rule | **verified** |
| PMP-0004 | Pump short-cycling | 3 | rule | **verified** |
| PMP-0005 | Flow through stopped pump | 2 | rule | **verified** |
| PMP-0006 | Pump input-power degradation | 3 | statistical | **verified** |

All six are Phase 2. Thresholds that depend on pump size, branch design flow,
sensor uncertainty, or a fitted model are explicitly site-configured on their
cards.

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
- **PMP-0003 suppresses PMP-0005 on the same pump** because unreliable run
  proof invalidates the stopped/running premise. The stopped-flow graph remains
  raw and the host scopes suppression by equipment instance.
- **PMP-0004 complements VFD-0004**: pump starts and analog speed hunting are
  different signatures. Neither suppresses the other.
- **PMP-0006 relates to VFD-0001/VFD-0005 but is not globally suppressed by
  them.** A drive finding invalidates expected power only when the deployment's
  model actually consumes the disputed drive state/speed and the host can prove
  both rules belong to the same pump/drive.

## Ontology and cluster decisions

The PR 03 point additions pin ASHRAE 223 to the inspected public-review
artifact `1.0.0-ppr.2.1` (SHA-256
`1f156f9938c0be430d2216e01e31bb183c438ba318d8d4a23d2f074ebcd6f573`),
matching the ERV/VFD expansion precedent. This is an explicit migration from
the former unverified `v1.0.0-2026` label, not a claim of a final release.

No Pump Delivery Failure cluster is added. Running with no flow, deadheading,
proof disagreement, and flow through a stopped branch have mutually different
premises and no single trigger whose correction should clear the set within the
cluster contract's 24–48 hour window.
