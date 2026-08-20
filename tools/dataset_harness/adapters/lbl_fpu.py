"""Inventory-backed adapter for the external LBNL simulated FPU dataset.

The source archive is intentionally not bundled.  A local manifest records the
inventory evidence and exact source-column bindings; this module refuses to
guess a mapping from column-name resemblance.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
MANIFEST_NAME = "lbl_fpu_manifest.json"
MANIFEST_SCHEMA = "cxf-library/dataset-manifest/lbl-fpu/v1"
KNOWN_RULES = tuple(f"FPB-{number:04d}" for number in range(1, 7))
REQUIRED_GATES = {
    "occupied",
    "enabled",
    "airflow_established",
    "stable",
    "baseline_ready",
    "point_valid",
}
GATE_RULE_CONTRACT = {
    "occupied": set(KNOWN_RULES),
    "enabled": set(KNOWN_RULES),
    "airflow_established": set(KNOWN_RULES[1:]),
    "stable": set(KNOWN_RULES[1:]),
    "baseline_ready": set(KNOWN_RULES[3:]),
    "point_valid": set(KNOWN_RULES),
}
MODEL_POINTS = {"fan_airflow_expected", "rht_delta_t_expected"}
READINESS_FIELDS = {"method", "version", "inputs", "known_good_basis", "validation_error", "update_policy"}
CASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
GATE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class DatasetError(ValueError):
    """A deterministic, user-facing dataset or manifest error."""


@dataclass(frozen=True)
class ColumnBinding:
    canonical: str
    column: str
    kind: str
    source_unit: str
    target_unit: str
    true_values: frozenset[str]
    false_values: frozenset[str]
    inventory_evidence: str
    proxy: str | None
    readiness: dict[str, Any] | None
    independent: bool | None
    independence_evidence: str | None
    derived_from: tuple[str, ...]


@dataclass(frozen=True)
class GateBinding:
    name: str
    column: str
    true_values: frozenset[str]
    false_values: frozenset[str]
    applies_to: tuple[str, ...]
    description: str
    inventory_evidence: str
    proxy: str | None
    derived_from: tuple[str, ...]


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    file: str
    subtype: str
    label: str
    inventory_evidence: str
    fault_class: str | None
    severity: str | None
    expected_rules: tuple[str, ...]
    step_s: int
    timestamp_column: str
    startup_lead_s: int
    fault_start: datetime | None
    mappings: dict[str, ColumnBinding]
    gates: dict[str, GateBinding]


@dataclass
class LoadedCase:
    spec: CaseSpec
    source_path: Path
    timestamps: list[datetime]
    rows: list[dict[str, Any]]
    gate_values: dict[str, list[bool]]
    timeline: dict[str, Any]

    def gate_mask(self, rule: str, inputs: list[str] | None = None) -> list[bool]:
        raw = [True] * len(self.rows)
        for gate in self.spec.gates.values():
            if "*" not in gate.applies_to and rule not in gate.applies_to:
                continue
            raw = [left and right for left, right in zip(raw, self.gate_values[gate.name])]
        if inputs is not None:
            raw = [
                enabled and all(row.get(point) is not None for point in inputs)
                for enabled, row in zip(raw, self.rows)
            ]

        lead = self.spec.startup_lead_s
        if lead <= 0:
            return raw
        result: list[bool] = []
        eligible_since: datetime | None = None
        previous_timestamp: datetime | None = None
        for timestamp, enabled in zip(self.timestamps, raw):
            if previous_timestamp is not None and (
                timestamp - previous_timestamp
            ).total_seconds() != self.spec.step_s:
                eligible_since = None
            if not enabled:
                eligible_since = None
                result.append(False)
                previous_timestamp = timestamp
                continue
            if eligible_since is None:
                eligible_since = timestamp
            result.append((timestamp - eligible_since).total_seconds() >= lead)
            previous_timestamp = timestamp
        return result

    def evaluable_segments(self, rule: str, inputs: list[str]) -> list[list[int]]:
        mask = self.gate_mask(rule, inputs)
        segments: list[list[int]] = []
        current: list[int] = []
        for index, (timestamp, row, gated) in enumerate(zip(self.timestamps, self.rows, mask)):
            valid = gated
            contiguous = bool(current) and index == current[-1] + 1 and (
                timestamp - self.timestamps[current[-1]]
            ).total_seconds() == self.spec.step_s
            if valid and (not current or contiguous):
                current.append(index)
            elif valid:
                segments.append(current)
                current = [index]
            elif current:
                segments.append(current)
                current = []
        if current:
            segments.append(current)
        return segments

    def mapping_report(self, inputs: list[str]) -> dict[str, Any]:
        bindings: dict[str, str | None] = {}
        binding_details: dict[str, dict[str, Any] | None] = {}
        proxies: list[dict[str, str]] = []
        conversions: list[dict[str, str]] = []
        for point in inputs:
            binding = self.spec.mappings.get(point)
            bindings[point] = binding.column if binding else None
            if not binding:
                binding_details[point] = None
                continue
            binding_details[point] = {
                "source_column": binding.column,
                "inventory_evidence": binding.inventory_evidence,
                "readiness": binding.readiness,
                "independent": binding.independent,
                "independence_evidence": binding.independence_evidence,
                "derived_from": list(binding.derived_from),
            }
            if binding.proxy:
                proxies.append({"point": point, "detail": binding.proxy})
            if binding.source_unit != binding.target_unit:
                conversions.append(
                    {
                        "point": point,
                        "from": binding.source_unit,
                        "to": binding.target_unit,
                        "formula": conversion_description(binding.source_unit, binding.target_unit),
                    }
                )
        return {
            "canonical_to_source": bindings,
            "binding_details": binding_details,
            "proxies": proxies,
            "unit_conversions": conversions,
        }


def _as_string_set(value: Any, field: str) -> frozenset[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, (str, int, bool)) for item in value):
        raise DatasetError(f"{field} must be a non-empty list of exact source tokens")
    result = frozenset(str(item).strip().lower() for item in value)
    if "" in result:
        raise DatasetError(f"{field} cannot treat a missing/empty value as Boolean")
    return result


def _parse_timestamp(value: str, field: str) -> datetime:
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise DatasetError(f"{field}: invalid ISO-8601 timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        raise DatasetError(f"{field}: timestamp must include UTC offset or Z")
    if parsed.microsecond:
        raise DatasetError(f"{field}: sub-second timestamps are unsupported for integer-step replay")
    return parsed


def _validate_readiness(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not READINESS_FIELDS.issubset(value):
        raise DatasetError(f"{field} must contain {sorted(READINESS_FIELDS)}")
    if not isinstance(value["inputs"], list) or not all(isinstance(item, str) and item for item in value["inputs"]):
        raise DatasetError(f"{field}.inputs must be a list of named model/reference inputs")
    for name in READINESS_FIELDS - {"inputs"}:
        if not isinstance(value[name], str) or not value[name].strip():
            raise DatasetError(f"{field}.{name} must be a non-empty string")
    return value


def _point_contracts() -> dict[str, dict[str, Any]]:
    path = REPO / "points" / "fpb.points.json"
    document = json.loads(path.read_text())
    return {point["name"]: point for point in document["points"]}


def conversion_description(source: str, target: str) -> str:
    descriptions = {
        ("cfm", "L/s"): "L/s = cfm × 0.47194745",
        ("m3/s", "L/s"): "L/s = m3/s × 1000",
        ("degF", "degC"): "degC = (degF − 32) × 5/9",
        ("delta_degF", "K"): "K = Δ°F × 5/9",
        ("fraction", "%"): "% = fraction × 100",
    }
    return descriptions.get((source, target), "identity")


def convert_number(value: float, source: str, target: str) -> float:
    if source == target:
        return value
    conversions = {
        ("cfm", "L/s"): lambda number: number * 0.47194745,
        ("m3/s", "L/s"): lambda number: number * 1000.0,
        ("degF", "degC"): lambda number: (number - 32.0) * 5.0 / 9.0,
        ("delta_degF", "K"): lambda number: number * 5.0 / 9.0,
        ("fraction", "%"): lambda number: number * 100.0,
    }
    converter = conversions.get((source, target))
    if not converter:
        raise DatasetError(f"unsupported unit conversion {source!r} -> {target!r}")
    return converter(value)


def _parse_bool(value: str, true_values: frozenset[str], false_values: frozenset[str], field: str) -> bool:
    token = value.strip().lower()
    if token in true_values:
        return True
    if token in false_values:
        return False
    raise DatasetError(f"{field}: boolean token {value!r} is neither explicitly true nor false")


def _source_cell(row: dict[str | None, Any], column: str, field: str) -> str:
    value = row.get(column)
    if not isinstance(value, str):
        raise DatasetError(f"{field}: missing source value")
    return value


class LblFpuAdapter:
    slug = "lbl-fpu"
    version = "v1"
    name = "LBNL simulated FPU"
    doi = "10.25984/1881324"
    description = "Inventory-backed adapter for the external parallel/series FPU dataset"

    def __init__(self, dataset_root: Path):
        self.root = dataset_root.resolve()
        self.manifest_path = self.root / MANIFEST_NAME
        if not self.manifest_path.is_file():
            raise DatasetError(
                f"missing {self.manifest_path}; create it from the official inventory using the documented manifest contract"
            )
        try:
            self.manifest = json.loads(self.manifest_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise DatasetError(f"cannot read {self.manifest_path}: {exc}") from exc
        self._validate_manifest()
        self.cases = tuple(self._parse_case(raw) for raw in self.manifest["cases"])
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise DatasetError("manifest case ids must be unique")

    def _validate_manifest(self) -> None:
        if self.manifest.get("schema") != MANIFEST_SCHEMA:
            raise DatasetError(f"manifest schema must be {MANIFEST_SCHEMA!r}")
        dataset = self.manifest.get("dataset")
        if not isinstance(dataset, dict) or dataset.get("doi") != self.doi:
            raise DatasetError(f"manifest dataset.doi must be {self.doi}")
        if not isinstance(dataset.get("inventory"), str) or not dataset["inventory"].strip():
            raise DatasetError("manifest dataset.inventory must identify the inventory artifact used")
        if not isinstance(dataset.get("version"), str) or not dataset["version"].strip():
            raise DatasetError("manifest dataset.version must identify the local source release or retrieval")
        if not isinstance(self.manifest.get("cases"), list) or not self.manifest["cases"]:
            raise DatasetError("manifest cases must be a non-empty list")

    def _parse_case(self, raw: Any) -> CaseSpec:
        if not isinstance(raw, dict):
            raise DatasetError("each manifest case must be an object")
        case_id = raw.get("id")
        if not isinstance(case_id, str) or not CASE_ID_PATTERN.fullmatch(case_id):
            raise DatasetError("case id must be a 1-128 character safe token using letters, digits, dot, underscore, or hyphen")
        subtype = raw.get("subtype")
        if subtype not in {"parallel", "series"}:
            raise DatasetError(f"case {case_id}: subtype must be parallel or series")
        label = raw.get("label")
        if label not in {"fault_free", "faulted"}:
            raise DatasetError(f"case {case_id}: label must be fault_free or faulted")
        raw_expected_rules = raw.get("expected_rules", [])
        if not isinstance(raw_expected_rules, list) or not all(isinstance(rule, str) for rule in raw_expected_rules):
            raise DatasetError(f"case {case_id}: expected_rules must be a list of rule ids")
        expected_rules = tuple(raw_expected_rules)
        if any(rule not in KNOWN_RULES for rule in expected_rules):
            raise DatasetError(f"case {case_id}: expected_rules contains an unknown FPB rule")
        if len(expected_rules) != len(set(expected_rules)):
            raise DatasetError(f"case {case_id}: expected_rules contains duplicates")
        if label == "faulted" and not expected_rules:
            raise DatasetError(f"case {case_id}: faulted cases must declare expected_rules from inventory semantics")
        if label == "fault_free" and expected_rules:
            raise DatasetError(f"case {case_id}: fault-free cases cannot declare expected_rules")
        case_evidence = raw.get("inventory_evidence")
        if not isinstance(case_evidence, str) or not case_evidence.strip():
            raise DatasetError(f"case {case_id}: inventory_evidence is required for label and target provenance")
        step_s = raw.get("step_s")
        if type(step_s) is not int or step_s <= 0:
            raise DatasetError(f"case {case_id}: step_s must be a positive integer")
        timestamp_column = raw.get("timestamp_column")
        if not isinstance(timestamp_column, str) or not timestamp_column:
            raise DatasetError(f"case {case_id}: timestamp_column is required")
        startup_lead_s = raw.get("startup_lead_s", 0)
        if type(startup_lead_s) is not int or startup_lead_s < 0:
            raise DatasetError(f"case {case_id}: startup_lead_s must be a non-negative integer")
        fault_start = raw.get("fault_start")
        if fault_start is not None and not isinstance(fault_start, str):
            raise DatasetError(f"case {case_id}: fault_start must be an ISO-8601 string")
        parsed_fault_start = _parse_timestamp(fault_start, f"case {case_id}.fault_start") if fault_start else None
        if label == "faulted" and parsed_fault_start is None:
            raise DatasetError(f"case {case_id}: faulted cases require fault_start for an explicit TPR window")
        if label == "fault_free" and parsed_fault_start is not None:
            raise DatasetError(f"case {case_id}: fault-free cases cannot declare fault_start")
        fault_class = raw.get("fault_class")
        if fault_class is not None and (not isinstance(fault_class, str) or not fault_class.strip()):
            raise DatasetError(f"case {case_id}: fault_class must be null or a non-empty string")
        if label == "faulted" and fault_class is None:
            raise DatasetError(f"case {case_id}: faulted cases require an inventory-backed fault_class")
        if label == "fault_free" and fault_class is not None:
            raise DatasetError(f"case {case_id}: fault-free cases cannot declare fault_class")
        severity = raw.get("severity")
        if severity is not None and (not isinstance(severity, str) or not severity.strip()):
            raise DatasetError(f"case {case_id}: severity must be null or a non-empty string")

        file_name = raw.get("file")
        if not isinstance(file_name, str) or not file_name:
            raise DatasetError(f"case {case_id}: file is required")
        resolved = (self.root / file_name).resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise DatasetError(f"case {case_id}: file escapes dataset root")

        contracts = _point_contracts()
        raw_mappings = raw.get("mappings")
        if not isinstance(raw_mappings, dict) or not raw_mappings:
            raise DatasetError(f"case {case_id}: mappings must be a non-empty object")
        mappings: dict[str, ColumnBinding] = {}
        for canonical, binding in raw_mappings.items():
            if canonical not in contracts:
                raise DatasetError(f"case {case_id}: unknown canonical point {canonical!r}")
            if not isinstance(binding, dict):
                raise DatasetError(f"case {case_id}.{canonical}: mapping must be an object")
            column = binding.get("column")
            if not isinstance(column, str) or not column:
                raise DatasetError(f"case {case_id}.{canonical}: source column is required")
            kind = binding.get("kind", contracts[canonical]["kind"])
            if kind != contracts[canonical]["kind"]:
                raise DatasetError(
                    f"case {case_id}.{canonical}: kind {kind!r} conflicts with point contract {contracts[canonical]['kind']!r}"
                )
            source_unit = binding.get("unit")
            if not isinstance(source_unit, str) or not source_unit:
                raise DatasetError(f"case {case_id}.{canonical}: source unit is required")
            target_unit = contracts[canonical]["unit"]
            if kind == "real":
                convert_number(0.0, source_unit, target_unit)
                true_values = false_values = frozenset()
            elif kind == "bool":
                if source_unit != "bool" or target_unit != "bool":
                    raise DatasetError(f"case {case_id}.{canonical}: booleans must use unit bool")
                true_values = _as_string_set(binding.get("true_values"), f"case {case_id}.{canonical}.true_values")
                false_values = _as_string_set(binding.get("false_values"), f"case {case_id}.{canonical}.false_values")
                if true_values & false_values:
                    raise DatasetError(f"case {case_id}.{canonical}: true/false token sets overlap")
            else:
                raise DatasetError(f"case {case_id}.{canonical}: unsupported kind {kind!r}")
            evidence = binding.get("inventory_evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                raise DatasetError(f"case {case_id}.{canonical}: inventory_evidence is required")
            readiness = binding.get("readiness")
            if canonical in MODEL_POINTS:
                readiness = _validate_readiness(readiness, f"case {case_id}.{canonical}.readiness")
            independent = binding.get("independent")
            independence_evidence = binding.get("independence_evidence")
            raw_derived_from = binding.get("derived_from", [])
            if not isinstance(raw_derived_from, list) or not all(isinstance(item, str) and item for item in raw_derived_from):
                raise DatasetError(f"case {case_id}.{canonical}.derived_from must be a list of canonical/source inputs")
            derived_from = tuple(raw_derived_from)
            if independent is not None and not isinstance(independent, bool):
                raise DatasetError(f"case {case_id}.{canonical}.independent must be Boolean when present")
            if canonical in {"primary_airflow_reference", "fan_status"}:
                if independent is not True:
                    raise DatasetError(f"case {case_id}.{canonical}: binding must be explicitly independent")
                if not isinstance(independence_evidence, str) or not independence_evidence.strip():
                    raise DatasetError(f"case {case_id}.{canonical}: independence_evidence is required")
            if canonical == "primary_airflow_reference":
                readiness = _validate_readiness(readiness, f"case {case_id}.{canonical}.readiness")
                readiness_inputs = readiness["inputs"]
                if "primary_airflow" in derived_from or "primary_airflow" in readiness_inputs:
                    raise DatasetError(
                        f"case {case_id}.primary_airflow_reference: reference must be explicitly independent and not derived from primary_airflow"
                    )
            elif canonical != "fan_status" and independence_evidence is not None:
                raise DatasetError(
                    f"case {case_id}.{canonical}: independence_evidence is reserved for independent proof/reference bindings"
                )
            proxy = binding.get("proxy")
            if proxy is not None and (not isinstance(proxy, str) or not proxy.strip()):
                raise DatasetError(f"case {case_id}.{canonical}: proxy must be null or a non-empty disclosure")
            mappings[canonical] = ColumnBinding(
                canonical=canonical,
                column=column,
                kind=kind,
                source_unit=source_unit,
                target_unit=target_unit,
                true_values=true_values,
                false_values=false_values,
                inventory_evidence=evidence,
                proxy=proxy,
                readiness=readiness,
                independent=independent,
                independence_evidence=independence_evidence,
                derived_from=derived_from,
            )

        reference = mappings.get("primary_airflow_reference")
        primary = mappings.get("primary_airflow")
        if reference and primary:
            forbidden = {"primary_airflow".casefold(), primary.column.casefold()}
            dependencies = {
                value.casefold()
                for value in (*reference.derived_from, *reference.readiness["inputs"])
            }
            if reference.column.casefold() == primary.column.casefold() or forbidden & dependencies:
                raise DatasetError(
                    f"case {case_id}.primary_airflow_reference: reference reuses the canonical primary airflow source column"
                )

        fan_command = mappings.get("fan_cmd")
        fan_status = mappings.get("fan_status")
        if fan_command and fan_status:
            forbidden = {"fan_cmd".casefold(), fan_command.column.casefold()}
            dependencies = {value.casefold() for value in fan_status.derived_from}
            if fan_status.column.casefold() == fan_command.column.casefold() or forbidden & dependencies:
                raise DatasetError(
                    f"case {case_id}.fan_status: proof reuses the fan command or its bound source column"
                )

        actual_fan_flow = mappings.get("fan_airflow")
        expected_fan_flow = mappings.get("fan_airflow_expected")
        if actual_fan_flow and expected_fan_flow:
            forbidden = {"fan_airflow".casefold(), actual_fan_flow.column.casefold()}
            dependencies = {
                value.casefold()
                for value in (*expected_fan_flow.derived_from, *expected_fan_flow.readiness["inputs"])
            }
            if expected_fan_flow.column.casefold() == actual_fan_flow.column.casefold() or forbidden & dependencies:
                raise DatasetError(
                    f"case {case_id}.fan_airflow_expected: expected model reuses measured fan airflow"
                )
        if actual_fan_flow and fan_status:
            forbidden = {"fan_airflow".casefold(), actual_fan_flow.column.casefold()}
            proof_claims = {fan_status.column.casefold(), *(value.casefold() for value in fan_status.derived_from)}
            if forbidden & proof_claims:
                raise DatasetError(
                    f"case {case_id}.fan_status: proof cannot be derived from fan airflow used by FPB-0004"
                )

        leaving_temperature = mappings.get("rht_coil_leaving_temp")
        entering_temperature = mappings.get("rht_coil_entering_temp")
        expected_delta_t = mappings.get("rht_delta_t_expected")
        if entering_temperature and leaving_temperature and (
            entering_temperature.column.casefold() == leaving_temperature.column.casefold()
        ):
            raise DatasetError(
                f"case {case_id}: reheat entering and leaving temperatures require distinct source columns"
            )
        if leaving_temperature and expected_delta_t:
            forbidden = {
                "rht_delta_t".casefold(),
                "rht_coil_leaving_temp".casefold(),
                leaving_temperature.column.casefold(),
            }
            dependencies = {
                value.casefold()
                for value in (*expected_delta_t.derived_from, *expected_delta_t.readiness["inputs"])
            }
            if expected_delta_t.column.casefold() == leaving_temperature.column.casefold() or forbidden & dependencies:
                raise DatasetError(
                    f"case {case_id}.rht_delta_t_expected: expected model reuses the measured leaving-temperature outcome"
                )

        primary_setpoint = mappings.get("primary_airflow_sp")
        if primary and primary_setpoint and primary.column.casefold() == primary_setpoint.column.casefold():
            raise DatasetError(
                f"case {case_id}: primary airflow measurement and setpoint require distinct source columns"
            )

        columns_to_points: dict[str, list[str]] = {}
        for point, binding in mappings.items():
            columns_to_points.setdefault(binding.column.casefold(), []).append(point)
        aliases = [sorted(points) for points in columns_to_points.values() if len(points) > 1]
        invalid_aliases = []
        for points in aliases:
            series_flow_alias = (
                subtype == "series"
                and set(points) == {"primary_airflow", "fan_airflow"}
                and bool(mappings["fan_airflow"].proxy)
            )
            if not series_flow_alias:
                invalid_aliases.append(points)
        if invalid_aliases:
            raise DatasetError(
                f"case {case_id}: canonical mappings require distinct source columns; aliases={invalid_aliases}"
            )

        raw_gates = raw.get("gates")
        if not isinstance(raw_gates, dict) or not REQUIRED_GATES.issubset(raw_gates):
            available = set(raw_gates) if isinstance(raw_gates, dict) else set()
            missing = sorted(REQUIRED_GATES - available)
            raise DatasetError(f"case {case_id}: missing required gate definitions {missing}")
        gates: dict[str, GateBinding] = {}
        for name, binding in raw_gates.items():
            if not isinstance(name, str) or not GATE_NAME_PATTERN.fullmatch(name):
                raise DatasetError(f"case {case_id}: gate names must be safe lower_snake_case tokens")
            if not isinstance(binding, dict):
                raise DatasetError(f"case {case_id}.gates.{name}: gate must be an object")
            column = binding.get("column")
            description = binding.get("description")
            evidence = binding.get("inventory_evidence")
            proxy = binding.get("proxy")
            raw_derived_from = binding.get("derived_from", [])
            raw_applies_to = binding.get("applies_to", ["*"])
            if not isinstance(raw_applies_to, list) or not all(isinstance(rule, str) for rule in raw_applies_to):
                raise DatasetError(f"case {case_id}.gates.{name}: applies_to must be a list of rule ids or *")
            applies_to = tuple(raw_applies_to)
            if not isinstance(column, str) or not column or not isinstance(description, str) or not description:
                raise DatasetError(f"case {case_id}.gates.{name}: column and description are required")
            if not isinstance(evidence, str) or not evidence.strip():
                raise DatasetError(f"case {case_id}.gates.{name}: inventory_evidence is required")
            if proxy is not None and (not isinstance(proxy, str) or not proxy.strip()):
                raise DatasetError(f"case {case_id}.gates.{name}: proxy must be null or a non-empty disclosure")
            if not isinstance(raw_derived_from, list) or not all(
                isinstance(item, str) and item for item in raw_derived_from
            ):
                raise DatasetError(f"case {case_id}.gates.{name}: derived_from must be a list of source/canonical inputs")
            if not applies_to or any(rule != "*" and rule not in KNOWN_RULES for rule in applies_to):
                raise DatasetError(f"case {case_id}.gates.{name}: applies_to contains an unknown rule")
            if len(applies_to) != len(set(applies_to)) or ("*" in applies_to and len(applies_to) != 1):
                raise DatasetError(f"case {case_id}.gates.{name}: applies_to must be unique and use * alone")
            true_values = _as_string_set(binding.get("true_values"), f"case {case_id}.gates.{name}.true_values")
            false_values = _as_string_set(binding.get("false_values"), f"case {case_id}.gates.{name}.false_values")
            if true_values & false_values:
                raise DatasetError(f"case {case_id}.gates.{name}: true/false token sets overlap")
            gates[name] = GateBinding(
                name,
                column,
                true_values,
                false_values,
                applies_to,
                description,
                evidence,
                proxy,
                tuple(raw_derived_from),
            )

        for name, required_rules in GATE_RULE_CONTRACT.items():
            applies_to = gates[name].applies_to
            covered = set(KNOWN_RULES) if "*" in applies_to else set(applies_to)
            missing_rules = sorted(required_rules - covered)
            if missing_rules:
                raise DatasetError(f"case {case_id}.gates.{name}: applies_to must cover {missing_rules}")

        gate_forbidden_points = {
            "occupied": set(mappings),
            "enabled": set(mappings),
            "airflow_established": {"primary_airflow", "fan_airflow"},
            "stable": {"primary_airflow", "fan_airflow", "rht_coil_leaving_temp"},
            "baseline_ready": {
                "primary_airflow",
                "primary_airflow_reference",
                "fan_airflow",
                "fan_airflow_expected",
                "rht_coil_leaving_temp",
                "rht_delta_t_expected",
            },
            "point_valid": set(mappings),
        }
        for name in set(gates) - set(gate_forbidden_points):
            gate_forbidden_points[name] = set(mappings)
        for name, forbidden_points in gate_forbidden_points.items():
            forbidden = {point.casefold() for point in forbidden_points}
            forbidden.update(
                mappings[point].column.casefold() for point in forbidden_points if point in mappings
            )
            gate = gates[name]
            claims = {gate.column.casefold(), *(value.casefold() for value in gate.derived_from)}
            if forbidden & claims:
                raise DatasetError(
                    f"case {case_id}.gates.{name}: gate reuses a target outcome instead of independent readiness/quality evidence"
                )

        return CaseSpec(
            case_id=case_id,
            file=file_name,
            subtype=subtype,
            label=label,
            inventory_evidence=case_evidence,
            fault_class=fault_class,
            severity=severity,
            expected_rules=expected_rules,
            step_s=step_s,
            timestamp_column=timestamp_column,
            startup_lead_s=startup_lead_s,
            fault_start=parsed_fault_start,
            mappings=mappings,
            gates=gates,
        )

    def select_cases(
        self,
        *,
        subtype: str | None = None,
        label: str | None = None,
        severity: str | None = None,
        case_ids: set[str] | None = None,
    ) -> list[CaseSpec]:
        if case_ids is not None:
            unknown = sorted(case_ids - {case.case_id for case in self.cases})
            if unknown:
                raise DatasetError(f"unknown case ids: {unknown}")
        selected = [
            case
            for case in self.cases
            if (subtype is None or case.subtype == subtype)
            and (label is None or case.label == label)
            and (severity is None or case.severity == severity)
            and (case_ids is None or case.case_id in case_ids)
        ]
        if not selected:
            raise DatasetError("no dataset cases match the requested selectors")
        return selected

    def load_case(
        self,
        case: CaseSpec,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        strict_timeline: bool = True,
    ) -> LoadedCase:
        source_path = (self.root / case.file).resolve()
        if not source_path.is_file():
            raise DatasetError(f"case {case.case_id}: missing source file {source_path}")
        required = {case.timestamp_column}
        required.update(binding.column for binding in case.mappings.values())
        required.update(gate.column for gate in case.gates.values())
        timestamps: list[datetime] = []
        rows: list[dict[str, Any]] = []
        gate_values = {name: [] for name in case.gates}
        with source_path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            if any(not isinstance(name, str) or not name.strip() for name in fieldnames):
                raise DatasetError(f"case {case.case_id}: source file contains an empty column header")
            if len(fieldnames) != len(set(fieldnames)):
                raise DatasetError(f"case {case.case_id}: source file contains duplicate column headers")
            missing = sorted(required - set(fieldnames))
            if missing:
                raise DatasetError(f"case {case.case_id}: source file missing required columns {missing}")
            for row_number, source_row in enumerate(reader, start=2):
                if None in source_row:
                    raise DatasetError(f"{source_path}:{row_number}: row has more values than the header")
                timestamp = _parse_timestamp(
                    _source_cell(source_row, case.timestamp_column, f"{source_path}:{row_number}:{case.timestamp_column}"),
                    f"{source_path}:{row_number}",
                )
                if start and timestamp < start:
                    continue
                if end and timestamp > end:
                    continue
                canonical_row: dict[str, Any] = {}
                for point, binding in case.mappings.items():
                    raw_value = _source_cell(
                        source_row, binding.column, f"{source_path}:{row_number}:{binding.column}"
                    )
                    if raw_value.strip() == "":
                        canonical_row[point] = None
                    elif binding.kind == "bool":
                        canonical_row[point] = _parse_bool(
                            raw_value, binding.true_values, binding.false_values, f"{source_path}:{row_number}:{binding.column}"
                        )
                    else:
                        try:
                            number = float(raw_value)
                        except ValueError as exc:
                            raise DatasetError(
                                f"{source_path}:{row_number}:{binding.column}: expected numeric value, got {raw_value!r}"
                            ) from exc
                        if not math.isfinite(number):
                            raise DatasetError(
                                f"{source_path}:{row_number}:{binding.column}: non-finite numbers are invalid"
                            )
                        converted = convert_number(number, binding.source_unit, binding.target_unit)
                        if not math.isfinite(converted):
                            raise DatasetError(
                                f"{source_path}:{row_number}:{binding.column}: unit conversion produced a non-finite value"
                            )
                        canonical_row[point] = converted
                for name, gate in case.gates.items():
                    gate_values[name].append(
                        _parse_bool(
                            _source_cell(source_row, gate.column, f"{source_path}:{row_number}:{gate.column}"),
                            gate.true_values,
                            gate.false_values,
                            f"{source_path}:{row_number}:{gate.column}",
                        )
                    )
                timestamps.append(timestamp)
                rows.append(canonical_row)
        if not rows:
            raise DatasetError(f"case {case.case_id}: no rows remain after date filtering")

        deltas = [int((right - left).total_seconds()) for left, right in zip(timestamps, timestamps[1:])]
        duplicates = sum(delta == 0 for delta in deltas)
        out_of_order = sum(delta < 0 for delta in deltas)
        missing_intervals = [
            {"after": timestamps[index].isoformat(), "delta_s": delta}
            for index, delta in enumerate(deltas)
            if delta > case.step_s
        ]
        cadence_mismatches = sum(delta != case.step_s for delta in deltas)
        irregular_intervals = sum(
            delta > 0 and (delta < case.step_s or delta % case.step_s != 0) for delta in deltas
        )
        timeline = {
            "rows": len(rows),
            "first": timestamps[0].isoformat(),
            "last": timestamps[-1].isoformat(),
            "duplicates": duplicates,
            "out_of_order": out_of_order,
            "missing_intervals": missing_intervals,
            "cadence_mismatches": cadence_mismatches,
            "irregular_intervals": irregular_intervals,
            "dropped_rows": 0,
        }
        if strict_timeline and (duplicates or out_of_order or irregular_intervals):
            raise DatasetError(
                f"case {case.case_id}: timeline has duplicates={duplicates}, out_of_order={out_of_order}, "
                f"irregular_intervals={irregular_intervals}; replay refuses to reorder or resample rows"
            )
        return LoadedCase(case, source_path, timestamps, rows, gate_values, timeline)

    def fingerprint(self, cases: list[CaseSpec]) -> str:
        digest = hashlib.sha256()
        for path in [self.manifest_path, *((self.root / case.file).resolve() for case in sorted(cases, key=lambda item: item.case_id))]:
            digest.update(path.relative_to(self.root).as_posix().encode())
            with path.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"
