from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
