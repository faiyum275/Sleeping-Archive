from __future__ import annotations

import unittest

from backend.pricing import enrich_usage, scale_usage_summary, summarize_usage_records


class UsagePricingTests(unittest.TestCase):
    def test_enrich_usage_adds_output_tokens_and_costs(self):
        usage = enrich_usage(
            {
                "prompt_tokens": 1000,
                "candidate_tokens": 500,
                "thoughts_tokens": 20,
                "total_tokens": 1520,
            },
            source="live",
        )

        self.assertEqual(usage["output_tokens"], 520)
        self.assertEqual(usage["pricing_tier"], "standard")
        self.assertAlmostEqual(usage["input_cost_usd"], 0.00125, places=6)
        self.assertAlmostEqual(usage["output_cost_usd"], 0.0052, places=6)
        self.assertAlmostEqual(usage["total_cost_usd"], 0.00645, places=6)
        self.assertFalse(usage["approximate"])

    def test_summary_keeps_per_call_standard_pricing(self):
        summary = summarize_usage_records(
            [
                {
                    "prompt_tokens": 150000,
                    "candidate_tokens": 50000,
                    "thoughts_tokens": 0,
                    "total_tokens": 200000,
                    "source": "live",
                },
                {
                    "prompt_tokens": 150000,
                    "candidate_tokens": 50000,
                    "thoughts_tokens": 0,
                    "total_tokens": 200000,
                    "source": "live",
                },
            ]
        )

        self.assertEqual(summary["call_count"], 2)
        self.assertEqual(summary["prompt_tokens"], 300000)
        self.assertEqual(summary["output_tokens"], 100000)
        self.assertAlmostEqual(summary["input_cost_usd"], 0.375, places=6)
        self.assertAlmostEqual(summary["output_cost_usd"], 1.0, places=6)
        self.assertAlmostEqual(summary["total_cost_usd"], 1.375, places=6)
        self.assertEqual(summary["sources"], ["live"])

    def test_scale_usage_summary_multiplies_numeric_fields(self):
        scaled = scale_usage_summary(
            {
                "call_count": 4,
                "prompt_tokens": 2000,
                "candidate_tokens": 600,
                "thoughts_tokens": 0,
                "output_tokens": 600,
                "total_tokens": 2600,
                "input_cost_usd": 0.0025,
                "output_cost_usd": 0.006,
                "total_cost_usd": 0.0085,
                "sources": ["estimate"],
                "approximate": True,
            },
            3,
        )

        self.assertEqual(scaled["call_count"], 12)
        self.assertEqual(scaled["prompt_tokens"], 6000)
        self.assertEqual(scaled["output_tokens"], 1800)
        self.assertEqual(scaled["total_tokens"], 7800)
        self.assertAlmostEqual(scaled["total_cost_usd"], 0.0255, places=6)
        self.assertEqual(scaled["sources"], ["estimate"])
        self.assertTrue(scaled["approximate"])


if __name__ == "__main__":
    unittest.main()
