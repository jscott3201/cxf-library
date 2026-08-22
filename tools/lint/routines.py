#!/usr/bin/env python3
"""Validate routine catalog contracts and optional donor byte parity."""

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import TypeGuard


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = Path("routines/registry.json")
COVERAGE_PATH = Path("routines/g36/coverage.json")
SOURCE_PIN_PATH = Path("routines/g36/SOURCE_PIN")
DONOR_PIN_PATH = Path("routines/g36/DONOR_PIN")

REGISTRY_KEYS = frozenset(("schema", "routines"))
COVERAGE_KEYS = frozenset(("schema", "profile", "completeness", "areas", "claims"))
ROW_KEYS = frozenset(
    (
        "id",
        "class_id",
        "variant_id",
        "name",
        "family",
        "level",
        "status",
        "path",
        "canonical_class",
        "evidence_tier",
        "completeness",
    )
)
COMPLETENESS_KEYS = frozenset(
    ("donor_configuration", "canonical_class", "family_package", "guideline_profile")
)

INTERFACE_KEYS = frozenset(("schema", "routine_id", "tick_profile", "connectors"))
CONNECTOR_KEYS = frozenset(("id", "direction", "value_type", "unit", "quantity", "shape"))
VECTORS_KEYS = frozenset(("schema", "routine_id", "clock", "scenarios"))
CLOCK_KEYS = frozenset(("step_s", "horizon_s"))
SCENARIO_KEYS = frozenset(("name", "inputs", "expect"))
STEP_KEYS = frozenset(("t", "value"))
EXPECT_KEYS = frozenset(("output", "from_s", "to_s", "equals", "tolerance"))
PROVENANCE_KEYS = frozenset(
    (
        "schema",
        "routine_id",
        "runtime",
        "donor",
        "upstream",
        "fixed_parameters",
        "implementation",
        "donor_columns",
        "artifacts",
        "evidence",
        "private_reference",
    )
)
RUNTIME_KEYS = frozenset(("repository", "commit", "tick_profile", "content_id"))
DONOR_KEYS = frozenset(("repository", "commit"))
UPSTREAM_KEYS = frozenset(("repository", "commit", "canonical_class", "source_file"))
IMPLEMENTATION_KEYS = frozenset(("selected_branch", "block_class", "parameters"))
DONOR_COLUMNS_KEYS = frozenset(("time", "connectors"))
ARTIFACT_KEYS = frozenset(("role", "local_path", "donor_path", "sha256"))
EVIDENCE_KEYS = frozenset(("tier", "status", "artifact"))
PRIVATE_REFERENCE_KEYS = frozenset(("profile", "audit_status", "sections"))

LEVELS = frozenset(("leaf", "controller", "fragment"))
STATUSES = frozenset(
    ("draft", "ported", "engine_verified", "source_evidenced", "adopted", "deprecated")
)
EVIDENCE_TIERS = tuple(f"E{number}" for number in range(6))
COMPLETENESS_VALUES = frozenset(("complete", "partial", "not_applicable", "unknown"))
REQUIRED_BUNDLE_FILES = (
    "card.md",
    "routine.cxf.jsonld",
    "interface.json",
    "vectors.json",
    "diagram.svg",
    "provenance.json",
)

RUNTIME_REPOSITORY = "https://github.com/jscott3201/open-control-engine"
UPSTREAM_REPOSITORY = "https://github.com/lbl-srg/modelica-buildings"

PIN_RE = re.compile(r"^[0-9a-f]{40}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
CONTENT_ID_RE = re.compile(r"^cxf:fnv1a128:[0-9a-f]{32}$")
CLASS_ID_RE = re.compile(r"^G36-[A-Z0-9]+-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
VARIANT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ROUTINE_ID_RE = re.compile(
    r"^G36-[A-Z0-9]+-[A-Z0-9]+(?:-[A-Z0-9]+)*__"
    r"[a-z0-9]+(?:-[a-z0-9]+)*$"
)
CONNECTOR_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
ARTIFACT_ROLE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
DONOR_COLUMN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
PRIVATE_LEAK_RE = re.compile(
    r"G36_PDF_PATH|file://|/(?:Users|home|var)/|[A-Za-z]:\\|"
    r"\.(?:pdf|png|jpe?g)\b|data:image|<image\b",
    re.IGNORECASE,
)


def _read_json(repo_root, relative_path, errors):
    return _read_json_file(repo_root / relative_path, relative_path.as_posix(), errors)


def _read_json_file(path, label, errors):
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"{label}: file is missing")
        return None
    except (OSError, UnicodeError):
        errors.append(f"{label}: unable to read file")
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: invalid JSON at line {exc.lineno}, column {exc.colno}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label}: must contain a JSON object")
        return None
    return value


def _check_exact_keys(value, expected, label, errors):
    actual = set(value)
    if actual == expected:
        return
    details = []
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        details.append(f"missing {', '.join(missing)}")
    if unexpected:
        details.append(f"unexpected {', '.join(unexpected)}")
    errors.append(
        f"{label}: keys must be exactly {', '.join(sorted(expected))} "
        f"({'; '.join(details)})"
    )


def _check_enum(value, allowed, label, errors):
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{label}: must be one of {', '.join(sorted(allowed))}")


def _check_completeness(value, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label}: must be an object")
        return
    _check_exact_keys(value, COMPLETENESS_KEYS, label, errors)
    for key in sorted(COMPLETENESS_KEYS & set(value)):
        _check_enum(value[key], COMPLETENESS_VALUES, f"{label}.{key}", errors)


def _relative_path_problem(value, prefix=None):
    if not isinstance(value, str):
        return "must be a string"
    if value.startswith("/"):
        return "absolute paths are forbidden"
    if "\\" in value:
        return "backslashes are forbidden"
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return "control characters are forbidden"
    segments = value.split("/")
    if "" in segments:
        return "empty path segments are forbidden"
    if "." in segments:
        return "dot path segments are forbidden"
    if ".." in segments:
        return "parent traversal is forbidden"
    if prefix is not None and (segments[0] != prefix or len(segments) < 2):
        return f"path must be below {prefix}/"
    return None


def _local_path(base, relative):
    return base.joinpath(*relative.split("/"))


def _is_finite_number(value: object) -> TypeGuard[int | float]:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _is_json_scalar(value):
    return value is None or isinstance(value, (bool, str)) or _is_finite_number(value)


def _safe_nonempty_string(value):
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not any(ord(character) < 32 for character in value)
        and PRIVATE_LEAK_RE.search(value) is None
    )


def _scalar_equal(left, right):
    if _is_finite_number(left) and _is_finite_number(right):
        return left == right
    return type(left) is type(right) and left == right


def _read_pin(repo_root, relative_path, errors):
    label = relative_path.as_posix()
    try:
        text = (repo_root / relative_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"{label}: file is missing")
        return None
    except (OSError, UnicodeError):
        errors.append(f"{label}: unable to read file")
        return None
    value = text[:-1] if text.endswith("\n") else text
    if not PIN_RE.fullmatch(value):
        errors.append(f"{label}: must contain one lowercase 40-hex Git commit")
        return None
    return value


def _validate_row(row, index, errors, seen_ids, seen_paths):
    prefix = f"{REGISTRY_PATH.as_posix()}: routines[{index}]"
    if not isinstance(row, dict):
        errors.append(f"{prefix}: must be an object")
        return
    _check_exact_keys(row, ROW_KEYS, prefix, errors)
    for key in ("id", "class_id", "variant_id", "name", "family", "path"):
        if key in row and not isinstance(row[key], str):
            errors.append(f"{prefix}.{key}: must be a string")

    routine_id = row.get("id")
    class_id = row.get("class_id")
    variant_id = row.get("variant_id")
    path = row.get("path")
    if isinstance(routine_id, str):
        if not ROUTINE_ID_RE.fullmatch(routine_id):
            errors.append(f"{prefix}.id: does not match G36-<DOMAIN>-<SLUG>__<variant-id>")
        if routine_id in seen_ids:
            errors.append(
                f"{prefix}.id: duplicate {routine_id!r}; first used by routines[{seen_ids[routine_id]}]"
            )
        else:
            seen_ids[routine_id] = index
    if isinstance(class_id, str) and not CLASS_ID_RE.fullmatch(class_id):
        errors.append(f"{prefix}.class_id: does not match G36-<DOMAIN>-<SLUG>")
    if isinstance(variant_id, str) and not VARIANT_ID_RE.fullmatch(variant_id):
        errors.append(f"{prefix}.variant_id: must be lowercase kebab case")
    if all(isinstance(value, str) for value in (routine_id, class_id, variant_id)):
        expected_id = f"{class_id}__{variant_id}"
        if routine_id != expected_id:
            errors.append(f"{prefix}.id: must equal {expected_id!r}")

    if isinstance(path, str):
        problem = _relative_path_problem(path, "g36")
        if problem:
            errors.append(f"{prefix}.path: {problem}")
        if path in seen_paths:
            errors.append(
                f"{prefix}.path: duplicate {path!r}; first used by routines[{seen_paths[path]}]"
            )
        else:
            seen_paths[path] = index
    if "level" in row:
        _check_enum(row["level"], LEVELS, f"{prefix}.level", errors)
    if "status" in row:
        _check_enum(row["status"], STATUSES, f"{prefix}.status", errors)
    if "evidence_tier" in row:
        _check_enum(row["evidence_tier"], EVIDENCE_TIERS, f"{prefix}.evidence_tier", errors)

    if "canonical_class" in row:
        canonical_class = row["canonical_class"]
        if canonical_class is not None and not isinstance(canonical_class, str):
            errors.append(f"{prefix}.canonical_class: must be a string or null")
        level = row.get("level")
        if level == "fragment" and canonical_class is not None:
            errors.append(f"{prefix}.canonical_class: fragments must use null")
        if level in ("leaf", "controller") and (
            not isinstance(canonical_class, str) or not canonical_class.strip()
        ):
            errors.append(f"{prefix}.canonical_class: non-fragments require a nonempty string")
    if "completeness" in row:
        _check_completeness(row["completeness"], f"{prefix}.completeness", errors)


def _validate_interface(value, label, routine_id, errors):
    connectors = {}
    if value is None:
        return connectors
    _check_exact_keys(value, INTERFACE_KEYS, label, errors)
    if value.get("schema") != "cxf-library/routine-interface/v1":
        errors.append(f"{label}: schema must be 'cxf-library/routine-interface/v1'")
    if value.get("routine_id") != routine_id:
        errors.append(f"{label}: routine_id must equal {routine_id!r}")
    if value.get("tick_profile") != "HostTick-v1":
        errors.append(f"{label}: tick_profile must be 'HostTick-v1'")
    rows = value.get("connectors")
    if not isinstance(rows, list) or not rows:
        errors.append(f"{label}: connectors must be a nonempty array")
        return connectors
    for index, connector in enumerate(rows):
        prefix = f"{label}: connectors[{index}]"
        if not isinstance(connector, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        _check_exact_keys(connector, CONNECTOR_KEYS, prefix, errors)
        connector_id = connector.get("id")
        if not isinstance(connector_id, str) or not CONNECTOR_ID_RE.fullmatch(connector_id):
            errors.append(f"{prefix}.id: must be an ASCII connector identifier")
        elif connector_id in connectors:
            errors.append(f"{prefix}.id: duplicate {connector_id!r}")
        else:
            connectors[connector_id] = connector
        _check_enum(connector.get("direction"), ("input", "output"), f"{prefix}.direction", errors)
        if connector.get("value_type") != "real":
            errors.append(f"{prefix}.value_type: must be 'real'")
        if connector.get("shape") != "scalar":
            errors.append(f"{prefix}.shape: must be 'scalar'")
        for key in ("unit", "quantity"):
            field = connector.get(key)
            if not isinstance(field, str) or not field.strip():
                errors.append(f"{prefix}.{key}: must be a nonempty string")
    if not any(row.get("direction") == "output" for row in connectors.values()):
        errors.append(f"{label}: at least one output connector is required")
    return connectors


def _validate_vectors(value, label, routine_id, connectors, errors):
    input_samples = {
        connector_id: []
        for connector_id, connector in connectors.items()
        if connector.get("direction") == "input"
    }
    output_samples = {
        connector_id: []
        for connector_id, connector in connectors.items()
        if connector.get("direction") == "output"
    }
    if value is None:
        return input_samples, output_samples
    _check_exact_keys(value, VECTORS_KEYS, label, errors)
    if value.get("schema") != "cxf-library/routine-vectors/v1":
        errors.append(f"{label}: schema must be 'cxf-library/routine-vectors/v1'")
    if value.get("routine_id") != routine_id:
        errors.append(f"{label}: routine_id must equal {routine_id!r}")
    clock = value.get("clock")
    horizon = None
    if not isinstance(clock, dict):
        errors.append(f"{label}: clock must be an object")
    else:
        _check_exact_keys(clock, CLOCK_KEYS, f"{label}: clock", errors)
        step = clock.get("step_s")
        horizon = clock.get("horizon_s")
        if not _is_finite_number(step) or step <= 0:
            errors.append(f"{label}: clock.step_s must be finite and greater than zero")
        if not _is_finite_number(horizon) or horizon < 0:
            errors.append(f"{label}: clock.horizon_s must be finite and non-negative")
    scenarios = value.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append(f"{label}: scenarios must be a nonempty array")
        return input_samples, output_samples
    names = set()
    for index, scenario in enumerate(scenarios):
        prefix = f"{label}: scenarios[{index}]"
        if not isinstance(scenario, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        _check_exact_keys(scenario, SCENARIO_KEYS, prefix, errors)
        name = scenario.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}.name: must be a nonempty string")
        elif name in names:
            errors.append(f"{prefix}.name: duplicate {name!r}")
        else:
            names.add(name)
        inputs = scenario.get("inputs")
        if not isinstance(inputs, dict):
            errors.append(f"{prefix}.inputs: must be an object")
        else:
            for connector_id, spec in inputs.items():
                connector = connectors.get(connector_id)
                if connector is None or connector.get("direction") != "input":
                    errors.append(f"{prefix}.inputs: {connector_id!r} is not a declared input")
                if _is_finite_number(spec):
                    if connector_id in input_samples:
                        input_samples[connector_id].append((0.0, float(spec)))
                    continue
                if not isinstance(spec, list) or not spec:
                    errors.append(f"{prefix}.inputs.{connector_id}: must be a number or nonempty step array")
                    continue
                previous_t = None
                for step_index, item in enumerate(spec):
                    step_label = f"{prefix}.inputs.{connector_id}[{step_index}]"
                    if not isinstance(item, dict):
                        errors.append(f"{step_label}: must be an object")
                        continue
                    _check_exact_keys(item, STEP_KEYS, step_label, errors)
                    t = item.get("t")
                    item_value = item.get("value")
                    if not _is_finite_number(t) or t < 0 or (
                        _is_finite_number(horizon) and t > horizon
                    ):
                        errors.append(f"{step_label}.t: must be finite and within the clock horizon")
                    elif previous_t is not None and t <= previous_t:
                        errors.append(f"{step_label}.t: steps must be strictly increasing")
                    else:
                        previous_t = t
                    if not _is_finite_number(item_value):
                        errors.append(f"{step_label}.value: must be a finite number")
                    elif connector_id in input_samples and _is_finite_number(t):
                        input_samples[connector_id].append((float(t), float(item_value)))
        expects = scenario.get("expect")
        if not isinstance(expects, list) or not expects:
            errors.append(f"{prefix}.expect: must be a nonempty array")
            continue
        for expect_index, expect in enumerate(expects):
            expect_label = f"{prefix}.expect[{expect_index}]"
            if not isinstance(expect, dict):
                errors.append(f"{expect_label}: must be an object")
                continue
            _check_exact_keys(expect, EXPECT_KEYS, expect_label, errors)
            output = expect.get("output")
            connector = connectors.get(output) if isinstance(output, str) else None
            if connector is None or connector.get("direction") != "output":
                errors.append(f"{expect_label}.output: {output!r} is not a declared output")
            start = expect.get("from_s")
            end = expect.get("to_s")
            equals = expect.get("equals")
            tolerance = expect.get("tolerance")
            if not _is_finite_number(start) or not _is_finite_number(end) or start < 0 or end < start:
                errors.append(f"{expect_label}: assertion window must be finite, non-negative, and ordered")
            elif _is_finite_number(horizon) and end > horizon:
                errors.append(f"{expect_label}.to_s: must not exceed the clock horizon")
            if not _is_finite_number(equals):
                errors.append(f"{expect_label}.equals: must be a finite number")
            if not _is_finite_number(tolerance) or tolerance < 0:
                errors.append(f"{expect_label}.tolerance: must be finite and non-negative")
            if (
                output in output_samples
                and _is_finite_number(start)
                and _is_finite_number(end)
                and start == end
                and _is_finite_number(equals)
                and tolerance == 0
            ):
                output_samples[output].append((float(start), float(equals)))
    return (
        {connector_id: sorted(samples) for connector_id, samples in input_samples.items()},
        {connector_id: sorted(samples) for connector_id, samples in output_samples.items()},
    )


def _validate_object(value, expected_keys, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label}: must be an object")
        return None
    _check_exact_keys(value, expected_keys, label, errors)
    return value


def _read_artifact(bundle, relative, label, errors):
    try:
        return _local_path(bundle, relative).read_bytes()
    except FileNotFoundError:
        errors.append(f"{label}: artifact is missing")
    except OSError:
        errors.append(f"{label}: unable to read artifact")
    return None


def _validate_provenance(
    value,
    label,
    routine_id,
    row,
    connectors,
    bundle,
    engine_pin,
    donor_pin,
    source_pin,
    profile,
    donor_root,
    errors,
):
    result = {
        "fixed_parameters": {},
        "implementation": {},
        "donor_columns": {},
        "artifacts": {},
        "max_tier": None,
        "content_id": None,
        "modelica_derived": False,
    }
    if value is None:
        return result
    _check_exact_keys(value, PROVENANCE_KEYS, label, errors)
    if value.get("schema") != "cxf-library/routine-provenance/v1":
        errors.append(f"{label}: schema must be 'cxf-library/routine-provenance/v1'")
    if value.get("routine_id") != routine_id:
        errors.append(f"{label}: routine_id must equal {routine_id!r}")

    runtime = _validate_object(value.get("runtime"), RUNTIME_KEYS, f"{label}: runtime", errors)
    if runtime is not None:
        if runtime.get("repository") != RUNTIME_REPOSITORY:
            errors.append(f"{label}: runtime.repository must name open-control-engine")
        if engine_pin is not None and runtime.get("commit") != engine_pin:
            errors.append(f"{label}: runtime.commit must equal ENGINE_PIN")
        if runtime.get("tick_profile") != "HostTick-v1":
            errors.append(f"{label}: runtime.tick_profile must be 'HostTick-v1'")
        content_id = runtime.get("content_id")
        if not isinstance(content_id, str) or not CONTENT_ID_RE.fullmatch(content_id):
            errors.append(f"{label}: runtime.content_id must be an evaluator content ID")
        else:
            result["content_id"] = content_id

    donor = _validate_object(value.get("donor"), DONOR_KEYS, f"{label}: donor", errors)
    if donor is not None:
        if donor.get("repository") != RUNTIME_REPOSITORY:
            errors.append(f"{label}: donor.repository must name open-control-engine")
        if donor_pin is not None and donor.get("commit") != donor_pin:
            errors.append(f"{label}: donor.commit must equal DONOR_PIN")
    upstream = _validate_object(value.get("upstream"), UPSTREAM_KEYS, f"{label}: upstream", errors)
    if upstream is not None:
        if upstream.get("repository") != UPSTREAM_REPOSITORY:
            errors.append(f"{label}: upstream.repository must name modelica-buildings")
        else:
            result["modelica_derived"] = True
        if source_pin is not None and upstream.get("commit") != source_pin:
            errors.append(f"{label}: upstream.commit must equal SOURCE_PIN")
        if upstream.get("canonical_class") != row.get("canonical_class"):
            errors.append(f"{label}: upstream.canonical_class must equal the registry")
        source_file_problem = _relative_path_problem(upstream.get("source_file"))
        if source_file_problem:
            errors.append(f"{label}: upstream.source_file: {source_file_problem}")

    fixed = value.get("fixed_parameters")
    if not isinstance(fixed, dict) or not fixed:
        errors.append(f"{label}: fixed_parameters must be a nonempty object")
    else:
        result["fixed_parameters"] = fixed
        for key in sorted(fixed):
            if not isinstance(key, str) or not CONNECTOR_ID_RE.fullmatch(key):
                errors.append(f"{label}: fixed_parameters keys must be ASCII identifiers")
            if not _is_json_scalar(fixed[key]):
                errors.append(
                    f"{label}: fixed_parameters.{key} must be a JSON scalar with finite numbers"
                )
    implementation = _validate_object(
        value.get("implementation"), IMPLEMENTATION_KEYS, f"{label}: implementation", errors
    )
    if implementation is not None:
        result["implementation"] = implementation
        for key in ("selected_branch", "block_class"):
            if not _safe_nonempty_string(implementation.get(key)):
                errors.append(f"{label}: implementation.{key} must be a safe nonempty string")
        parameters = implementation.get("parameters")
        if not isinstance(parameters, dict):
            errors.append(f"{label}: implementation.parameters must be an object")
        else:
            for key in sorted(parameters):
                if not isinstance(key, str) or not CONNECTOR_ID_RE.fullmatch(key):
                    errors.append(f"{label}: implementation.parameters keys must be ASCII identifiers")
                if not _is_finite_number(parameters[key]):
                    errors.append(
                        f"{label}: implementation.parameters.{key} must be a finite number"
                    )

    donor_columns = _validate_object(
        value.get("donor_columns"), DONOR_COLUMNS_KEYS, f"{label}: donor_columns", errors
    )
    if donor_columns is not None:
        time_column = donor_columns.get("time")
        connector_columns = donor_columns.get("connectors")
        if not isinstance(time_column, str) or not DONOR_COLUMN_RE.fullmatch(time_column):
            errors.append(f"{label}: donor_columns.time must be an ASCII column identifier")
        if not isinstance(connector_columns, dict):
            errors.append(f"{label}: donor_columns.connectors must be an object")
        else:
            expected_ids = set(connectors)
            if set(connector_columns) != expected_ids:
                errors.append(
                    f"{label}: donor_columns.connectors keys must equal interface connector IDs"
                )
            mapped_columns = []
            for connector_id in sorted(connector_columns):
                column = connector_columns[connector_id]
                if not isinstance(column, str) or not DONOR_COLUMN_RE.fullmatch(column):
                    errors.append(
                        f"{label}: donor_columns.connectors.{connector_id} "
                        "must be an ASCII column identifier"
                    )
                else:
                    mapped_columns.append(column)
            if len(mapped_columns) != len(set(mapped_columns)):
                errors.append(f"{label}: donor_columns connector columns must be unique")
            if isinstance(time_column, str) and time_column in mapped_columns:
                errors.append(f"{label}: donor_columns.time must be distinct from connector columns")
            result["donor_columns"] = donor_columns

    artifacts = value.get("artifacts")
    seen_roles = {}
    seen_local_paths = {}
    seen_donor_paths = {}
    if not isinstance(artifacts, list):
        errors.append(f"{label}: artifacts must be an array")
    else:
        for index, artifact in enumerate(artifacts):
            prefix = f"{label}: artifacts[{index}]"
            if not isinstance(artifact, dict):
                errors.append(f"{prefix}: must be an object")
                continue
            _check_exact_keys(artifact, ARTIFACT_KEYS, prefix, errors)
            role = artifact.get("role")
            if not isinstance(role, str) or not ARTIFACT_ROLE_RE.fullmatch(role):
                errors.append(f"{prefix}.role: must be a lowercase snake-case identifier")
                continue
            if role in seen_roles:
                errors.append(f"{prefix}.role: duplicate {role!r}")
            else:
                seen_roles[role] = artifact
            local_path = artifact.get("local_path")
            donor_path = artifact.get("donor_path")
            for key, path_value in (("local_path", local_path), ("donor_path", donor_path)):
                problem = _relative_path_problem(path_value)
                if problem:
                    errors.append(f"{prefix}.{key}: {problem}")
            for key, path_value, seen in (
                ("local_path", local_path, seen_local_paths),
                ("donor_path", donor_path, seen_donor_paths),
            ):
                if isinstance(path_value, str) and _relative_path_problem(path_value) is None:
                    if path_value in seen:
                        errors.append(f"{prefix}.{key}: duplicate {path_value!r}")
                    else:
                        seen[path_value] = index
            sha256 = artifact.get("sha256")
            if not isinstance(sha256, str) or not HASH_RE.fullmatch(sha256):
                errors.append(f"{prefix}.sha256: must be lowercase 64-hex")
            if isinstance(local_path, str) and _relative_path_problem(local_path) is None:
                local_bytes = _read_artifact(bundle, local_path, f"{prefix}.local_path", errors)
                if local_bytes is not None and isinstance(sha256, str):
                    actual = hashlib.sha256(local_bytes).hexdigest()
                    if actual != sha256:
                        errors.append(f"{prefix}.sha256: does not match {local_path}")
                if (
                    donor_root is not None
                    and local_bytes is not None
                    and isinstance(donor_path, str)
                    and _relative_path_problem(donor_path) is None
                ):
                    donor_bytes = _read_artifact(
                        donor_root, donor_path, f"{prefix}.donor_path", errors
                    )
                    if donor_bytes is not None and donor_bytes != local_bytes:
                        errors.append(f"{prefix}.donor_path: donor bytes differ from {local_path}")
        required_roles = {"graph"}
        row_tier = row.get("evidence_tier")
        if row_tier in EVIDENCE_TIERS and EVIDENCE_TIERS.index(row_tier) >= 3:
            required_roles.update(("structural_oracle", "donor_reference"))
        missing_roles = required_roles - set(seen_roles)
        if missing_roles:
            errors.append(f"{label}: artifacts missing required roles {', '.join(sorted(missing_roles))}")
        if (
            row_tier in EVIDENCE_TIERS
            and EVIDENCE_TIERS.index(row_tier) >= 3
            and not any(
                role == "provenance" or role.endswith("_provenance") for role in seen_roles
            )
        ):
            errors.append(f"{label}: artifacts require at least one provenance role")
        graph_targets = [
            role
            for role, artifact in seen_roles.items()
            if artifact.get("local_path") == "routine.cxf.jsonld"
        ]
        if graph_targets != ["graph"]:
            errors.append(
                f"{label}: exactly the graph artifact must target routine.cxf.jsonld"
            )
        result["artifacts"] = {
            role: artifact.get("local_path")
            for role, artifact in seen_roles.items()
            if isinstance(artifact.get("local_path"), str)
        }

    evidence = value.get("evidence")
    tiers = []
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{label}: evidence must be a nonempty array")
    else:
        for index, item in enumerate(evidence):
            prefix = f"{label}: evidence[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix}: must be an object")
                continue
            _check_exact_keys(item, EVIDENCE_KEYS, prefix, errors)
            tier = item.get("tier")
            _check_enum(tier, EVIDENCE_TIERS, f"{prefix}.tier", errors)
            if isinstance(tier, str) and tier in EVIDENCE_TIERS:
                tiers.append(tier)
            if item.get("status") != "complete":
                errors.append(f"{prefix}.status: must be 'complete'")
            artifact_path = item.get("artifact")
            problem = _relative_path_problem(artifact_path)
            if problem:
                errors.append(f"{prefix}.artifact: {problem}")
            elif not _local_path(bundle, artifact_path).is_file():
                errors.append(f"{prefix}.artifact: file is missing")
        if tiers:
            expected_tiers = list(EVIDENCE_TIERS[: EVIDENCE_TIERS.index(max(tiers)) + 1])
            if tiers != expected_tiers:
                errors.append(f"{label}: evidence tiers must be ordered and contiguous from E0")
            else:
                result["max_tier"] = tiers[-1]

    private_reference = _validate_object(
        value.get("private_reference"),
        PRIVATE_REFERENCE_KEYS,
        f"{label}: private_reference",
        errors,
    )
    if private_reference is not None:
        if private_reference.get("profile") != profile:
            errors.append(f"{label}: private_reference.profile must equal coverage.profile")
        if private_reference.get("audit_status") != "not_used":
            errors.append(f"{label}: private_reference.audit_status must be 'not_used'")
        if private_reference.get("sections") != []:
            errors.append(f"{label}: private_reference.sections must be empty")
    return result


def _id_refs(node, key):
    value = node.get(key)
    items = value if isinstance(value, list) else [value]
    return [item.get("@id") for item in items if isinstance(item, dict) and isinstance(item.get("@id"), str)]


def _local_name(identifier, root_id):
    prefix = f"{root_id}."
    return identifier[len(prefix) :] if identifier.startswith(prefix) else None


def _cxf_number(value):
    if _is_finite_number(value):
        return float(value)
    if isinstance(value, dict) and isinstance(value.get("@value"), str):
        try:
            number = float(value["@value"])
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _validate_graph(value, label, row, connectors, provenance, errors):
    if value is None:
        return
    graph = value.get("@graph")
    if not isinstance(graph, list):
        errors.append(f"{label}: @graph must be an array")
        return
    node_ids = [
        node.get("@id")
        for node in graph
        if isinstance(node, dict) and isinstance(node.get("@id"), str)
    ]
    if len(node_ids) != len(set(node_ids)):
        errors.append(f"{label}: @graph node IDs must be unique")
    nodes = {
        node.get("@id"): node
        for node in graph
        if isinstance(node, dict) and isinstance(node.get("@id"), str)
    }
    canonical = row.get("canonical_class")
    roots = [
        node
        for node in nodes.values()
        if isinstance(node.get("@type"), str)
        and node["@type"].rsplit("#", 1)[-1] == canonical
        and "S231:hasOutput" in node
    ]
    if len(roots) != 1:
        errors.append(f"{label}: expected one root with canonical class {canonical!r}")
        return
    root = roots[0]
    root_id = root["@id"]
    declared = {}
    for direction, key, graph_type in (
        ("input", "S231:hasInput", "S231:RealInput"),
        ("output", "S231:hasOutput", "S231:RealOutput"),
    ):
        for identifier in _id_refs(root, key):
            name = _local_name(identifier, root_id)
            node = nodes.get(identifier)
            if name is None or node is None:
                errors.append(f"{label}: root {direction} {identifier!r} does not resolve")
                continue
            if name in declared:
                errors.append(f"{label}: duplicate root connector {name!r}")
            declared[name] = direction
            manifest = connectors.get(name)
            if manifest is None:
                errors.append(f"{label}: root {direction} {name!r} is absent from interface.json")
                continue
            if manifest.get("direction") != direction:
                errors.append(f"{label}: connector {name!r} direction disagrees with interface.json")
            if node.get("@type") != graph_type:
                errors.append(f"{label}: connector {name!r} must use {graph_type}")
            if node.get("S231:isOfDataType") != {"@id": "S231:Real"}:
                errors.append(f"{label}: connector {name!r} must declare S231:Real data type")
            if node.get("S231:unit") != manifest.get("unit"):
                errors.append(f"{label}: connector {name!r} unit disagrees with interface.json")
            if node.get("S231:quantity") != manifest.get("quantity"):
                errors.append(f"{label}: connector {name!r} quantity disagrees with interface.json")
    if set(declared) != set(connectors):
        errors.append(f"{label}: root connector IDs must equal interface.json")

    fixed = provenance.get("fixed_parameters", {})
    parameter_ids = _id_refs(root, "S231:hasParameter")
    parameter_values = {}
    for identifier in parameter_ids:
        name = _local_name(identifier, root_id)
        node = nodes.get(identifier)
        if name is not None and node is not None:
            if name in parameter_values:
                errors.append(f"{label}: duplicate root fixed parameter {name!r}")
            parameter_values[name] = node.get("S231:value")
    if set(parameter_values) != set(fixed):
        errors.append(f"{label}: root fixed parameters must equal provenance.json")
    else:
        for key, expected in fixed.items():
            if not _scalar_equal(parameter_values.get(key), expected):
                errors.append(f"{label}: fixed parameter {key!r} disagrees with provenance.json")

    implementation = provenance.get("implementation", {})
    block_class = implementation.get("block_class")
    block_ids = _id_refs(root, "S231:containsBlock")
    blocks = [
        nodes[identifier]
        for identifier in block_ids
        if identifier in nodes
        and isinstance(nodes[identifier].get("@type"), str)
        and nodes[identifier]["@type"].rsplit("#", 1)[-1] == block_class
    ]
    if len(blocks) != 1:
        errors.append(f"{label}: expected one fixture block matching provenance.json")
        return
    block = blocks[0]
    block_parameter_ids = _id_refs(block, "S231:hasParameter")
    block_parameters = {}
    for identifier in block_parameter_ids:
        name = _local_name(identifier, block["@id"])
        node = nodes.get(identifier)
        if name is not None and node is not None:
            if name in block_parameters:
                errors.append(f"{label}: duplicate fixture block parameter {name!r}")
            block_parameters[name] = _cxf_number(node.get("S231:value"))
    expected_parameters = implementation.get("parameters")
    if not isinstance(expected_parameters, dict) or not all(
        _is_finite_number(value) for value in expected_parameters.values()
    ):
        expected_block_parameters = None
    else:
        expected_block_parameters = {
            key: float(value) for key, value in expected_parameters.items()
        }
    if block_parameters != expected_block_parameters:
        errors.append(f"{label}: fixture block parameters disagree with provenance.json")


def _read_reference_rows(bundle, relative_path, donor_columns, connectors, label, errors):
    if not isinstance(relative_path, str) or _relative_path_problem(relative_path) is not None:
        return []
    path = _local_path(bundle, relative_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        errors.append(f"{label}: unable to read donor reference")
        return []
    column_headers = [
        line.removeprefix("# columns:").strip().split()
        for line in lines
        if line.startswith("# columns:")
    ]
    if len(column_headers) != 1 or not column_headers[0]:
        errors.append(f"{label}: must contain exactly one '# columns:' header")
        return []
    columns = column_headers[0]
    if len(columns) != len(set(columns)):
        errors.append(f"{label}: column names must be unique")
        return []
    time_column = donor_columns.get("time") if isinstance(donor_columns, dict) else None
    connector_columns = (
        donor_columns.get("connectors") if isinstance(donor_columns, dict) else None
    )
    if not isinstance(time_column, str) or not isinstance(connector_columns, dict):
        return []
    required_columns = {time_column}
    required_columns.update(
        column for column in connector_columns.values() if isinstance(column, str)
    )
    missing_columns = required_columns - set(columns)
    if missing_columns:
        errors.append(f"{label}: mapped columns are missing: {', '.join(sorted(missing_columns))}")
        return []
    if set(connector_columns) != set(connectors):
        return []
    indexes = {column: columns.index(column) for column in required_columns}
    rows = []
    for line in lines:
        if not line or line.startswith("#") or line.startswith("double "):
            continue
        fields = line.split()
        if len(fields) != len(columns):
            errors.append(f"{label}: row width must equal the '# columns:' header")
            return []
        try:
            values = [float(field) for field in fields]
        except ValueError:
            errors.append(f"{label}: donor reference contains a non-numeric row")
            return []
        if not all(math.isfinite(value) for value in values):
            errors.append(f"{label}: donor reference values must be finite")
            return []
        rows.append(
            {
                "time": values[indexes[time_column]],
                "connectors": {
                    connector_id: values[indexes[column]]
                    for connector_id, column in connector_columns.items()
                },
            }
        )
    if not rows:
        errors.append(f"{label}: donor reference has no rows")
    else:
        times = [row["time"] for row in rows]
        if times[0] < 0 or any(
            right <= left for left, right in zip(times, times[1:])
        ):
            errors.append(f"{label}: time values must be non-negative and strictly increasing")
    return rows


def _scan_private_leaks(bundle, label, errors):
    for path in sorted(candidate for candidate in bundle.rglob("*") if candidate.is_file()):
        relative = path.relative_to(bundle).as_posix()
        if path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}:
            errors.append(f"{label}/{relative}: private document, image, or local path leakage")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if PRIVATE_LEAK_RE.search(text):
            errors.append(f"{label}/{relative}: private document, image, or local path leakage")


def _validate_claim_bounds(row, provenance, label, errors):
    max_tier = provenance.get("max_tier")
    row_tier = row.get("evidence_tier")
    if max_tier in EVIDENCE_TIERS and row_tier in EVIDENCE_TIERS:
        if EVIDENCE_TIERS.index(row_tier) > EVIDENCE_TIERS.index(max_tier):
            errors.append(f"{label}: registry evidence_tier exceeds completed provenance evidence")
    status_minimum = {"ported": "E0", "engine_verified": "E1", "source_evidenced": "E3", "adopted": "E5"}
    needed = status_minimum.get(row.get("status"))
    if needed is not None and (
        max_tier not in EVIDENCE_TIERS
        or EVIDENCE_TIERS.index(max_tier) < EVIDENCE_TIERS.index(needed)
    ):
        errors.append(f"{label}: registry status exceeds completed provenance evidence")
    completeness = row.get("completeness")
    if not isinstance(completeness, dict) or max_tier not in EVIDENCE_TIERS:
        return
    required = {"donor_configuration": "E2", "canonical_class": "E3", "family_package": "E5", "guideline_profile": "E5"}
    for axis, tier in required.items():
        if completeness.get(axis) == "complete" and EVIDENCE_TIERS.index(max_tier) < EVIDENCE_TIERS.index(tier):
            errors.append(f"{label}: completeness.{axis} requires {tier} evidence")


def _validate_bundle(repo_root, row, engine_pin, donor_pin, source_pin, profile, donor_root, errors):
    relative = row.get("path")
    if not isinstance(relative, str) or _relative_path_problem(relative, "g36") is not None:
        return
    bundle = repo_root / "routines" / Path(*relative.split("/"))
    label = f"routines/{relative}"
    if not bundle.is_dir():
        errors.append(f"{label}: registered bundle directory is missing")
        return
    for required in REQUIRED_BUNDLE_FILES:
        if not (bundle / required).is_file():
            errors.append(f"{label}/{required}: required bundle file is missing")
    routine_id = row.get("id")
    if not isinstance(routine_id, str):
        return
    interface_label = f"{label}/interface.json"
    vectors_label = f"{label}/vectors.json"
    provenance_label = f"{label}/provenance.json"
    graph_label = f"{label}/routine.cxf.jsonld"
    interface = _read_json_file(bundle / "interface.json", interface_label, errors)
    vectors = _read_json_file(bundle / "vectors.json", vectors_label, errors)
    provenance_value = _read_json_file(bundle / "provenance.json", provenance_label, errors)
    graph = _read_json_file(bundle / "routine.cxf.jsonld", graph_label, errors)
    connectors = _validate_interface(interface, interface_label, routine_id, errors)
    donor_inputs, donor_outputs = _validate_vectors(
        vectors, vectors_label, routine_id, connectors, errors
    )
    provenance = _validate_provenance(
        provenance_value,
        provenance_label,
        routine_id,
        row,
        connectors,
        bundle,
        engine_pin,
        donor_pin,
        source_pin,
        profile,
        donor_root,
        errors,
    )
    if provenance.get("modelica_derived") and row.get("level") != "fragment":
        for required in ("LICENSE-BUILDINGS.html", "THIRD_PARTY_NOTICES.md"):
            if not (bundle / required).is_file():
                errors.append(f"{label}/{required}: required Modelica attribution file is missing")
    _validate_graph(graph, graph_label, row, connectors, provenance, errors)
    reference_path = provenance.get("artifacts", {}).get("donor_reference")
    reference_label = (
        f"{label}/{reference_path}" if isinstance(reference_path, str) else f"{label}: donor reference"
    )
    rows = _read_reference_rows(
        bundle,
        reference_path,
        provenance.get("donor_columns", {}),
        connectors,
        reference_label,
        errors,
    )
    if rows:
        for connector_id, connector in sorted(connectors.items()):
            expected = [(row["time"], row["connectors"][connector_id]) for row in rows]
            if connector.get("direction") == "input":
                actual = donor_inputs.get(connector_id, [])
                kind = "input steps"
            else:
                actual = donor_outputs.get(connector_id, [])
                kind = "zero-tolerance output expectations"
            if actual != expected:
                errors.append(
                    f"{vectors_label}: {connector_id} {kind} must cover every donor reference row exactly"
                )
    card_path = bundle / "card.md"
    try:
        card = card_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        card = ""
    if card and "diagram.svg" not in card:
        errors.append(f"{label}/card.md: must reference diagram.svg")
    _scan_private_leaks(bundle, label, errors)
    _validate_claim_bounds(row, provenance, label, errors)


def _validate(repo_root, donor_root=None):
    repo_root = Path(repo_root)
    donor_root = Path(donor_root) if donor_root is not None else None
    errors = []
    registry = _read_json(repo_root, REGISTRY_PATH, errors)
    coverage = _read_json(repo_root, COVERAGE_PATH, errors)
    source_pin = _read_pin(repo_root, SOURCE_PIN_PATH, errors)
    donor_pin = _read_pin(repo_root, DONOR_PIN_PATH, errors)
    engine_pin = _read_pin(repo_root, Path("ENGINE_PIN"), errors)

    profile = coverage.get("profile") if isinstance(coverage, dict) else None
    registry_rows = None
    if registry is not None:
        _check_exact_keys(registry, REGISTRY_KEYS, REGISTRY_PATH.as_posix(), errors)
        if registry.get("schema") != "cxf-library/routine-registry/v1":
            errors.append(f"{REGISTRY_PATH.as_posix()}: schema must be 'cxf-library/routine-registry/v1'")
        rows = registry.get("routines")
        if not isinstance(rows, list):
            errors.append(f"{REGISTRY_PATH.as_posix()}: routines must be an array")
        else:
            registry_rows = rows
            seen_ids = {}
            seen_paths = {}
            for index, row in enumerate(rows):
                _validate_row(row, index, errors, seen_ids, seen_paths)
            ids = [row.get("id") for row in rows if isinstance(row, dict)]
            if len(ids) == len(rows) and all(isinstance(value, str) for value in ids):
                string_ids = [value for value in ids if isinstance(value, str)]
                if string_ids != sorted(string_ids):
                    errors.append(f"{REGISTRY_PATH.as_posix()}: routines must be sorted by id")

    if coverage is not None:
        _check_exact_keys(coverage, COVERAGE_KEYS, COVERAGE_PATH.as_posix(), errors)
        if coverage.get("schema") != "cxf-library/g36-coverage/v1":
            errors.append(f"{COVERAGE_PATH.as_posix()}: schema must be 'cxf-library/g36-coverage/v1'")
        if not isinstance(profile, str) or not profile.strip():
            errors.append(f"{COVERAGE_PATH.as_posix()}: profile must be a nonempty string")
        completeness = coverage.get("completeness")
        _check_completeness(completeness, f"{COVERAGE_PATH.as_posix()}: completeness", errors)
        for key in ("areas", "claims"):
            value = coverage.get(key)
            if not isinstance(value, list):
                errors.append(f"{COVERAGE_PATH.as_posix()}: {key} must be an array")
            elif value:
                errors.append(f"{COVERAGE_PATH.as_posix()}: {key} must be empty in v1")
        if registry_rows == [] and isinstance(completeness, dict):
            for key in sorted(COMPLETENESS_KEYS & set(completeness)):
                if completeness[key] != "unknown":
                    errors.append(
                        f"{COVERAGE_PATH.as_posix()}: completeness.{key} must be "
                        "'unknown' while the registry is empty"
                    )
        if registry_rows and isinstance(completeness, dict):
            for key in sorted(COMPLETENESS_KEYS):
                if completeness.get(key) != "complete":
                    continue
                applicable_values = []
                for row in registry_rows:
                    row_completeness = (
                        row.get("completeness") if isinstance(row, dict) else None
                    )
                    if (
                        isinstance(row_completeness, dict)
                        and row_completeness.get(key) != "not_applicable"
                    ):
                        applicable_values.append(row_completeness.get(key))
                if not applicable_values or any(
                    value != "complete" for value in applicable_values
                ):
                    errors.append(
                        f"{COVERAGE_PATH.as_posix()}: completeness.{key} cannot be 'complete' "
                        "unless every applicable registry row is complete"
                    )

    registered_paths = set()
    if registry_rows is not None:
        for row in registry_rows:
            if isinstance(row, dict) and isinstance(row.get("path"), str):
                path = row["path"]
                if _relative_path_problem(path, "g36") is None:
                    registered_paths.add(path)
                    _validate_bundle(
                        repo_root,
                        row,
                        engine_pin,
                        donor_pin,
                        source_pin,
                        profile,
                        donor_root,
                        errors,
                    )
    g36_root = repo_root / "routines" / "g36"
    if g36_root.is_dir():
        for graph_path in sorted(g36_root.rglob("routine.cxf.jsonld")):
            bundle_path = graph_path.parent.relative_to(repo_root / "routines").as_posix()
            if bundle_path not in registered_paths:
                errors.append(f"routines/{bundle_path}: bundle has no registry row")
    return sorted(errors), len(registry_rows) if registry_rows is not None else 0


def validate(repo_root=REPO_ROOT, donor_root=None):
    """Return deterministic validation errors for a repository root."""
    return _validate(repo_root, donor_root)[0]


def main(repo_root=REPO_ROOT, argv=None):
    args = [] if argv is None else list(argv)
    donor_root = None
    if args:
        if len(args) != 2 or args[0] != "--donor-root":
            print("usage: routines.py [--donor-root <open-control-checkout>]")
            return 2
        donor_root = Path(args[1])
    errors, routine_count = _validate(repo_root, donor_root)
    if errors:
        print("\n".join(errors))
        return 1
    suffix = " (donor parity checked)" if donor_root is not None else ""
    print(f"routine catalog lint: {routine_count} routines OK{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(argv=sys.argv[1:]))
