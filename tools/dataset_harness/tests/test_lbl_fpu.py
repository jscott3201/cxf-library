from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.dataset_harness.adapters.lbl_fpu import DatasetError, LblFpuAdapter


FIXTURE = Path(__file__).parent / "fixtures" / "lbl_fpu_tiny"


class LblFpuAdapterTests(unittest.TestCase):
    def copy_fixture(self, destination: Path) -> Path:
        root = destination / "dataset"
        shutil.copytree(FIXTURE, root)
        return root

    def rewrite_csv(self, path: Path, mutate) -> None:
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0])
        fields, rows = mutate(fields, rows)
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_discovers_both_subtypes_and_labels(self):
        adapter = LblFpuAdapter(FIXTURE)
        self.assertEqual(
            [(case.case_id, case.subtype, case.label) for case in adapter.cases],
            [
                ("pfpu_fault_free_tiny", "parallel", "fault_free"),
                ("sfpu_restricted_fan_tiny", "series", "faulted"),
            ],
        )
        self.assertEqual(adapter.select_cases(subtype="parallel")[0].case_id, "pfpu_fault_free_tiny")
        self.assertEqual(adapter.select_cases(severity="synthetic-high")[0].case_id, "sfpu_restricted_fan_tiny")

    def test_unit_conversion_and_gate_lead_are_explicit(self):
        adapter = LblFpuAdapter(FIXTURE)
        loaded = adapter.load_case(adapter.cases[0])
        self.assertAlmostEqual(loaded.rows[0]["primary_airflow"], 100.0, places=1)
        self.assertAlmostEqual(loaded.rows[0]["rht_coil_entering_temp"], 20.0, places=8)
        self.assertAlmostEqual(loaded.rows[0]["rht_delta_t_expected"], 10.0, places=8)
        self.assertEqual(loaded.gate_mask("FPB-0004"), [False, False, True, True, True, True])
        report = loaded.mapping_report(["primary_airflow", "rht_coil_entering_temp"])
        self.assertEqual(len(report["unit_conversions"]), 2)

    def test_duplicate_and_out_of_order_rows_are_reported_and_block_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            csv_path = root / "pfpu_fault_free.csv"

            def duplicate(fields, rows):
                rows[1]["timestamp"] = rows[0]["timestamp"]
                rows[2]["timestamp"] = "2025-12-31T23:59:00Z"
                return fields, rows

            self.rewrite_csv(csv_path, duplicate)
            adapter = LblFpuAdapter(root)
            loaded = adapter.load_case(adapter.cases[0], strict_timeline=False)
            self.assertEqual(loaded.timeline["duplicates"], 1)
            self.assertEqual(loaded.timeline["out_of_order"], 1)
            with self.assertRaisesRegex(DatasetError, "replay refuses to reorder"):
                adapter.load_case(adapter.cases[0], strict_timeline=True)

    def test_missing_interval_splits_state_without_interpolation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            csv_path = root / "sfpu_restricted_fan.csv"

            def remove_row(fields, rows):
                del rows[6]
                return fields, rows

            self.rewrite_csv(csv_path, remove_row)
            adapter = LblFpuAdapter(root)
            loaded = adapter.load_case(adapter.cases[1])
            self.assertEqual(len(loaded.timeline["missing_intervals"]), 1)
            self.assertEqual(len(loaded.evaluable_segments("FPB-0004", ["fan_status", "fan_airflow", "fan_airflow_expected"])), 2)

    def test_boolean_tokens_are_never_interpolated_or_guessed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            csv_path = root / "pfpu_fault_free.csv"

            def corrupt(fields, rows):
                rows[2]["fan_proof"] = "maybe"
                return fields, rows

            self.rewrite_csv(csv_path, corrupt)
            adapter = LblFpuAdapter(root)
            with self.assertRaisesRegex(DatasetError, "neither explicitly true nor false"):
                adapter.load_case(adapter.cases[0])

    def test_missing_required_source_column_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            csv_path = root / "pfpu_fault_free.csv"

            def remove_column(fields, rows):
                fields.remove("fan_proof")
                for row in rows:
                    row.pop("fan_proof")
                return fields, rows

            self.rewrite_csv(csv_path, remove_column)
            adapter = LblFpuAdapter(root)
            with self.assertRaisesRegex(DatasetError, "missing required columns.*fan_proof"):
                adapter.load_case(adapter.cases[0])

    def test_circular_primary_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            manifest_path = root / "lbl_fpu_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            reference = manifest["cases"][0]["mappings"]["primary_airflow_reference"]
            reference["independent"] = True
            reference["derived_from"] = []
            reference["readiness"]["inputs"] = ["primary_cfm"]
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(DatasetError, "reuses the canonical primary airflow source"):
                LblFpuAdapter(root)

    def test_primary_reference_and_fan_proof_cannot_reuse_accused_sources(self):
        for mapping_name, accused_column, message in [
            ("primary_airflow_reference", "primary_cfm", "reference reuses"),
            ("fan_status", "fan_cmd", "proof reuses"),
        ]:
            with self.subTest(mapping=mapping_name), tempfile.TemporaryDirectory() as temporary:
                root = self.copy_fixture(Path(temporary))
                manifest_path = root / "lbl_fpu_manifest.json"
                manifest = json.loads(manifest_path.read_text())
                manifest["cases"][0]["mappings"][mapping_name]["column"] = accused_column
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(DatasetError, message):
                    LblFpuAdapter(root)

    def test_expected_models_cannot_reuse_measured_outcomes(self):
        for expected, actual_column, message in [
            ("fan_airflow_expected", "fan_cfm", "reuses measured fan airflow"),
            ("rht_delta_t_expected", "coil_out_f", "reuses the measured leaving-temperature"),
        ]:
            with self.subTest(mapping=expected), tempfile.TemporaryDirectory() as temporary:
                root = self.copy_fixture(Path(temporary))
                manifest_path = root / "lbl_fpu_manifest.json"
                manifest = json.loads(manifest_path.read_text())
                manifest["cases"][0]["mappings"][expected]["column"] = actual_column
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(DatasetError, message):
                    LblFpuAdapter(root)

    def test_required_gate_applicability_cannot_be_routed_away(self):
        for gate, applies_to in [("baseline_ready", ["FPB-0001"]), ("point_valid", ["FPB-0001"])]:
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as temporary:
                root = self.copy_fixture(Path(temporary))
                manifest_path = root / "lbl_fpu_manifest.json"
                manifest = json.loads(manifest_path.read_text())
                manifest["cases"][0]["gates"][gate]["applies_to"] = applies_to
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(DatasetError, rf"gates\.{gate}: applies_to must cover"):
                    LblFpuAdapter(root)

    def test_startup_lead_restarts_after_a_source_gap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            csv_path = root / "pfpu_fault_free.csv"

            def remove_row(fields, rows):
                del rows[3]
                return fields, rows

            self.rewrite_csv(csv_path, remove_row)
            adapter = LblFpuAdapter(root)
            loaded = adapter.load_case(adapter.cases[0])
            self.assertEqual(loaded.gate_mask("FPB-0004"), [False, False, True, False, False])

    def test_startup_lead_restarts_after_a_missing_required_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            csv_path = root / "pfpu_fault_free.csv"

            def blank_input(fields, rows):
                rows[3]["fan_cfm"] = ""
                return fields, rows

            self.rewrite_csv(csv_path, blank_input)
            adapter = LblFpuAdapter(root)
            loaded = adapter.load_case(adapter.cases[0])
            inputs = ["fan_status", "fan_airflow", "fan_airflow_expected"]
            self.assertEqual(loaded.gate_mask("FPB-0004", inputs), [False, False, True, False, False, False])
            self.assertEqual(loaded.evaluable_segments("FPB-0004", inputs), [[2]])

    def test_gate_and_proof_dependencies_cannot_reuse_target_outcomes(self):
        mutations = [
            (
                lambda case: case["mappings"]["fan_status"].update(derived_from=["fan_airflow"]),
                "proof cannot be derived from fan airflow",
            ),
            (
                lambda case: case["gates"]["airflow_established"].update(derived_from=["fan_cfm"]),
                "gate reuses a target outcome",
            ),
            (
                lambda case: case["gates"]["point_valid"].update(column="primary_cfm"),
                "gate reuses a target outcome",
            ),
        ]
        for mutate, message in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                root = self.copy_fixture(Path(temporary))
                manifest_path = root / "lbl_fpu_manifest.json"
                manifest = json.loads(manifest_path.read_text())
                mutate(manifest["cases"][0])
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(DatasetError, message):
                    LblFpuAdapter(root)

    def test_distinct_measurement_setpoint_and_coil_locations_are_enforced(self):
        mutations = [
            (
                lambda case: case["mappings"]["primary_airflow_sp"].update(column="primary_cfm"),
                "measurement and setpoint require distinct",
            ),
            (
                lambda case: case["mappings"]["rht_coil_leaving_temp"].update(column="coil_in_f"),
                "entering and leaving temperatures require distinct",
            ),
        ]
        for mutate, message in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                root = self.copy_fixture(Path(temporary))
                manifest_path = root / "lbl_fpu_manifest.json"
                manifest = json.loads(manifest_path.read_text())
                mutate(manifest["cases"][0])
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(DatasetError, message):
                    LblFpuAdapter(root)

    def test_series_flow_alias_requires_explicit_topology_proxy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            manifest_path = root / "lbl_fpu_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            series = manifest["cases"][1]
            series["mappings"]["fan_airflow"]["column"] = "primary_cfm"
            series["mappings"]["fan_airflow"]["proxy"] = (
                "Topology-proven SFPU series path; primary and fan airflow are the same physical stream."
            )
            manifest_path.write_text(json.dumps(manifest))
            adapter = LblFpuAdapter(root)
            self.assertEqual(
                adapter.cases[1].mappings["fan_airflow"].column,
                adapter.cases[1].mappings["primary_airflow"].column,
            )

    def test_additional_independent_host_gate_is_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            manifest_path = root / "lbl_fpu_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["cases"][0]["gates"]["hydronic_available"] = {
                "column": "hydronic_ready",
                "true_values": ["1"],
                "false_values": ["0"],
                "applies_to": ["FPB-0003", "FPB-0006"],
                "description": "Fixture hydronic availability gate.",
                "inventory_evidence": "Original fixture host truth field.",
                "derived_from": [],
            }
            manifest_path.write_text(json.dumps(manifest))
            csv_path = root / "pfpu_fault_free.csv"

            def add_gate_column(fields, rows):
                fields.append("hydronic_ready")
                for row in rows:
                    row["hydronic_ready"] = "1"
                return fields, rows

            self.rewrite_csv(csv_path, add_gate_column)
            adapter = LblFpuAdapter(root)
            loaded = adapter.load_case(adapter.cases[0])
            self.assertIn("hydronic_available", loaded.spec.gates)

    def test_unit_conversion_overflow_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            manifest_path = root / "lbl_fpu_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["cases"][0]["mappings"]["primary_airflow"]["unit"] = "m3/s"
            manifest_path.write_text(json.dumps(manifest))
            csv_path = root / "pfpu_fault_free.csv"

            def overflow(fields, rows):
                rows[0]["primary_cfm"] = "1e308"
                return fields, rows

            self.rewrite_csv(csv_path, overflow)
            adapter = LblFpuAdapter(root)
            with self.assertRaisesRegex(DatasetError, "unit conversion produced a non-finite"):
                adapter.load_case(adapter.cases[0])

    def test_case_identity_and_target_labels_require_safe_inventory_provenance(self):
        mutations = [
            (lambda case: case.update(id="../escape"), "case id must be"),
            (lambda case: case.update(inventory_evidence=""), "inventory_evidence is required"),
            (lambda case: case.update(fault_class=None), "faulted cases require"),
        ]
        for mutate, message in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                root = self.copy_fixture(Path(temporary))
                manifest_path = root / "lbl_fpu_manifest.json"
                manifest = json.loads(manifest_path.read_text())
                mutate(manifest["cases"][1])
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(DatasetError, message):
                    LblFpuAdapter(root)

    def test_malformed_csv_shapes_fail_as_dataset_errors(self):
        def duplicate_header(text: str) -> str:
            lines = text.splitlines()
            fields = lines[0].split(",")
            fields[-1] = fields[-2]
            lines[0] = ",".join(fields)
            return "\n".join(lines) + "\n"

        def empty_header(text: str) -> str:
            lines = text.splitlines()
            fields = lines[0].split(",")
            fields[-1] = ""
            lines[0] = ",".join(fields)
            return "\n".join(lines) + "\n"

        def extra_cell(text: str) -> str:
            lines = text.splitlines()
            lines[1] += ",extra"
            return "\n".join(lines) + "\n"

        def missing_cell(text: str) -> str:
            lines = text.splitlines()
            lines[1] = lines[1].rsplit(",", 1)[0]
            return "\n".join(lines) + "\n"

        for mutate, message in [
            (duplicate_header, "duplicate column headers"),
            (empty_header, "empty column header"),
            (extra_cell, "more values than the header"),
            (missing_cell, "missing source value"),
        ]:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                root = self.copy_fixture(Path(temporary))
                csv_path = root / "pfpu_fault_free.csv"
                csv_path.write_text(mutate(csv_path.read_text()))
                adapter = LblFpuAdapter(root)
                with self.assertRaisesRegex(DatasetError, message):
                    adapter.load_case(adapter.cases[0])

    def test_substep_or_nonintegral_cadence_blocks_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            csv_path = root / "pfpu_fault_free.csv"

            def shorten_interval(fields, rows):
                rows[1]["timestamp"] = "2026-01-01T00:00:30Z"
                return fields, rows

            self.rewrite_csv(csv_path, shorten_interval)
            adapter = LblFpuAdapter(root)
            loaded = adapter.load_case(adapter.cases[0], strict_timeline=False)
            self.assertEqual(loaded.timeline["irregular_intervals"], 2)
            with self.assertRaisesRegex(DatasetError, "refuses to reorder or resample"):
                adapter.load_case(adapter.cases[0])

    def test_proxy_disclosure_is_in_mapping_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            manifest_path = root / "lbl_fpu_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["cases"][0]["mappings"]["fan_status"]["proxy"] = "current threshold, not rotation proof"
            manifest_path.write_text(json.dumps(manifest))
            adapter = LblFpuAdapter(root)
            loaded = adapter.load_case(adapter.cases[0])
            report = loaded.mapping_report(["fan_status"])
            self.assertEqual(report["proxies"][0]["point"], "fan_status")


if __name__ == "__main__":
    unittest.main()
