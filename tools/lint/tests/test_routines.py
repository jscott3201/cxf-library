import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.lint import routines as routine_lint


PINS = {
    "routines/g36/SOURCE_PIN": "a131864e4c4df22ebcd52bb8da439de0087ac365\n",
    "routines/g36/DONOR_PIN": "41e997fd130c5e454446b40bcc3ba576429876b4\n",
}
UNKNOWN_COMPLETENESS = {
    "donor_configuration": "unknown",
    "canonical_class": "unknown",
    "family_package": "unknown",
    "guideline_profile": "unknown",
}


def valid_row(class_id="G36-GEN-EXAMPLE", variant_id="default", path=None):
    return {
        "id": f"{class_id}__{variant_id}",
        "class_id": class_id,
        "variant_id": variant_id,
        "name": "Example",
        "family": "generic",
        "level": "leaf",
        "status": "draft",
        "path": path if path is not None else f"g36/{class_id.lower()}/{variant_id}",
        "canonical_class": "Buildings.Controls.OBC.ASHRAE.G36.Generic.Example",
        "evidence_tier": "E0",
        "completeness": copy.deepcopy(UNKNOWN_COMPLETENESS),
    }


class RoutineLintTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.write_registry([])
        self.write_coverage()
        for relative_path, value in PINS.items():
            self.write_text(relative_path, value)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_text(self, relative_path, value):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def write_json(self, relative_path, value):
        self.write_text(relative_path, json.dumps(value) + "\n")

    def write_registry(self, rows, **extra):
        value = {
            "schema": "cxf-library/routine-registry/v1",
            "routines": rows,
        }
        value.update(extra)
        self.write_json("routines/registry.json", value)

    def write_coverage(self, **changes):
        value = {
            "schema": "cxf-library/g36-coverage/v1",
            "profile": "G36-2021-private-audit",
            "completeness": copy.deepcopy(UNKNOWN_COMPLETENESS),
            "areas": [],
            "claims": [],
        }
        value.update(changes)
        self.write_json("routines/g36/coverage.json", value)

    def assert_error(self, expected):
        errors = routine_lint.validate(self.root)
        self.assertTrue(
            any(expected in error for error in errors),
            f"{expected!r} not found in {errors!r}",
        )
        return errors

    def test_valid_zero_state(self):
        self.assertEqual(routine_lint.validate(self.root), [])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = routine_lint.main(self.root)
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "routine catalog lint: 0 routines OK\n")

    def test_missing_source_and_donor_pins(self):
        for relative_path in PINS:
            with self.subTest(relative_path=relative_path):
                (self.root / relative_path).unlink()
                self.assert_error(f"{relative_path}: file is missing")
                self.write_text(relative_path, PINS[relative_path])

    def test_malformed_source_and_donor_pins(self):
        for relative_path in PINS:
            with self.subTest(relative_path=relative_path):
                self.write_text(relative_path, "ABCDEF\n")
                self.assert_error(
                    f"{relative_path}: must contain one lowercase 40-hex Git commit"
                )
                self.write_text(relative_path, PINS[relative_path])

        self.write_text(
            "routines/g36/SOURCE_PIN",
            " a131864e4c4df22ebcd52bb8da439de0087ac365 \n",
        )
        self.assert_error(
            "routines/g36/SOURCE_PIN: must contain one lowercase 40-hex Git commit"
        )

    def test_wrong_registry_and_coverage_schema_ids(self):
        self.write_registry([])
        registry = json.loads((self.root / "routines/registry.json").read_text())
        registry["schema"] = "wrong"
        self.write_json("routines/registry.json", registry)
        self.assert_error("registry.json: schema must be 'cxf-library/routine-registry/v1'")

        self.write_registry([])
        self.write_coverage(schema="wrong")
        self.assert_error("coverage.json: schema must be 'cxf-library/g36-coverage/v1'")

    def test_missing_malformed_and_non_object_json(self):
        registry_path = self.root / "routines/registry.json"
        registry_path.unlink()
        self.assert_error("routines/registry.json: file is missing")

        self.write_text("routines/registry.json", "{")
        self.assert_error("routines/registry.json: invalid JSON at line 1, column 2")

        self.write_json("routines/registry.json", [])
        self.assert_error("routines/registry.json: must contain a JSON object")

    def test_registry_and_coverage_top_level_keys_are_exact(self):
        self.write_registry([], runtime_pin="deadbeef")
        self.assert_error("unexpected runtime_pin")

        for key in ("donor_pin", "source_pin", "implemented_variants"):
            with self.subTest(key=key):
                self.write_coverage(**{key: "duplicate"})
                self.assert_error(f"unexpected {key}")

        self.write_coverage()
        coverage = json.loads((self.root / "routines/g36/coverage.json").read_text())
        del coverage["claims"]
        self.write_json("routines/g36/coverage.json", coverage)
        self.assert_error("missing claims")

    def test_registry_must_be_an_array(self):
        self.write_registry({})
        self.assert_error("routines/registry.json: routines must be an array")

    def test_registry_row_keys_and_types_are_exact(self):
        row = valid_row()
        del row["family"]
        row["extra"] = True
        self.write_registry([row])
        errors = self.assert_error("missing family; unexpected extra")
        self.assertFalse(any("Traceback" in error for error in errors))

        row = valid_row()
        row["name"] = 3
        self.write_registry([row])
        self.assert_error("routines[0].name: must be a string")

    def test_duplicate_routine_ids_and_paths(self):
        first = valid_row()
        duplicate_id = valid_row(path="g36/generic/other")
        self.write_registry([first, duplicate_id])
        self.assert_error("routines[1].id: duplicate 'G36-GEN-EXAMPLE__default'")

        second = valid_row("G36-GEN-SECOND", path=first["path"])
        self.write_registry([first, second])
        self.assert_error(f"routines[1].path: duplicate {first['path']!r}")

    def test_registry_rows_must_be_sorted_by_id(self):
        second = valid_row("G36-GEN-SECOND")
        first = valid_row("G36-GEN-EXAMPLE")
        self.write_registry([second, first])
        self.assert_error("routines/registry.json: routines must be sorted by id")

    def test_routine_identity_must_match_class_and_variant(self):
        row = valid_row()
        row["id"] = "G36-GEN-OTHER__default"
        self.write_registry([row])
        self.assert_error("routines[0].id: must equal 'G36-GEN-EXAMPLE__default'")

    def test_class_variant_and_routine_id_grammar(self):
        row = valid_row(class_id="g36-GEN-EXAMPLE")
        self.write_registry([row])
        self.assert_error("routines[0].class_id: does not match G36-<DOMAIN>-<SLUG>")

        row = valid_row(variant_id="Not_Kebab")
        self.write_registry([row])
        self.assert_error("routines[0].variant_id: must be lowercase kebab case")

        row = valid_row()
        row["id"] = "not-a-routine-id"
        self.write_registry([row])
        self.assert_error(
            "routines[0].id: does not match G36-<DOMAIN>-<SLUG>__<variant-id>"
        )

    def test_unsafe_paths_are_rejected(self):
        cases = {
            "/g36/example": "absolute paths are forbidden",
            "g36\\example": "backslashes are forbidden",
            "g36/example/../other": "parent traversal is forbidden",
            "../g36/example": "parent traversal is forbidden",
            "g36//example": "empty path segments are forbidden",
            "g36/./example": "dot path segments are forbidden",
            "": "empty path segments are forbidden",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.write_registry([valid_row(path=path)])
                self.assert_error(f"routines[0].path: {expected}")

    def test_invalid_level_status_and_evidence_tier(self):
        cases = {
            "level": ("package", "routines[0].level: must be one of"),
            "status": ("verified", "routines[0].status: must be one of"),
            "evidence_tier": ("E6", "routines[0].evidence_tier: must be one of"),
        }
        for key, (value, expected) in cases.items():
            with self.subTest(key=key):
                row = valid_row()
                row[key] = value
                self.write_registry([row])
                self.assert_error(expected)

    def test_registry_completeness_keys_and_values(self):
        row = valid_row()
        del row["completeness"]["family_package"]
        self.write_registry([row])
        self.assert_error("routines[0].completeness: keys must be exactly")

        row = valid_row()
        row["completeness"]["guideline_profile"] = "done"
        self.write_registry([row])
        self.assert_error("completeness.guideline_profile: must be one of")

    def test_canonical_class_rule(self):
        for level in ("leaf", "controller"):
            with self.subTest(level=level):
                row = valid_row()
                row["level"] = level
                row["canonical_class"] = None
                self.write_registry([row])
                self.assert_error("canonical_class: non-fragments require a nonempty string")

        row = valid_row()
        row["level"] = "fragment"
        self.write_registry([row])
        self.assert_error("canonical_class: fragments must use null")

        row["canonical_class"] = None
        self.write_registry([row])
        self.assertEqual(routine_lint.validate(self.root), [])

    def test_coverage_profile_and_completeness_contract(self):
        self.write_coverage(profile=" ")
        self.assert_error("coverage.json: profile must be a nonempty string")

        completeness = copy.deepcopy(UNKNOWN_COMPLETENESS)
        del completeness["donor_configuration"]
        self.write_coverage(completeness=completeness)
        self.assert_error("coverage.json: completeness: keys must be exactly")

        completeness = copy.deepcopy(UNKNOWN_COMPLETENESS)
        completeness["canonical_class"] = "complete"
        self.write_coverage(completeness=completeness)
        self.assert_error("must be 'unknown' while the registry is empty")

    def test_nonempty_areas_and_claims_are_rejected(self):
        for key in ("areas", "claims"):
            with self.subTest(key=key):
                self.write_coverage(**{key: ["claim"]})
                self.assert_error(f"coverage.json: {key} must be empty in v1")

        self.write_coverage(areas={})
        self.assert_error("coverage.json: areas must be an array")

    def test_expected_failures_have_deterministic_output_without_traceback(self):
        self.write_text("routines/g36/SOURCE_PIN", "bad\n")
        self.write_text("routines/g36/DONOR_PIN", "bad\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = routine_lint.main(self.root)
        self.assertEqual(result, 1)
        lines = output.getvalue().splitlines()
        self.assertEqual(lines, sorted(lines))
        self.assertEqual(
            lines,
            [
                "routines/g36/DONOR_PIN: must contain one lowercase 40-hex Git commit",
                "routines/g36/SOURCE_PIN: must contain one lowercase 40-hex Git commit",
            ],
        )
        self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
