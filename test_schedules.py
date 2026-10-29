#!/usr/bin/env python3
"""Checks the scheduler manifest and its date rules. Run: python test_schedules.py"""
import ast
import unittest
from datetime import date, timedelta
from pathlib import Path

import schedules

SERVER_TREE = ast.parse(Path(__file__).with_name("server.py").read_text(encoding="utf-8"))


class ScheduleManifestTests(unittest.TestCase):
    def test_calendar_and_lifecycle_poll_intervals(self):
        self.assertEqual(schedules.CALENDAR_SYNC_INTERVAL_SECONDS, 300)
        self.assertEqual(schedules.LIFECYCLE_INTERVAL_SECONDS, 3600)

    def test_periodic_jobs_are_unique_and_have_positive_intervals(self):
        names = [job.name for job in schedules.PERIODIC_JOBS]
        handlers = [job.handler for job in schedules.PERIODIC_JOBS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(handlers), len(set(handlers)))
        self.assertTrue(all(job.interval_seconds > 0 for job in schedules.PERIODIC_JOBS))

    def test_periodic_handlers_exist_in_server(self):
        defined = {node.name for node in ast.walk(SERVER_TREE)
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue({job.handler for job in schedules.PERIODIC_JOBS} <= defined)

    def test_treasurer_sheet_is_manual_only(self):
        handlers = {job.handler for job in schedules.PERIODIC_JOBS}
        self.assertIn("treasurer_sheet", schedules.MANUAL_ONLY_TASKS)
        self.assertNotIn("daily_treasurer_if_due", handlers)
        self.assertNotIn("sweep_treasurer_sheet", handlers)
        loop = next(node for node in SERVER_TREE.body
                    if isinstance(node, ast.FunctionDef) and node.name == "scheduler_loop")
        calls = {node.func.id for node in ast.walk(loop)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertNotIn("daily_treasurer_if_due", calls)
        self.assertNotIn("sweep_treasurer_sheet", calls)

    def test_class_date_windows_include_boundaries(self):
        cases = (
            ("low_enrollment_alert", 8, True),
            ("low_enrollment_alert", 14, True),
            ("low_enrollment_alert", 7, False),
            ("low_enrollment_alert", 15, False),
            ("after_class_note_request", -1, True),
            ("student_thank_you", -4, True),
            ("student_thank_you", -2, True),
            ("student_thank_you", -5, False),
            ("marketing_request", -6, True),
            ("marketing_request", -3, True),
            ("marketing_request", -2, False),
        )
        for rule, days, expected in cases:
            with self.subTest(rule=rule, days=days):
                self.assertEqual(schedules.class_event_due(rule, days), expected)

    def test_deadline_campaign_cadence_and_deadline_day(self):
        start = date(2026, 11, 1)
        deadline = date(2026, 11, 15)
        self.assertTrue(schedules.deadline_campaign_due(start, start, deadline, 7))
        self.assertTrue(schedules.deadline_campaign_due(start + timedelta(days=7), start, deadline, 7))
        self.assertTrue(schedules.deadline_campaign_due(deadline, start, deadline, 7))
        self.assertFalse(schedules.deadline_campaign_due(start + timedelta(days=1), start, deadline, 7))
        self.assertFalse(schedules.deadline_campaign_due(deadline + timedelta(days=1), start, deadline, 7))


if __name__ == "__main__":
    unittest.main()