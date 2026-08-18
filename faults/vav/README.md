# VAV Fault Rules

VAV terminal unit fault detection rules (`VAV-*`). Source grounding: HVAC
FDD Reference v1.0 ch.10 (adapted authority — see each card's Deviations
section). The chapter's economics are multiplicative: a building has dozens or
hundreds of boxes, so a small per-box inefficiency — an oversized minimum, a
leaking reheat valve — compounds into the "74% problem" class of building-wide
waste. Excess minimum flow (VAV-0001) is PNNL's top-performing office EEM.

Point dictionary: [`points/vav.points.json`](../../points/vav.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| VAV-0001 | Minimum airflow setpoint too high | 3 | rule | **verified** |
| VAV-0002 | Rogue zone driving AHU reset | 3 | rule | **verified** |
| VAV-0003 | Reheat valve open with zone satisfied | 3 | rule | **verified** |
| VAV-0004 | Airflow tracking error | 3 | rule | **verified** |
| VAV-0005 | Damper hunting / oscillation | 3 | rule | **verified** |
| VAV-0006 | Reheat waste during cooling season | 3 | rule | **verified** |
| VAV-0010 | Zone temperature sensor drift | 3 | statistical | planned |
| VAV-0007 | VAV airflow tracking CUSUM | 3 | statistical | **verified** |
| VAV-0008 | Zone temperature CUSUM | 3 | statistical | **verified** |
| VAV-0009 | Reheat coil leakage CUSUM | 3 | statistical | **verified** |

Severity and method per the reference's ch.10 cards (its §5.8.2 index carries
no severity column). VAV-0010 is phase 3; its neighbor-comparison method is
expressible with a host-derived median point and can be authored once the
phase-3 scope opens.

VAV-0007/VAV-0008/VAV-0009 are the VPACC trio (NIST/CEC PIER Project 2.3 §5.1):
two-sided CUSUM charts over the three per-box error signals, the library's
first feedback-loop topology (`Discrete.UnitDelay` accumulators with in-graph
occupancy reset). A box without a discharge-air sensor runs 101/102 as the
source's reduced two-channel VPACC; 103 is the one channel that needs
`vav_dat`. Parameter defaults are calibrated by the committed harness method
(tools/simharness `vavcal`) plus the source's Iowa Energy Center campaign, and
remain per-box commissioning values on every card.

## Relationships

- **VAV-0001 / 052 / 055** are the zone-level reheat-waste family — the
  terminal-unit end of CLU-02's "74% problem" (AHU-0019/AHU-0023 see the same
  defect from the air handler's side via `zone_reheat_fraction`).
- **VAV-0002** is the zone-side cause of the reset failures AHU-0023/AHU-0024
  detect at the AHU: one rogue zone holds the reset down for everyone.
- **VAV-0004/VAV-0005** are the box-mechanics pair (tracking and stability);
  VAV-0005 is AHU-0022's zone-level sibling and reuses its detector
  patterns.
