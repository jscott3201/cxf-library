# VAV Fault Rules

VAV terminal unit fault detection rules (`VAV-FC-*`). Source grounding: HVAC
FDD Reference v1.0 ch.10 (adapted authority — see each card's Deviations
section). The chapter's economics are multiplicative: a building has dozens or
hundreds of boxes, so a small per-box inefficiency — an oversized minimum, a
leaking reheat valve — compounds into the "74% problem" class of building-wide
waste. Excess minimum flow (VAV-FC-050) is PNNL's top-performing office EEM.

Point dictionary: [`points/vav.points.json`](../../points/vav.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| VAV-FC-050 | Minimum airflow setpoint too high | 3 | rule | **verified** |
| VAV-FC-051 | Rogue zone driving AHU reset | 3 | rule | **verified** |
| VAV-FC-052 | Reheat valve open with zone satisfied | 3 | rule | **verified** |
| VAV-FC-053 | Airflow tracking error | 3 | rule | **verified** |
| VAV-FC-054 | Damper hunting / oscillation | 3 | rule | **verified** |
| VAV-FC-055 | Reheat waste during cooling season | 3 | rule | **verified** |
| VAV-FC-100 | Zone temperature sensor drift | 3 | statistical | planned |
| VAV-FC-101 | VAV airflow tracking CUSUM | 3 | statistical | **verified** |
| VAV-FC-102 | Zone temperature CUSUM | 3 | statistical | **verified** |
| VAV-FC-103 | Reheat coil leakage CUSUM | 3 | statistical | **verified** |

Severity and method per the reference's ch.10 cards (its §5.8.2 index carries
no severity column). VAV-FC-100 is phase 3; its neighbor-comparison method is
expressible with a host-derived median point and can be authored once the
phase-3 scope opens.

VAV-FC-101/102/103 are the VPACC trio (NIST/CEC PIER Project 2.3 §5.1):
two-sided CUSUM charts over the three per-box error signals, the library's
first feedback-loop topology (`Discrete.UnitDelay` accumulators with in-graph
occupancy reset). A box without a discharge-air sensor runs 101/102 as the
source's reduced two-channel VPACC; 103 is the one channel that needs
`vav_dat`. Parameter defaults are calibrated by the committed harness method
(tools/simharness `vavcal`) plus the source's Iowa Energy Center campaign, and
remain per-box commissioning values on every card.

## Relationships

- **VAV-FC-050 / 052 / 055** are the zone-level reheat-waste family — the
  terminal-unit end of CLU-02's "74% problem" (AHU-FC-053/057 see the same
  defect from the air handler's side via `zone_reheat_fraction`).
- **VAV-FC-051** is the zone-side cause of the reset failures AHU-FC-057/058
  detect at the AHU: one rogue zone holds the reset down for everyone.
- **VAV-FC-053/054** are the box-mechanics pair (tracking and stability);
  VAV-FC-054 is AHU-FC-056's zone-level sibling and reuses its detector
  patterns.
