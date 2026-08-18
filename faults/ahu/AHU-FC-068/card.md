---
schema: cxf-library/fault-card/v1
id: AHU-FC-068
name: Economizing past changeover
equipment: ahu
status: verified
phase: 2
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "Bushby, Castro, Schein, House (2001), NIST/CEC PIER Project 2.3 report — §4.2 Rule 9 (Table 1, p. 9): `Toa > Tco + εt` in Mode 3; Mode 1-5 actuator signatures §4.1-4.2 (pp. 6-7); threshold defaults §4.2.3 (p. 11)"
  - "House, Vaezi-Nejad, Whitcomb (2001), ASHRAE Transactions 107(1), 'An Expert Rule Set for Fault Detection in Air-Handling Units' — the paper the PIER report names as APAR's derivation"
  - "PNNL-27338 §3.4 (Katipamula et al. 2018) — the same test seventeen years later: a damper-position-only 'economizing when it should not' check, gated on the differential dry-bulb comparison rather than a fixed changeover temperature"
  - "Both reports were read through internal paraphrased digests; neither is redistributed with this library"
  - "Sibling precedent: AHU-FC-051 (mirrored graph, changeover-type switch, every parameter shape); AHU-FC-064 (the heating-side excess-OA relative)"
  - "Library extension: the HVAC FDD Reference v1.0 ch.9 specifies AHU-FC-001..065 and stops — see faults/ahu/README.md"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [AHU-FC-051, AHU-FC-064]
playbooks: [economizer-failure]
operating_states: "OS#3 (mechanical cooling with 100% outdoor air) — host-gated. The actuator half of that signature, a modulating cooling coil with the OA damper open, is also tested in-rule by clgOn and dmprHigh; the mode determination itself is the host's."
preconditions: "Supply fan running, and the unit must have a return-air path — a 100%-outdoor-air or makeup-air unit has no changeover to miss and reads as a permanent fault. The outdoor/return comparison must be evaluable: |oat - rat| >= TMIN (APAR's own ∆Tmin is 5.6 °C / 10 °F, §4.2.3 p. 11; AHU-FC-051 cites PNNL-27338's 5 °F for the same gate), since two sensors reading within their combined error of each other cannot establish which air is warmer. Hosts also gate on OAT sensor quality — a sensor reading low produces this fault's signature with the economizer control working correctly (diagnosis 3). When either gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - oat
  - rat
  - clg_vlv_cmd
  - oa_dmpr_cmd
outputs:
  - name: yFault
    description: True while outdoor conditions have been past changeover, mechanical cooling has run, and the OA damper command has stayed above econ_damper_high_threshold, all continuously for at least alarm_delay
params:
  econ_type_is_ddb:
    default: true
    unit: bool
    description: Changeover type — true = differential dry-bulb (compare oat to rat), false = fixed changeover temperature (compare oat to econ_hl_temp). Same parameter, same meaning, same default as AHU-FC-051; a unit running both rules must carry the same value in both
    cxf: isDDB.k
  econ_hl_temp:
    default: 21.0
    unit: "°C"
    description: Fixed changeover temperature, used only when econ_type_is_ddb is false. This is APAR's Tco, the temperature at which the unit should step from 100% outdoor air to minimum outdoor air
    cxf: hlConst.k
  temp_deadband:
    default: 1.0
    unit: "°C"
    description: Margin the changeover comparison must clear before economizing counts as unjustified; binds both changeover branches. APAR's own value for this threshold is εt = 1.7 °C (§4.2.3, p. 11) — see Deviations
    cxf: [ddbPast.t, hlPast.t]
  cooling_enabled_threshold:
    default: 10.0
    unit: "%"
    description: Cooling valve command above which mechanical cooling counts as active
    cxf: clgOn.t
  econ_damper_high_threshold:
    default: 75.0
    unit: "%"
    description: OA damper command above which the unit counts as still economizing rather than holding a minimum position
    cxf: dmprHigh.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU mechanical cooling energy, from outdoor air imported above the ventilation minimum
  savings_range: "5-20% of cooling energy is PNNL-27338 §3's published range for correcting economizer faults as a class; neither source breaks out the share belonging to this direction alone"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "excess_clg_kw = (oa_dmpr_cmd/100 − design_min_oa_fraction) × supply_airflow × ρ·cp × (oat − rat) — the sensible load the unit imports above its ventilation minimum. design_min_oa_fraction and supply_airflow are host values, not points of this rule. Sensible only: on a humid day the latent term is the larger half, so this is a floor"
emissions:
  scope: "2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:c68dcb56b390b6fa7294fb9245b6f8f2"
  date: 2026-08-18
---

## Description

Outdoor air stopped being worth having and the dampers never found out. The
unit opened wide for free cooling on a mild morning, the afternoon turned hot,
and the sequence that should have stepped the dampers back to minimum position
and let the coil carry the load did not run — so the coil is carrying the load
anyway, plus the load the open dampers keep importing. On a 30 °C afternoon
against 22 °C return air, every point of outdoor air fraction above the
ventilation minimum hands the cooling coil another 8 °C of sensible lift on
that share of the airflow, and more than that once the outdoor air is humid.

This is AHU-FC-051 run backwards. That rule finds a unit that should be
economizing and is not; this one finds a unit that should have stopped and has
not. Same four points, same three conjuncts, same graph with the temperature
comparison and the damper comparison both reversed. The pair covers the two
ways one changeover decision fails, and because both use the same deadband
around the same comparison, they cannot both assert on the same unit at the
same time.

It is the quieter of the two failures. A damper stuck at minimum is eventually
noticed as a cooling bill; a damper stuck open in cooling weather is noticed as
a cooling bill *and* an occupant who is warm, but only if the coil runs out of
capacity — and until it does, the unit holds setpoint and looks healthy. This
rule is a library extension: the HVAC FDD Reference's chapter 9 does not
specify it, and the logic comes from APAR Rule 9 with the graph shape, the
parameter set and the changeover switch taken from AHU-FC-051.

## Detection Logic

```
past_changeover = (oat - rat)          > temp_deadband   when econ_type_is_ddb
                = (oat - econ_hl_temp) > temp_deadband   otherwise

yFault = past_changeover
     AND clg_vlv_cmd > cooling_enabled_threshold
     AND oa_dmpr_cmd > econ_damper_high_threshold
     sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-068 block graph](diagram.svg)

Both changeover branches are computed on every tick and `pastSel`
(`Logical.Switch`, `y = u2 ? u1 : u3`) picks one: `isDDB` selects the
differential branch (`oat - rat`, the default) or the fixed-changeover branch
(`oat - econ_hl_temp`). The two branches are not two implementations of one
idea — they are the two sources' two forms. APAR Rule 9 is written against a
fixed changeover temperature Tco (Table 1, p. 9), which is `hlPast` exactly;
PNNL-27338 §3.4 gates on a differential dry-bulb comparison, which is `ddbPast`
exactly. Subtracting first and thresholding the difference is what lets one
`temp_deadband` serve both, and it is the operand order — `oat` on `u1` in both
subtractions — that makes this the reverse of AHU-FC-051, where `oat` sits on
`u2`.

`clgOn` and `dmprHigh` are the APAR Mode-3 actuator signature: mechanical
cooling modulating with the outdoor air damper open. Mode determination stays
host-side, as it does for every card in this chapter and as the report itself
derives it (§4.1-4.2, pp. 6-7: from coil-valve and damper control signals
alone, with no mode sensor anywhere in the method), but
carrying the signature in-graph is what makes the finding self-evident from the
rule instead of dependent on how a particular host classified the mode. The
cooling conjunct is not decoration: with the coil shut there is no mechanical
cooling being paid for and nothing to recover, and the same open damper is then
either a purge cycle or a comfort problem rather than this fault.

All three comparisons are strict, so a damper commanded to exactly 75%, a
cooling valve at exactly 10%, or an outdoor-air excess of exactly 1.0 °C does
not trip the rule. `persist` then requires 30 continuous minutes, long enough
to ride out the damper stroke itself, the mixed-air loop settling after a
changeover, and the minutes either side of the changeover point when the
comparison is genuinely marginal.

## Possible Diagnoses

APAR states plainly (§4.2.2, p. 11) that no specific fault set has been
established for its rules — anything that satisfies a rule is detected, and
isolating the source is separate work — so this list is authored from the
mechanisms that raise an outdoor-air damper *command* past changeover:

1. Changeover setpoint too high, or a fixed high limit left at a factory
   default that does not fit the climate — the controller is doing exactly what
   it was told and the instruction is wrong
2. Economizer enable logic with no disable path: the sequence opens on a
   favorable comparison and never re-tests it, so the damper stays where the
   morning left it
3. OAT sensor reading low — sun-shielded, mounted in a soffit or over a warm
   roof, or drifted — so the controller still believes outdoor air is worth
   importing
4. A changeover device (dry-bulb or enthalpy switch) failed in its
   "economize" state, which on units that use one is a single point of failure
   with no other symptom
5. A mixed-air low-limit or freeze-protection loop holding the damper open past
   changeover, which happens when its setpoint was never re-tuned for cooling
   weather
6. An override left in place after service — a damper driven open by hand and
   never released; AHU-FC-061 finds the override flag itself

Note what is *not* on this list. A damper commanded to minimum but mechanically
stuck open never raises `oa_dmpr_cmd` and is invisible here; that is
AHU-FC-054's (stuck actuator) and AHU-FC-062's (mixing box) territory, and the
blind spot is recorded under Deviations.

## Energy Impact

EXCESS_CONSUMPTION, HIGH confidence, DIRECT_MEASUREMENT. The waste is the
sensible load the unit imports above its ventilation minimum,
`(oa_dmpr_cmd/100 − design_min_oa_fraction) × supply_airflow × ρ·cp ×
(oat − rat)`, and every term but the design fraction and the airflow is already
on this rule's own wires. Confidence is HIGH because the fault condition is
read directly from commands and temperatures with no baseline and no model, on
the same signals two independent primary sources chose for the same test. The
estimate is a floor rather than a total: it is sensible-only, and in a humid
climate the latent load of the excess outdoor air is the larger half of the
bill.

PNNL-27338 §3 puts 5-20% of cooling energy on correcting economizer faults as a
class, and that is the range carried in `savings_range` — but the class
includes AHU-FC-051's direction and the OA-fraction faults AHU-FC-055 finds, so
read it as the size of the family rather than of this member. Climate
sensitivity is cooling-dominant and sharply seasonal: the fault costs nothing
in the weather that created it and everything in the weather that follows,
which is exactly why it survives — it is born in a mild shoulder-season
afternoon and only bills in July.

## Emissions Impact

Scope 2, DIRECT_EMISSIONS, HIGH confidence; typical 1,000-6,000 kg CO₂e/yr,
scaled from AHU-FC-051's range for the same equipment and the same displaced
mechanical cooling. The whole impact is electric compressor or chiller work, so
it lands entirely in purchased electricity. The hours are the grid's worst:
this fault bills during hot afternoons, coincident with cooling peaks, when the
marginal generator is far dirtier than the annual average — use the marginal
operating emissions rate (MOER), not an average grid factor, or the estimate
will understate by the width of the summer peak.

## Deviations

- **This rule is a library extension, not a transcription.** The HVAC FDD
  Reference's chapter 9 specifies AHU-FC-001 through 065 and stops. The name,
  severity 3, phase 2 and `method: rule` are assigned here: severity 3 matches
  AHU-FC-051 and AHU-FC-064, its two nearest neighbours, because the fault is
  an energy finding with no equipment-protection or comfort urgency behind it;
  phase 2 because the rule presupposes a site that has already configured a
  changeover type and threshold for AHU-FC-051 and gains most of its value read
  next to that card. Everything else — the graph, the parameters, the diagnosis
  list, the energy claim — is authored here from APAR Rule 9, PNNL-27338 §3.4
  and AHU-FC-051's shape.
- **APAR Rule 9 is a Mode 3 rule, so `clgOn` tests cooling *active*, not
  closed.** Table 1 (p. 9) and Table 2 (p. 10) both place Rule 9 under
  "Mechanical Cooling with 100% Outdoor Air," whose signature per §4.1 (p. 7)
  is a modulating cooling coil valve with the outdoor air damper fully open.
  The intuitive reading — that "economizing" means Mode 2, both coils closed
  and dampers modulating — is the wrong mode for this rule and would invert the
  cooling conjunct. Rule 15 is the Mode 4 mirror of Rule 9 within APAR's own
  economizer pair, and it is AHU-FC-051 that carries that direction here.
- **Differential dry-bulb is the shipped default; APAR's fixed Tco is the other
  branch.** Rule 9 is literally `Toa > Tco + εt`, a fixed-changeover test, and
  that is `hlPast` with `econ_hl_temp` standing in for Tco. The default is the
  differential branch anyway, for two reasons: AHU-FC-051 ships DDB by default
  and a mirrored pair configured two different ways is worse than either, and
  PNNL-27338 §3.4 — the independent corroboration this card leans on — gates on
  the differential comparison rather than a fixed limit. A site running APAR
  literally sets `econ_type_is_ddb = false` and `econ_hl_temp` to its own Tco.
- **`temp_deadband` ships at 1.0 °C, not APAR's εt = 1.7 °C.** §4.2.3 (p. 11)
  commits εt = 1.7 °C (3 °F) flat across every temperature-comparison rule in
  the set, and calls the value heuristic in the same paragraph while naming
  measurement-uncertainty composition (`εt = εToa + εTma`) as the more rigorous
  approach it did not take. This card ships AHU-FC-051's 1.0 °C instead, and
  the reason is the pair, not the physics: with one deadband on both cards the
  two rules bracket a symmetric ±1.0 °C dead zone around the changeover point
  and provably cannot both assert, whereas 1.0 on one and 1.7 on the other
  gives the pair a lopsided window for no gain. The cost is real — 1.0 °C is
  inside the combined error of two commodity temperature sensors, which is
  precisely what APAR's 1.7 °C was sized to clear — so a site with untrimmed
  sensors should raise it, and must raise it on **both** cards together.
- **`econ_damper_high_threshold = 75%` is adopted, and it sits between the two
  sources.** APAR's Mode-3 signature is a fully open damper, and the rule set's
  own reading of "fully open" is `ud > 1 − εd` — above 98% with §4.2.3's
  εd = 0.02 — since Rules 21 and 24 use `εd < ud < 1 − εd` to mean a damper
  that is merely modulating. PNNL-27338 §3.4
  uses `avg_damper_signal > 30%` (1.5 × a 20% minimum-position setpoint) for
  the same finding. Shipping 98% would miss every damper that hangs at 80%,
  which is most of them, since the failures in the diagnosis list park the
  command wherever the last favorable comparison left it. Shipping 30% would
  make this rule a damper-position restatement of AHU-FC-055 (excess outdoor
  air while occupied), which already owns that ground through the OA-fraction
  ratio. 75% is above any plausible minimum-position setting — so the finding
  is unambiguously "still economizing" rather than "somewhat above minimum" —
  and it is the mirror of AHU-FC-051's 25% minimum-position line, which keeps
  the pair symmetric. A site that wants PNNL's sensitivity retunes to 30% and
  should expect the overlap with AHU-FC-055 that comes with it.
- **The rule reads the damper command, not its position, and that is a blind
  spot.** `oa_dmpr_cmd` is what AHU-FC-051 reads and what APAR Rule 9's `ud`
  is (§4.2.1, p. 8: control signals, not feedback), so the choice is
  consistent with both. The consequence is that a damper commanded to minimum
  and mechanically stuck open — a disconnected linkage at the open end, a
  failed spring return — produces the entire physical fault and none of the
  signature this rule tests. Nothing in the point dictionary fixes it:
  `actuator_cmd`/`actuator_pos` are the role points AHU-FC-054 binds for
  exactly this comparison, and duplicating that rule inside this one would
  trade a documented gap for a redundant graph. Run AHU-FC-054 on the OA damper
  alongside this rule; that pairing is the coverage, not either card alone.
- **The evaluability gate `|oat - rat| >= ∆Tmin` is a precondition, not an
  in-graph output.** APAR attaches such a gate to Rules 2 and 18 explicitly
  and to Rule 9 not at all, so there is no reference NO_EVAL vector to expose
  as a `y…Ok` output the way AHU-FC-064 does. The gate still matters — the
  differential branch subtracts two sensors that can sit within each other's
  error — and it is declared for host enforcement in `preconditions`, with
  APAR's own ∆Tmin = 5.6 °C named there. Same placement as AHU-FC-051, which
  is the point: the mirrored pair should be gated identically.
- **All three comparisons are strict** (`>`, `>`, `>`). Neither source
  specifies boundary behaviour, and the engine's `Reals` comparisons are strict
  in any case — there is no `GreaterEqual` to write. A damper sitting exactly
  on 75%, a valve exactly on 10%, and a temperature excess of exactly 1.0 °C
  all read healthy; the vectors pin all three, and both sides of each
  (`damper_exactly_at_threshold` against `damper_just_above_threshold`,
  `cooling_exactly_at_threshold` against `cooling_just_above_threshold`,
  `deadband_edge_then_past_changeover` for the temperature pair).
- **`alarm_delay = 1800 s` is adopted from AHU-FC-051; neither source specifies
  an alarm persistence.** APAR evaluates its rules per sample and leaves
  filtering to the implementation; PNNL-27338 averages a 15-60 minute data
  window and compares the average (§1.2), which is a different mechanism with a
  similar effect. Thirty continuous minutes matches the sibling and is what
  makes the pair's alarms comparable in latency.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a unit already past changeover with its damper open when the
  controller restarts waits out the full 30 minutes instead of alarming on the
  first tick.
- **`clusters: []`, and CLU-03 is deliberately not claimed.** CLU-03
  (Economizer Failure) has AHU-FC-051 as its trigger, and SCHEMA.md's cluster
  contract is that fixing the trigger clears the members within 24-48 h. That
  does not hold here: a damper stuck open is not cleared by repairing a damper
  stuck closed, and the two cannot even be true of one unit at once. This card
  shares CLU-03's playbook and none of its clearing semantics. Whether the
  cluster grows a second economizer syndrome, or CLU-03's contract is widened,
  is the cluster owner's call and not this card's to make.
- **`suppresses` and `suppressed_by` are both empty.** AHU-FC-055 is the
  nearest suppression candidate — a damper open past changeover also inflates
  the outdoor-air fraction AHU-FC-055 measures, so the two will often fire
  together on one unit — but both findings are true and separately actionable,
  and this rule is the more specific of the pair rather than a reason to
  disbelieve the other. Suppression edges must also be declared on both cards,
  which makes any edge here an index-level decision rather than a card-level
  one.
- **No published test vectors exist for this rule.** APAR publishes a rule
  table and a threshold list, not cases, and PNNL-27338 publishes an algorithm,
  so all eleven scenarios in `vectors.json` are authored: three ordinary cases
  (correct changeover, the fault, still-favorable), one for each conjunct
  blocking alone, both sides of all three thresholds, and three transients
  across the `TrueDelay` edge (clear-before-delay, cycle-resets-persistence,
  and a mid-run entry into the fault).
- Operating states and preconditions are declared in frontmatter for host
  enforcement rather than encoded in the block graph, per the library's design
  stance. APAR derives its five modes from coil-valve and damper control
  signals alone with no mode sensor (§4.1-4.2, pp. 6-7), which is the same
  host-side derivation this
  library's `operating_states` convention already assumes — a 2001 report and a
  2021 guideline reaching the same architecture independently.

## Notes

Read this card and AHU-FC-051 as one policy. They bind the same four points,
carry the same six parameters with the same names and defaults, and differ only
in the direction of the temperature comparison and the direction of the damper
comparison. Retuning one without the other is the mistake to guard against:
raise `temp_deadband` on this card alone and the dead zone between the two
rules goes lopsided, change `econ_type_is_ddb` on one and the pair starts
answering two different questions about the same unit.

With default parameters the vectors exercise only the DDB branch. `vectors/v1`
stages inputs, not parameters, so `isDDB` holds `true` for every scenario in
`vectors.json`: `hlConst`, `hlGap` and `hlPast` are loaded, evaluated and
structurally verified on each tick, but their result never reaches `yFault`
through `u3` of the switch. The fixed-changeover path — which is APAR Rule 9
in its literal form — is behaviorally exercised only by hosts that set
`econ_type_is_ddb = false` via `set_param`, and such a host should run its own
commissioning check rather than inherit confidence from these vectors. Same
limitation, and the same wording, as AHU-FC-051's note.

Do not deploy this rule on a unit without a return-air path. A 100%-outdoor-air
unit, a makeup-air unit, or an AHU running a mandated full-outdoor-air mode has
its damper open by design in any weather, and every conjunct here will hold
every hot afternoon. The precondition says so; this is the case where ignoring
it produces a confident, permanent, wrong alarm.

When the alarm is real, the fastest discriminator is the same one AHU-FC-064
uses, run in reverse. Command the OA damper to minimum and watch the mixed-air
temperature fall toward return temperature. If it moves, the sequence never
commanded minimum in the first place and the fix is at a desk — a changeover
setpoint, a missing disable branch, a stale override. If it does not move, the
command was not the problem and AHU-FC-054 on the OA damper is the rule that
will say so. Check the OAT sensor before either: a sensor reading 4 °C low is
cheaper to find than a roof visit, and it manufactures this fault out of
correctly working economizer logic.
