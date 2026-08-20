import csv
import tempfile
import unittest
from pathlib import Path

from tools.simharness import harness


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.old_step = harness.STEP_S
        harness.STEP_S = 3600

    def tearDown(self):
        harness.STEP_S = self.old_step

    @staticmethod
    def write_day(path: Path, month: int, day: int) -> None:
        with path.open("w", newline="") as f:
            rows = csv.writer(f)
            rows.writerow(["Date/Time", "value"])
            for hour in range(1, 25):
                rows.writerow([f" {month:02}/{day:02}  {hour:02}:00:00", hour])

    def test_exact_requested_period_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "eplusout.csv"
            self.write_day(path, 7, 6)
            result = harness.validate_csv_timeline(path, (7, 6), (7, 6))
            self.assertEqual(result["samples"], 24)
            self.assertEqual(result["observed_last"], "07/06  24:00:00")

    def test_reused_csv_cannot_be_relabelled(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "eplusout.csv"
            self.write_day(path, 7, 6)
            with self.assertRaisesRegex(ValueError, "observed period does not match"):
                harness.validate_csv_timeline(path, (1, 6), (1, 6))

    def test_missing_runperiod_is_created(self):
        model = {}
        harness.configure_period_and_timestep(model, (1, 6), (1, 12))
        self.assertEqual(len(model["RunPeriod"]), 1)
        period = next(iter(model["RunPeriod"].values()))
        self.assertEqual(period["begin_month"], 1)
        self.assertEqual(period["end_day_of_month"], 12)


class ReplayResultTests(unittest.TestCase):
    def test_relative_and_absolute_replay_paths_are_isolated(self):
        log = """relative/replay/TOWER-0005__one
  PASS scenario_one
/tmp/out/replay/CHW-0009__one
  FAIL scenario_two
relative/replay/TOWER-0005__two
  FAIL scenario_three
"""
        self.assertEqual(harness.replay_results(log), {
            "TOWER-0005__one": "pass",
            "CHW-0009__one": "fail",
            "TOWER-0005__two": "fail",
        })


if __name__ == "__main__":
    unittest.main()
