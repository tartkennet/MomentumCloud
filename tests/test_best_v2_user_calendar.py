import unittest
from datetime import datetime
from best_v2_user_calendar import close_status
from verify_best_v2_production import matches_publication


class CloseCalendarTests(unittest.TestCase):
    def test_holidays_short_session_and_independent_dst(self):
        for stamp,expected in [
            ('2026-11-11T21:16:00Z','2026-11-11'), # Veterans Day is an equity trading day.
            ('2026-11-26T23:00:00Z','2026-11-25'), # Thanksgiving.
            ('2026-11-27T18:16:00Z','2026-11-27'), # 13:00 NY close.
            ('2026-04-03T22:00:00Z','2026-04-02'), # Good Friday.
            ('2026-03-20T20:14:00Z','2026-03-19'), # US DST, Sweden still CET.
            ('2026-03-20T20:16:00Z','2026-03-20'),
            ('2026-10-27T20:16:00Z','2026-10-27'), # Sweden CET, US still DST.
            ('2026-11-09T21:14:00Z','2026-11-06'),
        ]:
            with self.subTest(stamp=stamp):
                self.assertEqual(close_status(datetime.fromisoformat(stamp))['expected_price_as_of'],expected)

    def test_old_ready_journal_cannot_pass_publication_check(self):
        expected=dict(price_as_of='2026-11-11',paper={'journal_sha256':'new'},provenance={'source_commit':'commit'})
        self.assertTrue(matches_publication(expected,expected))
        self.assertFalse(matches_publication({**expected,'paper':{'journal_sha256':'old'}},expected))
