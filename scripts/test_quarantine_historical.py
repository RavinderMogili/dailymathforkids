import json
import unittest

import quarantine_historical


class HistoricalQuarantineTests(unittest.TestCase):
    def test_manifest_generation_is_deterministic_and_has_both_dispositions(self):
        first = quarantine_historical.build_manifest(quarantine_historical.DAILY_DIR)
        second = quarantine_historical.build_manifest(quarantine_historical.DAILY_DIR)
        self.assertEqual(
            json.dumps(first, ensure_ascii=False, sort_keys=True),
            json.dumps(second, ensure_ascii=False, sort_keys=True),
        )
        self.assertGreater(first["summary"]["hidden_items"], 0)
        self.assertGreater(first["summary"]["flagged_items"], 0)
        self.assertEqual(
            first["summary"]["hidden_items"] + first["summary"]["flagged_items"],
            len(first["items"]),
        )

    def test_only_explicit_hidden_identity_is_quarantined(self):
        manifest = {
            "items": [
                {
                    "date": "2026-08-17",
                    "grade": "G2",
                    "question_index": 3,
                    "disposition": "hidden",
                    "restoration_status": "quarantined",
                },
                {
                    "date": "2026-08-17",
                    "grade": "G2",
                    "question_index": 4,
                    "disposition": "flagged",
                    "restoration_status": "visible",
                },
            ]
        }
        self.assertTrue(quarantine_historical.is_quarantined("2026-08-17", "G2", 3, manifest))
        self.assertFalse(quarantine_historical.is_quarantined("2026-08-17", "G2", 4, manifest))
        self.assertFalse(quarantine_historical.is_quarantined("2026-08-17", "G2", 5, manifest))
        self.assertEqual(
            quarantine_historical.filter_archive_dates(["2026-08-17"], manifest),
            ["2026-08-17"],
        )


if __name__ == "__main__":
    unittest.main()
