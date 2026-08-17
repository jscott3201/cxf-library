# Repo Landscape — where cxf-library fits

Three sibling projects (all `jscott3201` on GitHub):

| Local path | GitHub | Role |
|---|---|---|
| `~/Development/cxf-json` | `jscott3201/cxf-json` | Rust **reader/parser** for CXF JSON-LD (syntax, vocabulary, graph integrity) |
| `~/Development/open-control` | `jscott3201/open-control-engine` | Rust **execution engine** for CDL sequences ingested as CXF |
| `~/Development/cxf-library` (this repo) | private | **Content library**: our CXF JSON routines / control programs; CDL-based FDD rules |

## open-control-engine (local `open-control`) — what matters for us

Pure-Rust embeddable library (17 crates, `oce-*`), no daemon/async/db. Facade:
`Engine<S: Store>` in `crates/oce-api/src/engine.rs` — `load_cxf(&[u8])` →
flatten → validate → frozen Kahn-scheduled DAG → `tick`/`simulate`/`step_realtime`,
plus `set_input/get_output`, `watch`, `get/set_param`, `checkpoint/restore`,
`export_cxf`, `point_list`.

- **136 registered elementary block classes** (Reals 52, Logical 26, Integers 24,
  Routing 15, Discrete 7, Conversions 4, Psychrometrics 3, Utilities 2).
  Machine-readable manifest: `tools/reference-catalog/oce-blocks.registry-manifest.json`.
  Includes everything FDD rules need: comparators (Greater/LessThreshold, Hysteresis),
  logic (And/Or/Not/MultiAnd), timing (Timer, TrueDelay, TrueFalseHold,
  TrueHoldWithReset), latches (Latch, Toggle, Edge/FallingEdge/Change), Switch,
  MovingAverage-family filters (reals_filters.rs), PID, Utilities.Assert.
- **Unit of deployment = a CXF `.jsonld` document.** No "routine" abstraction.
  Dialect: `@context` with `S231: http://data.ashrae.org/S231P#`, flat `@graph`,
  `S231:Block` + `containsBlock/hasInput/hasOutput/hasParameter/isConnectedTo`,
  elementary instances typed by CDL class IRI. Normative contract for external
  emitters (us!): `docs/cxf-composite-subset.md`.
- **G36 today**: 48 CXF fixtures + 43 supported runtime sequences over 31
  `Buildings.Controls.OBC.ASHRAE.G36.*` class paths (economizers, supply temp/fan,
  freeze protection, trim-and-respond, zone states, cooling-only VAV incl. its
  **Alarms ladder** — `cooling_only_alarms.jsonld`, 203 nodes, yLowFloAla/
  yFloSenAla/yLeaDamAla). Catalog:
  `tools/reference-catalog/Buildings.Controls.OBC.ASHRAE.G36.catalog.json`.
  Policy: "selected-explicit-cxf-variants-supported", not arbitrary composites.
- **Verification culture**: independent oracle generator (`tools/golden-gen`,
  firewalled from oce-blocks), golden CSV traces, determinism/funnel/oracle test
  triads, OpenModelica differential evidence. Any sequence we author should come
  with the same: fixture + input schedule + expected trace. FDD test vectors from
  the fault cards slot directly into this pattern.
- **No FDD subsystem and no fail-safe policy.** `PointStatus` (Fault/Stale/...)
  stages identically to Ok; staleness/fault reaction is explicitly the host's job
  (`docs/host-responsibilities.md`). `Utilities.Assert` is a warning sink only.
  → The FDD meta-layer (NO_EVAL, gap handling, suppression, accumulators) is a
  **host-side concern** wrapped around engine ticks, or a future crate above
  `oce-api` — not something to force into CDL block logic.
- Vendored upstream: `third_party/modelica-buildings-cdl/Buildings/` (176 .mo) and
  `cxf/` (44 modelica-json translations) — reference material for authoring.
- Placeholders that always error: `load_from_semantic`, `load_modelica`.

## cxf-json — what matters for us

Contract crate + evidence crate; profile-governed (`spec/PROFILE.md`, v0.1.8);
no public parse API yet (projection/validation are pub(crate)). Not our runtime
path — the engine has its own CXF importer — but:

- `_research/UPSTREAM-CXF.md` there is the best single doc on the modelica-json
  pipeline and its emitter quirks (C-001..C-007: `connectedTo` vs `isConnectedTo`,
  three S231 namespace generations, JS-object leakage in `value`, etc.).
- Its validation posture (warn only when provably out of domain) and its
  negative corpora (w016) are a model for how we lint library documents.
- D-024: never copy upstream fixture bytes — author synthetic content.

## Dialect note (authoring pitfall)

The OBC spec says `connectedTo`; the engine fixtures use `S231:isConnectedTo`
and namespace `http://data.ashrae.org/S231P#`. cxf-json treats these dialects as
distinct, never merged. **When authoring for the engine, match the engine's
composite-subset contract** (`open-control/docs/cxf-composite-subset.md`) exactly.

## What this repo will hold (mission)

1. **FDD rule library authored against CDL semantics**, exported/stored as CXF
   JSON documents the engine can load — grounded in the HVAC FDD Reference
   (see fdd-reference-digest.md) as guidance, G36 §5.16.14 for the 001-range.
2. **G36 routine enhancements** — our variants/extensions of the engine's
   supported sequences.
3. Per-rule metadata the CXF logic can't carry (severity, impact category,
   playbook, suppression relations, test vectors) — sidecar files next to each
   document.
