# cxf-library Schema

Normative contract for this library's layout and file formats. Version: **v1**
(all per-file `schema:` fields reference this document). Changes to any contract
in this file require bumping the affected `…/v1` identifier.

## Layout

```
cxf-library/
├── SCHEMA.md                    # this contract
├── points/<equip>.points.json   # canonical point dictionary per equipment family
├── faults/<equip>/<FAULT-ID>/   # one folder per fault rule
│   ├── card.md                  # fault card: YAML frontmatter (machine) + prose (human)
│   ├── rule.cxf.jsonld          # detection logic, hand-authored CXF JSON-LD
│   ├── vectors.json             # executable test scenarios
│   └── diagram.svg              # block-graph figure referenced from card.md
├── faults/<equip>/README.md     # chapter index and status table
├── playbooks/<slug>.md          # remediation playbooks (shared across faults)
├── clusters/clusters.json       # fault clusters (syndromes with shared root cause)
├── routines/                    # G36 routine enhancements (non-fault control programs)
├── tools/verify/                # Rust harness: loads each rule into the engine, runs vectors
└── _research/                   # source digests and orientation notes (non-normative)
```

Equipment family keys: `ahu`, `vav`, `rtu`, `hp`, `fcu`, `chw`, `hw`, `erv`,
`pmp`, `vfd`, `sys`. Fault IDs follow `{EQUIP}-FC-{NNN}` (001–049 G36-derived,
050–099 research-backed, 100–149 advanced statistical, 150–199 ML) per the HVAC
FDD Reference; folder name is the fault ID, uppercase.

## Design stance (why the pieces split this way)

- **A fault rule is a CDL composite block**: canonical point inputs → elementary
  comparison/logic/timing blocks → boolean fault output(s). Stored as CXF the
  open-control engine loads directly.
- **The rule computes the fault condition given valid data.** Data quality
  (NO_EVAL), operating-state gating, suppression, and energy accumulation are
  host/runtime concerns declared in the card frontmatter, never encoded in the
  block graph. The engine is deliberately status-blind; hosts enforce
  `preconditions` and `operating_states` before trusting `yFault`.
- **Semantics live in the point dictionary** (Brick + ASHRAE 223P), keyed by
  canonical point name. CXF documents stay semantics-free in v1; a generator may
  later inject annotations from the dictionary (the engine preserves unknown
  keys losslessly).

## `card.md` contract (`cxf-library/fault-card/v1`)

YAML frontmatter followed by Markdown prose. Frontmatter fields:

| Field | Type | Req | Meaning |
|---|---|---|---|
| `schema` | string | ✓ | `cxf-library/fault-card/v1` |
| `id` | string | ✓ | Fault ID, equals folder name |
| `name` | string | ✓ | Short human name |
| `equipment` | string | ✓ | Equipment family key |
| `status` | enum | ✓ | `draft` \| `verified` \| `adopted` \| `deprecated` |
| `phase` | int | ✓ | Rollout phase (1–4) |
| `method` | enum | ✓ | `rule` \| `statistical` \| `ml` \| `meta` |
| `severity` | int | ✓ | 1 Critical · 2 High · 3 Warning · 4 Info |
| `category` | enum | ✓ | `CRITICAL_WASTE` \| `EFFICIENCY_LOSS` \| `EXCESS_CONSUMPTION` \| `COMFORT_ENERGY` \| `PROTECTIVE` |
| `confidence` | enum | ✓ | `HIGH` \| `MEDIUM` \| `LOW` (evidence strength) |
| `estimation_method` | enum | ✓ | `DIRECT_MEASUREMENT` \| `BASELINE_COMPARISON` \| `PROXY_ESTIMATION` \| `QUALITATIVE_ONLY` |
| `source` | list | ✓ | Provenance refs (reference §, PNNL report, G36 §) |
| `g36` | string\|null | ✓ | G36 clause for 001-range rules, else null |
| `clusters` | list | | Cluster IDs this rule participates in |
| `suppresses` | list | | Rule IDs silenced while this fault is active |
| `suppressed_by` | list | | Rule IDs that silence this rule when active |
| `adjudicates` | map | | Sensor-health rules only: `{points: [...], verdict: invalid_while_active \| ambiguous}` — the canonical point(s) whose data validity this rule judges. Hosts derive the NO_EVAL fan-out from downstream cards' `points` lists (point-keyed, so it stays complete as rules are added — never a hand-written rule list). `invalid_while_active`: treat the point as invalid for all consumers while this fault asserts; `ambiguous`: a redundancy-pair rule that cannot name which member drifted. |
| `related` | list | | Co-occurring rules (informational) |
| `playbooks` | list | ✓ | Playbook slugs in `playbooks/` |
| `operating_states` | string | ✓ | Applicable states (`all` or list, prose ok) |
| `preconditions` | string | ✓ | Host-enforced evaluation gate, prose |
| `points` | list | ✓ | Canonical point names consumed (see below) |
| `outputs` | list | ✓ | `{name, description}` — boundary outputs |
| `params` | map | ✓ | name → `{default, unit, description, cxf}` |
| `energy_impact` | map | ✓ | `{affected_subsystem, savings_range, climate_sensitivity, runtime_estimation}` |
| `emissions` | map | ✓ | `{scope, method}` |
| `verified` | map | ✓ | `{engine_rev, content_id, date}` — all null until verified |

Conventions:
- **Every entry in `points` is a canonical name from
  `points/<equipment>.points.json`, and the CXF boundary input connector for it
  has exactly that local name.** This single convention makes point binding
  mechanical for every consumer.
- `params.*.cxf` is the parameter's CXF path relative to the root block
  (`<instance>.<param>`, e.g. `persist.delayTime`) so hosts can retune deployed
  rules via `set_param` without re-authoring. It may be a list of paths when
  one card parameter binds several block parameters (e.g. an evaluation
  window driving sampler periods and dwell times); hosts must set every
  listed path together.
- Signal units are those declared in the point dictionary (°C, Pa, %, bool).
  Hosts must feed those units; rules do no unit conversion in v1.
- `verified.engine_rev` is the open-control git rev the vectors last passed
  against; `verified.content_id` is the engine's exported `cxf:fnv1a128:…`
  diagnostic identity. Git history is the integrity record for the bytes.

Prose sections (in order): `## Description`, `## Detection Logic`,
`## Possible Diagnoses`, `## Energy Impact`, `## Emissions Impact`,
`## Deviations` (differences from the source reference and why — required, may
be "None"), `## Notes` (optional).

`## Detection Logic` contains the equation in a fenced block plus the block
graph as `![…](diagram.svg)` (a standalone SVG file — GitHub renders linked
SVG but strips inline SVG). Diagram conventions: boundary inputs as blue pills
on the left, fault outputs as red pills on the right, elementary blocks as
rounded rectangles labeled `instance` over `Class · key params`, signal flow
left to right.

**Card style (conciseness contract, adopted 2026-08-18; exemplar:
`faults/ahu/AHU-FC-050/card.md`).** Cards are clear, concise, and outlay the
conditions — they are specifications, not design journals. Targets:
Description ≤ ~10 lines; Detection Logic prose ≤ ~15 lines beyond the
equation and diagram (timing semantics, strictness, deployer must-knows
only — no block-by-block narration of the diagram); Energy/Emissions ≤ ~8
lines each; Notes ≤ ~8 lines or omitted. Deviations keeps EVERY engineering
decision but each as one bullet of 2–5 lines (decision + one-sentence why +
citation) — no alternatives-considered essays. Never narrate vector
scenarios in the card (vectors.json is that record), except a sentence
naming a deliberately-pinned engine behavior. Typical full card:
~140–220 lines (statistical cards may run ~250).

## `rule.cxf.jsonld` contract

Target dialect: the open-control engine's composite subset
(`open-control/docs/cxf-composite-subset.md`), matching its G36 fixture style:

- `@context`: `{"S231": "http://data.ashrae.org/S231P#", "base": "<fault ns>"}`
  where the fault namespace is `urn:cxf-library:<fault-id-lowercase>#`.
- Flat `@graph`, full IRIs written out. Root block:
  `<ns><fault_id_snake>` with `@type S231:Block`, `S231:label`,
  `S231:containsBlock`, `S231:hasInput` (boundary points), `S231:hasOutput`.
- Child instances: `<root>.<label>`; `@type` is
  `<ns>Buildings.Controls.OBC.CDL.<ClassPath>` (the engine resolves the class
  from the IRI fragment). Only registry-supported classes.
- Ports `<instance>.<portName>` typed `S231:RealInput`/`S231:BooleanInput`/…
  with `S231:isOfDataType`; connections via `S231:isConnectedTo` on the source
  (output) node.
- Parameters: `<instance>.<param>` nodes carrying `S231:value` typed literals;
  referenced from `S231:hasParameter`. Set only non-default values.
- Fault outputs are `BooleanOutput`s; primary output is named `yFault` (true
  while the fault condition persists). Additional outputs allowed (e.g.
  sub-condition flags) and must be listed in the card's `outputs`. When the
  reference semantics include an in-rule evaluability condition (a NO_EVAL
  test vector), expose it as an additional boolean output (`y…` name); the
  card documents that false means NO_EVAL — the host must consult it before
  interpreting `yFault`. Secondary outputs come in TWO kinds and the card's
  `outputs` prose must say which: **evaluability flags** (`y…Ok` — false
  means NO_EVAL) and **sub-condition/direction flags** (e.g. SYS-FC-055's
  `yBias`/`yNoise`, SYS-FC-057's direction flags — diagnostic detail only;
  false never means NO_EVAL). Hosts must not treat every non-`yFault`
  boolean as an evaluability gate.
- No semantic annotations in v1 (see design stance). No `oce.*` class aliases.

## `vectors.json` contract (`cxf-library/vectors/v1`)

```json
{
  "schema": "cxf-library/vectors/v1",
  "clock": { "step_s": 60, "horizon_s": 1800 },
  "scenarios": [
    {
      "name": "snake_case_name",
      "description": "optional",
      "inputs": {
        "htg_vlv_cmd": 20.0,
        "clg_vlv_cmd": [ { "t": 0, "value": 30.0 }, { "t": 600, "value": 0.0 } ]
      },
      "expect": [
        { "output": "yFault", "from_s": 0, "to_s": 840, "equals": false }
      ]
    }
  ]
}
```

- `inputs`: canonical point name → constant (number/bool) or a step list
  `[{t, value}…]` (piecewise-constant; each value staged before the first tick
  with model time ≥ its `t`).
- `expect`: windowed assertions on boundary outputs, inclusive of both ends,
  checked at every tick whose time falls in the window. Reals compare with
  optional `tolerance` (default 1e-9).
- Scenarios are independent: each runs on a freshly loaded engine.
- Windows must respect timing parameters (e.g. leave ≥ one step of margin
  around an `alarm_delay` edge rather than asserting the exact boundary tick).
- Scenarios must cover at minimum: the reference card's published test vectors,
  one threshold-edge case, and one transient case exercising delay/reset
  behavior where the rule has timing state.

## `points/<equip>.points.json` contract (`cxf-library/points/v1`)

```json
{
  "schema": "cxf-library/points/v1",
  "equipment": "ahu",
  "points": [
    {
      "name": "htg_vlv_cmd",
      "description": "Heating coil valve command (0 = closed, 100 = full open)",
      "kind": "real",
      "unit": "%",
      "qudt_unit": "PERCENT",
      "brick": null,
      "s223": null,
      "provisional": true
    }
  ]
}
```

- `name` is the library-wide canonical identifier (snake_case; suffixes: none =
  measured, `_sp` setpoint, `_cmd` command, `_status` status, `_fbk` feedback).
- **Role points** (documented exception, `points/sys.points.json` only): the
  cross-equipment sensor-health rules bind role names (`sensor_value`,
  `sensor_value_a/b`, `equip_active`) rather than canonical points, because
  the same graph deploys against many real points. Role entries carry
  `brick: null, s223: null`; the host's instance configuration records each
  binding, and that record is also what resolves the rule's `adjudicates`
  target and drives its NO_EVAL fan-out. The reference's own SYS-FC-054 card
  uses the same role form ("varies by application").
- `derived: true` marks host-computed points rather than physical ones — both
  aggregates (a max or fraction across zones) and physical transforms (e.g.
  saturation temperatures from pressure via a refrigerant P-T lookup). The
  entry's `notes` must state the derivation and its site-specific inputs
  (which refrigerant, which underlying points); rules consume derived points
  exactly like physical ones, and the derivation itself never appears in a
  rule graph.
- A top-level `namespaces` map records the exact ontology IRIs and the versions
  the terms were verified against.
- `brick`: verified Brick class local name (namespace
  `https://brickschema.org/schema/Brick#`).
- `s223`: object `{pattern, property_class, quantitykind, unit, medium,
  aspects, enumerationkind?}` using verified ASHRAE 223P terms
  (`enumerationkind` for enumerated properties). See
  `_research/223p-point-modeling.md` for the modeling pattern.
- Every term must be verified against the published ontology files — never
  from memory. `provisional: true` additionally marks entries with genuine
  ambiguity (class-choice judgment calls, unit conflicts, or patterns
  unattested in the standard's reference models); the per-point `notes` field
  records the specifics. All s223 entries also await confirmation against the
  formal ASHRAE 223 standard text once obtained.

## `clusters/clusters.json` (`cxf-library/clusters/v1`)

Array of `{id, name, trigger, members, playbook, prevalence, energy_impact}`.
`trigger` fires first; fixing it should clear `members` within 24–48 h.

## Playbooks

`playbooks/<slug>.md`: prose with a header block (Applies To, Fix Complexity,
Typical Time, Typical Cost, Energy Impact) and the four-step workflow:
Verify → Remote fix → On-site service → Confirm resolution. Faults reference
playbooks by slug; playbooks list the fault IDs they apply to.

## Verification

`tools/verify` loads each fault's `rule.cxf.jsonld` into the open-control
engine (path dependency, in-process), replays every `vectors.json` scenario
tick by tick, and checks the assertion windows. A fault may be marked
`status: verified` only when all scenarios pass; record the engine rev,
exported content ID, and date in `verified`. Re-verify (and re-record) after
any engine pin bump or rule edit.
