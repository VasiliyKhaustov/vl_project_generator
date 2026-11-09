from __future__ import annotations

import unittest

from backend.api.routes import _compute_run_progress, _merge_run_steps


class RunProgressTests(unittest.TestCase):
    def test_progress_does_not_drop_when_steps_regress(self) -> None:
        payload = {
            "status": "processing",
            "steps": {"files_uploaded": True, "tu_extracted": True},
        }
        self.assertEqual(_compute_run_progress(payload, 0), 18)
        self.assertEqual(
            _compute_run_progress(
                {"status": "processing", "steps": {"files_uploaded": True}},
                18,
            ),
            18,
        )

    def test_completed_is_100(self) -> None:
        self.assertEqual(
            _compute_run_progress({"status": "completed", "steps": {}}, 40),
            100,
        )

    def test_merge_keeps_completed_steps(self) -> None:
        merged = _merge_run_steps(
            {"files_uploaded": True, "tu_extracted": True},
            {"files_uploaded": True, "tu_extracted": False, "plan_analyzed": True},
        )
        self.assertTrue(merged["tu_extracted"])
        self.assertTrue(merged["plan_analyzed"])


if __name__ == "__main__":
    unittest.main()
