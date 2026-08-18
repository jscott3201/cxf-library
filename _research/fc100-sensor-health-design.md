# Sensor-health rules (FC-100 family) — design

Non-normative. This is a decision document for a family that does not exist yet:
no fault directories, no CXF, no vectors. It proposes where the rules live, how
their output is consumed, and which engine blocks they can be built from. Engine
claims are read from the pinned rev `e2ff2f8` (`ENGINE_PIN`) and cite the source
file; the arithmetic claim in §4.1 is derived from those equations and
cross-checked against the engine's own pinned test trace, not yet against a
library vector.

## Verdict

1. Three rule shapes: **flatline**, **spike/rate**, **redundancy-pair bias**.
2. They do not violate the library's design stance, because the stance's "data
   quality is host-side" is about *delivery* (freshness, BACnet status, gaps) and
   these rules are about *physical plausibility* — which the library already
   ships twice, as AHU-FC-062 and RTU-FC-052. §2.
3. Add one frontmatter key, `adjudicates`, naming the **point** a rule judges
   rather than the rules it silences. The host derives the suppression set from
   the `points` lists every card already carries. §2.3.
4. Author them once in a new `sys` chapter rather than once per equipment
   family. The cost is real and named: the boundary-input names stop being
   canonical point names. §3.
5. Build spike/rate on `Discrete.UnitDelay` and flatline on `Discrete.Sampler`.
   `Reals.Derivative` is the wrong block for both at BAS tick rates, for a
   reason that is arithmetic rather than aesthetic. §4.
6. No new physical points. Two previously undetected redundancy pairs are
   authorable today from the existing dictionaries; the fleet-comparison form
   needs one new host-derived point per quantity. §5.

## 1. Scope

Every rule in this library reads a sensor and believes it. The 05x-range cards
say so in their own Deviations sections — PMP-FC-050's diagnosis 5 is "the flow
meter is what failed", and the card admits three points cannot separate that from
the four real pump faults. AHU-FC-062 and RTU-FC-052 are the two places the
library already pushes back, and both are narrow: 062 tests one temperature
against an envelope built from two others, 052 tests a temperature difference
against the compressor and heater state. Neither notices a sensor that has
stopped moving, and neither notices one that jumps 30 °C between samples.

Three shapes cover the rest of the ground, and all three are cross-equipment:
the physics of a stuck transmitter does not depend on whether it is bolted to an
AHU or a heat pump.

**Flatline.** The reading has not moved while the system it measures was running.
A frozen transmitter, a controller holding a last-known-good value, or a point
that lost its BACnet subscription and is being re-served from cache all present
identically: a signal with zero variance under a load that should be producing
some. The test is `|u − baseline| < tolerance` held continuously for a window,
gated by an activity signal, where the tolerance is what separates "not moving"
from "not moving *much*" — a real temperature sensor in a stable duct has
quantization noise, and demanding bit-identical samples finds nothing.

**Spike / rate.** The reading moved further between two samples than the physical
process can move. Air temperature in a duct has thermal mass behind it; a 15 °C
step in 60 seconds is not a temperature, it is a wiring fault, a failing A/D
channel, or a units change nobody announced. The test is a bound on the
sample-to-sample difference. It is the cheapest sensor rule to write and the one
most sensitive to the tick rate, for reasons §4 works through.

**Redundancy-pair bias.** Two measurements of the same physical quantity, or of
two quantities related by a known constraint, have diverged beyond the band that
combined sensor accuracy explains. Mixed air is the canonical case: it is a blend
of outdoor and return air, so `mat` must lie between `oat` and `rat`, and at the
extremes of the damper travel it must nearly equal one of them. This shape is the
only one of the three that can catch **drift** — the slow, monotone kind that
flatline and spike are both structurally blind to, because it is neither still
nor fast.

### Public grounding

Yang et al. (2008) is the closest published precedent for what this family is:
sequential rule-based detection of temperature-sensor faults in AHUs, validated
against real units rather than simulation. Its lesson for the ID-scheme decision
in §3 is that the *sequence* is what buys isolation — a single pairwise
comparison tells you one of two sensors is wrong, and only a chain of overlapping
comparisons tells you which. That is exactly the ambiguity §2.3 pushes into the
`adjudicates` field rather than pretending away.

Liao et al. (2021) put threshold rules and a CNN in one framework and split the
work between them: the rule layer handles sensor faults, the learned layer
handles the compound ones. That is the same layering this document proposes, with
the CNN half absent — the library's 100-range is threshold and statistical, and
the ML band is 150–199 per the reference's numbering. The paper is useful here as
published evidence that a cheap deterministic sensor layer under a heavier
diagnostic layer works in the field, at least on the AHUs they tested.

Dey & Dong (2016) is the motivation stated negatively. They layer a Bayesian
belief network over APAR because a satisfied APAR rule does not identify a root
cause: the same rule fires for coil fouling, a stuck damper, a leaking valve, and
a **temperature-sensor bias**. Their fix is probabilistic disambiguation after
the fact. This library's fix is to detect the sensor case directly and take it
out of the candidate set before the equipment rules are read at all — which only
works if the sensor verdict is available to the host as an input to how it reads
everything else. Hence §2.

## 2. The stance problem

The library's stance is one sentence in `README.md`: *the graph computes
fault-given-valid-data, and only that*. A sensor-health rule appears to break it
immediately, because its `yFault` **is** a claim about data validity. That
reading is worth taking seriously before answering it, because the answer decides
the frontmatter contract.

### 2.1 Two things are called "data quality"

**Delivery quality.** Did a sample arrive, when, and what did the field bus say
about it. The engine is deliberately blind here: `docs/host-responsibilities.md`
states that a sample is converted from its value regardless of `PointStatus`, and
that `Fault`, `Stale`, `Uninitialized` and `Override` stage identically to `Ok`.
The host owns the status reaction policy. The reference's ch.4 rules — ≤2× poll
interval interpolate, 10×–60 min pause evaluation and hold active faults, >60 min
NO_EVAL and reset rolling state — are all delivery quality. **None of this
changes.**

**Physical plausibility.** The sample arrived on time, with clean status, and is
wrong. This is a property of the signal, computable from the signal, and it is a
fault of a piece of equipment — a sensor is equipment. The library already ships
two rules of exactly this kind and nobody argued they broke the stance:
AHU-FC-062 (`mat` outside the `oat`/`rat` envelope, severity 3, playbook
`sensor-drift`, suppresses fourteen rules) and RTU-FC-052 (PNNL's AFDD0, the
sensor-consistency prerequisite for its chapter, suppresses two).

The FC-100 family is category two, generalized. It is not a new kind of object in
the library; it is the third, fourth and fifth members of a set that already has
two.

### 2.2 Why the stance survives, stated as three claims

**The graph still emits booleans computed from its declared inputs.** No status,
no staleness, no tri-state, no self-reference. A flatline rule on `sat` reads
`sat` and an activity signal and emits a boolean. That is the same object every
other card in this library ships.

**The NO_EVAL decision stays with the host.** The graph says "this reading has
not moved in four hours while the fan ran". It does not say "stop evaluating
AHU-FC-050". The card *declares* the mapping from that verdict to the downstream
consequence, and the host enforces it — which is precisely what `preconditions`,
`operating_states` and `suppresses` already are: declared for host enforcement,
never encoded in the block graph.

**The sensor rule assumes its own inputs are mechanically delivered.** This is
the load-bearing claim and the one that keeps the layering acyclic. A flatline
rule fed a stale value that the host held over from twenty minutes ago will
report flatline, and it will be *right about the number it was given and wrong
about the sensor*. The rule cannot tell those apart and does not try. Staleness,
comms loss and gap handling must be resolved by the host **before** the sensor
rule runs. The sensor rules do not subsume host data quality; they sit on top of
it and depend on it.

The layering, in order:

```
host: delivery quality (freshness, PointStatus, gaps)   →  NO_EVAL for everything
  graph: sensor health (FC-100)                          →  NO_EVAL for the point
    graph: equipment faults (FC-0xx)                     →  the finding
```

### 2.3 The frontmatter contract: `adjudicates`

A sensor rule's `yFault = true` is not a NO_EVAL for itself. It is a finding with
its own severity, its own playbook (`sensor-drift` exists), and its own work
order. It becomes NO_EVAL *for other rules*, and the schema has no way to say so.

`suppresses` is the closest existing field and it conflates two different host
actions:

- *Redundant*: PMP-FC-051 suppresses PMP-FC-050 because the deadhead is the
  specific diagnosis and no-flow is the general one. The suppressed rule's
  verdict is still **true**; it is just noise.
- *Invalid*: AHU-FC-062 suppresses fourteen rules because their inputs are
  garbage. Their verdicts are not true-but-noisy, they are meaningless, and per
  the reference's own gap handling the host should also **reset their rolling
  state** — a `MovingAverage` that integrated four hours of a flatlined sensor is
  carrying that poison forward after the alarm clears.

Proposed addition to the `cxf-library/fault-card/v1` frontmatter:

```yaml
adjudicates:
  points: [sat]                 # canonical point name(s) this rule judges
  verdict: invalid_while_active # yFault true ⇒ every rule on this equipment
                                # instance consuming these points is NO_EVAL
```

For a pair rule that cannot attribute the fault to one member:

```yaml
adjudicates:
  points: [mat, oat, rat]
  verdict: ambiguous            # one of these is wrong; the rule cannot say which,
                                # so all of them go NO_EVAL
```

Key the field to the **point**, not to the rule list, for four reasons.

**The fan-out is derivable.** Every card already lists `points`. The host computes
the affected set as `{rules bound to this equipment instance whose points
intersect adjudicates.points}`. No card enumerates the others, and no card goes
stale when a rule is added. AHU-FC-062's hand-written fourteen-entry `suppresses`
list is the counter-example: it is correct today and will be silently incomplete
the first time someone authors an AHU rule that reads `mat`.

**It is lintable.** `tools/verify/src/lint.rs` already checks that every name in
`points` exists in `points/<equip>.points.json`. `adjudicates.points ⊆ points`
plus the same dictionary check is four lines in the same function. A rule-name
list can only be checked for existence, never for completeness.

**It carries the ambiguity honestly.** A bias rule between two sensors genuinely
cannot say which one drifted, and `verdict: ambiguous` is the schema saying so
out loud rather than the card picking a victim in prose. Yang et al. (2008) is
the upgrade path here: a *sequence* of overlapping comparisons can isolate the
member, and a future rule that does that would carry `verdict:
invalid_while_active` over one point instead.

**It does not touch the CXF.** `adjudicates` is card metadata, like `suppresses`
and `preconditions`. The block graph is unchanged and the engine never sees it.

Two constraints fall out and should be normative if the field is adopted:

- A card carrying `adjudicates` **MUST NOT** appear in any other card's
  `suppresses`. Otherwise an equipment fault can silence the sensor rule that
  invalidates it, which is a cycle with a wrong answer at both ends.
- Where the sensor rule needs a second signal to be evaluable (the activity
  gate), that goes out as a boolean boundary output named `y…Ok`, exactly like
  HP-FC-050's `yPowerOk` and PMP-FC-050's `yRunOk`. The rule's own evaluability
  and the point's validity are different outputs and must not be merged.

## 3. ID scheme

### Option A — per-family FC-100s

`AHU-FC-100/101/102`, `VAV-FC-101/102/103` (100 is taken), `RTU-FC-101/102/103`
(100 is taken by condenser airflow restriction, deferred), and so on across ten
families.

For: the linter works unchanged, because every boundary input is a canonical name
from that family's dictionary — the library's single strongest convention,
the one that makes point binding mechanical. Chapter READMEs and the book
generator need no structural change. The 100-range is already reserved for phase-3
work in every family README.

Against: the flatline graph for `sat` is byte-identical to the one for
`zone_temp`, `chwst`, `oat` and `pump_dp`. Thirty near-duplicate fault
directories, each with its own vectors, its own diagram, and its own
`verified.content_id` to re-record on every engine pin bump. The numbering is not
even uniform — RTU-FC-100 and VAV-FC-100 are already allocated to unrelated
faults. And the reference's own band definition for 100–149 is "advanced
statistical (change-point, regression)", which a threshold test on a sample
difference is not; the cards would carry `method: rule` inside a statistical band.

### Option B — one shared `sys` family

`sys` is already a legal equipment key in `SCHEMA.md` and is the only one with no
chapter. The reference's ch.16 already puts sensor work there: SYS-FC-054 "sensor
drift cross-validation" and SYS-FC-055 "virtual sensor drift", both already listed
as members of CLU-09 (Sensor Integrity Failure) in `clusters/clusters.json`, both
already listed in `playbooks/sensor-drift.md`.

For: one graph per shape, one set of vectors, one content ID, one place to fix a
bug. The rules genuinely are equipment-agnostic, and the precedent for "one
graph, many bindings" is already set and already verified — `faults/rtu/README.md`
records that RTU-FC-054/055 are gated by the AHU-FC-062 envelope check
"instantiated against the RTU's own mat/oat/rat points (the 062 graph is
equipment-agnostic)". `adjudicates` resolves against the bound instance at deployment, so the
suppression fan-out is per-instance regardless of where the card lives.

Against, and this is a real cost: the boundary inputs cannot be canonical point
names, because the point is different on every binding. `points/sys.points.json`
would carry role names — `sensor_value`, `sensor_value_a`, `sensor_value_b`,
`equip_active` — and the host's instance config would record which real point each
one is bound to. **That breaks the convention that makes binding mechanical**, and
it is not a small break: the rest of this library can be bound by name matching
alone, and these three rules cannot.

### Recommendation

**Option B, with the binding cost paid explicitly rather than hidden.** Author
`SYS-FC-100` (flatline), `SYS-FC-101` (spike/rate) and `SYS-FC-102` (pair bias)
in a new `faults/sys/` chapter with a new `points/sys.points.json`.

Two things make the cost payable. First, `adjudicates.points` is where the real
point name lands: the host must record "this instance's `sensor_value` is
`ahu-3/sat`" anyway to compute the suppression fan-out, so the binding is already
a required artifact of the design, not an extra one. Second, the alternative is
worse in the same place — thirty copies of one graph is thirty chances for the
copies to drift apart, and the library has no cross-card diff check that would
catch it.

Implications, all in files owned elsewhere:

- **`SCHEMA.md`**: add the `adjudicates` row to the frontmatter table; add
  `sensor_value`-style role points to the `points/v1` prose as a documented
  exception to the canonical-name convention, or the schema and the family
  contradict each other on day one.
- **`points/sys.points.json`**: new file. Role points cannot carry meaningful
  Brick or 223P tags (the semantics belong to whatever they are bound to), so
  every entry is `brick: null, s223: null` with `notes` naming the binding
  contract. This is the first dictionary entry in the library that is
  deliberately untagged and it needs a sentence in `_research/223p-point-modeling.md`
  saying why.
- **`faults/sys/README.md`**: new chapter index. `tools/book/generate.py`
  discovers families by walking `faults/*` with no hardcoded list, so the book
  picks it up with no code change.
- **`tools/verify/src/lint.rs`**: `adjudicates.points ⊆ points`, plus the
  dictionary membership check it already runs for `points`.
- **Every family README with a reserved FC-100 row**: `vav` (planned) and `rtu`
  (deferred) both carry one. Each needs a line pointing at the sys family so the
  slot is not filled with a duplicate.
- **`clusters/clusters.json`**: CLU-09's trigger is AHU-FC-062. If SYS-FC-100..102
  land, the trigger is arguably one of them and 062 becomes a member. Single-writer
  file; flag, do not edit.

**The numbering collision is unresolved and belongs to Justin.** SYS-FC-102 (pair
bias) and the reference's own SYS-FC-054 (sensor drift cross-validation) are the
same rule. Either 102 takes the 054 slot — which is the reference's number, keeps
CLU-09 and the playbook's "Applies to" line correct as written, and abandons the
"FC-100 family" framing for that one card — or 054 is marked superseded when it is
transcribed. Carried into §6.

## 4. Engine mechanics

> **Correction (2026-08-18, from SYS-FC-101's verification):** the UnitDelay
> `y_start` seed can survive up to **two** sample periods, not one. The init
> branch stages the input only at a sample instant, so a rule loaded between
> instants stages nothing, the next instant promotes seed→seed, and the first
> real sample appears up to `2 × samplePeriod` after load. The one-period
> claim below holds only for grid-aligned loads; SYS-FC-101's startup inhibit
> and vectors are built to the two-period bound.

All three blocks named in the task exist at the pin. Verified in
`crates/oce-blocks/src/registry/`:

| Class | Registry file | Params at the pin |
|---|---|---|
| `CDL.Reals.Derivative` | `reals_filters.rs:26` | `y_start` only (default 0.0) |
| `CDL.Discrete.UnitDelay` | `discrete.rs:69` | `samplePeriod` (required, ≥ 1e-3), `y_start` (default 0.0) |
| `CDL.Discrete.Sampler` | `discrete.rs:53` | `samplePeriod` (required, ≥ 1e-3) |

### 4.1 `Reals.Derivative` at the pin, and why it is the wrong block here

Read `crates/oce-blocks/src/reals_filters.rs:53-171`. Three facts decide the
design.

**It has three input pins, not one.** Upstream declares the gain `k` and the time
constant `T` as `RealInput` connectors in declaration order `k, T, u` (indices
0/1/2), and all three feed through. Only `y_start` is a parameter. So a rule using
this block needs two `Reals.Sources.Constant` instances wired into `k` and `T`,
and the card's tunables are `kSrc.k` and `tSrc.k` — parameters of the constants,
not of the derivative. Three nodes and two connections where the block diagram
suggests one.

**It is a filtered derivative, and the filter's discretization biases the
reading by a factor of the tick rate.** The equations are
`y = (k/T_nonZero)·(u − x)` with `x` advanced by the implicit-Euler helper
`x ← (x + α·u)/(1 + α)`, `α = dt/T`, `T_nonZero = max(T, 1e-13)`. Working the
recurrence for a constant ramp of slope `s` gives a steady-state output of

```
y = k · s · (1 + dt/T)
```

which is the true derivative only in the limit `dt/T → 0`. At a 300 s BAS tick
with `T = 300 s`, the block reports **twice** the actual slope. Holding the error
under 5% needs `T ≥ 20·dt` = 6000 s at that tick rate — and the filter's own
settling time is on the order of `T`, so buying accuracy costs a hundred minutes
of lag, which defeats the point of a spike detector. A threshold tuned on a
300 s trend and deployed on a 60 s trend moves by 25% with no edit to the card.

(Derivation cross-checked against the engine's own pinned trace: in
`reals_filters_derivative_tests.rs::derivative_gain_and_time_constant_inputs_act_live`,
`k=1, T=0.5, u: 0→1` at `t=0.1` pins `y=2.0`, and the next tick with `k=2.5` pins
`y=4.1666…`; both fall out of the recurrence above. The ramp result itself is
derived and simulated, not yet pinned by a library vector — pin it before any
card depends on it.)

**Its step response ignores dt entirely.** A step `Δu` arriving on one tick emits
`y ≈ k·Δu/T` regardless of how much time that tick covered. The same 5 °C jump
reads identically whether it happened over 60 s or 600 s. For a *slew* bound —
which is a quantity per unit time — that is the wrong answer. For a
*step-magnitude* bound it is the right answer computed the expensive way, and
subtracting two samples gets there with no filter and no bias.

**Warmup.** First tick: `tick_dt` returns 0 when the previous-time word is unset,
and the state seeds to `x = u − T·y_start/k`, so `y = y_start` exactly (pinned:
`y_start = 0.25` emits `0x3fd0000000000000`). Default `y_start = 0` means the
first tick reads "no change", which is the harmless direction for a rate test.

One legitimate use survives: `k = 60` makes the output °C/min instead of °C/s,
which matters because a 0.5 °C/min bound written in engine units is 0.008333, and
a number like that in a card's `params` table is hostile to the technician who has
to retune it. If a card ever does use `Derivative`, it should carry `k = 60` for
that reason alone.

### 4.2 `Discrete.UnitDelay` — the recommended spike/rate primitive

Read `crates/oce-blocks/src/discrete.rs:51-173`.

`y = pre(u_internal)` on the `samplePeriod` clock, with `feeds_through == false`
— it is the discrete loop cut. Two state words track the upstream pair: the held
output and the staged sample. `|u − UnitDelay(u)| > slew_bound` is then an exact
sample-to-sample difference in the signal's own units, with no filter, no
discretization bias, and no dependence on the tick rate for its *value*.

Three mechanics that must be in the card:

**The sample grid is anchored to absolute model time, not to controller start.**
`initial_sample_time` computes `t0 = round6(floor(t_start/period)·period)`. A rule
loaded at `t = 137 s` with a 60 s period gets `t0 = 120`, not 137.

**The effective lookback is a range, not a constant.** At any tick `t ∈ [t_k,
t_{k+1})` the emitted value is the sample taken at `t_{k−1}`, because
`update_state` promotes staged→held at the instant and stages the current input.
So the age of the delayed sample runs over `[P, 2P)`. If `samplePeriod` equals the
host tick interval, this collapses to exactly one tick and the rule means what it
looks like it means. If it does not, the rule detects "any excursion exceeding the
bound within one to two sample periods", which is a defensible semantic but a
different one, and the threshold is then a per-window magnitude rather than a
rate. Either way the card must state the tick interval it was tuned at, and
`samplePeriod` and the bound must be set together — the precedent for one card
parameter binding a set that must move together is AHU-FC-056's `window` and
HP-FC-050's slope/intercept pair.

**The warmup artifact is the mirror image of `Derivative`'s and it is dangerous.**
`y` holds `y_start` until the *second* sample instant. With the default
`y_start = 0`, the first difference on a 22 °C duct temperature is
`|22 − 0| = 22 °C` — a fabricated spike, on tick one, on every restart. Two
mitigations, and the first is the right one:

1. `Logical.TrueDelay` with `delayOnInit = true` (the library's standing choice on
   every `persist` instance) and `alarm_delay ≥ 2·samplePeriod`. The artifact
   cannot survive the timer. **Pin it with a vector** that shows the raw
   difference spiking and `yFault` staying false, exactly as RTU-FC-050 and
   FCU-FC-001 pin their `Logical.Edge` startup pulses.
2. Setting `y_start` to a plausible mid-scale reading. This buries the artifact
   instead of documenting it and makes the parameter a per-point site value for
   no diagnostic gain. Not recommended.

### 4.3 `Discrete.Sampler` — the recommended flatline primitive

Read the `Sampler` block in `crates/oce-blocks/src/discrete_sampled.rs`. Its
`!initialized` branch returns the live input, so the block **emits the current
reading on its first tick** — no startup artifact, which is why AHU-FC-057 chose it and said so in its
Deviations.

Flatline is then AHU-FC-057's pattern pointed at a sensor instead of a setpoint:

```
flat = |u − Sampler(u, window)| < flatline_tolerance,  held continuously for window
yFault = flat AND equip_active,  sustained for alarm_delay
```

This is exact at any tick rate. The alternative, `Reals.MovingAverage`, is not:
its history is a fixed 64-checkpoint ring (`reals_filters.rs:400`) that warns once
and drops the oldest checkpoint when a window needs more, which sets a minimum
tick interval of `window/64` — AHU-FC-056 computes 112.5 s for its 7200 s window
and AHU-FC-057 rejected the block outright for a weekly window. A flatline window
of four hours would need ticks no faster than 225 s. Do not use `MovingAverage`
here.

The Sampler has its own honest limit and it must go in Deviations: the baseline
**re-arms every period**, so the test is "did the signal stay within tolerance of
where it was at the start of this window". A slow monotone drift that never
exceeds the tolerance within one window is invisible to it — permanently, not
just for one window. Flatline cannot detect drift. That is the redundancy-pair
rule's job and the reason all three shapes are needed rather than two.

### 4.4 Vector-pinning strategy, by shape

`vectors.json` runs each scenario on a freshly loaded engine with a fixed
`clock.step_s`, and windows must leave ≥ one step of margin around timing edges
(`SCHEMA.md`). Per shape:

**Flatline** — `step_s` must divide the sampler period, or the first sample
instant lands where no tick does. Pin: (a) a genuinely frozen signal asserting at
exactly `window + alarm_delay`; (b) a signal wobbling just *under* the tolerance
still asserting, which is the case that proves the tolerance is not decorative;
(c) a wobble just *over* the tolerance never asserting; (d) the re-arm miss from
§4.3 — a slow ramp that drifts several degrees across a day and never asserts,
pinned as a documented blind spot rather than left for a site to discover; (e) the
activity gate false, verdict NO_EVAL not healthy.

**Spike/rate** — pin the startup artifact from §4.2 explicitly (raw difference
large, `yFault` false). Pin both sides of the bound at a single tick, and the
boundary itself: comparisons are strict `Reals.GreaterThreshold`, so a difference
landing exactly on the bound reads healthy, and the card says so — the standing
convention in this library since PMP-FC-050. Pin the multi-tick miss: a ramp that
stays under the bound on every single tick but covers three times the bound over
five ticks, which the rule does not and cannot catch. Pin the recovery edge.

**Pair bias** — `|a − b|` throws away the sign, so pin the symmetric pair: `a`
high by 4 °C and `b` high by 4 °C must both assert, and the card must state that
the two are indistinguishable in the output. That is the vector-level expression
of `verdict: ambiguous`. Pin three sides of the band as AHU-FC-062 does
(inside, exactly on, outside). If the rule gates on a damper position or a mode,
pin the gate transition — AHU-FC-062's precondition already excludes the two
minutes after an economizer changeover, and a bias rule reading `mat` needs the
same exclusion for the same reason.

## 5. Points impact

**Flatline and spike need no new physical points.** Each consumes one existing
real point plus an activity gate, and every family already has a gate candidate:
`sf_status` (ahu, rtu), `comp_status` (rtu, hp), `pump_status` (pmp),
`boiler_status` / `hw_pump_status` (hw), `erv_enabled` (erv), `chiller_kw > 0`
(chw), `vfd_speed > 0` (vfd), `operating_state` (fcu). **`vav` has none** — the
box has no fan, and the honest gate is `zone_airflow > 0` or the parent AHU's
`sf_status`, which is a cross-equipment binding no dictionary expresses. This is
a second, independent argument for the `sys` family's generic `equip_active`
boolean with a per-family host mapping recorded at binding.

### Redundancy pairs actually present in the dictionaries

Surveyed all ten `points/*.points.json` files. Three usable, four that look usable
and are not.

**Usable today, no new points:**

1. **`mat` against `oat` and `rat` (ahu, rtu).** The strongest pair in the
   library and already half-built: AHU-FC-062 tests the envelope
   (`min ≤ mat ≤ max` within `sensor_tolerance`). The *bias* form needs the
   mixing fraction, and `oa_dmpr_cmd` is not it — the gap between commanded
   damper position and actual OA fraction is what AHU-FC-053/054 exist to
   detect, so using it here would import their fault as this rule's noise. The
   form that survives is the pair at the **extremes**: with the damper commanded
   shut, `mat` must track `rat` within a band; at full economizer it must track
   `oat`. Narrow window, no model, and it catches the drift the envelope test
   misses because the envelope is wide whenever `oat` and `rat` are far apart.
2. **`erv_oa_entering_temp` against `oat` (erv).** Two sensors in the same
   outdoor air stream, both already in one dictionary, no host derivation, no
   mode gating beyond `erv_enabled`. The cleanest pair rule available and the
   one to author first as the shape's proof.
3. **`sat` against `mat` under a known coil state (ahu, rtu, fcu).** This is
   RTU-FC-052's test and it is already written. Listed here so the FC-100 family
   does not re-detect it; if the sys family covers this shape, RTU-FC-052 should
   be cited as the equipment-specific instance, not duplicated.

**Needs one new host-derived point per quantity:** the fleet-comparison form —
one instance's reading against the site's other instances. `oat` appears in six
dictionaries (ahu, rtu, hp, hw, erv, vav) and every one of them nominally measures
the same air. The obstacle is naming, not physics: the rule shape is
`|oat_a − oat_b| > band`, which needs two boundary inputs of the same canonical
name, and the library's convention forbids it. The fix that keeps the convention
is a host-derived aggregate — `oat_reference`, the site median — making the rule
single-instance with one ordinary input. Precedent for host-derived aggregates is
established: `zone_dmpr_pos_max`, `zone_reheat_fraction` and
`satisfied_zone_fraction` all carry `derived: true` today. (`chw_valve_max` is
described as host-derived in its `notes` but is missing the flag — a separate
dictionary bug, not this family's to fix.) The fleet form is also exactly
VAV-FC-100's shape, which is why it is a question in §6 rather than a decision
here.

**Look like pairs, are not:**

- **Command/feedback pairs** — `vfd_speed_cmd`/`vfd_speed`, `actuator_cmd`/
  `actuator_pos`, `pump_cmd`/`pump_status`, `zone_airflow`/`zone_airflow_sp`,
  `dsp`/`dsp_sp`. These are actuator health, not sensor health, the divergence is
  at least as likely to be the actuator as the sensor, and VFD-FC-050,
  AHU-FC-054 and VAV-FC-053 already own them. Explicitly out of scope.
- **`chwst`/`chwrt`** — they differ by the load, by design. Not redundant.
- **`chwst`/`chwst_sp`** — a control-performance test, not a redundancy test.
- **`thermal_power`/`elec_power` (hp), `fuel_power`/`thermal_power` (hw)** —
  ratio plausibility, owned by HP-FC-050 and HW-FC-051.

Net: flatline and spike are zero-points changes. Pair bias is zero-points for the
`mat` and ERV forms and one new `derived: true` entry per quantity for the fleet
form.

## 6. Open questions for Justin

**1. Severity and category conventions for sensor faults.** Both existing sensor
gates are `severity: 3`, `confidence: LOW`, `estimation_method: QUALITATIVE_ONLY`,
with `energy_impact.savings_range` hedged as "sensor-dependent". Severity 3 means
"1–2 wk, FP < 5%" on the reference's scale, but a flatlined `sat` blinds the AHU's
entire diagnostic set for those two weeks — the impact is the fan-out, not the
sensor. Three ways to go: keep 3 for consistency with 062/052; raise the
adjudicating rules to 2 on fan-out grounds; or keep 3 and switch `category` from
`COMFORT_ENERGY` to `PROTECTIVE`, since the value delivered is avoided false
alarms and preserved diagnostic coverage rather than energy. The third is the most
honest and the least precedented. Note the reference's index carries no severity
column, so this is the library's call either way.

**2. Suppression fan-out mechanics.** Assuming `adjudicates` is adopted:

- Does AHU-FC-062's existing fourteen-entry `suppresses` list get rewritten as
  `adjudicates: {points: [mat, oat, rat], verdict: ambiguous}`? It is a
  single-writer card and the rewrite changes verified behaviour documentation
  without changing a byte of CXF.
- What does the host do when the computed closure covers **every** rule on the
  equipment — which a bad `oat` does, since `oat` feeds the economizer rules, the
  lockout rules, and both pair rules? Report the sensor finding and go silent, or
  keep reporting with reduced confidence? The reference has a precedent for the
  second: BACnet in-alarm/overridden maps to "uncertain — reduced confidence"
  rather than to skip.
- Should `adjudicates` cards be un-suppressible by construction (§2.3 proposes
  yes, as a MUST), and does the linter enforce it?
- Does an adjudicated NO_EVAL also **reset rolling state** in the suppressed
  rules? The reference's >60 min gap rule says reset; a `MovingAverage` that ate
  four hours of a flatlined sensor is poisoned well past the alarm clearing, and
  nothing in the schema says whose job that is.

**3. Does VAV-FC-100 join this family or stay separate?** It is currently reserved
in `faults/vav/README.md` as "Zone temperature sensor drift", phase 3,
`statistical`, with a neighbour-comparison method the README already notes is
"expressible with a host-derived median point". That is the fleet-comparison shape
from §5, not the pair shape — one reading against a population, which is a
different statistic with different failure modes (it goes wrong when the
population is genuinely heterogeneous, e.g. a perimeter zone in the sun). Options:
(a) VAV-FC-100 stays where it is and the sys family covers only self-consistency
and pairs, leaving fleet comparison as a per-family rule; (b) VAV-FC-100 becomes
the canonical fleet-comparison card and the sys family cites it; (c) a fourth sys
shape, `SYS-FC-103` fleet-median bias, and VAV-FC-100 is marked as its
instantiation for zones. (a) is the smallest change and (c) is the one that
matches how the other three shapes are being argued for.

**4. The SYS-FC-054 collision (from §3).** The reference's SYS-FC-054 *is* the
pair-bias rule, it is already a CLU-09 member, and `playbooks/sensor-drift.md`
already lists it in "Applies to" alongside a reference to "paired installations
(SYS-FC-054 cross-validation)" in its step 3. Either the pair rule takes the 054
number — coherent with everything already written, at the cost of the family not
being three consecutive IDs — or it is SYS-FC-102 and the 054 slot is marked
superseded before anyone transcribes it. This needs deciding before the first card
is authored, because the playbook and the cluster file both already point at 054.

## Sources

Public, cited by DOI. Nothing in this document is transcribed from licensed
material.

- Yang, H., Cho, S., Tae, C.-S., Zaheeruddin, M. (2008). Sequential rule based
  algorithms for temperature sensor fault detection in air handling units.
  *Energy Conversion and Management* 49(8), 2291–2306.
  [10.1016/j.enconman.2008.01.029](https://doi.org/10.1016/j.enconman.2008.01.029)
- Liao, H., Cai, W., Cheng, F., Dubey, S., Rajesh, P. B. (2021). An Online
  Data-Driven Fault Diagnosis Method for Air Handling Units by Rule and
  Convolutional Neural Networks. *Sensors* 21(13), 4358.
  [10.3390/s21134358](https://doi.org/10.3390/s21134358)
- Dey, D., Dong, B. (2016). A probabilistic approach to diagnose faults of air
  handling units in buildings. *Energy and Buildings* 130, 177–187.
  [10.1016/j.enbuild.2016.08.017](https://doi.org/10.1016/j.enbuild.2016.08.017)

Engine sources are the pinned rev `e2ff2f8` of the open-control engine:
`crates/oce-blocks/src/reals_filters.rs`, `discrete.rs`, `discrete_sampled.rs`,
`registry/reals_filters.rs`, `registry/discrete.rs`,
`reals_filters_derivative_tests.rs`, and `docs/host-responsibilities.md`.
