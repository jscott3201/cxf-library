from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from tools.dataset_harness import harness


TEST_ROOT = Path(__file__).parent
FIXTURE = TEST_ROOT / "fixtures" / "lbl_fpu_tiny"
FAKE_VERIFIER = TEST_ROOT / "fake_verifier.py"


def tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class DatasetHarnessCliTests(unittest.TestCase):
    def invoke(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = harness.main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_list_adapters_is_discoverable(self):
        code, stdout, stderr = self.invoke(["list-adapters"])
        self.assertEqual(code, 0, stderr)
        self.assertIn("lbl-fpu/v1", stdout)

    def test_inspect_supports_subtype_case_kind_and_date_filters(self):
        code, stdout, stderr = self.invoke(
            [
                "inspect",
                "--adapter",
                "lbl-fpu",
                "--dataset",
                str(FIXTURE),
                "--subtype",
                "parallel",
                "--case-kind",
                "fault-free",
                "--start",
                "2026-01-01",
                "--end",
                "2026-01-01",
            ]
        )
        self.assertEqual(code, 0, stderr)
        self.assertIn("pfpu_fault_free_tiny", stdout)
        self.assertNotIn("sfpu_restricted_fan_tiny", stdout)
        self.assertIn("mapping primary_airflow: column='primary_cfm'", stdout)
        self.assertIn("inventory_evidence=", stdout)
        self.assertIn("gate point_valid:", stdout)

    def test_replay_invokes_trace_contract_and_writes_deterministic_schema(self):
        before = tree_fingerprint(FIXTURE)
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            first = output_root / "first.json"
            second = output_root / "second.json"
            base = [
                "replay",
                "--adapter",
                "lbl-fpu",
                "--dataset",
                str(FIXTURE),
                "--rules",
                "FPB-0001,FPB-0004",
                "--verifier",
                str(FAKE_VERIFIER),
            ]
            code, stdout, stderr = self.invoke([*base, "--output", str(first)])
            self.assertEqual(code, 0, stderr)
            self.assertIn("wrote", stdout)
            code, _, stderr = self.invoke([*base, "--output", str(second)])
            self.assertEqual(code, 0, stderr)
            first_document = json.loads(first.read_text())
            second_document = json.loads(second.read_text())
            self.assertEqual(first_document, second_document)
            self.assertEqual(first_document["schema"], "cxf-library/dataset-validation/v1")
            self.assertEqual(first_document["summary"]["results"], 4)
            self.assertEqual(first_document["summary"]["fault_free_alarm_samples"], 0)
            self.assertEqual(
                sorted(path.name for path in output_root.iterdir()),
                ["first.json", "second.json"],
                "temporary vectors must be removed and all writes must stay in the selected output directory",
            )
        self.assertEqual(tree_fingerprint(FIXTURE), before, "replay must never modify source data")

    def test_missing_dataset_manifest_has_readable_exit_two(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, _, stderr = self.invoke(
                ["inspect", "--adapter", "lbl-fpu", "--dataset", temporary]
            )
        self.assertEqual(code, 2)
        self.assertIn("missing", stderr)
        self.assertIn("lbl_fpu_manifest.json", stderr)

    def test_verifier_command_uses_python_for_test_double(self):
        command = harness.verifier_command(FAKE_VERIFIER, Path("rule"), Path("vectors.json"))
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[2], "--trace-json")

    def test_invalid_date_and_protected_output_fail_without_writing(self):
        code, _, stderr = self.invoke(
            [
                "inspect",
                "--adapter",
                "lbl-fpu",
                "--dataset",
                str(FIXTURE),
                "--start",
                "2026-99-99",
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("invalid date selector", stderr)

        protected_output = FIXTURE / "must-not-exist.json"
        code, _, stderr = self.invoke(
            [
                "replay",
                "--adapter",
                "lbl-fpu",
                "--dataset",
                str(FIXTURE),
                "--rules",
                "FPB-0001",
                "--verifier",
                str(FAKE_VERIFIER),
                "--output",
                str(protected_output),
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("must stay under the ignored target", stderr)
        self.assertFalse(protected_output.exists())

    def test_case_selectors_reject_unknown_and_duplicate_ids(self):
        for selector, message in [
            ("pfpu_fault_free_tiny,typo", "unknown case ids"),
            ("pfpu_fault_free_tiny,pfpu_fault_free_tiny", "contains duplicates"),
        ]:
            with self.subTest(selector=selector):
                code, _, stderr = self.invoke(
                    [
                        "inspect",
                        "--adapter",
                        "lbl-fpu",
                        "--dataset",
                        str(FIXTURE),
                        "--case",
                        selector,
                    ]
                )
                self.assertEqual(code, 2)
                self.assertIn(message, stderr)

    def test_target_detection_ignores_pre_fault_alarms(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "dataset"
            shutil.copytree(FIXTURE, root)
            manifest_path = root / "lbl_fpu_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["cases"][1]["fault_start"] = "2026-01-02T00:05:00Z"
            manifest_path.write_text(json.dumps(manifest))
            adapter = harness.ADAPTERS["lbl-fpu"](root)
            loaded = adapter.load_case(adapter.cases[1])

            def pre_fault_trace(_verifier, _rule, vectors_path):
                vectors = json.loads(vectors_path.read_text())
                step = vectors["clock"]["step_s"]
                count = int(vectors["clock"]["horizon_s"] // step) + 1
                return {
                    "schema": harness.TRACE_SCHEMA,
                    "engine_pin": harness.ENGINE_PIN,
                    "engine_source_revision": harness.ENGINE_PIN,
                    "rule_content_id": "cxf:test:pre-fault",
                    "clock": {"step_s": step},
                    "scenarios": [
                        {
                            "name": scenario["name"],
                            "samples": [
                                {"t": index * step, "outputs": {"yFault": index <= 6}}
                                for index in range(count)
                            ],
                        }
                        for scenario in vectors["scenarios"]
                    ],
                }

            with tempfile.TemporaryDirectory() as vectors_root, mock.patch.object(
                harness, "run_trace", side_effect=pre_fault_trace
            ):
                result = harness.replay_case_rule(
                    loaded, "FPB-0004", Path(vectors_root), FAKE_VERIFIER
                )
            metrics = result["metrics"]
            self.assertGreater(metrics["alarm_samples"], 0)
            self.assertGreater(metrics["target_post_fault_evaluable_samples"], 0)
            self.assertGreater(metrics["target_post_fault_alarm_samples"], 0)
            self.assertEqual(metrics["target_post_fault_alarm_episodes"], 0)
            self.assertEqual(metrics["target_detected_rule_case_pairs"], 0)
            self.assertEqual(metrics["target_evaluable_rule_case_pairs"], 1)
            self.assertIsNone(metrics["median_detection_latency_s"])

    def test_malformed_trace_shapes_fail_as_dataset_errors(self):
        valid = {
            "schema": harness.TRACE_SCHEMA,
            "engine_pin": harness.ENGINE_PIN,
            "engine_source_revision": harness.ENGINE_PIN,
            "rule_content_id": harness.recorded_rule_content_id("FPB-0001"),
            "clock": {"step_s": 60},
            "scenarios": [],
        }
        variants = [
            ([], "root must be an object"),
            ({**valid, "clock": True}, "clock must be an object"),
            ({**valid, "clock": {"step_s": True}}, "step_s must be a finite positive"),
            ({**valid, "clock": {"step_s": float("nan")}}, "step_s must be a finite positive"),
        ]
        for payload, message in variants:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                vectors = Path(temporary) / "vectors.json"
                vectors.write_text("{}")

                def fake_run(*_args, **kwargs):
                    kwargs["stdout"].write(json.dumps(payload).encode())
                    return types.SimpleNamespace(returncode=0)

                with mock.patch.object(harness.subprocess, "run", side_effect=fake_run):
                    with self.assertRaisesRegex(harness.DatasetError, message):
                        harness.run_trace(FAKE_VERIFIER, "FPB-0001", vectors)

    def test_malformed_sample_shapes_fail_as_dataset_errors(self):
        adapter = harness.ADAPTERS["lbl-fpu"](FIXTURE)
        loaded = adapter.load_case(adapter.cases[0])

        def trace_with(sample_mutation):
            def make_trace(_verifier, rule, vectors_path):
                vectors = json.loads(vectors_path.read_text())
                step = vectors["clock"]["step_s"]
                count = int(vectors["clock"]["horizon_s"] // step) + 1
                scenarios = []
                for scenario in vectors["scenarios"]:
                    samples = [
                        {"t": index * step, "outputs": {"yFault": False}}
                        for index in range(count)
                    ]
                    replacement = sample_mutation(samples)
                    if replacement is not None:
                        samples = replacement
                    scenarios.append({"name": scenario["name"], "samples": samples})
                return {
                    "schema": harness.TRACE_SCHEMA,
                    "engine_pin": harness.ENGINE_PIN,
                    "engine_source_revision": harness.ENGINE_PIN,
                    "rule_content_id": harness.recorded_rule_content_id(rule),
                    "clock": {"step_s": step},
                    "scenarios": scenarios,
                }

            return make_trace

        variants = [
            (lambda _samples: {}, "samples must be a list"),
            (lambda samples: samples.__setitem__(0, True), "sample must be an object"),
            (lambda samples: samples[0].update(t=True), "timestamp does not match"),
            (lambda samples: samples[0].update(outputs=True), "outputs must be an object"),
        ]
        for mutate, message in variants:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary, mock.patch.object(
                harness, "run_trace", side_effect=trace_with(mutate)
            ):
                with self.assertRaisesRegex(harness.DatasetError, message):
                    harness.replay_case_rule(loaded, "FPB-0001", Path(temporary), FAKE_VERIFIER)

    def test_invalid_utf8_csv_has_clean_cli_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "dataset"
            shutil.copytree(FIXTURE, root)
            (root / "pfpu_fault_free.csv").write_bytes(b"\xff\xfe")
            code, _, stderr = self.invoke(
                [
                    "inspect",
                    "--adapter",
                    "lbl-fpu",
                    "--dataset",
                    str(root),
                    "--case",
                    "pfpu_fault_free_tiny",
                ]
            )
            self.assertEqual(code, 2)
            self.assertIn("codec can't decode", stderr)
            self.assertNotIn("Traceback", stderr)


if __name__ == "__main__":
    unittest.main()
