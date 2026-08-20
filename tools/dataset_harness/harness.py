#!/usr/bin/env python3
"""Offline external-dataset inspection and CXF replay CLI."""

from __future__ import annotations

import argparse
import json
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
from tools.dataset_harness.adapters.lbl_fpu import DatasetError, KNOWN_RULES, LoadedCase  # noqa: E402


RESULT_SCHEMA = "cxf-library/dataset-validation/v1"
TRACE_SCHEMA = "cxf-library/replay-trace/v1"


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
        REPO / "tools" / "verify" / "src" / "main.rs",
        REPO / "ENGINE_PIN",
    ]
    if binary.is_file() and binary.stat().st_mtime >= max(path.stat().st_mtime for path in verifier_sources):
        return [str(binary), "--trace-json", str(rule_dir), str(vectors_path)]
    return [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(REPO / "tools" / "verify" / "Cargo.toml"),
        "--",
        "--trace-json",
        str(rule_dir),
        str(vectors_path),
    ]


def run_trace(verifier: Path | None, rule: str, vectors_path: Path) -> dict[str, Any]:
    command = verifier_command(verifier, REPO / "faults" / "fpb" / rule, vectors_path)
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise DatasetError(f"{rule}: verifier trace failed with exit {completed.returncode}: {detail[-2000:]}")
    try:
        trace = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DatasetError(f"{rule}: verifier returned non-JSON trace output") from exc
    if trace.get("schema") != TRACE_SCHEMA:
        raise DatasetError(f"{rule}: verifier returned unsupported trace schema {trace.get('schema')!r}")
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
            "description": gate.description,
            "applies_to": list(gate.applies_to),
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

    fault_values: list[bool] = []
    sample_timestamps: list[datetime] = []
    segment_starts: set[int] = set()
    segment_traces: dict[int, list[tuple[datetime, bool]]] = {}
    by_length: dict[int, list[tuple[int, list[int]]]] = defaultdict(list)
    for segment_number, indices in enumerate(segments, start=1):
        by_length[len(indices)].append((segment_number, indices))
    for length, group in sorted(by_length.items()):
        vectors = vectors_for_segments(loaded, inputs, group)
        vectors_path = temp_root / f"{loaded.spec.case_id}__{rule}__{length}.json"
        vectors_path.write_text(json.dumps(vectors, indent=2, sort_keys=True) + "\n")
        trace = run_trace(verifier, rule, vectors_path)
        if trace.get("clock", {}).get("step_s") != loaded.spec.step_s:
            raise DatasetError(f"{rule}: verifier trace cadence does not match source cadence")
        raw_scenarios = trace.get("scenarios")
        if not isinstance(raw_scenarios, list) or not all(
            isinstance(scenario, dict) and isinstance(scenario.get("name"), str) for scenario in raw_scenarios
        ):
            raise DatasetError(f"{rule}: verifier trace scenarios are malformed")
        trace_by_name = {scenario["name"]: scenario for scenario in raw_scenarios}
        expected_names = {f"{loaded.spec.case_id}__segment_{number:04d}" for number, _ in group}
        if set(trace_by_name) != expected_names or len(trace_by_name) != len(raw_scenarios):
            raise DatasetError(f"{rule}: verifier trace scenario identity does not match requested vectors")
        for segment_number, indices in group:
            name = f"{loaded.spec.case_id}__segment_{segment_number:04d}"
            scenario = trace_by_name.get(name)
            if not scenario:
                raise DatasetError(f"{rule}: verifier trace omitted scenario {name}")
            samples = scenario.get("samples", [])
            if len(samples) != len(indices):
                raise DatasetError(f"{rule}: verifier returned {len(samples)} samples for {len(indices)} source rows")
            values: list[tuple[datetime, bool]] = []
            for sample_number, (sample, source_index) in enumerate(zip(samples, indices)):
                if sample.get("t") != sample_number * loaded.spec.step_s:
                    raise DatasetError(f"{rule}: verifier trace timestamp does not match requested cadence")
                value = sample.get("outputs", {}).get("yFault")
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
    detected = bool(alarm_samples) if is_target_fault else False
    latency: float | None = None
    if detected and loaded.spec.fault_start:
        first_alarm = min(timestamp for timestamp, value in zip(sample_timestamps, fault_values) if value)
        latency = max(0.0, (first_alarm - loaded.spec.fault_start).total_seconds())
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
        "faulted_detected_cases": int(detected),
        "faulted_total_cases": int(is_target_fault and bool(fault_values)),
        "median_detection_latency_s": latency,
    }
    return {
        "case": loaded.spec.case_id,
        "rule": rule,
        "subtype": loaded.spec.subtype,
        "label": loaded.spec.label,
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
    }


def selected_cases(adapter: Any, args: argparse.Namespace) -> list[Any]:
    case_ids = {item.strip() for item in args.case.split(",") if item.strip()} if getattr(args, "case", None) else None
    label = getattr(args, "case_kind", None)
    label = label.replace("-", "_") if label else None
    return adapter.select_cases(
        subtype=getattr(args, "subtype", None),
        label=label,
        severity=getattr(args, "severity", None),
        case_ids=case_ids,
    )


def load_selected(adapter: Any, args: argparse.Namespace, *, strict: bool) -> list[LoadedCase]:
    start = parse_datetime_bound(getattr(args, "start", None))
    end = parse_datetime_bound(getattr(args, "end", None), end=True)
    return [adapter.load_case(case, start=start, end=end, strict_timeline=strict) for case in selected_cases(adapter, args)]


def print_inspection(adapter: Any, loaded_cases: list[LoadedCase], rules: list[str]) -> None:
    print(f"adapter: {adapter.slug}/{adapter.version}")
    print(f"dataset: {adapter.name} (DOI {adapter.doi})")
    for loaded in loaded_cases:
        timeline = loaded.timeline
        print(
            f"case {loaded.spec.case_id}: subtype={loaded.spec.subtype} label={loaded.spec.label} "
            f"severity={loaded.spec.severity or '-'} rows={timeline['rows']} "
            f"duplicates={timeline['duplicates']} out_of_order={timeline['out_of_order']} "
            f"missing_intervals={len(timeline['missing_intervals'])} "
            f"irregular_intervals={timeline['irregular_intervals']} dropped_rows={timeline['dropped_rows']}"
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
    loaded_cases = load_selected(adapter, args, strict=False)
    print_inspection(adapter, loaded_cases, rules)
    bad = [
        loaded
        for loaded in loaded_cases
        if loaded.timeline["duplicates"]
        or loaded.timeline["out_of_order"]
        or loaded.timeline["irregular_intervals"]
    ]
    if bad:
        print("replay status: blocked by duplicate/out-of-order/irregular timestamps")
    return 0


def command_replay(args: argparse.Namespace) -> int:
    adapter = ADAPTERS[args.adapter](args.dataset)
    rules = parse_rules(args.rules)
    loaded_cases = load_selected(adapter, args, strict=True)
    print_inspection(adapter, loaded_cases, rules)
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
    if REPO.resolve() in output.parents and repository_target not in output.parents:
        raise DatasetError("replay output inside the repository must stay under the ignored target/ directory")
    for protected in (path.resolve() for path in protected_roots):
        if output == protected or protected in output.parents:
            raise DatasetError(f"refusing to write replay output inside protected source/artifact tree {protected}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dataset-harness-", dir=output.parent) as temporary:
        temp_root = Path(temporary)
        results = [
            replay_case_rule(loaded, rule, temp_root, args.verifier)
            for loaded in loaded_cases
            for rule in rules
        ]
    latencies = [
        result["metrics"]["median_detection_latency_s"]
        for result in results
        if result["metrics"]["median_detection_latency_s"] is not None
    ]
    document = {
        "schema": RESULT_SCHEMA,
        "adapter": f"{adapter.slug}/{adapter.version}",
        "dataset": {
            "name": adapter.name,
            "doi": adapter.doi,
            "inventory": adapter.manifest["dataset"]["inventory"],
            "version": adapter.manifest["dataset"]["version"],
            "local_fingerprint": adapter.fingerprint(selected_cases(adapter, args)),
            "cases": len(loaded_cases),
        },
        "selection": {
            "rules": rules,
            "cases": [loaded.spec.case_id for loaded in loaded_cases],
            "subtype": args.subtype,
            "case_kind": args.case_kind,
            "severity": args.severity,
            "start": args.start,
            "end": args.end,
        },
        "summary": {
            "results": len(results),
            "evaluable_samples": sum(result["metrics"]["evaluable_samples"] for result in results),
            "fault_free_alarm_samples": sum(result["metrics"]["fault_free_alarm_samples"] for result in results),
            "fault_free_alarm_episodes": sum(result["metrics"]["fault_free_alarm_episodes"] for result in results),
            "faulted_detected_cases": sum(result["metrics"]["faulted_detected_cases"] for result in results),
            "faulted_total_cases": sum(result["metrics"]["faulted_total_cases"] for result in results),
            "median_detection_latency_s": statistics.median(latencies) if latencies else None,
        },
        "results": results,
        "notes": [
            "Rates use fault-free evaluable samples, never all source rows, as the denominator.",
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
    except (DatasetError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
