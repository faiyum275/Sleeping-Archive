from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from backend.storage.repository import Repository


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp_test"


def build_temp_repository(root: Path) -> Repository:
    repository = Repository()
    storage_dir = root / "storage"
    repository.storage_dir = storage_dir
    repository.history_dir = storage_dir / "history"
    repository.settings_path = storage_dir / "settings.json"
    repository.loop_state_path = storage_dir / "loop_state.json"
    repository.sil_log_path = storage_dir / "sil_log.json"
    repository.app_meta_path = storage_dir / "app_meta.json"
    repository.ensure_storage()
    return repository


def iso_days_ago(days: int) -> str:
    return (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")


class VisitGreetingTests(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TEMP_ROOT.mkdir(exist_ok=True)
        self.temp_dir = TEST_TEMP_ROOT / f"visit_{uuid4().hex}"
        self.temp_dir.mkdir()
        self.repository = build_temp_repository(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_first_visit_uses_onboarding_greeting(self) -> None:
        meta, greeting, days_away, first_visit = self.repository.record_visit()

        self.assertTrue(first_visit)
        self.assertEqual(days_away, 0)
        self.assertIn("처음", greeting)
        self.assertEqual(meta["visit_count"], 1)
        self.assertIsNotNone(meta["first_visit_at"])

    def test_return_visit_uses_return_branch(self) -> None:
        self.repository.save_meta(
            {
                "first_visit_at": iso_days_ago(7),
                "last_visit_at": iso_days_ago(2),
                "total_runs": 1,
                "visit_count": 3,
                "total_completed_loops": 4,
                "last_return_days": 0,
                "affinity_stage": "warm",
                "last_reentry_log_date": None,
            }
        )

        meta, greeting, days_away, first_visit = self.repository.record_visit()

        self.assertFalse(first_visit)
        self.assertEqual(days_away, 2)
        self.assertIn("2일", greeting)
        self.assertIn("돌아오", greeting)
        self.assertEqual(meta["affinity_stage"], "warm")
        self.assertEqual(meta["last_reentry_log_date"], datetime.now(timezone.utc).date().isoformat())

    def test_long_absence_uses_long_absence_branch(self) -> None:
        self.repository.save_meta(
            {
                "first_visit_at": iso_days_ago(40),
                "last_visit_at": iso_days_ago(21),
                "total_runs": 2,
                "visit_count": 8,
                "total_completed_loops": 10,
                "last_return_days": 0,
                "affinity_stage": "close",
                "last_reentry_log_date": None,
            }
        )

        meta, greeting, days_away, first_visit = self.repository.record_visit()

        self.assertFalse(first_visit)
        self.assertEqual(days_away, 21)
        self.assertIn("21일", greeting)
        self.assertIn("오래", greeting)
        self.assertEqual(meta["affinity_stage"], "close")


if __name__ == "__main__":
    unittest.main()
