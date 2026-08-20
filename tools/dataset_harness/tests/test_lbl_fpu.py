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
            reference["readiness"]["inputs"] = ["primary_airflow"]
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(DatasetError, "must be explicitly independent"):
                LblFpuAdapter(root)

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
