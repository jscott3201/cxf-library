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
├── routines/                    # executable control-routine catalog
│   ├── registry.json            # executable routine inventory
│   └── g36/                     # G36 pins, coverage, and fixed-variant bundles
├── tools/verify/                # Rust harness: loads each rule into the engine, runs vectors
```

Equipment family keys: `ahu`, `vav`, `fpb`, `rtu`, `hp`, `fcu`, `chw`, `hw`, `hx`,
`erv`, `pmp`, `vfd`, `sys`, `tower`. Fault IDs live in a general namespace:
`{EQUIP}-{NNNN}` — uppercase family key, four digits, contiguous from `0001`
per family in authoring order. The folder name is the fault ID. The number
carries no semantic meaning; provenance lives in each card's `source:` list.
IDs are stable identifiers and are never reused; renames are exceptional (the
CXF does not embed the fault ID, so a rename never churns `content_id`, but it
does break external links and every cross-reference).

**`faults/registry.json`** (`cxf-library/registry/v1`) is the library-wide
fault-code map: one row per rule — `id`, `family`, `name`, `method`, `status`,
and `legacy_id` (the rule's pre-2026-08-18 `{EQUIP}-FC-{NNN}` code, for
continuity with older references). The registry is orchestrator-maintained
like `clusters/clusters.json`, and `tools/lint/registry.py` enforces in CI
that it stays a bijection with the fault dirs, that IDs match the format and
their folder, and that names/statuses match the cards. When a card is added,
renamed, or changes status, the registry row moves with it in the same PR.

Reserved-but-unauthored IDs (a planned rule a README or card already names)
are allowed: they appear in prose and index tables marked planned/deferred,
never in the registry, and the next authored rule in that family takes the
next free number, honoring any reservation.

## Routine catalog

Routine contracts are independent of fault contracts. Nothing in this section
changes a fault schema identifier or fault behavior.

Pin ownership is split by purpose:

- Root `ENGINE_PIN` is the runtime evaluator revision.
- `routines/g36/DONOR_PIN` is the exact open-control-engine donor fixture and
  golden revision.
- `routines/g36/SOURCE_PIN` is the exact upstream Modelica Buildings source
  revision.

Each pin file contains one lowercase 40-hex Git commit. The pin files are the
authoritative locations for these revisions.

### `routines/registry.json` (`cxf-library/routine-registry/v1`)

The registry is an object with exactly two keys: `schema` and `routines`.
`schema` is `cxf-library/routine-registry/v1`; `routines` is an array. The
registry owns the executable routine inventory.

Rows have exactly these keys:

| Field | Type | Contract |
|---|---|---|
| `id` | string | `<class-id>__<variant-id>` |
| `class_id` | string | `G36-<DOMAIN>-<SLUG>` |
| `variant_id` | string | lowercase kebab case |
| `name` | string | display name |
| `family` | string | routine family |
| `level` | enum | `leaf` \| `controller` \| `fragment` |
| `status` | enum | `draft` \| `ported` \| `engine_verified` \| `source_evidenced` \| `adopted` \| `deprecated` |
| `path` | string | safe repository-relative POSIX path below `g36/` |
| `canonical_class` | string\|null | nonempty canonical class for non-fragments; null for fragments |
| `evidence_tier` | enum | `E0` through `E5` |
| `completeness` | object | four-axis completeness declaration |

`<DOMAIN>` is one uppercase ASCII alphanumeric segment. `<SLUG>` is one or
more uppercase ASCII alphanumeric segments separated by hyphens. Variant IDs
contain lowercase ASCII alphanumeric segments separated by single hyphens.
Routine IDs MUST equal the row's `<class_id>__<variant_id>`.

Registry paths MUST start with `g36/`. Absolute paths, backslashes, empty
segments, `.` segments, and `..` segments are invalid. IDs and paths MUST each
be unique, and rows MUST be sorted by `id`.

Every `completeness` object has exactly these keys:
`donor_configuration`, `canonical_class`, `family_package`, and
`guideline_profile`. Each value is `complete`, `partial`, `not_applicable`, or
`unknown`.

### Executable variant bundle

A registered path resolves below `routines/`. Each executable fixed-variant
directory contains:

- `card.md`: independently authored purpose, specialization, interface,
  behavior, evidence, completeness, exclusions, and references;
- `routine.cxf.jsonld`: the executable CXF graph;
- `interface.json`: the scalar host interface;
- `vectors.json`: deterministic scalar replay scenarios;
- `diagram.svg`: an original signal-flow diagram;
- `provenance.json`: pinned source, donor, runtime, and artifact evidence; and
- optional `golden/` files preserved byte-for-byte from the donor.

The registry and bundle directories MUST be a bijection. A registered bundle
has every required file, and no unregistered directory contains
`routine.cxf.jsonld`. Modelica-derived non-fragment bundles also carry the
preserved Buildings license and a third-party notice.

### `interface.json` (`cxf-library/routine-interface/v1`)

The top-level object has exactly `schema`, `routine_id`, `tick_profile`, and
`connectors`. `schema` is `cxf-library/routine-interface/v1`; `routine_id`
matches the registry; `tick_profile` is `HostTick-v1`.

This v1 interface defines only scalar Real connectors. Each connector has
exactly `id`, `direction`, `value_type`, `unit`, `quantity`, and `shape`.
`id` is a unique ASCII identifier, `direction` is `input` or `output`,
`value_type` is `real`, `unit` and `quantity` are nonempty strings, and
`shape` is `scalar`. Connector declarations MUST equal the root CXF input and
output declarations, including direction, type, unit, and quantity.

### `vectors.json` (`cxf-library/routine-vectors/v1`)

The top-level object has exactly `schema`, `routine_id`, `clock`, and
`scenarios`. `schema` is `cxf-library/routine-vectors/v1`, and `routine_id`
matches the registry. `clock` has exactly positive finite `step_s` and finite
non-negative `horizon_s` values.

`scenarios` is a nonempty array. Each scenario has exactly `name`, `inputs`,
and `expect`. Inputs use declared input connector IDs and are either finite
scalar numbers or ordered steps of exactly `{t, value}`. Expectations have
exactly `output`, `from_s`, `to_s`, `equals`, and `tolerance`; they use a
declared output, finite scalar numbers, an inclusive window, and a
non-negative absolute tolerance. Scenarios execute in fresh engines.

Relative tolerance, CSV trace ingestion, non-scalar values, and controller
trace semantics are not part of this contract.

### `provenance.json` (`cxf-library/routine-provenance/v1`)

The top-level object has exactly `schema`, `routine_id`, `runtime`, `donor`,
`upstream`, `fixed_parameters`, `implementation`, `donor_columns`, `artifacts`,
`evidence`, and `private_reference`.

- `runtime` has exactly `repository`, `commit`, `tick_profile`, and
  `content_id`. The commit equals `ENGINE_PIN`, the tick profile is
  `HostTick-v1`, and `content_id` is the evaluator-derived identity. This
  identity is separate from the stable human `routine_id`.
- `donor` has exactly `repository` and `commit`; its commit equals `DONOR_PIN`.
  `upstream` has exactly `repository`, `commit`, `canonical_class`, and
  `source_file`. Its commit equals `SOURCE_PIN`, its canonical class equals the
  registry row, and its source file is a safe nonempty upstream-relative path.
- `fixed_parameters` is a nonempty object keyed by ASCII identifiers. Values
  are JSON strings, numbers, booleans, or null; numbers MUST be finite. The
  root CXF parameters MUST have the same keys and values.
- `implementation` records a safe nonempty selected source branch and block
  class. Its `parameters` object is keyed by ASCII identifiers and contains
  finite scalar numbers. The root CXF contains exactly one block of that class
  with exactly those parameters.
- `donor_columns` has exactly `time` and `connectors`. `time` names the donor
  reference time column. `connectors` maps every interface connector ID to one
  unique donor column name, including mappings where donor and CXF names
  differ. Column names are ASCII identifiers and the time column is distinct.
- Each `artifacts` row has exactly `role`, `local_path`, `donor_path`, and
  `sha256`. Roles are unique lowercase snake-case identifiers. Paths are safe
  relative POSIX paths with no backslashes, empty or dot segments, or
  traversal; paths within each column are unique. Local hashes MUST match the
  files. When donor parity is requested, copied bytes MUST equal the files at
  `donor_path`. E3 bundles include `graph`, `structural_oracle`, and
  `donor_reference` roles plus at least one `provenance` or
  `*_provenance` role. Exactly the `graph` artifact has local path
  `routine.cxf.jsonld`; other artifact names and locations are bundle-owned.
- The donor-reference artifact has one `# columns:` header and finite numeric
  rows. Its mapped time values are non-negative and strictly increasing. It
  contains the mapped time and every declared connector column. Routine
  vectors MUST cover every mapped input and output value at every donor time;
  donor-reference output expectations use point windows and zero tolerance.
- `evidence` rows have exactly `tier`, `status`, and `artifact`. Evidence tiers
  are ordered and contiguous from E0, statuses are `complete`, and artifact
  paths are safe and present. The registry tier cannot exceed the highest
  completed evidence tier.
- `private_reference` has exactly `profile`, `audit_status`, and `sections`.
  This scalar v1 requires `audit_status: not_used` and empty `sections`; no
  private text or local path is recorded.

Registry status, evidence tier, and completeness MUST not exceed the completed
provenance evidence.

### `routines/g36/coverage.json` (`cxf-library/g36-coverage/v1`)

Coverage declares profile scope and claims; it does not repeat the registry's
inventory. The top-level object has exactly `schema`, `profile`,
`completeness`, `areas`, and `claims`. `schema` is
`cxf-library/g36-coverage/v1`, and `profile` is a nonempty string.
`completeness` uses the same exact four-axis object as a registry row.

In this version, `areas` and `claims` MUST remain empty arrays. While the
registry is empty, all four coverage completeness values MUST be `unknown`.
For a nonempty registry, an aggregate axis may be `complete` only when every
applicable registry row is `complete` for that axis. Pin fields and an
`implemented_variants` inventory do not belong in coverage.

Arrays, vectors or member lists, enum-domain behavior, optional connectors,
host services beyond `HostTick-v1`, package acceptance or composition, and E4
or E5 claims are deferred.

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

**`validation:` (optional frontmatter block, adopted 2026-08-18).** Records
empirical validation runs against the card's rule. A list; each entry:
`kind` (`simulation_fpr` | `simulation_tpr` — for `simulation_tpr`, `failures` counts MISSED detections), `harness` (e.g.
`simharness/v1`), `date`, `fleet` (one-line description of buildings ×
climates × period), `scenarios` (count), `failures` (count), optional
`notes` (one line, e.g. the finding a failure represents). Results are
facts about a specific fleet and gating configuration, not guarantees;
the harness README documents mapping proxies and gating. Cards without
the block simply have not been swept yet.

**Card style (conciseness contract, adopted 2026-08-18; exemplar:
`faults/ahu/AHU-0016/card.md`).** Cards are clear, concise, and outlay the
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
  means NO_EVAL) and **sub-condition/direction flags** (e.g. SYS-0006's
  `yBias`/`yNoise`, SYS-0008's direction flags — diagnostic detail only;
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
  target and drives its NO_EVAL fan-out. The reference's own SYS-0005 card
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
  the internal 223P point-modeling note (local-only, not distributed) for the modeling pattern.
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
