---
schema: cxf-library/fault-card/v1
id: RTU-FC-055
name: Insufficient ventilation air
equipment: rtu
status: verified
phase: 2
method: rule
severity: 2
category: COMFORT_ENERGY
confidence: MEDIUM
estimation_method: QUALITATIVE_ONLY
source:
  - "HVAC FDD Reference v1.0 §11, RTU-FC-055"
  - "PNNL-23790 (RTU AFDD6)"
  - "ASHRAE Standard 62.1"
  - "PNNL EEM-06 (OA damper faults)"
g36: null
clusters: []
suppresses: []
suppressed_by: [AHU-FC-062]
related: [RTU-FC-054, AHU-FC-006, AHU-FC-060]
playbooks: [economizer-failure]
operating_states: "occupied with the supply fan running — both conjuncts are in the graph (occ_schedule, sf_status), because the reference writes them into the fault equation and both are canonical RTU points"
preconditions: "Occupancy schedule data available and current; the host evaluates the schedule (time zone, calendar, holidays) into the boolean occ_schedule point, and a stale or unknown schedule makes the verdict NO_EVAL rather than healthy. MAT must pass its integrity gate (AHU-FC-062, see suppressed_by): the fraction is a ratio of temperature differences, so a biased mixed-air reading moves it directly, and this rule's deficit branch is exactly where a low MAT lands. The temperature-difference gate is signalled in-rule by yTempDeltaOk; when it is false the verdict is NO_EVAL, not healthy."
points:
  - oat
  - rat
  - mat
  - sf_status
  - occ_schedule
outputs:
  - name: yFault
    description: True while the outdoor air fraction has stayed more than oa_deficit_margin below design_min_oa_fraction, occupied and with the supply fan running, for at least alarm_delay, with the temperature difference large enough to evaluate
  - name: yTempDeltaOk
    description: Evaluability signal — true when |oat − rat| exceeds min_delta; false means NO_EVAL and the host must ignore yFault
params:
  design_min_oa_fraction:
    default: 0.15
    unit: "1"
    description: Design minimum outdoor air fraction the unit owes its occupants (0–1)
    cxf: designConst.k
  oa_deficit_margin:
    default: 0.05
    unit: "1"
    description: Tolerance below the design minimum before the shortfall counts as a fault
    cxf: deficitBig.t
  min_delta:
    default: 6.0
    unit: "°C"
    description: Minimum |oat − rat| for the fraction to be meaningful; below it the rule is not evaluable
    cxf: deltaOk.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: RTU outdoor air intake — indoor air quality rather than energy
  savings_range: "IAQ primary; energy impact secondary — under-ventilation saves thermal energy while failing the occupants"
  climate_sensitivity: neutral
  runtime_estimation: "none — the reference publishes no formula and there is no waste term to compute. Fixing this fault costs energy rather than recovering it, so a host must not accumulate savings from yFault"
emissions:
  scope: "1|2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:2d1a469cb6689db185713b59c4047434"
  date: 2026-08-17
---

## Description

The unit is not delivering the outdoor air its occupants are owed. The building
is occupied, the fan is running, and the mixing-box energy balance says the
share of outdoor air in the supply is below the design minimum by more than the
allowance. Unlike every other fault on this quotient, the finding is a health
one: ASHRAE 62.1 sets the minimum for a reason, and a unit that misses it is
accumulating CO₂, humidity, and whatever else the space generates. That is why
the reference rates it severity 2 while rating its excess-air twin a 3.

Nothing about under-ventilation announces itself. The space holds temperature —
better than it should, since the unit has less outdoor air to condition — and
the energy signature runs the wrong way, so a bill review will never find it.
Two of the four diagnoses below are physical obstructions at the intake, one is
a number somebody typed, and the fourth is a building-pressure problem the unit
cannot see from its own points; none of them raises a complaint anyone will
phone in.

The fraction is inferred from three temperatures rather than measured, which
makes the diagnostic cheap and makes it conditional: outdoor and return air have
to differ enough for the mixture to locate the fraction between them. Hence the
explicit evaluability output.

## Detection Logic

```
oaf          = (mat − rat) / (oat − rat)
yTempDeltaOk = |oat − rat| > min_delta                  (false ⇒ host reports NO_EVAL)
yFault       = (design_min_oa_fraction − oaf > oa_deficit_margin)
               AND occ_schedule AND sf_status AND yTempDeltaOk,
               sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![RTU-FC-055 block graph](diagram.svg)

The fraction core is RTU-FC-054's, unchanged: `matRat` and `oatRat` form the two
differences and `oaf` divides them. `deficit` then subtracts the other way round
— `designConst.k − oaf` rather than `oaf − designConst.k` — so `deficitBig`
tests a positive gap against a positive threshold. That is the same identity
RTU-FC-054 uses, read from the other side: `oaf < design − margin` exactly when
`design − oaf > margin`. It keeps both reference tunables as independent
single-value `set_param` paths and keeps every parameter in the document
non-negative, which is the library's standing preference (precedent:
AHU-FC-055's `designConst`).

`and1` conjoins the deficit with the occupancy schedule, `and2` adds fan status,
and `gate` adds evaluability. Both occupancy and fan status are inputs to the
block rather than host preconditions, because the reference writes them into the
fault equation and both are canonical RTU points — the same reasoning that puts
`htg_vlv_cmd` inside AHU-FC-064 and `sf_status`/`occ_schedule` inside
AHU-FC-052. They participate in the persistence, too: the 30-minute clock starts
when the last conjunct becomes true, so a deficit that predates occupancy is
timed from the start of the occupied period, not from the start of the deficit.
The `occupancy_start_restarts_persistence` vector pins that.

`deltaOk`'s output is both `gate`'s second input and the boundary output
`yTempDeltaOk`, which is what makes the unguarded division safe. CDL `Divide`
follows IEEE-754, so `oat = rat` yields ±∞ or NaN rather than an error, and a
near-zero denominator amplifies ordinary sensor noise into a fraction of any
magnitude. NaN compares false everywhere and can never raise `deficitBig` — but
−∞ and a noise-inflated finite fraction both can, and a collapsing denominator
throws the quotient to either sign with equal ease, so the deficit branch is
exactly as exposed as RTU-FC-054's excess branch. `gate` stops them, because a
denominator small enough to misbehave is by construction a denominator below
`min_delta`. Garbage arithmetic cannot assert a fault; it can only make the rule
report itself unevaluable. The `small_delta_not_evaluable` vector pins that: the
fraction there reads 0.05, `deficitBig` is true, and `yFault` stays down.

Both comparisons are strict. A fraction sitting exactly at
`design_min_oa_fraction − oa_deficit_margin` is not a fault, and a temperature
difference of exactly `min_delta` is not evaluable. `persist` requires 30
continuous minutes, which rides out a damper stroke and a purge cycle; recovery
is immediate on the tick the fraction climbs back inside the margin.

## Possible Diagnoses

1. OA damper stuck closed or nearly closed
2. OA damper minimum position set too low
3. OA intake blocked — debris, snow, or ice
4. Exhaust fan creating negative building pressure

## Energy Impact

COMFORT_ENERGY, MEDIUM confidence, QUALITATIVE_ONLY, mapped to PNNL EEM-06 (OA
damper faults). The reference's own wording is that IAQ is the primary concern
and energy is secondary, and it publishes no savings range or runtime formula
for this card, because there is nothing to compute: under-ventilation is not
waste. A unit conditioning 5% outdoor air instead of 15% spends less on that air
than it should, and correcting the damper will raise the heating and cooling
load rather than lower it. The number worth carrying is the one going the other
way — the ventilation the occupants did not get — and this rule has the fraction
for it (`design_min_oa_fraction − oaf`, already on the wire at `deficit.y`) but
not the airflow to turn it into cubic metres.

A host that accumulates energy savings across a fault library must therefore
exclude this rule explicitly. AHU-FC-006 carries the same warning for its low
branch; this rule is that branch made reachable, so the warning matters more
here.

## Emissions Impact

Scope 1 or 2 depending on how the unit heats, QUALITATIVE_EMISSIONS, MEDIUM
confidence. The reference's figure is 50–300 kg CO₂e/yr and it labels IAQ the
primary concern with emissions secondary; the sign is negative, in the sense
that fixing the fault raises emissions slightly by restoring the ventilation
load the unit was supposed to carry. No avoided-emissions basis applies, and
none is claimed.

## Deviations

- **`min_delta` default adopted, not transcribed.** The reference states the
  fraction is computed only when `|OAT − RAT| > min_delta` but omits the
  parameter from its tunables table. This card adopts 6.0 °C, the same value
  RTU-FC-054, AHU-FC-055, and AHU-FC-064 use, so every rule in the library that
  runs this quotient agrees on when it is meaningful (PNNL-27338 uses 5 °F for
  the same computation). A site that retunes one should retune all of them.
- **The deficit is computed as a positive gap.** The reference writes the test
  as `oa_fraction < (design_min_oa_fraction − oa_deficit_margin)`. Implemented
  literally, the two tunables would have to be folded into one threshold value
  and a host could no longer retune either alone. Subtracting the fraction from
  a `Reals.Sources.Constant` and comparing the remaining gap against
  `oa_deficit_margin` keeps both as independent single-value `set_param` paths,
  keeps every parameter non-negative, and is algebraically identical.
- **Occupancy and fan status are in the graph, unlike RTU-FC-054's economizer
  term.** The library keeps operating-state gating host-side, and its twin
  RTU-FC-054 does exactly that with `economizer_should_be_inactive(oat, mode)`.
  The two terms here are different: `occ_schedule` and `sf_status` are canonical
  RTU points with measured or host-published values, so the reference's
  `in_occupied_schedule AND sf_status = ON` transcribes directly rather than
  needing a mode enumeration the point dictionary does not carry. The precedents
  are AHU-FC-052, which takes both points into its graph, and AHU-FC-064, which
  takes `htg_vlv_cmd` in for the same reason. What stays host-side is the
  schedule's provenance — time zone, calendar, holidays — which is why
  `preconditions` still names it.
- **Evaluability is an output, not just a precondition.** The `min_delta` test
  is computable from this rule's own inputs, so SCHEMA.md requires exposing it
  as a boolean output: `yTempDeltaOk`. It is additionally wired into `gate`, so
  `yFault` reads false throughout a non-evaluable period — but false `yFault`
  under false `yTempDeltaOk` means "unknown", not "healthy", and on a health
  fault that distinction is the whole point.
- **Both comparisons are strict** (`>`). The reference does not specify boundary
  behavior; CDL `Reals` offers no `GreaterEqual`, so the choice is made rather
  than inherited. The disagreement with an inclusive reading has measure zero on
  a real temperature signal and errs toward silence, and both boundaries are
  pinned from both sides in `vectors.json`. One caveat on the deficit edge: the
  nominal alarm point — a fraction of exactly 0.10 against a 0.15 design and a
  0.05 margin — is not representable in binary. Computed as (20 − 22)/(2 − 22)
  the fraction is the double nearest 0.10, and subtracting it from the double
  nearest 0.15 lands two ulps below the double nearest 0.05, so
  `deficit_exactly_at_threshold` reads healthy. Decimal arithmetic gives the
  same verdict through the strict `>`, so the rounding hides nothing here; a
  host binding coarsely quantized temperatures should still not read anything
  into a fraction sitting on the threshold.
- **No published test vectors.** The reference's chapter 11 card states the
  logic, the tunables, the diagnoses, and the energy and emissions profiles, but
  publishes no worked vectors for this fault. `vectors.json` is authored from
  the equation: healthy minimum ventilation, a shut damper, each of the two
  boolean conjuncts holding the alarm down on its own, a negative inferred
  fraction, both sides of the deficit boundary, both sides of the evaluability
  boundary, the NO_EVAL case with `deficitBig` true to prove the gate does the
  work, a transient shorter than `alarm_delay`, an occupancy start that restarts
  the persistence, and a recovery.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a deficit already present at load waits out the full 30
  minutes instead of alarming on the first tick after a controller restart.

## Notes

This rule catches what AHU-FC-006 cannot, and the arithmetic is the reason.
AHU-FC-006 is G36 FC#6: the same quotient, tested symmetrically against a 0.30
tolerance. Its Notes record the finding — with `%OAmin` at 0.15 and eF at 0.30,
its low-side alarm point is a fraction below −0.15, which a physical mixing box
cannot produce, so no damper position trips it. A damper welded shut delivers
zero ventilation and AHU-FC-006 reads the unit as healthy; its
`damper_shut_no_ventilation_stays_silent` vector pins that miss deliberately.
Here the alarm point is a fraction below 0.10, and the same shut damper reads a
deficit of 0.15 against a 0.05 margin and alarms —
`damper_shut_no_outdoor_air` is the same scenario with the opposite verdict. The
two rules are complementary rather than redundant: FC#6 polices deviation from a
G36 minimum-OA state in either direction with a band sized to suppress false
alarms, and this is the dedicated under-ventilation alarm with a margin sized
for that one job. A site that wants a real ventilation-deficit alarm should
deploy this one and not expect FC#6 to supply it.

A negative inferred fraction reads here as a large deficit and alarms — `mat`
above both `oat` and `rat` puts `oaf` below zero, and `negative_fraction_alarms`
pins the verdict. With honest sensors that is a genuine finding: a shut damper
plus heat picked up before the sensor — conduction through the casing, or fan
heat where the sensor sits downstream of a draw-through fan. With a lying `mat`
it is not a ventilation finding at all, and it is exactly what the
AHU-FC-062 suppression exists to silence. Expect the pair to fire together and
read AHU-FC-062 first; when both are active the sensor is the story and the
fraction is noise.

`suppressed_by: [AHU-FC-062]` is transcribed verbatim from the reference's note
on this card, and it points across equipment families on purpose. AHU-FC-062
tests whether MAT lies inside the envelope its two sources bracket, and that
graph consumes nothing but `mat`, `oat`, and `rat` — it is equipment-agnostic,
exactly as AHU-FC-061's block graph is, and the host instantiates it against
this RTU's own three points rather than against an air handler elsewhere in the
building.

Field-verify before dispatching a damper repair. Three temperatures and a design
constant infer the fraction; a CO₂ reading in the space, or a smoke pencil at
the intake, measures the thing that actually matters and costs an afternoon. If
the fraction is genuinely low, command the damper open and watch the mixed-air
temperature move toward outdoor: no movement means the actuator, linkage, or a
blocked intake, and the
[economizer-failure](../../../playbooks/economizer-failure.md) playbook's
on-site steps apply. Movement means the sequence never commanded minimum
position, and the fix is at a desk. Check the intake screen first in a climate
that gets snow — diagnosis 3 is the one that fixes itself for free and comes
back every winter.
