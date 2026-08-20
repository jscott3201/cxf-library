# Hydronic Heat-Exchanger Fault Rules

Hydronic heat-exchanger rules (`HX-*`) cover one indirect liquid-to-liquid
four-port heat exchanger. The primary side normally belongs to the external or
source network; the secondary side normally belongs to the served/load loop.
Both identities stay fixed while signed heat transfer may reverse.

Point dictionary: [`points/hx.points.json`](../../points/hx.points.json).
Brick 1.4.4 provides exact generic `Heat_Exchanger`; ASHRAE 223 PPR2.1 provides
exact `HydronicHeatExchanger` with paired primary/secondary inlet and outlet
connection points.

Excluded from the initial family: air/refrigerant heat exchangers and coils,
direct-contact devices, phase-changing steam service, potable-water service,
and an HX bank whose temperatures/flows do not preserve one coherent identity.

## Index

| ID | Name | Sev | Method | Status |
|---|---|---:|---|---|
| HX-0001 | Hydronic heat-exchanger effectiveness degradation | 3 | statistical | **verified** |
| HX-0002 | Heat exchanger active with one-side flow missing | 2 | rule | **verified** |
| HX-0003 | Heat transfer persists with control valve commanded closed | 3 | rule | **verified** |

## Topology and telemetry

| Tier | Required contract | Supported rule |
|---|---|---|
| Flow proof | final both-flow exchange command plus individual primary/secondary branch flows | HX-0002 |
| Performance | four connection-point temperatures, both branch flows, configured fluid properties, validated actual and frozen expected effectiveness | HX-0001 |
| Isolation | final isolating-valve command plus validated signed heat-transfer derivation | HX-0003 |

`primary` and `secondary` are side identities, never synonyms for hot/cold or
supply/return. Positive `heat_transfer_rate` means primary loses heat and
secondary gains it; cooling normally has the opposite sign. HX-0001 and
HX-0003 are magnitude-based and work in either direction.

Common-header/fleet flow, duplicated side sensors, unaligned timestamps, a
baseline fitted on the scored interval, or missing glycol properties make the
thermal rules NO_EVAL. The CXF graphs do not calculate effectiveness: the host
must validate every denominator and side energy balance before publishing the
derived point.

## Source and validation posture

EnergyPlus 25.1.0's official `HeatExchanger:FluidToFluid` model and
`PlantLoopChainHeating.idf`/`PlantLoopChainCooling.idf` testfiles provide the
healthy Layer 3 path. The library has not yet claimed a completed simulation
campaign for these rules. Guelpa and Verda (Applied Energy 258, 2020,
doi:10.1016/j.apenergy.2019.114059) provide field precedent for fouling
detection from primary flow and both-side temperatures across 325 district
heating substations, but no source provides portable alarm thresholds.

## Relationships

- HX-0002 is proof/evaluability context for HX-0001, but no global suppression
  is encoded because fault IDs are not instance-scoped.
- HX-0003 can explain degradation or wasted transfer while HX-0001 remains a
  separate performance verdict.
- PMP-0001/PMP-0003 may locate a failed pump behind HX-0002; they are related
  workflows, not duplicate HX signatures.
