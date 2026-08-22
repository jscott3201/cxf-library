#!/usr/bin/env python3
"""Validate the routine registry, G36 pins, and coverage zero-state."""

import json
import re
from pathlib import Path


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

LEVELS = frozenset(("leaf", "controller", "fragment"))
STATUSES = frozenset(
    ("draft", "ported", "engine_verified", "source_evidenced", "adopted", "deprecated")
)
EVIDENCE_TIERS = frozenset(f"E{number}" for number in range(6))
COMPLETENESS_VALUES = frozenset(("complete", "partial", "not_applicable", "unknown"))

PIN_RE = re.compile(r"^[0-9a-f]{40}$")
CLASS_ID_RE = re.compile(r"^G36-[A-Z0-9]+-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
VARIANT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ROUTINE_ID_RE = re.compile(
    r"^G36-[A-Z0-9]+-[A-Z0-9]+(?:-[A-Z0-9]+)*__"
    r"[a-z0-9]+(?:-[a-z0-9]+)*$"
)


def _read_json(repo_root, relative_path, errors):
    label = relative_path.as_posix()
    path = repo_root / relative_path
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
        errors.append(
            f"{label}: invalid JSON at line {exc.lineno}, column {exc.colno}"
        )
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


def _path_problem(value):
    if value.startswith("/"):
        return "absolute paths are forbidden"
    if "\\" in value:
        return "backslashes are forbidden"
    segments = value.split("/")
    if "" in segments:
        return "empty path segments are forbidden"
    if "." in segments:
        return "dot path segments are forbidden"
    if ".." in segments:
        return "parent traversal is forbidden"
    if segments[0] != "g36" or len(segments) < 2:
        return "path must be below g36/"
    return None


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
        problem = _path_problem(path)
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


def _read_pin(repo_root, relative_path, errors):
    label = relative_path.as_posix()
    try:
        text = (repo_root / relative_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"{label}: file is missing")
        return
    except (OSError, UnicodeError):
        errors.append(f"{label}: unable to read file")
        return
    value = text[:-1] if text.endswith("\n") else text
    if not PIN_RE.fullmatch(value):
        errors.append(f"{label}: must contain one lowercase 40-hex Git commit")


def _validate(repo_root):
    repo_root = Path(repo_root)
    errors = []
    registry = _read_json(repo_root, REGISTRY_PATH, errors)
    coverage = _read_json(repo_root, COVERAGE_PATH, errors)
    _read_pin(repo_root, SOURCE_PIN_PATH, errors)
    _read_pin(repo_root, DONOR_PIN_PATH, errors)

    registry_rows = None
    if registry is not None:
        _check_exact_keys(registry, REGISTRY_KEYS, REGISTRY_PATH.as_posix(), errors)
        if registry.get("schema") != "cxf-library/routine-registry/v1":
            errors.append(
                f"{REGISTRY_PATH.as_posix()}: schema must be "
                "'cxf-library/routine-registry/v1'"
            )
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
            errors.append(
                f"{COVERAGE_PATH.as_posix()}: schema must be "
                "'cxf-library/g36-coverage/v1'"
            )
        profile = coverage.get("profile")
        if not isinstance(profile, str) or not profile.strip():
            errors.append(f"{COVERAGE_PATH.as_posix()}: profile must be a nonempty string")
        completeness = coverage.get("completeness")
        _check_completeness(
            completeness, f"{COVERAGE_PATH.as_posix()}: completeness", errors
        )
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

    return sorted(errors), len(registry_rows) if registry_rows is not None else 0


def validate(repo_root=REPO_ROOT):
    """Return deterministic validation errors for a repository root."""
    return _validate(repo_root)[0]


def main(repo_root=REPO_ROOT):
    errors, routine_count = _validate(repo_root)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"routine catalog lint: {routine_count} routines OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
