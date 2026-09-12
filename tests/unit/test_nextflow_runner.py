"""
Unit tests for NextflowRunner pipeline execution bridge.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pipeline.nextflow_runner import NextflowRunner


class TestNextflowRunner(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.workspace_root = Path(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_runner_initialization_and_detection(self):
        runner = NextflowRunner(workspace_root=str(self.workspace_root))
        with patch("shutil.which", return_value=None):
            self.assertFalse(runner.has_nextflow())

    def test_run_pipeline_deterministic(self):
        runner = NextflowRunner(workspace_root=str(self.workspace_root))
        sample_ids = ["S1", "S2", "S3", "S4"]
        output_dir = str(Path(self.tmp_dir) / "results")
        reads_dir = str(Path(self.tmp_dir) / "reads")

        quant_map = runner.run_pipeline(
            project_id="PROJ_TEST_NF",
            sample_ids=sample_ids,
            reads_dir=reads_dir,
            output_dir=output_dir,
            allow_mock=True
        )

        self.assertEqual(len(quant_map), 4)
        for sid in sample_ids:
            self.assertIn(sid, quant_map)
            sf_path = Path(quant_map[sid]) / "quant.sf"
            self.assertTrue(sf_path.exists())


if __name__ == "__main__":
    unittest.main()
