"""
Unit tests for benchmarks/directional_validator.py
"""

import unittest
import pandas as pd
from benchmarks.directional_validator import DirectionalBenchmarkValidator

class TestDirectionalBenchmarkValidator(unittest.TestCase):

    def test_calculate_directional_metrics(self):
        pipeline_df = pd.DataFrame({
            "gene_id": ["AT1G01010", "AT3G24650", "AT5G66170", "AT1G22710"],
            "shrunk_log2FoldChange": [2.5, -1.8, 0.5, -0.2],
            "padj": [0.01, 0.02, 0.20, 0.50]
        })
        reference_df = pd.DataFrame({
            "gene_id": ["AT1G01010", "AT3G24650", "AT5G66170", "AT1G22710"],
            "log2FoldChange": [2.3, -1.6, 0.4, -0.3],
            "padj": [0.005, 0.01, 0.15, 0.60]
        })

        metrics = DirectionalBenchmarkValidator.calculate_directional_metrics(
            pipeline_df, reference_df
        )

        self.assertGreaterEqual(metrics["spearman_log2fc_rho"], 0.9)
        self.assertEqual(metrics["directional_matrix"]["UP_UP"], 2)
        self.assertEqual(metrics["directional_matrix"]["DOWN_DOWN"], 2)
        self.assertEqual(metrics["directional_matrix"]["UP_DOWN"], 0)
        self.assertEqual(metrics["directional_matrix"]["DOWN_UP"], 0)
        self.assertEqual(metrics["directional_matrix"]["concordance_rate"], 1.0)
        self.assertTrue(metrics["is_benchmark_passed"])

if __name__ == "__main__":
    unittest.main()
