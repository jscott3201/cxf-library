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
  the inventory semantics actually target;
- canonical point → exact source-column mapping, source unit, and a non-empty
  `inventory_evidence` locator;
- exact source tokens for Boolean true and false—unknown values fail rather
  than being guessed or interpolated;
- proxy disclosures and every performed unit conversion;
- independent-reference evidence for `primary_airflow_reference`; and
- model readiness metadata for `fan_airflow_expected` and
  `rht_delta_t_expected` (method/version/inputs/known-good basis/validation
  error/update policy).

The independent reference carries the same readiness record; its `inputs` and
`derived_from` lists must not contain `primary_airflow`.

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
valid/fresh. Each gate declares the rules it applies to. The harness ANDs the
applicable gates, enforces the startup lead, and additionally requires every
rule input to be present. Invalid rows and source gaps split windows into fresh
engine scenarios, resetting state exactly as host NO_EVAL should. Boolean
status is never interpolated. Duplicate or out-of-order timestamps block replay;
missing intervals are reported and split rather than filled.

## Existing-engine replay

For each contiguous evaluable window the harness creates a temporary
`cxf-library/vectors/v1` scenario under the chosen output directory. It invokes:

```text
cxf-verify --trace-json <committed-fault-dir> <temporary-vectors.json>
```

The Rust trace mode loads the committed graph into the same open-control engine
used by ordinary verification and returns boundary outputs per native-cadence
tick. The Python tool never evaluates CDL blocks. Temporary vectors are removed,
and canonical rule artifacts are read-only.

## Results and metric definitions

Output conforms to `result.schema.json` and schema
`cxf-library/dataset-validation/v1`. It contains the selected cases, local
fingerprint, point mappings, proxies, conversions, gate definitions, evaluable
sample/segment counts, alarm samples/episodes, target-case detections, and
detection latency.

`fault_free_alarm_sample_rate` uses **fault-free evaluable samples** as its
denominator, never all source rows. A new alarm episode is a false→true
transition within one evaluable segment; a new segment resets episode state.
Faulted detection metrics count only cases whose inventory-backed
`expected_rules` includes that rule. Latency is measured from the manifest
`fault_start` to the first evaluable alarm.

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
smoke. No external archive was available during PR11 implementation, so only
fixture behavior is recorded: there is no full-data FPR/TPR claim and no card
validation block.

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
