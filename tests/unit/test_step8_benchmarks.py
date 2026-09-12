"""
Step 8 End-to-End Scientific Validation & Benchmarking Test Suite.

Evaluates the RNA-Seq AI Agent against NASA OSDR datasets (OSD-678 & OSD-120) across:
- Task 1: Dataset / Experimental Design Understanding
- Task 2: Differential Expression Analysis
- Task 3: Gene Annotation
- Task 4: Scientific Visualization (Volcano & Heatmap Plots)
- Task 5: Literature Retrieval & Evidence Hierarchy Classification
- Task 6: Multi-Tool Scientific Reasoning Loop
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
import pandas as pd

from agent.orchestrator.agent_runner import AgentOrchestrator, AgentResponse
from agent.llm.providers import MockLLMProvider
from agent.llm.client import LLMResponse, ToolCallRequest
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.literature_tool import LiteratureTool
from agent.tools.gene_annotation_tool import GeneAnnotationTool
from agent.tools.visualization_tools import VolcanoPlotTool, PCAPlotTool, HeatmapTool
from agent.tools.candidate_prioritization_tool import CandidatePrioritizationTool
from pipeline.backend_api import RNASeqBackendAPI


class TestStep8Benchmarks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.api = RNASeqBackendAPI()
        cls.osd678_de_csv = Path("results/osd678_validation/contrasts/A1_Col0_Light_Flight_vs_Ground.csv").resolve()
        cls.osd678_vst_csv = Path("results/osd120_primary_analysis/vst_counts.csv").resolve()

        cls.osd120_de_csv = Path("results/osd120_primary_analysis/differential_expression.csv").resolve()

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_step8_"))
        self.mock_provider = MockLLMProvider()
        self.orchestrator = AgentOrchestrator(backend_api=self.api, llm_provider=self.mock_provider)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_task_1_experimental_design_understanding(self):
        """TASK 1: Verify agent queries and retrieves experimental design & contrasts for OSD-678 and OSD-120."""
        # Query datasets from backend
        ds_resp = self.orchestrator.list_datasets()
        self.assertTrue(ds_resp.success)
        self.assertEqual(ds_resp.operation, "LIST_DATASETS")
        ds_ids = [d.dataset_id for d in ds_resp.datasets]
        self.assertIn("OSD-678", ds_ids)
        self.assertIn("OSD-120", ds_ids)

        # Query contrasts for OSD-678
        c678_resp = self.orchestrator.list_contrasts("OSD-678")
        self.assertTrue(c678_resp.success)
        self.assertEqual(c678_resp.operation, "LIST_CONTRASTS")
        c678_ids = [c.id for c in c678_resp.contrasts]
        self.assertIn("A1_Col0_Light_Flight_vs_Ground", c678_ids)
        self.assertIn("B1_Col0_Dark_Flight_vs_Ground", c678_ids)

        # Query contrasts for OSD-120
        c120_resp = self.orchestrator.list_contrasts("OSD-120")
        self.assertTrue(c120_resp.success)
        c120_ids = [c.id for c in c120_resp.contrasts]
        self.assertIn("Primary_OSD120_Flight_vs_Ground", c120_ids)

    def test_task_2_differential_expression_execution(self):
        """TASK 2: Verify differential expression tool execution on supported contrast (A1_Col0_Light_Flight_vs_Ground)."""
        de_tool = self.orchestrator.tool_registry.get("run_differential_expression")
        self.assertIsNotNone(de_tool)

        res = de_tool.run({
            "dataset_id": "OSD-678",
            "contrast_id": "A1_Col0_Light_Flight_vs_Ground",
            "fdr_cutoff": 0.05,
            "lfc_cutoff": 1.0
        })

        self.assertEqual(res.status, "success")
        self.assertEqual(res.tool_name, "run_differential_expression")
        self.assertIn("dataset_id", res.result)
        self.assertEqual(res.result["dataset_id"], "OSD-678")
        self.assertIn("contrast_count", res.result)
        self.assertIn("summary_metrics", res.result)
        self.assertEqual(res.provenance["wrapped_class"] if "wrapped_class" in res.provenance else res.provenance["engine"], "PyDESeq2 v0.5.4")

    def test_task_3_gene_annotation(self):
        """TASK 3: Verify GeneAnnotationTool annotates candidate genes returned by DE analysis."""
        annot_tool = self.orchestrator.tool_registry.get("annotate_gene")
        self.assertIsNotNone(annot_tool)

        res = annot_tool.run({"gene_id": "AT3G17609", "organism": "Arabidopsis thaliana"})
        self.assertEqual(res.status, "success")
        self.assertEqual(res.result["gene_id"], "AT3G17609")
        self.assertEqual(res.result["symbol"], "HYH")
        self.assertEqual(res.result["annotation_source"], "TAIR10")
        self.assertEqual(res.provenance["wrapped_class"], "GeneAnnotator")

    def test_task_4_visualization_figure_generation(self):
        """TASK 4: Verify VolcanoPlotTool and HeatmapTool generate valid non-empty publication figures."""
        # 1. Volcano Plot
        volcano_tool = self.orchestrator.tool_registry.get("generate_volcano_plot")
        volcano_out = str(self.test_dir / "bench_volcano.png")

        res_v = volcano_tool.run({
            "de_results_path": str(self.osd678_de_csv),
            "output_path": volcano_out,
            "fdr_thresh": 0.05,
            "lfc_thresh": 1.0
        })

        self.assertEqual(res_v.status, "success")
        self.assertTrue(Path(volcano_out).exists())
        self.assertGreater(Path(volcano_out).stat().st_size, 0)
        self.assertEqual(res_v.artifacts[0].artifact_type, "image")

        # 2. Heatmap Plot
        heatmap_tool = self.orchestrator.tool_registry.get("generate_heatmap")
        heatmap_out = str(self.test_dir / "bench_heatmap.png")

        res_h = heatmap_tool.run({
            "vst_counts_path": str(self.osd678_vst_csv),
            "de_results_path": str(self.osd678_de_csv),
            "output_path": heatmap_out,
            "top_n": 10
        })

        if res_h.status != "success":
            print(f"\nHEATMAP TOOL ERROR: {res_h.error}")
        self.assertEqual(res_h.status, "success")

        self.assertTrue(Path(heatmap_out).exists())
        self.assertGreater(Path(heatmap_out).stat().st_size, 0)

    def test_task_5_literature_retrieval_and_evidence_hierarchy(self):
        """TASK 5: Verify LiteratureTool retrieves grounded snippets and enforces evidence classification hierarchy."""
        lit_tool = self.orchestrator.tool_registry.get("search_literature")
        self.assertIsNotNone(lit_tool)

        res = lit_tool.run({"gene_id": "CRY1"})
        self.assertEqual(res.status, "success")
        self.assertGreaterEqual(res.result["match_count"], 1)

        snippets = res.result["snippets"]
        first_snip = snippets[0]
        self.assertIn("title", first_snip)
        self.assertIn("journal_or_source", first_snip)
        self.assertIn("doi", first_snip)

        # Grounding check: verify evidence statement validation via guardrails
        claims = self.orchestrator.interpret_de_results(
            de_summary={"dataset_id": "OSD-678"},
            top_genes=[{"gene_id": "AT1G04400", "symbol": "CRY1"}],
            enrichment_summary={}
        )

        self.assertGreaterEqual(len(claims), 1)

        # First claim is an OBSERVATION
        self.assertEqual(claims[0].evidence_type, "OBSERVATION")
        self.assertTrue(claims[0].guardrail_passed)

    def test_task_6_multi_tool_scientific_reasoning_loop(self):
        """TASK 6: Verify multi-step agent reasoning loop combining DE, candidate prioritization, gene annotation, literature, and volcano plotting."""
        volcano_out = str(self.test_dir / "multi_step_volcano.png")

        # Step 1: LLM calls evaluate_candidate_genes
        call1 = ToolCallRequest(
            tool_name="evaluate_candidate_genes",
            arguments={"candidate_genes": ["AT3G17609", "AT4G04720"], "primary_de_path": str(self.osd678_de_csv)}
        )
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call1], finish_reason="tool_calls"))

        # Step 2: LLM calls search_literature
        call2 = ToolCallRequest(tool_name="search_literature", arguments={"gene_id": "HYH"})
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call2], finish_reason="tool_calls"))

        # Step 3: LLM calls generate_volcano_plot
        call3 = ToolCallRequest(
            tool_name="generate_volcano_plot",
            arguments={"de_results_path": str(self.osd678_de_csv), "output_path": volcano_out}
        )
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call3], finish_reason="tool_calls"))

        # Step 4: Final synthesis
        synthesis_markdown = (
            "### Benchmark Synthesis Report\n"
            "- [OBSERVED] Evaluated 2 candidate genes (AT3G17609 / HYH, AT4G04720 / CPK21) against OSD-678 primary contrast.\n"
            "- [STATISTICAL] Both candidates passed FDR threshold (padj < 0.05) with concordant directional expression.\n"
            "- [LITERATURE-SUPPORTED] HYH is implicated in light signalling and circadian clock regulation under spaceflight.\n"
            "- [INTERPRETATION] Spaceflight light exposure induces robust transcriptional reprogramming in root photomorphogenesis pathways."
        )
        self.mock_provider.queue_response(LLMResponse(content=synthesis_markdown, tool_calls=[], finish_reason="stop"))

        resp = self.orchestrator.agentic_query(
            user_query="Prioritize candidates AT3G17609 and AT4G04720 in OSD-678, search literature, and plot volcano"
        )

        self.assertTrue(resp.success)
        self.assertEqual(resp.iterations_count, 4)
        self.assertEqual(len(resp.tool_results), 3)
        self.assertEqual(resp.tool_results[0].tool_name, "evaluate_candidate_genes")
        self.assertEqual(resp.tool_results[1].tool_name, "search_literature")
        self.assertEqual(resp.tool_results[2].tool_name, "generate_volcano_plot")
        self.assertTrue(Path(volcano_out).exists())
        self.assertIn("[STATISTICAL]", resp.message)
        self.assertIn("[LITERATURE-SUPPORTED]", resp.message)



if __name__ == "__main__":
    unittest.main()
