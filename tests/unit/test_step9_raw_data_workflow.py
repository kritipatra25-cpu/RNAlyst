"""
Step 5 End-to-End Integration & Benchmark Test: Dataset-Agnostic Raw Data Workflow.

Executes the complete raw FASTQ workflow for an arbitrary researcher dataset:
Project Creation -> FASTQ Validation -> Read Quantification -> Count Matrix Generation ->
PyDESeq2 Execution -> Volcano Plot Visualization -> Candidate Gene Annotation ->
Prioritization -> Literature Query -> Evidence Synthesis.
"""

import os
import gzip
import shutil
import tempfile
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

from pipeline.project_manager import ProjectManager
from pipeline.upload_handler import UploadHandler
from pipeline.quantification_runner import QuantificationRunner
from pipeline.backend_api import RNASeqBackendAPI, AnalysisRequest
from agent.tools.ingestion_tools import (
    CreateProjectTool, ValidateFASTQTool, QuantifyReadsTool
)
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.visualization_tools import VolcanoPlotTool
from agent.tools.gene_annotation_tool import GeneAnnotationTool
from agent.tools.candidate_prioritization_tool import CandidatePrioritizationTool
from agent.tools.literature_tool import LiteratureTool
from agent.tools.registry import ToolRegistry


class TestStep9RawDataWorkflow(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.projects_dir = Path(self.tmp_dir) / "projects"
        self.configs_dir = Path(self.tmp_dir) / "configs"
        self.sandbox_dir = Path(self.tmp_dir) / "uploads"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def create_mock_fastq_pair(self, sample_id: str) -> tuple:
        """Create valid gzipped FASTQ file pair for sample."""
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        r1_path = self.sandbox_dir / f"{sample_id}_R1.fastq.gz"
        r2_path = self.sandbox_dir / f"{sample_id}_R2.fastq.gz"

        r1_content = f"@{sample_id}_READ1/1\nATGCATGCATGC\n+\nIIIIIIIIIIII\n".encode("utf-8")
        r2_content = f"@{sample_id}_READ1/2\nTACGTACGTACG\n+\nIIIIIIIIIIII\n".encode("utf-8")

        with gzip.open(r1_path, "wb") as f1, gzip.open(r2_path, "wb") as f2:
            f1.write(r1_content)
            f2.write(r2_content)

        return r1_path, r2_path

    def create_mock_quant_sf(self, sample_dir: Path, gene_counts: dict):
        """Create mock quant.sf file mapping transcripts to count estimates."""
        sample_dir.mkdir(parents=True, exist_ok=True)
        sf_path = sample_dir / "quant.sf"
        rows = []
        for gid, count in gene_counts.items():
            rows.append({
                "Name": f"{gid}.1",
                "Length": 1000,
                "EffectiveLength": 900.0,
                "TPM": float(count * 10),
                "NumReads": float(count)
            })
        df = pd.DataFrame(rows)
        df.to_csv(sf_path, sep="\t", index=False)
        return sf_path

    def test_end_to_end_raw_data_workflow(self):
        """Execute full 9-step dataset-agnostic raw data pipeline for arbitrary dataset 'ARBITRARY_STUDY_2026'."""
        project_id = "ARBITRARY_STUDY_2026"
        sample_ids = ["S1", "S2", "S3", "S4", "S5", "S6"]
        conditions = ["Treatment", "Treatment", "Treatment", "Control", "Control", "Control"]

        # STEP 1: Create Project
        create_tool = CreateProjectTool(
            projects_dir=str(self.projects_dir),
            configs_dir=str(self.configs_dir)
        )
        res_create = create_tool.run({
            "project_id": project_id,
            "name": "Arbitrary User Study 2026",
            "origin": "LOCAL_FASTQ",
            "organism": "Arabidopsis thaliana",
            "condition_column": "condition",
            "sample_ids": sample_ids,
            "conditions": conditions,
            "numerator_level": "Treatment",
            "reference_level": "Control"
        })
        self.assertEqual(res_create.status, "success")
        self.assertEqual(res_create.result["project_id"], project_id)

        # STEP 2: Validate FASTQ Reads for Sample S1
        r1, r2 = self.create_mock_fastq_pair("S1")
        val_tool = ValidateFASTQTool(sandbox_root=str(self.sandbox_dir))
        res_val = val_tool.run({
            "fastq_file_path": str(r1),
            "paired_file_path": str(r2)
        })
        self.assertEqual(res_val.status, "success")
        self.assertTrue(res_val.result["is_valid"])

        # STEP 3: Quantify Reads across 6 Samples & Generate Count Matrix
        np.random.seed(42)
        quant_map = {}
        for idx, sid in enumerate(sample_ids):
            s_dir = Path(self.tmp_dir) / f"quant_{sid}"
            is_treatment = conditions[idx] == "Treatment"

            # Create 20 mock genes with differential signal
            gene_counts = {}
            for g_idx in range(1, 21):
                gid = f"AT{g_idx:02d}G10000"
                base_count = 100 + g_idx * 50
                if g_idx <= 5:  # First 5 genes up-regulated in Treatment
                    mult = 4.0 if is_treatment else 1.0
                else:
                    mult = 1.0
                noise = np.random.randint(-5, 5)
                gene_counts[gid] = max(10, int(base_count * mult + noise))

            self.create_mock_quant_sf(s_dir, gene_counts)
            quant_map[sid] = str(s_dir)

        quant_tool = QuantifyReadsTool(projects_dir=str(self.projects_dir))
        res_quant = quant_tool.run({
            "project_id": project_id,
            "quant_directories": quant_map
        })
        self.assertEqual(res_quant.status, "success")
        counts_csv_path = Path(res_quant.result["counts_matrix_path"])
        self.assertTrue(counts_csv_path.exists())

        # Verify count matrix dimensions
        df_counts = pd.read_csv(counts_csv_path)
        self.assertEqual(len(df_counts), 20)
        self.assertIn("gene_id", df_counts.columns)

        # Shared backend API with custom configs_dir
        api = RNASeqBackendAPI(configs_dir=str(self.configs_dir))

        # STEP 4: Run DESeq2 via DESeq2Tool
        deseq2_tool = DESeq2Tool(backend_api=api)
        res_deseq = deseq2_tool.run({
            "dataset_id": project_id,
            "contrast_id": "Treatment_vs_Control",
            "fdr_cutoff": 0.05,
            "lfc_cutoff": 1.0
        })
        self.assertEqual(res_deseq.status, "success")
        self.assertIn("execution_status", res_deseq.result)

        # STEP 5: Generate Volcano Plot using generated DE output
        de_csv_path = self.projects_dir / project_id / "results" / "contrasts" / "Treatment_vs_Control.csv"
        volcano_tool = VolcanoPlotTool()
        res_volcano = volcano_tool.run({
            "de_results_path": str(de_csv_path),
            "output_path": str(self.projects_dir / project_id / "results" / "volcano_plot.png"),
            "fdr_thresh": 0.05,
            "lfc_thresh": 1.0,
            "title": "Treatment vs Control Volcano Plot"
        })
        self.assertEqual(res_volcano.status, "success")
        self.assertTrue(len(res_volcano.artifacts) > 0)
        self.assertTrue(Path(res_volcano.artifacts[0].path).exists())

        # STEP 6: Annotate Gene
        ann_tool = GeneAnnotationTool()
        res_ann = ann_tool.run({
            "gene_id": "AT01G10000",
            "organism": "Arabidopsis thaliana"
        })
        self.assertEqual(res_ann.status, "success")
        self.assertIn("symbol", res_ann.result)

        # STEP 7: Candidate Prioritization
        prio_tool = CandidatePrioritizationTool()
        res_prio = prio_tool.run({
            "candidate_genes": ["AT01G10000", "AT02G10000"],
            "primary_de_path": str(de_csv_path)
        })
        self.assertEqual(res_prio.status, "success")
        self.assertEqual(res_prio.result["candidate_count"], 2)

        # STEP 8: Literature Retrieval
        lit_tool = LiteratureTool()
        res_lit = lit_tool.run({
            "gene_id": "AT01G10000",
            "organism": "Arabidopsis thaliana"
        })
        self.assertEqual(res_lit.status, "success")

        # STEP 9: Verify Full ToolRegistry Integration
        registry = ToolRegistry()
        for t in [create_tool, val_tool, quant_tool, deseq2_tool, volcano_tool, ann_tool, prio_tool, lit_tool]:
            registry.register(t)

        all_schemas = registry.get_tool_schemas()
        self.assertEqual(len(all_schemas), 8)


if __name__ == "__main__":
    unittest.main()
