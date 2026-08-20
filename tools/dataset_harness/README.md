# External Dataset Harness

This optional, offline tool replays committed CXF rules against locally supplied
HVAC datasets. It owns dataset mapping, unit conversion, host-equivalent gating,
and metrics; it does **not** implement rule logic. Temporary vectors are executed
by `tools/verify` against the repository-pinned open-control engine.

The first adapter is `lbl-fpu/v1`, for the [official LBNL simulated fan-powered
unit dataset](https://faultdetection.lbl.gov/dataset/simulated-fpu/) (DOI
[`10.25984/1881324`](https://doi.org/10.25984/1881324)). The source archive,
inventory, and any derived large replay files remain external to git and normal
CI. The committed `tests/fixtures/lbl_fpu_tiny/` files are original synthetic
test data; they contain no source records.

## Quick start

Obtain and unpack the dataset manually from the official source. Review its
inventory, then create an inventory-backed manifest in the unpacked directory:

```text
/path/to/unpacked/fpu/
├── lbl_fpu_manifest.json
├── selected-pfpu-case.csv
└── selected-sfpu-case.csv
```

The adapter never downloads data and never infers semantics from similar-looking
column names. Inspect mappings before replay:

```bash
python3 tools/dataset_harness/harness.py list-adapters

python3 tools/dataset_harness/harness.py inspect \
  --adapter lbl-fpu \
  --dataset /path/to/unpacked/fpu

python3 tools/dataset_harness/harness.py replay \
  --adapter lbl-fpu \
  --dataset /path/to/unpacked/fpu \
  --rules FPB-0001,FPB-0002,FPB-0003,FPB-0004,FPB-0005,FPB-0006 \
  --output target/dataset-harness/lbl-fpu-results.json
```

`inspect` and `replay` also accept `--case`, `--subtype parallel|series`,
`--case-kind fault-free|faulted`, `--severity`, `--start`, and `--end`.
Dates are inclusive; timestamps must be ISO-8601 with an offset (or a UTC
`YYYY-MM-DD` selector).

## Local manifest contract

The required file is `lbl_fpu_manifest.json` with schema
`cxf-library/dataset-manifest/lbl-fpu/v1`. The original tiny fixture is a
complete executable example. Each case records:

- a stable case ID, relative CSV path, `parallel`/`series` subtype, native
  `step_s`, timestamp column, and optional startup lead;
- a dataset version/retrieval identifier and the exact inventory artifact used;
- `fault_free` or `faulted`, inventory fault class/severity, and the FPB rules
  the inventory semantics actually target, plus a case-level
  `inventory_evidence` locator; faulted cases require an explicit `fault_start`;
- canonical point → exact source-column mapping, source unit, and a non-empty
  `inventory_evidence` locator;
- exact source tokens for Boolean true and false—unknown values fail rather
  than being guessed or interpolated;
- gate-level inventory evidence, dependency lists, and proxy disclosures;
- proxy disclosures and every performed unit conversion;
- explicit independence evidence for `fan_status` and
  `primary_airflow_reference`; and
- model readiness metadata for `fan_airflow_expected` and
  `rht_delta_t_expected` (method/version/inputs/known-good basis/validation
  error/update policy).

The independent reference carries the same readiness record; its `inputs` and
`derived_from` lists must not contain `primary_airflow` or the source column
bound to it. It also requires a plain-language `independence_evidence` record;
aliases or direct transforms of the accused signal remain invalid evidence.

The same anti-circularity rule applies to other evidence lanes. `fan_status`
cannot reuse the final command column or declare it as a dependency.
`fan_airflow_expected` cannot reuse measured fan airflow, and
`rht_delta_t_expected` cannot reuse the measured leaving-temperature outcome.
Expected-model readiness inputs remain explicit and reviewable.
Command/setpoint and measured channels, coil entering/leaving temperatures, and
gate/outcome channels must remain distinct. In particular, fan proof cannot be
derived from the fan-flow outcome used by FPB-0004, and readiness/quality gates
cannot reuse the outcomes they gate.
One narrow topology exception is allowed: an SFPU may bind `primary_airflow`
and `fan_airflow` to the same proven series-flow source when the `fan_airflow`
binding explicitly discloses that topology-equivalent proxy. PFPU mappings and
all other aliases remain invalid.

The adapter rejects a primary-air reference that is not explicitly independent
or that lists `primary_airflow` among its inputs. Missing canonical points make
only the affected rule NO_EVAL; the adapter never manufactures fan proof,
reference truth, or an expected baseline.

Supported source conversions are intentionally small and auditable:

| Source | Canonical | Conversion |
|---|---|---|
| cfm | L/s | `× 0.47194745` |
| m³/s | L/s | `× 1000` |
| degF | degC | `(degF - 32) × 5/9` |
| delta_degF | K | `× 5/9` |
| fraction | % | `× 100` |

Add a reviewed conversion only when the source inventory establishes the unit.
Rules themselves perform no implicit conversion.

## Mapping and evaluability

Candidate LBNL mappings remain case-specific:

| Source fault class | Candidate rule | Required evidence |
|---|---|---|
| Restricted terminal fan flow | FPB-0004 | fan-path flow and known-good, same-path expected flow |
| Primary airflow sensor bias | FPB-0005 | canonical measurement plus genuinely independent same-stream reference |
| Reheat valve leaking/stuck | FPB-0003/0006 | coil-local temperatures, final valve command, hydronic availability |
| Reheat coil air/water fouling | FPB-0006 | valid expected delta-T and full-heat condition |
| Primary damper/control fault | FPB-0002 | primary inlet flow and final active primary setpoint |
| Fault-free PFPU/SFPU | every rule with complete points | all rule-specific gates satisfied |

FPB-0001 is not independently evaluable unless the data has both a final fan
command and an independent run proof. One modeled run signal cannot be copied
into both inputs. Likewise, FPB-0004/0006 are NO_EVAL without defensible
expected models, and FPB-0005 is NO_EVAL without independent evidence.

Every manifest case defines six gate categories: occupied, enabled,
airflow-established, stable mode/setpoint, baseline/reference ready, and point
valid/fresh. Each gate declares the rules it applies to, and the adapter rejects
an applicability list that routes a required gate away from a consumer (for
example, baseline readiness must cover FPB-0004..0006 and point validity must
cover all six rules). The harness ANDs the applicable gates, enforces the
startup lead, and additionally requires every rule input to be present. Invalid
rows and source gaps split windows into fresh engine scenarios, resetting both
engine state and the startup lead exactly as host NO_EVAL should. Boolean status
is never interpolated. Duplicate, out-of-order, or nonintegral-cadence
timestamps block replay; missing whole intervals are reported and split rather
than filled.

Deployments may add well-formed, inventory-backed gates for hydronic
availability, local/HAND, smoke/freeze lockout, maintenance, or other host
obligations. Additional gates must use safe names, explicit rule applicability,
dependency/proxy disclosure, and independent non-outcome source columns; the
six mandatory categories retain their fixed minimum applicability contract.

`inspect` prints each canonical-to-source binding, source and target units,
conversion, inventory evidence, proxy/readiness/independence metadata, gate
definition, and rule evaluability. Treat that output as the mapping review
boundary before any replay.

## Existing-engine replay

For each contiguous evaluable window the harness creates a temporary
`cxf-library/vectors/v1` scenario under the chosen output directory. It invokes:

```text
cxf-verify --trace-json <committed-fault-dir> <temporary-vectors.json>
```

The Rust trace mode loads the committed graph into the same open-control engine
used by ordinary verification and returns boundary outputs per native-cadence
tick. It rejects unsafe clocks and ambiguous boundary-output names, and embeds
the declared engine pin, actual engine source revision at build time, and the
engine-exported rule content ID. The Python caller rejects a trace whose engine
identity differs from `ENGINE_PIN`. The Python tool never evaluates CDL blocks.
Temporary vectors are removed, and canonical rule artifacts are read-only.

Selected cases are loaded, replayed, and released one at a time; the default
selection therefore does not retain the full external archive in memory.
Highly fragmented windows are sent in bounded batches (at most 512 scenarios
and 1,000,000 samples per trace); verifier runtime and stdout/stderr are also
bounded. The fallback Cargo invocation is `--offline` and fails if required
dependencies are not already cached.

## Results and metric definitions

Output conforms to `result.schema.json` and schema
`cxf-library/dataset-validation/v1`. It contains the selected cases, local
fingerprint, point mappings, proxies, conversions, gate definitions, evaluable
sample/segment counts, alarm samples/episodes, target-case detections, and
detection latency.

`fault_free_alarm_sample_rate` uses **fault-free evaluable samples** as its
denominator, never all source rows. A new alarm episode is a false→true
transition within one evaluable segment; a new segment resets episode state.
Target detection metrics count inventory-backed rule-case pairs, because one
source case may target more than one rule. Their denominator includes only pairs
with evaluable samples at or after `fault_start`; pre-fault alarms do not count
as detections, including an alarm already true across the fault boundary. A
detection requires a post-fault false→true episode onset. Latency is measured
from `fault_start` to that onset. Results report both declared and evaluable
target-pair counts so NO_EVAL coverage cannot disappear behind a detection rate.

The result records the library Git revision, `ENGINE_PIN`, actual engine source
revision, verifier path/mode/binary SHA-256, harness/adapter/schema SHA-256,
point-dictionary SHA-256, per-rule graph/card SHA-256, and engine-exported
content ID alongside the dataset fingerprint and an explicit library-worktree
dirty flag. Explicit verifier paths outside the repository binary are labeled
`explicit-untrusted`; all traces still must match the card's recorded content
ID. The dataset fingerprint is checked before and after replay, and a changing
source aborts the result. A rule that is entirely NO_EVAL has graph/card digests
but null runtime identity because no engine trace was executed.

The local fingerprint streams SHA-256 over the manifest and every selected CSV,
including relative filenames. This is reproducible but can take time on a large
selection. Results are facts about one dataset version, mapping, and gate set;
they are not field-performance guarantees. Do not add card `validation:` blocks
until a reproducible full-data run exists and its mapping has been reviewed.

## Data and redistribution posture

Do not commit or redistribute LBNL source files, inventory PDFs, archive
fragments, or derived large traces here. Obtain them from the official source
and follow its current license/terms. Output defaults to the ignored
`target/dataset-harness/` directory. A user-selected output path is allowed, but
the harness writes only the result and removable temporary vectors beneath that
path's parent. If `cxf-verify` has not been built yet, Cargo also creates its
normal ignored build cache under `tools/verify/target/`. Output inside this
repository is accepted only under `target/`, and output inside the source
dataset directory is always rejected.

## Tests and current validation status

```bash
python3 -m unittest discover -s tools/dataset_harness/tests -v
```

CI runs the original tiny PFPU/SFPU fixtures and an existing-engine replay
smoke. The local contract suite currently includes 32 Python tests plus two Rust
trace-clock tests. No external archive was available during PR11 implementation,
so only fixture behavior is recorded: there is no full-data FPR/TPR claim and no
card validation block.

## Adding a future adapter

Add an adapter under `adapters/`, register it in `adapters/__init__.py`, and
provide original tiny fixtures covering discovery, timestamps/gaps, conversions,
Boolean handling, mapping failures, proxies, gates, deterministic results, and
CLI errors. Keep the common result schema and existing-engine trace boundary.

Planned adapters, not implemented here:

- LBNL boiler plant: preserve per-boiler/per-pump identity, firing proof, stable
  eligible capacity, and plant mode gates.
- LBNL chiller plant: preserve per-chiller versus common-header topology,
  refrigerant derivations, and staging/plant-transition exclusions.
- LBNL RTU: require final command versus independent proof and document every
  runtime-fraction, airflow, or modeled-status proxy.
