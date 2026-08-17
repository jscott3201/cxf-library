# CDL / CXF Spec Notes

Sources: https://obc.lbl.gov/specification/cdl.html · https://obc.lbl.gov/specification/cxf.html
(LBNL OpenBuildingControl; CDL standardized as ANSI/ASHRAE Standard 231.)

## CDL (Control Description Language)

Declarative, vendor-neutral block-diagram language for building control sequences.
A restricted subset of Modelica 3.6 — no `inner`/`outer`, no `algorithm` sections in
composite/elementary blocks, no clocked state machines, no `initial equation`.

### Model of computation
Synchronous data flow: values persist until changed; events consume zero simulated
time; every input connects to exactly one output; the connection graph is acyclic
(no algebraic loops). Deterministic and non-blocking — suited to real-time BAS.

### Building blocks
- **Elementary blocks** (predefined, non-modifiable): `CDL.Reals` (Add, Subtract,
  Multiply, Gain, Limiter, Min, Max, Hysteresis, PID, MultiplyByParameter, …),
  `CDL.Logical` (And, Or, Not, edge detect, timers, …), `CDL.Integers`,
  `CDL.Discrete` (sampling, ZOH, triggered ops), `CDL.Sources` (Constant, Ramp,
  Pulse, CivilTime), `CDL.Interfaces` (Real/Integer/BooleanInput/Output).
  Semantics: y(t), x'(t) = f(p, t, x(t), u(t)) — implementations must reproduce
  identical I/O behavior regardless of internal language.
- **Composite blocks**: hierarchical composition of elementary/composite blocks,
  with parameters, exposed connectors, and `connect` equations. Stored as `.mo`
  files, package name = directory path. Single inheritance via `extends`.
- **Extension blocks** (`__cdl(extensionBlock=true)`): full Modelica (algorithms,
  external C, FMU import, state machines, statistical/fault-detection algorithms).
  Must compile to FMU 2.0. **Escape hatch for logic CDL can't express.**

### Types & declarations
Real (with quantity/unit/displayUnit/min/max/nominal), Integer, Boolean, String,
Enumeration. `parameter` = time-invariant, user/API-adjustable, not connectable;
`constant` = fixed at compile time. 1-D/2-D arrays, 1-indexed, sizes fixed at
translation; `fill`, `cat`, iterator expressions.

### Connections
Same-type connectors only; attributes (quantity/unit/min/max) must be consistent;
inputs require exactly one source.

### Key annotations
- `__cdl(generatePointlist=…, controlledDevice=…)` — point list export.
- `__cdl(connection(hardwired=…))` — hard vs soft I/O.
- `__cdl(trend(interval=…, enable=…))` — trending spec.
- `__cdl(default=…)` — fallbacks for conditionally-removable inputs.
- `__cdl(semantic(metadataLanguage="Brick 1.3 text/turtle" "…"))` — embeds Brick /
  Haystack / ASHRAE 223P ontology metadata. **This is where FDD point tags
  (Haystack markers from the point dictionary) ride along.**
- `__cdl(InstanceInReference=false)` — marks deviations from a source spec (G36).

### Translation flags (modelica-json)
`evaluatePropagatedParameters`, `evaluateExpressions` — flatten parameter
propagation / expressions for BAS platforms that don't support them.

## CXF (Control eXchange Format)

JSON-LD serialization of a *specifically configured* CDL instance (not a library).
Logic is identical to the CDL source; format differs.

- Grounded in `CXF-Core.jsonld` (RDF classes: Package, Block, ElementaryBlock,
  CompositeBlock, ExtensionBlock, InputConnector/OutputConnector, Parameter,
  Constant, DataType, Real/Integer/BooleanInput/Output, EnumerationType, String).
- Properties: `hasInput`/`hasOutput`, `hasParameter`/`hasConstant`, `hasInstance`,
  `connectedTo`, `isOfDataType`, `hasFmuPath`, `translationSoftware(Version)`.
- Instance IRIs: `Package.Path#instance`, children dotted (`parent.child`).
- Flat `@graph` of nodes — no nested block objects; containment is via edges.
- Arrays may be flattened row-major with underscores (`B[1,2]` → `B_1_2`).
- Expressions preserved by default or evaluated at translation.
- Elementary blocks appear **without equations** — the engine must supply the
  block semantics (this is what open-control-engine implements).
- Export gated by `__cdl(export=true)`; extension blocks need FMU paths.

## What our cxf-json crate adds on top (see cxf-json repo)

- Namespace dialects are real and messy: `http://data.ashrae.org/S231#`,
  `…/S231P#`, legacy `https://…/S231P#` — kept distinct, never merged.
- `connectedTo` vs `isConnectedTo` emitter divergence; QUDT units
  (`qudt:hasUnit`, `qudt:hasQuantityKind`); upstream emitter bugs cataloged
  (JS-object leakage in `value`, `conditionalExpression: "not undefined"`, …).
- Validation posture: warn/error only when provably out of domain; unknown
  predicates preserved as extension records. Codes CXF-V-001..005, CXF-P-000..006.
- Authoritative reader profile: `cxf-json/spec/PROFILE.md`.

## Implications for FDD-as-CDL (this repo's mission)

1. A fault rule = a CDL **composite block**: point inputs → comparison/logic
   elementary blocks → `yFault` BooleanOutput. Tunable parameters (thresholds,
   AlarmDelay) = CDL `parameter`s. Persistence = `Logical.TrueDelay`-style blocks.
2. Haystack markers from the FDD point dictionary map to `__cdl(semantic(...))`
   annotations on input connectors → survive into CXF → machine-discoverable
   point binding at deployment.
3. Statistical rules (rolling averages, baselines, change-point) exceed the
   elementary library → **extension blocks** (FMU) or engine-native meta layer.
4. Engine-level semantics that CDL cannot express (NO_EVAL data quality,
   hierarchical suppression, energy accumulators, gap handling) sit *around*
   rules, not inside them — they belong to the engine/runtime contract, with
   fault metadata (severity, category, playbook refs) carried as annotations
   or sidecar metadata rather than block logic.
