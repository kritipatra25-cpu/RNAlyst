"""
Unit tests for Structured Data Ingestion Tools (Step 4).
"""

import os
import gzip
import shutil
import tempfile
import unittest
from pathlib import Path
import pandas as pd

from agent.tools.ingestion_tools import (
    CreateProjectTool,
    ValidateFASTQTool,
    QuantifyReadsTool,
    FetchOSDRStudyTool
)
from agent.tools.registry import ToolRegistry


class TestIngestionTools(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.projects_dir = Path(self.tmp_dir) / "projects"
        self.configs_dir = Path(self.tmp_dir) / "configs"
        self.sandbox_dir = Path(self.tmp_dir) / "uploads"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_project_tool(self):
        """Test CreateProjectTool execution via ToolRegistry."""
        tool = CreateProjectTool(
            projects_dir=str(self.projects_dir),
            configs_dir=str(self.configs_dir)
        )

        res = tool.run({
            "project_id": "INGEST_TOOL_PROJ",
            "name": "Ingestion Tool Test Project",
            "origin": "LOCAL_FASTQ",
            "organism": "Mus musculus",
            "condition_column": "condition",
            "sample_ids": ["S1", "S2", "S3", "S4", "S5", "S6"],
            "conditions": ["Flight", "Flight", "Flight", "Ground", "Ground", "Ground"],
            "numerator_level": "Flight",
            "reference_level": "Ground"
        })

        self.assertEqual(res.status, "success")
        self.assertEqual(res.result["project_id"], "INGEST_TOOL_PROJ")
        self.assertEqual(res.result["total_samples"], 6)
        self.assertEqual(res.result["replicate_status"], "INFERENTIAL")
        self.assertTrue((self.projects_dir / "INGEST_TOOL_PROJ" / "project.json").exists())

    def test_validate_fastq_tool(self):
        """Test ValidateFASTQTool execution on gzipped FASTQ file."""
        fastq_content = (
            "@SEQ1/1\nATGCATGCATGC\n+\nIIIIIIIIIIII\n"
            "@SEQ2/1\nGCTAGCTAGCTA\n+\nIIIIIIIIIIII\n"
        ).encode("utf-8")

        gz_path = Path(self.tmp_dir) / "sample_valid.fastq.gz"
        with gzip.open(gz_path, "wb") as f:
            f.write(fastq_content)

        tool = ValidateFASTQTool(sandbox_root=str(self.sandbox_dir))
        res = tool.run({"fastq_file_path": str(gz_path)})

        self.assertEqual(res.status, "success")
        self.assertTrue(res.result["is_valid"])

    def test_quantify_reads_tool(self):
        """Test QuantifyReadsTool aggregation."""
        # 1. Initialize project first
        pm_tool = CreateProjectTool(
            projects_dir=str(self.projects_dir),
            configs_dir=str(self.configs_dir)
        )
        pm_tool.run({
            "project_id": "QUANT_PROJ",
            "name": "Quant Project",
            "origin": "LOCAL_FASTQ",
            "organism": "Arabidopsis thaliana",
            "condition_column": "condition",
            "sample_ids": ["S1"],
            "conditions": ["Flight"],
            "numerator_level": "Flight",
            "reference_level": "Ground"
        })

        # 2. Create mock quant.sf
        s1_dir = Path(self.tmp_dir) / "S1"
        s1_dir.mkdir(parents=True, exist_ok=True)
        sf_path = s1_dir / "quant.sf"
        df_quant = pd.DataFrame([
            {"Name": "AT1G01010.1", "Length": 1000, "EffectiveLength": 900.0, "TPM": 50.0, "NumReads": 100.0}
        ])
        df_quant.to_csv(sf_path, sep="\t", index=False)

        tool = QuantifyReadsTool(projects_dir=str(self.projects_dir))
        res = tool.run({"project_id": "QUANT_PROJ", "quant_directories": {"S1": str(s1_dir)}})

        self.assertEqual(res.status, "success")
        self.assertEqual(res.result["project_id"], "QUANT_PROJ")
        self.assertTrue(Path(res.result["counts_matrix_path"]).exists())

    def test_tool_registry_registration(self):
        """Verify all 4 ingestion tools register successfully into ToolRegistry."""
        registry = ToolRegistry()

        c_tool = CreateProjectTool(projects_dir=str(self.projects_dir), configs_dir=str(self.configs_dir))
        v_tool = ValidateFASTQTool(sandbox_root=str(self.sandbox_dir))
        q_tool = QuantifyReadsTool(projects_dir=str(self.projects_dir))
        f_tool = FetchOSDRStudyTool()

        registry.register(c_tool)
        registry.register(v_tool)
        registry.register(q_tool)
        registry.register(f_tool)

        schemas = registry.get_tool_schemas()
        tool_names = [s["name"] for s in schemas]

        self.assertIn("create_project", tool_names)
        self.assertIn("validate_fastq", tool_names)
        self.assertIn("quantify_reads", tool_names)
        self.assertIn("fetch_osdr_study", tool_names)


if __name__ == "__main__":
    unittest.main()
