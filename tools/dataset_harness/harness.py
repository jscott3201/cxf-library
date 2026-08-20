#!/usr/bin/env python3
"""Offline external-dataset inspection and CXF replay CLI."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.dataset_harness.adapters import ADAPTERS  # noqa: E402
from tools.dataset_harness.adapters.lbl_fpu import (  # noqa: E402
    DatasetError,
    KNOWN_RULES,
    LoadedCase,
    conversion_description,
)


RESULT_SCHEMA = "cxf-library/dataset-validation/v1"
TRACE_SCHEMA = "cxf-library/replay-trace/v1"
ENGINE_PIN = (REPO / "ENGINE_PIN").read_text().strip()
MAX_TRACE_SCENARIOS = 512
MAX_TRACE_SAMPLES = 1_000_000
MAX_TRACE_STDOUT_BYTES = 256 * 1024 * 1024
MAX_TRACE_STDERR_BYTES = 2 * 1024 * 1024
TRACE_TIMEOUT_S = 300
CONTENT_ID_PATTERN = re.compile(r'content_id:\s*"(cxf:[^"]+)"')


def parse_datetime_bound(value: str | None, *, end: bool = False) -> datetime | None:
    if value is None:
        return None
    if len(value) == 10:
        try:
            parsed_date = datetime.fromisoformat(value).date()
        except ValueError as exc:
            raise DatasetError(f"invalid date selector {value!r}; use YYYY-MM-DD") from exc
        return datetime.combine(parsed_date, time.max if end else time.min, tzinfo=timezone.utc)
    candidate = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise DatasetError(f"invalid date/time selector {value!r}; use YYYY-MM-DD or ISO-8601 with offset") from exc
    if parsed.tzinfo is None:
        raise DatasetError(f"date/time selector {value!r} must include an offset")
    return parsed


def parse_rules(value: str | None) -> list[str]:
    rules = list(KNOWN_RULES) if not value else [item.strip().upper() for item in value.split(",") if item.strip()]
    unknown = sorted(set(rules) - set(KNOWN_RULES))
    if unknown:
        raise DatasetError(f"unknown or unsupported rule ids: {unknown}")
    if len(rules) != len(set(rules)):
        raise DatasetError("rule selection contains duplicates")
    return rules


def rule_inputs(rule: str) -> list[str]:
    path = REPO / "faults" / "fpb" / rule / "rule.cxf.jsonld"
    if not path.is_file():
        raise DatasetError(f"missing committed rule graph {path}")
    document = json.loads(path.read_text())
    roots = [node for node in document.get("@graph", []) if node.get("@type") == "S231:Block"]
    if len(roots) != 1:
        raise DatasetError(f"{rule}: graph must contain exactly one root S231:Block")
    declared = roots[0].get("S231:hasInput", [])
    if isinstance(declared, dict):
        declared = [declared]
    inputs: list[str] = []
    for reference in declared:
        path_value = reference.get("@id")
        if not isinstance(path_value, str) or "." not in path_value:
            raise DatasetError(f"{rule}: malformed boundary input reference {reference!r}")
        inputs.append(path_value.rsplit(".", 1)[1])
    return inputs


def recorded_rule_content_id(rule: str) -> str:
    card = REPO / "faults" / "fpb" / rule / "card.md"
    match = CONTENT_ID_PATTERN.search(card.read_text())
    if not match:
        raise DatasetError(f"{rule}: card lacks a recorded verified content id")
    return match.group(1)


def compress_series(values: list[Any], step_s: int) -> Any:
    if all(value == values[0] for value in values):
        return values[0]
    steps: list[dict[str, Any]] = []
    sentinel = object()
    previous: Any = sentinel
    for index, value in enumerate(values):
        if value != previous:
            steps.append({"t": index * step_s, "value": value})
            previous = value
    return steps


def vectors_for_segments(loaded: LoadedCase, inputs: list[str], segments: list[tuple[int, list[int]]]) -> dict[str, Any]:
    if not segments:
        raise DatasetError("internal error: cannot build vectors for an empty segment group")
    lengths = {len(indices) for _, indices in segments}
    if len(lengths) != 1:
        raise DatasetError("internal error: a vector group must contain equal-length segments")
    length = lengths.pop()
    scenarios = []
    for segment_number, indices in segments:
        scenarios.append(
            {
                "name": f"{loaded.spec.case_id}__segment_{segment_number:04d}",
                "description": "Temporary gated external-dataset replay window",
                "inputs": {
                    point: compress_series([loaded.rows[index][point] for index in indices], loaded.spec.step_s)
                    for point in inputs
                },
                "expect": [],
            }
        )
    return {
        "schema": "cxf-library/vectors/v1",
        "clock": {"step_s": loaded.spec.step_s, "horizon_s": (length - 1) * loaded.spec.step_s},
        "scenarios": scenarios,
    }


def verifier_command(verifier: Path | None, rule_dir: Path, vectors_path: Path) -> list[str]:
    if verifier:
        resolved = verifier.resolve()
        prefix = [sys.executable, str(resolved)] if resolved.suffix == ".py" else [str(resolved)]
        return [*prefix, "--trace-json", str(rule_dir), str(vectors_path)]
    binary = REPO / "tools" / "verify" / "target" / "debug" / "cxf-verify"
    verifier_sources = [
        REPO / "tools" / "verify" / "Cargo.toml",
        REPO / "tools" / "verify" / "Cargo.lock",
        REPO / "tools" / "verify" / "build.rs",
        REPO / "tools" / "verify" / "src" / "main.rs",
        REPO / "ENGINE_PIN",
    ]
    if binary.is_file() and binary.stat().st_mtime >= max(path.stat().st_mtime for path in verifier_sources):
        return [str(binary), "--trace-json", str(rule_dir), str(vectors_path)]
    return [
        "cargo",
        "run",
        "--quiet",
        "--offline",
        "--manifest-path",
        str(REPO / "tools" / "verify" / "Cargo.toml"),
        "--",
        "--trace-json",
        str(rule_dir),
        str(vectors_path),
    ]


def run_trace(verifier: Path | None, rule: str, vectors_path: Path) -> dict[str, Any]:
    command = verifier_command(verifier, REPO / "faults" / "fpb" / rule, vectors_path)
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            completed = subprocess.run(
                command,
                cwd=REPO,
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=TRACE_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DatasetError(f"{rule}: verifier trace exceeded {TRACE_TIMEOUT_S}s timeout") from exc
        stdout_size = stdout_file.seek(0, 2)
        stderr_size = stderr_file.seek(0, 2)
        if stdout_size > MAX_TRACE_STDOUT_BYTES:
            raise DatasetError(f"{rule}: verifier trace exceeded the {MAX_TRACE_STDOUT_BYTES}-byte stdout limit")
        if stderr_size > MAX_TRACE_STDERR_BYTES:
            raise DatasetError(f"{rule}: verifier trace exceeded the {MAX_TRACE_STDERR_BYTES}-byte stderr limit")
        stdout_file.seek(0)
        stderr_file.seek(0)
        try:
            stdout = stdout_file.read().decode("utf-8")
            stderr = stderr_file.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DatasetError(f"{rule}: verifier trace output is not UTF-8") from exc
    if completed.returncode != 0:
        detail = stderr.strip() or stdout.strip()
        raise DatasetError(f"{rule}: verifier trace failed with exit {completed.returncode}: {detail[-2000:]}")
    try:
        trace = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise DatasetError(f"{rule}: verifier returned non-JSON trace output") from exc
    if not isinstance(trace, dict):
        raise DatasetError(f"{rule}: verifier trace root must be an object")
    if trace.get("schema") != TRACE_SCHEMA:
        raise DatasetError(f"{rule}: verifier returned unsupported trace schema {trace.get('schema')!r}")
    if trace.get("engine_pin") != ENGINE_PIN:
        raise DatasetError(
            f"{rule}: verifier engine pin {trace.get('engine_pin')!r} does not match repository ENGINE_PIN {ENGINE_PIN}"
        )
    if trace.get("engine_source_revision") != ENGINE_PIN:
        raise DatasetError(
            f"{rule}: verifier was built from engine revision {trace.get('engine_source_revision')!r}, expected {ENGINE_PIN}"
        )
    if not isinstance(trace.get("rule_content_id"), str) or not trace["rule_content_id"].startswith("cxf:"):
        raise DatasetError(f"{rule}: verifier trace lacks a valid rule content id")
    expected_content_id = recorded_rule_content_id(rule)
    if trace["rule_content_id"] != expected_content_id:
        raise DatasetError(
            f"{rule}: verifier content id {trace['rule_content_id']!r} does not match card {expected_content_id!r}"
        )
    clock = trace.get("clock")
    if not isinstance(clock, dict):
        raise DatasetError(f"{rule}: verifier trace clock must be an object")
    step_s = clock.get("step_s")
    if isinstance(step_s, bool) or not isinstance(step_s, (int, float)) or not math.isfinite(step_s) or step_s <= 0:
        raise DatasetError(f"{rule}: verifier trace step_s must be a finite positive number")
    return trace


def _episode_count(values: list[bool], segment_starts: set[int]) -> int:
    episodes = 0
    previous = False
    for index, value in enumerate(values):
        if index in segment_starts:
            previous = False
        if value and not previous:
            episodes += 1
        previous = value
    return episodes


def replay_case_rule(
    loaded: LoadedCase,
    rule: str,
    temp_root: Path,
    verifier: Path | None,
) -> dict[str, Any]:
    inputs = rule_inputs(rule)
    missing_inputs = sorted(set(inputs) - set(loaded.spec.mappings))
    segments = [] if missing_inputs else loaded.evaluable_segments(rule, inputs)
    mapping = loaded.mapping_report(inputs)
    definitions = [
        {
            "name": gate.name,
            "source_column": gate.column,
            "description": gate.description,
            "applies_to": list(gate.applies_to),
            "inventory_evidence": gate.inventory_evidence,
            "proxy": gate.proxy,
            "derived_from": list(gate.derived_from),
        }
        for gate in loaded.spec.gates.values()
        if "*" in gate.applies_to or rule in gate.applies_to
    ]
    notes: list[str] = []
    if missing_inputs:
        notes.append(f"NO_EVAL: missing canonical inputs {missing_inputs}")
    if loaded.timeline["missing_intervals"]:
        notes.append("Source gaps split evaluator state; no interpolation was performed")
    if loaded.spec.label == "faulted" and rule not in loaded.spec.expected_rules:
        notes.append("Fault inventory does not label this rule as a target; alarm behavior is not counted as TPR")
    if loaded.spec.label == "faulted" and rule in loaded.spec.expected_rules:
        notes.append("TPR and latency use only evaluable samples at or after the manifest fault_start")

    fault_values: list[bool] = []
    sample_timestamps: list[datetime] = []
    segment_starts: set[int] = set()
    segment_traces: dict[int, list[tuple[datetime, bool]]] = {}
    trace_identity: tuple[str, str] | None = None
    by_length: dict[int, list[tuple[int, list[int]]]] = defaultdict(list)
    for segment_number, indices in enumerate(segments, start=1):
        by_length[len(indices)].append((segment_number, indices))
    for length, group in sorted(by_length.items()):
        max_batch = min(MAX_TRACE_SCENARIOS, max(1, MAX_TRACE_SAMPLES // length))
        for batch_number, offset in enumerate(range(0, len(group), max_batch), start=1):
            batch = group[offset : offset + max_batch]
            vectors = vectors_for_segments(loaded, inputs, batch)
            vectors_path = temp_root / f"{loaded.spec.case_id}__{rule}__{length}__{batch_number:04d}.json"
            vectors_path.write_text(json.dumps(vectors, indent=2, sort_keys=True) + "\n")
            trace = run_trace(verifier, rule, vectors_path)
            identity = (trace["engine_source_revision"], trace["rule_content_id"])
            if trace_identity is not None and identity != trace_identity:
                raise DatasetError(f"{rule}: verifier execution identity changed between replay windows")
            trace_identity = identity
            if trace["clock"]["step_s"] != loaded.spec.step_s:
                raise DatasetError(f"{rule}: verifier trace cadence does not match source cadence")
            raw_scenarios = trace.get("scenarios")
            if not isinstance(raw_scenarios, list) or not all(
                isinstance(scenario, dict) and isinstance(scenario.get("name"), str) for scenario in raw_scenarios
            ):
                raise DatasetError(f"{rule}: verifier trace scenarios are malformed")
            trace_by_name = {scenario["name"]: scenario for scenario in raw_scenarios}
            expected_names = {f"{loaded.spec.case_id}__segment_{number:04d}" for number, _ in batch}
            if set(trace_by_name) != expected_names or len(trace_by_name) != len(raw_scenarios):
                raise DatasetError(f"{rule}: verifier trace scenario identity does not match requested vectors")
            for segment_number, indices in batch:
                name = f"{loaded.spec.case_id}__segment_{segment_number:04d}"
                scenario = trace_by_name.get(name)
                if not scenario:
                    raise DatasetError(f"{rule}: verifier trace omitted scenario {name}")
                samples = scenario.get("samples")
                if not isinstance(samples, list):
                    raise DatasetError(f"{rule}: verifier trace samples must be a list")
                if len(samples) != len(indices):
                    raise DatasetError(f"{rule}: verifier returned {len(samples)} samples for {len(indices)} source rows")
                values: list[tuple[datetime, bool]] = []
                for sample_number, (sample, source_index) in enumerate(zip(samples, indices)):
                    if not isinstance(sample, dict):
                        raise DatasetError(f"{rule}: verifier trace sample must be an object")
                    sample_time = sample.get("t")
                    if (
                        isinstance(sample_time, bool)
                        or not isinstance(sample_time, (int, float))
                        or not math.isfinite(sample_time)
                        or sample_time != sample_number * loaded.spec.step_s
                    ):
                        raise DatasetError(f"{rule}: verifier trace timestamp does not match requested cadence")
                    outputs = sample.get("outputs")
                    if not isinstance(outputs, dict):
                        raise DatasetError(f"{rule}: verifier trace outputs must be an object")
                    value = outputs.get("yFault")
                    if not isinstance(value, bool):
                        raise DatasetError(f"{rule}: trace sample lacks Boolean yFault")
                    values.append((loaded.timestamps[source_index], value))
                segment_traces[segment_number] = values

    for segment_number in sorted(segment_traces):
        segment_starts.add(len(fault_values))
        for timestamp, value in segment_traces[segment_number]:
            sample_timestamps.append(timestamp)
            fault_values.append(value)

    alarm_samples = sum(fault_values)
    episodes = _episode_count(fault_values, segment_starts)
    is_target_fault = loaded.spec.label == "faulted" and rule in loaded.spec.expected_rules
    post_fault = [
        (timestamp, value)
        for timestamp, value in zip(sample_timestamps, fault_values)
        if loaded.spec.fault_start is not None and timestamp >= loaded.spec.fault_start
    ] if is_target_fault else []
    target_alarm_samples = sum(value for _, value in post_fault)
    target_alarm_onsets: list[datetime] = []
    previous = False
    for index, (timestamp, value) in enumerate(zip(sample_timestamps, fault_values)):
        if index in segment_starts:
            previous = False
        if (
            is_target_fault
            and loaded.spec.fault_start is not None
            and timestamp >= loaded.spec.fault_start
            and value
            and not previous
        ):
            target_alarm_onsets.append(timestamp)
        previous = value
    detected = bool(target_alarm_onsets)
    latency: float | None = None
    if detected and loaded.spec.fault_start is not None:
        first_alarm = min(target_alarm_onsets)
        latency = (first_alarm - loaded.spec.fault_start).total_seconds()
    target_pair_evaluable = int(is_target_fault and bool(post_fault))
    metrics = {
        "evaluable_samples": len(fault_values),
        "alarm_samples": alarm_samples,
        "alarm_episodes": episodes,
        "fault_free_alarm_samples": alarm_samples if loaded.spec.label == "fault_free" else 0,
        "fault_free_alarm_episodes": episodes if loaded.spec.label == "fault_free" else 0,
        "fault_free_evaluable_samples": len(fault_values) if loaded.spec.label == "fault_free" else 0,
        "fault_free_alarm_sample_rate": (
            alarm_samples / len(fault_values) if loaded.spec.label == "fault_free" and fault_values else None
        ),
        "target_post_fault_evaluable_samples": len(post_fault),
        "target_post_fault_alarm_samples": target_alarm_samples,
        "target_post_fault_alarm_episodes": len(target_alarm_onsets),
        "target_declared_rule_case_pairs": int(is_target_fault),
        "target_detected_rule_case_pairs": int(detected),
        "target_evaluable_rule_case_pairs": target_pair_evaluable,
        "median_detection_latency_s": latency,
    }
    return {
        "case": loaded.spec.case_id,
        "rule": rule,
        "subtype": loaded.spec.subtype,
        "label": loaded.spec.label,
        "inventory_evidence": loaded.spec.inventory_evidence,
        "fault_class": loaded.spec.fault_class,
        "severity": loaded.spec.severity,
        "mapping": mapping,
        "gating": {
            "description": "Logical AND of the listed rule-applicable host gates plus point validity; evaluator state resets across invalid windows",
            "definitions": definitions,
            "startup_lead_s": loaded.spec.startup_lead_s,
            "evaluable_samples": len(fault_values),
            "segments": len(segments),
            "source_timeline": loaded.timeline,
        },
        "metrics": metrics,
        "notes": notes,
        "_execution": {
            "engine_source_revision": trace_identity[0] if trace_identity else None,
            "rule_content_id": trace_identity[1] if trace_identity else None,
            "graph_sha256": "sha256:"
            + hashlib.sha256((REPO / "faults" / "fpb" / rule / "rule.cxf.jsonld").read_bytes()).hexdigest(),
            "card_sha256": "sha256:"
            + hashlib.sha256((REPO / "faults" / "fpb" / rule / "card.md").read_bytes()).hexdigest(),
        },
    }


def selected_cases(adapter: Any, args: argparse.Namespace) -> list[Any]:
    case_ids = None
    if getattr(args, "case", None):
        tokens = [item.strip() for item in args.case.split(",")]
        if any(not token for token in tokens):
            raise DatasetError("case selection contains an empty id")
        if len(tokens) != len(set(tokens)):
            raise DatasetError("case selection contains duplicates")
        case_ids = set(tokens)
    label = getattr(args, "case_kind", None)
    label = label.replace("-", "_") if label else None
    return adapter.select_cases(
        subtype=getattr(args, "subtype", None),
        label=label,
        severity=getattr(args, "severity", None),
        case_ids=case_ids,
    )


def print_inspection_header(adapter: Any) -> None:
    print(f"adapter: {adapter.slug}/{adapter.version}")
    print(f"dataset: {adapter.name} (DOI {adapter.doi})")


def print_case_inspection(loaded: LoadedCase, rules: list[str]) -> None:
    timeline = loaded.timeline
    print(
        f"case {loaded.spec.case_id}: subtype={loaded.spec.subtype} label={loaded.spec.label} "
        f"severity={loaded.spec.severity or '-'} rows={timeline['rows']} "
        f"duplicates={timeline['duplicates']} out_of_order={timeline['out_of_order']} "
        f"missing_intervals={len(timeline['missing_intervals'])} "
        f"irregular_intervals={timeline['irregular_intervals']} dropped_rows={timeline['dropped_rows']}"
    )
    print(f"  case inventory evidence: {loaded.spec.inventory_evidence}")
    for point, binding in sorted(loaded.spec.mappings.items()):
        conversion = conversion_description(binding.source_unit, binding.target_unit)
        print(
            f"  mapping {point}: column={binding.column!r}; kind={binding.kind}; "
            f"units={binding.source_unit}->{binding.target_unit}; conversion={conversion}; "
            f"inventory_evidence={binding.inventory_evidence!r}"
        )
        if binding.proxy:
            print(f"    proxy: {binding.proxy}")
        if binding.readiness:
            print(f"    readiness: {json.dumps(binding.readiness, sort_keys=True)}")
        if binding.independent is not None or binding.derived_from:
            print(
                f"    independent={binding.independent}; evidence={binding.independence_evidence!r}; "
                f"derived_from={list(binding.derived_from)}"
            )
    for gate in sorted(loaded.spec.gates.values(), key=lambda item: item.name):
        print(
            f"  gate {gate.name}: column={gate.column!r}; applies_to={list(gate.applies_to)}; "
            f"description={gate.description!r}; inventory_evidence={gate.inventory_evidence!r}; "
            f"proxy={gate.proxy!r}; derived_from={list(gate.derived_from)}"
        )
    for rule in rules:
        inputs = rule_inputs(rule)
        missing = sorted(set(inputs) - set(loaded.spec.mappings))
        segments = [] if missing else loaded.evaluable_segments(rule, inputs)
        samples = sum(len(segment) for segment in segments)
        proxy_points = [
            point for point in inputs if point in loaded.spec.mappings and loaded.spec.mappings[point].proxy
        ]
        state = "NO_EVAL" if missing or not samples else "evaluable"
        print(
            f"  {rule}: {state}; samples={samples}; segments={len(segments)}; "
            f"missing={missing or '-'}; proxies={proxy_points or '-'}"
        )


def command_inspect(args: argparse.Namespace) -> int:
    adapter = ADAPTERS[args.adapter](args.dataset)
    rules = parse_rules(args.rules)
    cases = selected_cases(adapter, args)
    start = parse_datetime_bound(getattr(args, "start", None))
    end = parse_datetime_bound(getattr(args, "end", None), end=True)
    print_inspection_header(adapter)
    bad = False
    for case in cases:
        loaded = adapter.load_case(case, start=start, end=end, strict_timeline=False)
        print_case_inspection(loaded, rules)
        bad = bad or bool(
            loaded.timeline["duplicates"]
            or loaded.timeline["out_of_order"]
            or loaded.timeline["irregular_intervals"]
        )
    if bad:
        print("replay status: blocked by duplicate/out-of-order/irregular timestamps")
    return 0


def command_replay(args: argparse.Namespace) -> int:
    adapter = ADAPTERS[args.adapter](args.dataset)
    rules = parse_rules(args.rules)
    cases = selected_cases(adapter, args)
    start = parse_datetime_bound(getattr(args, "start", None))
    end = parse_datetime_bound(getattr(args, "end", None), end=True)
    output = args.output.resolve()
    protected_roots = [
        adapter.root,
        REPO / "faults",
        REPO / "points",
        REPO / "playbooks",
        REPO / "clusters",
        REPO / "tools" / "dataset_harness" / "tests" / "fixtures",
    ]
    repository_target = (REPO / "target").resolve()
    repository_root = REPO.resolve()
    if (output == repository_root or repository_root in output.parents) and (
        output != repository_target and repository_target not in output.parents
    ):
        raise DatasetError("replay output inside the repository must stay under the ignored target/ directory")
    for protected in (path.resolve() for path in protected_roots):
        if output == protected or protected in output.parents:
            raise DatasetError(f"refusing to write replay output inside protected source/artifact tree {protected}")
    if output.exists() and not output.is_file():
        raise DatasetError(f"replay output must be a file path, not a directory: {output}")
    dataset_fingerprint = adapter.fingerprint(cases)
    output.parent.mkdir(parents=True, exist_ok=True)
    print_inspection_header(adapter)
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=".dataset-harness-", dir=output.parent) as temporary:
        temp_root = Path(temporary)
        for case in cases:
            loaded = adapter.load_case(case, start=start, end=end, strict_timeline=True)
            print_case_inspection(loaded, rules)
            results.extend(replay_case_rule(loaded, rule, temp_root, args.verifier) for rule in rules)

    rule_identities: dict[str, dict[str, Any]] = {}
    engine_source_revisions: set[str] = set()
    for result in results:
        identity = result.pop("_execution")
        rule = result["rule"]
        if identity["engine_source_revision"] is not None:
            engine_source_revisions.add(identity["engine_source_revision"])
        existing = rule_identities.get(rule)
        if existing is None:
            rule_identities[rule] = identity
            continue
        if existing["graph_sha256"] != identity["graph_sha256"] or existing["card_sha256"] != identity["card_sha256"]:
            raise DatasetError(f"{rule}: graph/card identity changed between selected cases")
        for field in ("engine_source_revision", "rule_content_id"):
            if existing[field] is not None and identity[field] is not None and existing[field] != identity[field]:
                raise DatasetError(f"{rule}: {field} changed between selected cases")
            if existing[field] is None:
                existing[field] = identity[field]
    if len(engine_source_revisions) > 1:
        raise DatasetError("verifier engine revision changed during replay")
    if adapter.fingerprint(cases) != dataset_fingerprint:
        raise DatasetError("dataset or manifest changed during replay; discard mixed-source results and rerun")

    latencies = [
        result["metrics"]["median_detection_latency_s"]
        for result in results
        if result["metrics"]["median_detection_latency_s"] is not None
    ]
    fault_free_evaluable = sum(result["metrics"]["fault_free_evaluable_samples"] for result in results)
    fault_free_alarms = sum(result["metrics"]["fault_free_alarm_samples"] for result in results)
    target_evaluable_pairs = sum(result["metrics"]["target_evaluable_rule_case_pairs"] for result in results)
    target_detected_pairs = sum(result["metrics"]["target_detected_rule_case_pairs"] for result in results)
    target_declared_pairs = sum(result["metrics"]["target_declared_rule_case_pairs"] for result in results)
    git_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=False
    )
    if git_revision.returncode != 0:
        raise DatasetError(f"cannot identify library revision: {git_revision.stderr.strip()}")
    git_status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if git_status.returncode != 0:
        raise DatasetError(f"cannot identify library worktree state: {git_status.stderr.strip()}")
    verifier_path = (
        args.verifier.resolve()
        if args.verifier
        else REPO / "tools" / "verify" / "target" / "debug" / "cxf-verify"
    )
    repository_verifier = (REPO / "tools" / "verify" / "target" / "debug" / "cxf-verify").resolve()
    verifier_mode = (
        "repository-default"
        if not args.verifier
        else "repository-binary"
        if verifier_path == repository_verifier
        else "explicit-untrusted"
    )
    verifier_sha256 = (
        "sha256:" + hashlib.sha256(verifier_path.read_bytes()).hexdigest()
        if verifier_path.is_file() and engine_source_revisions
        else None
    )
    document = {
        "schema": RESULT_SCHEMA,
        "adapter": f"{adapter.slug}/{adapter.version}",
        "execution": {
            "library_git_revision": git_revision.stdout.strip(),
            "library_git_dirty": bool(git_status.stdout.strip()),
            "engine_pin": ENGINE_PIN,
            "engine_source_revisions": sorted(engine_source_revisions),
            "verifier": {
                "mode": verifier_mode,
                "path": str(verifier_path),
                "sha256": verifier_sha256,
            },
            "tool_sha256": {
                path.relative_to(REPO).as_posix(): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                for path in [
                    REPO / "tools" / "dataset_harness" / "harness.py",
                    REPO / "tools" / "dataset_harness" / "adapters" / "lbl_fpu.py",
                    REPO / "tools" / "dataset_harness" / "result.schema.json",
                ]
            },
            "point_dictionary_sha256": "sha256:"
            + hashlib.sha256((REPO / "points" / "fpb.points.json").read_bytes()).hexdigest(),
            "rules": rule_identities,
        },
        "dataset": {
            "name": adapter.name,
            "doi": adapter.doi,
            "inventory": adapter.manifest["dataset"]["inventory"],
            "version": adapter.manifest["dataset"]["version"],
            "local_fingerprint": dataset_fingerprint,
            "cases": len(cases),
        },
        "selection": {
            "rules": rules,
            "cases": [case.case_id for case in cases],
            "subtype": args.subtype,
            "case_kind": args.case_kind,
            "severity": args.severity,
            "start": args.start,
            "end": args.end,
        },
        "summary": {
            "results": len(results),
            "evaluable_samples": sum(result["metrics"]["evaluable_samples"] for result in results),
            "fault_free_evaluable_samples": fault_free_evaluable,
            "fault_free_alarm_samples": fault_free_alarms,
            "fault_free_alarm_episodes": sum(result["metrics"]["fault_free_alarm_episodes"] for result in results),
            "fault_free_alarm_sample_rate": (
                fault_free_alarms / fault_free_evaluable if fault_free_evaluable else None
            ),
            "target_detected_rule_case_pairs": target_detected_pairs,
            "target_evaluable_rule_case_pairs": target_evaluable_pairs,
            "target_declared_rule_case_pairs": target_declared_pairs,
            "target_detection_rate": (
                target_detected_pairs / target_evaluable_pairs if target_evaluable_pairs else None
            ),
            "median_detection_latency_s": statistics.median(latencies) if latencies else None,
        },
        "results": results,
        "notes": [
            "Rates use fault-free evaluable samples, never all source rows, as the denominator.",
            "Target detection rates count inventory-labeled rule-case pairs with post-fault evaluable samples.",
            "This result is dataset- and mapping-specific evidence, not a field-performance guarantee.",
        ],
    }
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(f"wrote {output}")
    return 0


def add_selectors(parser: argparse.ArgumentParser, *, rules: bool) -> None:
    parser.add_argument("--adapter", choices=sorted(ADAPTERS), required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    if rules:
        parser.add_argument("--rules", help="comma-separated rule ids; defaults to FPB-0001..FPB-0006")
    else:
        parser.add_argument("--rules", help="optional comma-separated rules for the inspection report")
    parser.add_argument("--case", help="comma-separated case ids")
    parser.add_argument("--subtype", choices=["parallel", "series"])
    parser.add_argument("--case-kind", choices=["fault-free", "faulted"])
    parser.add_argument("--severity")
    parser.add_argument("--start", help="inclusive YYYY-MM-DD or ISO-8601 timestamp")
    parser.add_argument("--end", help="inclusive YYYY-MM-DD or ISO-8601 timestamp")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-adapters", help="list offline adapters")
    inspect_parser = subparsers.add_parser("inspect", help="validate inventory mappings and evaluability")
    add_selectors(inspect_parser, rules=False)
    replay_parser = subparsers.add_parser("replay", help="replay committed CXF rules through the existing engine")
    add_selectors(replay_parser, rules=True)
    replay_parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "target" / "dataset-harness" / "lbl-fpu-results.json",
    )
    replay_parser.add_argument("--verifier", type=Path, help="prebuilt cxf-verify binary or test double")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list-adapters":
            for slug, adapter in sorted(ADAPTERS.items()):
                print(f"{slug}/{adapter.version}\t{adapter.description}")
            return 0
        if args.command == "inspect":
            return command_inspect(args)
        return command_replay(args)
    except (DatasetError, OSError, UnicodeError, csv.Error, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
