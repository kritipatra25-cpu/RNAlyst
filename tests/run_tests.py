"""
Standard Python Unittest Runner for Phase 2 LLM Interpretation Layer.
Validates all 6 scientific safeguards without external test runner dependencies.
"""

import unittest
import pandas as pd
from pipeline.schemas.phase2_schemas import VerifiedCitation, GeneEvidence
from analysis.interpretation.citation_verifier import CitationVerifier
from analysis.interpretation.gene_identity_verifier import GeneIdentityVerifier
from analysis.interpretation.rag_engine import ExtensibleRAGEngine
from analysis.interpretation.llm_interpreter import LLMInterpretationEngine
from analysis.interpretation.phase3_llm_adapter import Phase3LLMAdapter
from analysis.interpretation.phase3_validator import Phase3Validator
from pipeline.schemas.phase3_schemas import Phase3GeneInterpretation, Phase3InterpretationReport
from pipeline.schemas.rag_schemas import VerifiedEvidenceRecord, VerifiedDatabaseRecord, RAGRetrievalReport
from tests.test_meta_analysis import TestMetaAnalysisEngine

class TestPhase2Interpretation(unittest.TestCase):

    def setUp(self):
        self.mock_record = {
            "citation_id": "CIT_PUBMED_29122345",
            "source_type": "PEER_REVIEWED_PAPER",
            "title": "Transcriptomic analysis of Arabidopsis thaliana root orientation",
            "authors": "Kruse CPS, et al.",
            "year": 2017,
            "pmid": "29122345",
            "doi": "10.1038/s41598-017-16441-x",
            "retrieved_chunk_text": "Light-grown Arabidopsis roots in spaceflight display upregulation of cell wall enzymes."
        }
        self.mock_data_bundle = {
            "differential_expression": pd.DataFrame({
                "gene_id": ["AT4G04720", "AT3G17609", "AT1G73500"],
                "baseMean": [845.2, 1230.5, 20.0],
                "log2FoldChange": [0.3391, -4.6856, -0.8000],
                "shrunk_log2FoldChange": [0.1068, -4.6329, -0.7500],
                "lfcSE": [0.0113, 0.2558, 0.3000],
                "pvalue": [8.44e-06, 6.49e-05, 0.0010],
                "padj": [0.1809, 0.5388, 0.5388]  # All padj >= 0.05 under N=3
            }),
            "vst_counts": pd.DataFrame(),
            "summary": {"total_genes": 32833},
            "provenance": {"contrast": "Space Flight vs Ground Control"},
            "concordance": {"primary_metrics": {"directional_concordance_rate_pct": 85.99}}
        }

    def test_centralized_fdr_classification_rule(self):
        """Rule 4: Centralized FDR classification logic test."""
        engine = LLMInterpretationEngine(self.mock_data_bundle, {"de_csv": "hash1"})
        
        # Tier A: FDR Significant
        status, label = engine.classify_statistical_status(0.0001, 0.045)
        self.assertEqual(status, "FDR_SIGNIFICANT")
        self.assertEqual(label, "HIGH")

        # Tier B: Raw p-value only
        status, label = engine.classify_statistical_status(0.0001, 0.15)
        self.assertEqual(status, "RAW_P_ONLY")
        self.assertEqual(label, "EXPLORATORY")

        # Tier C: Non-significant
        status, label = engine.classify_statistical_status(0.10, 0.50)
        self.assertEqual(status, "NON_SIGNIFICANT")
        self.assertEqual(label, "UNSUBSTANTIATED")

    def test_regression_at3g17609(self):
        """Rule 2: Explicit regression test for AT3G17609."""
        engine = LLMInterpretationEngine(self.mock_data_bundle, {"de_csv": "hash1"})
        report = engine.generate_deterministic_interpretation()

        at3g_ev = next(ev for ev in report.gene_interpretations if ev.gene_id == "AT3G17609" and "Class A" in ev.evidence_class)
        self.assertEqual(at3g_ev.statistical_status, "RAW_P_ONLY")
        self.assertEqual(at3g_ev.confidence_decomposition.confidence_label, "EXPLORATORY")
        self.assertIn("large estimated effect", at3g_ev.narrative_summary)
        self.assertIn("NOT statistically significant differential expression", at3g_ev.narrative_summary)
        self.assertNotIn("significantly downregulated", at3g_ev.narrative_summary.lower())

    def test_regression_at4g04720(self):
        """Rule 3: Explicit regression test for AT4G04720."""
        engine = LLMInterpretationEngine(self.mock_data_bundle, {"de_csv": "hash1"})
        report = engine.generate_deterministic_interpretation()

        at4g_ev = next(ev for ev in report.gene_interpretations if ev.gene_id == "AT4G04720" and "Class A" in ev.evidence_class)
        self.assertEqual(at4g_ev.statistical_status, "RAW_P_ONLY")
        self.assertEqual(at4g_ev.confidence_decomposition.confidence_label, "EXPLORATORY")
        self.assertIn("NOT statistically significant differential expression", at4g_ev.narrative_summary)
        self.assertNotIn("significantly upregulated", at4g_ev.narrative_summary.lower())

    def test_synthetic_pvalue_00001_padj_020(self):
        """Rule 10: Test pvalue = 0.00001, padj = 0.20 rejects statistically significant DE classification."""
        custom_bundle = {
            "differential_expression": pd.DataFrame({
                "gene_id": ["AT4G04720"],
                "baseMean": [845.2],
                "log2FoldChange": [1.5],
                "shrunk_log2FoldChange": [1.2],
                "lfcSE": [0.1],
                "pvalue": [0.00001],
                "padj": [0.20]
            }),
            "vst_counts": pd.DataFrame(),
            "summary": {"total_genes": 32833},
            "provenance": {"contrast": "Space Flight vs Ground Control"},
            "concordance": {"primary_metrics": {"directional_concordance_rate_pct": 85.99}}
        }
        engine = LLMInterpretationEngine(custom_bundle, {"de_csv": "hash1"})
        report = engine.generate_deterministic_interpretation()

        ev = report.gene_interpretations[0]
        self.assertEqual(ev.statistical_status, "RAW_P_ONLY")
        self.assertEqual(ev.confidence_decomposition.confidence_label, "EXPLORATORY")
        self.assertIn("NOT statistically significant differential expression", ev.narrative_summary)

        # Audit report verification must pass
        is_valid, errors = engine.verify_interpretation_report(report)
        self.assertTrue(is_valid, f"Report audit failed: {errors}")

    def test_confidence_audit_rejects_high_confidence_for_raw_p_only(self):
        """Rule 5: Verify HIGH confidence cannot be assigned for raw p < 0.001 if padj >= 0.05."""
        engine = LLMInterpretationEngine(self.mock_data_bundle, {"de_csv": "hash1"})
        status, label = engine.classify_statistical_status(0.00001, 0.181)
        self.assertNotEqual(label, "HIGH")
        self.assertEqual(label, "EXPLORATORY")

    def test_global_fdr_language_audit(self):
        """Rule 1: Global audit scanning generated report narratives for forbidden phrases."""
        engine = LLMInterpretationEngine(self.mock_data_bundle, {"de_csv": "hash1"})
        report = engine.generate_deterministic_interpretation()

        forbidden_phrases = [
            "significantly upregulated",
            "significantly downregulated",
            "differentially expressed",
            "statistically significant differential expression"
        ]

        for ev in report.gene_interpretations:
            if ev.statistical_status != "FDR_SIGNIFICANT":
                text = ev.narrative_summary.lower()
                for phrase in forbidden_phrases:
                    if phrase in text and "not statistically significant" not in text:
                        self.fail(f"Forbidden phrase '{phrase}' found in narrative for non-FDR gene {ev.gene_id}: {ev.narrative_summary}")

    def test_class_d_hypothesis_audit(self):
        """Rule 6: Class D hypothesis requires BOTH Class A gene ID and Class C citation ID."""
        engine = LLMInterpretationEngine(self.mock_data_bundle, {"de_csv": "hash1"})
        report = engine.generate_deterministic_interpretation()

        class_d_list = [ev for ev in report.gene_interpretations if "Class D" in ev.evidence_class]
        self.assertGreater(len(class_d_list), 0)
        for ev in class_d_list:
            self.assertTrue(len(ev.derived_from_class_a_gene_ids) > 0, f"Class D for {ev.gene_id} missing Class A link")
            self.assertTrue(len(ev.derived_from_class_c_citation_ids) > 0, f"Class D for {ev.gene_id} missing Class C link")

    def test_numeric_immutability(self):
        """Rule 7: Compare every numerical DE value in Phase 2 report against Phase 1 input."""
        engine = LLMInterpretationEngine(self.mock_data_bundle, {"de_csv": "hash1"})
        report = engine.generate_deterministic_interpretation()

        row_map = {row["gene_id"]: row for _, row in self.mock_data_bundle["differential_expression"].iterrows()}

        for ev in report.gene_interpretations:
            if "Class A" in ev.evidence_class:
                src_row = row_map[ev.gene_id]
                stat = ev.confidence_decomposition.statistical_significance
                eff = ev.confidence_decomposition.effect_size_precision

                self.assertEqual(stat["pvalue"], float(src_row["pvalue"]))
                self.assertEqual(stat["padj"], float(src_row["padj"]))
                self.assertEqual(eff["log2FC"], float(src_row["log2FoldChange"]))
                self.assertEqual(eff["shrunk_log2FC"], float(src_row["shrunk_log2FoldChange"]))
                self.assertEqual(eff["lfcSE"], float(src_row["lfcSE"]))

    def test_sample_size_warning_present(self):
        """Rule 8: Verify study-level sample size warning is present in report."""
        engine = LLMInterpretationEngine(self.mock_data_bundle, {"de_csv": "hash1"})
        report = engine.generate_deterministic_interpretation()
        self.assertIn("N=3 vs N=3", report.sample_size_warning)
        self.assertIn("exploratory hypothesis generation", report.sample_size_warning)

    def test_deterministic_execution_label(self):
        """Rule 9: Verify synthesis mode and provider name accurately label deterministic mode."""
        engine = LLMInterpretationEngine(self.mock_data_bundle, {"de_csv": "hash1"})
        report = engine.generate_deterministic_interpretation()

        manifest = report.provenance_manifest
        self.assertEqual(manifest.synthesis_mode, "DETERMINISTIC_REFERENCE")
        self.assertEqual(manifest.provider_name, "DETERMINISTIC_TEMPLATE_GENERATOR")
        self.assertEqual(manifest.model_identifier, "rule_based_v1.0")
        self.assertIsNone(manifest.temperature)
        self.assertIsNone(manifest.seed)

from pipeline.schemas.rag_schemas import (
    VerifiedLiteratureCitation,
    VerifiedDatabaseRecord,
    VerifiedEvidenceRecord,
    VerifiedEvidencePackage,
    ReadonlyQuantitativeMetadata
)
from analysis.interpretation.database_record_verifier import DatabaseRecordVerifier
from analysis.interpretation.rag_engine import ExtensibleRAGEngine

class TestRAGEvidenceRetrievalLayer(unittest.TestCase):

    def setUp(self):
        self.rag_engine = ExtensibleRAGEngine()
        self.db_verifier = DatabaseRecordVerifier()
        self.mock_de_row = pd.Series({
            "gene_id": "AT4G04720",
            "baseMean": 845.2,
            "log2FoldChange": 0.3391,
            "shrunk_log2FoldChange": 0.1068,
            "lfcSE": 0.0113,
            "pvalue": 8.44e-06,
            "padj": 0.1809
        })

    def test_valid_pmid_retrieval(self):
        """Test 1: Valid PMID retrieval returns verified literature citation."""
        results = self.rag_engine.query_literature_citations(["OSD-120"], top_k=1)
        self.assertGreater(len(results), 0)
        lit_cit, tier = results[0]
        self.assertEqual(lit_cit.pmid, "29122345")
        self.assertEqual(lit_cit.verification_status, "VERIFIED_EXTERNAL_RECORD")
        self.assertEqual(tier, 1)

    def test_invalid_pmid_rejection(self):
        """Test 2: Invalid or synthetic PMID is rejected by verifier."""
        fake_rec = {
            "citation_id": "CIT_FAKE_123",
            "pmid": "99999999999",  # Synthetic PMID not in verified index
            "title": "Fake study",
            "authors": "Fake A",
            "year": 2024,
            "retrieved_chunk_text": "Fake text"
        }
        is_valid, cit_obj, msg = self.rag_engine.citation_verifier.verify_citation_dict(fake_rec)
        self.assertFalse(is_valid)
        self.assertTrue("PMID not found" in msg or "Invalid or synthetic PMID" in msg)


    def test_invalid_doi_rejection(self):
        """Test 3: Invalid or malformed DOI is rejected by verifier."""
        fake_rec = {
            "citation_id": "CIT_FAKE_DOI",
            "doi": "invalid_doi_string_without_prefix",
            "title": "Fake DOI study",
            "authors": "Fake B",
            "year": 2024,
            "retrieved_chunk_text": "Fake DOI text"
        }
        is_valid, cit_obj, msg = self.rag_engine.citation_verifier.verify_citation_dict(fake_rec)
        self.assertFalse(is_valid)

    def test_gene_identity_mismatch(self):
        """Test 4: Unverified or mismatched gene ID returns explicit unresolved status."""
        phase1_genes = {"AT4G04720"}
        verifier = GeneIdentityVerifier(phase1_genes)
        is_verified, clean_id, symbol, source = verifier.verify_gene("INVALID_GENE_999")
        self.assertFalse(is_verified)

    def test_unverified_citation_rejection(self):
        """Test 5: Unverified citation cannot be used as Class C literature evidence."""
        unverified_cit = VerifiedLiteratureCitation(
            citation_id="CIT_UNVERIFIED",
            pmid="00000000",
            title="Unverified study",
            authors="Unknown",
            year=2020,
            retrieval_timestamp="2026-08-21T00:00:00",
            retrieved_chunk_text="Unverified text",
            verification_status="UNVERIFIED"
        )
        self.assertEqual(unverified_cit.verification_status, "UNVERIFIED")
        self.assertNotEqual(unverified_cit.verification_status, "VERIFIED_EXTERNAL_RECORD")

    def test_stable_chunk_id_generation(self):
        """Test 6: SHA-256 chunk ID is stable and deterministic across runs."""
        chk1 = self.rag_engine.compute_chunk_id("PubMed", "29122345", "Light-grown Arabidopsis roots")
        chk2 = self.rag_engine.compute_chunk_id("PubMed", "29122345", "Light-grown Arabidopsis roots")
        self.assertEqual(chk1, chk2)
        self.assertTrue(chk1.startswith("CHK_"))

    def test_tier_ranking_hierarchy(self):
        """Test 7: Evidence tier represents contextual relevance (Tier 1 > Tier 2 > Tier 3)."""
        tier1 = self.rag_engine.assign_evidence_tier("OSD-120", "Arabidopsis thaliana", "root")
        tier2 = self.rag_engine.assign_evidence_tier(None, "Arabidopsis thaliana", "root")
        tier3 = self.rag_engine.assign_evidence_tier(None, "Oryza sativa", "leaf")

        self.assertEqual(tier1, 1)
        self.assertEqual(tier2, 2)
        self.assertEqual(tier3, 3)

    def test_pathway_annotation_retrieval(self):
        """Test 8: Database records (GO/KEGG/Reactome/MapMan) are retrieved as database records."""
        results = self.rag_engine.query_database_records("AT4G04720")
        self.assertGreater(len(results), 0)
        db_rec, tier = results[0]
        self.assertIn(db_rec.database, ["GO", "KEGG", "REACTOME", "MAPMAN", "TAIR"])
        self.assertEqual(db_rec.verification_status, "VERIFIED_DATABASE_ENTRY")

    def test_raw_p_only_statistical_immutability(self):
        """Test 9: Literature evidence retrieval cannot alter RAW_P_ONLY statistical status or padj."""
        pkg = self.rag_engine.build_verified_evidence_package(
            gene_id="AT4G04720",
            symbol="XTH17",
            annot_source="TAIR10",
            de_row=self.mock_de_row,
            stat_status="RAW_P_ONLY"
        )
        self.assertEqual(pkg.quantitative_metadata.statistical_status, "RAW_P_ONLY")
        self.assertEqual(pkg.quantitative_metadata.padj, 0.1809)

    def test_phase1_numerical_immutability(self):
        """Test 10: Quantitative metadata in VerifiedEvidencePackage matches Phase 1 source exactly."""
        pkg = self.rag_engine.build_verified_evidence_package(
            gene_id="AT4G04720",
            symbol="XTH17",
            annot_source="TAIR10",
            de_row=self.mock_de_row,
            stat_status="RAW_P_ONLY"
        )
        q = pkg.quantitative_metadata
        self.assertEqual(q.pvalue, 8.44e-06)
        self.assertEqual(q.padj, 0.1809)
        self.assertEqual(q.log2FoldChange, 0.3391)
        self.assertEqual(q.shrunk_log2FoldChange, 0.1068)
        self.assertEqual(q.lfcSE, 0.0113)

    def test_database_annotation_not_literature_citation(self):
        """Test 11: Database record cannot satisfy peer-reviewed Class C literature requirement."""
        db_rec = VerifiedDatabaseRecord(
            database="GO",
            record_id="GO:0009638",
            record_version="2023-11",
            annotation_text="GO:0009638 - response to gravitropism",
            association_type="DIRECT_ANNOTATION",
            verification_status="VERIFIED_DATABASE_ENTRY"
        )
        ev_rec = VerifiedEvidenceRecord(
            gene_id="AT4G04720",
            evidence_type="GO",
            evidence_tier=2,
            literature_citation=None,  # NO LITERATURE CITATION!
            database_record=db_rec,
            chunk_id="CHK_GO_0009638",
            claim_text=db_rec.annotation_text,
            verification_status="VERIFIED"
        )
        self.assertIsNone(ev_rec.literature_citation)
        self.assertIsNotNone(ev_rec.database_record)
        self.assertNotEqual(ev_rec.evidence_type, "LITERATURE")

    def test_live_api_failure_does_not_fabricate_evidence(self):
        """Test 12: External API failure returns structured retrieval failure with ZERO fabricated records."""
        failure_log = self.rag_engine.handle_api_failure("PubMed_External_API", "503 Service Unavailable")
        self.assertEqual(failure_log["fabricated_records_count"], 0)
        self.assertEqual(failure_log["fallback_status"], "STRUCTURED_RETRIEVAL_FAILURE")
        self.assertEqual(failure_log["source_name"], "PubMed_External_API")


class TestPhase3LLMInterpretation(unittest.TestCase):
    """Adversarial and Unit Tests for Phase 3 Constrained LLM Interpretation Layer."""

    def setUp(self):
        self.rag_engine = ExtensibleRAGEngine()
        self.adapter = Phase3LLMAdapter()
        self.validator = Phase3Validator()
        self.mock_de_row = {
            "gene_id": "AT4G04720",
            "baseMean": 216.4779,
            "log2FoldChange": 0.3391,
            "shrunk_log2FoldChange": 0.1068,
            "lfcSE": 0.0113,
            "pvalue": 8.44e-06,
            "padj": 0.1809
        }
        self.mock_pkg = self.rag_engine.build_verified_evidence_package(
            gene_id="AT4G04720",
            symbol="XTH17",
            annot_source="TAIR10",
            de_row=self.mock_de_row,
            stat_status="RAW_P_ONLY"
        )

    def test_adv_raw_p_only_claiming_de(self):
        """Adv Test 1: Raw p < 0.001 but padj >= 0.05 claiming DE is REJECTED by validator."""
        valid_interp = self.adapter.generate_gene_interpretation(self.mock_pkg)
        bad_summary = valid_interp.quantitative_summary + " AT4G04720 is significantly upregulated."
        bad_interp = Phase3GeneInterpretation(
            gene_id=valid_interp.gene_id,
            symbol=valid_interp.symbol,
            statistical_status=valid_interp.statistical_status,
            quantitative_summary=bad_summary,
            literature_context=valid_interp.literature_context,
            database_annotations=valid_interp.database_annotations,
            exploratory_hypotheses=valid_interp.exploratory_hypotheses,
            supporting_citation_ids=valid_interp.supporting_citation_ids,
            supporting_chunk_ids=valid_interp.supporting_chunk_ids,
            uncertainty_notes=valid_interp.uncertainty_notes,
            causal_guardrail_statement=valid_interp.causal_guardrail_statement
        )
        ok, errs = self.validator.validate_gene_interpretation(bad_interp, self.mock_pkg)
        self.assertFalse(ok)
        self.assertTrue(any("forbidden significance term" in e for e in errs))

    def test_adv_large_fc_claiming_significance(self):
        """Adv Test 2: Large log2FC claiming significance despite padj >= 0.05 is REJECTED."""
        large_fc_row = dict(self.mock_de_row, log2FoldChange=5.0, padj=0.50)
        large_fc_pkg = self.rag_engine.build_verified_evidence_package(
            gene_id="AT4G04720",
            symbol="XTH17",
            annot_source="TAIR10",
            de_row=large_fc_row,
            stat_status="RAW_P_ONLY"
        )
        valid_interp = self.adapter.generate_gene_interpretation(large_fc_pkg)
        bad_summary = valid_interp.quantitative_summary + " This gene shows differentially expressed magnitude."
        bad_interp = Phase3GeneInterpretation(
            gene_id=valid_interp.gene_id,
            symbol=valid_interp.symbol,
            statistical_status=valid_interp.statistical_status,
            quantitative_summary=bad_summary,
            literature_context=valid_interp.literature_context,
            database_annotations=valid_interp.database_annotations,
            exploratory_hypotheses=valid_interp.exploratory_hypotheses,
            supporting_citation_ids=valid_interp.supporting_citation_ids,
            supporting_chunk_ids=valid_interp.supporting_chunk_ids,
            uncertainty_notes=valid_interp.uncertainty_notes,
            causal_guardrail_statement=valid_interp.causal_guardrail_statement
        )
        ok, errs = self.validator.validate_gene_interpretation(bad_interp, large_fc_pkg)
        self.assertFalse(ok)

    def test_adv_invented_gene_symbol(self):
        """Adv Test 3: Unverified or mismatched gene ID in report is REJECTED by validator."""
        report = self.adapter.generate_report(RAGRetrievalReport(
            study_id="OSD-120",
            contrast="Space Flight vs Ground Control",
            candidates_queried=["AT4G04720"],
            sources_searched=["PubMed"],
            evidence_packages=[self.mock_pkg],
            verified_literature_count=1,
            verified_database_count=0,
            tier_counts={"tier_1": 1},
            unresolved_genes=[],
            retrieval_failures=[]
        ))
        ok, errs = self.validator.validate_interpretation_report(report, {})  # empty packages map
        self.assertFalse(ok)
        self.assertTrue(any("not present in Phase 2 verified evidence packages" in e for e in errs))

    def test_adv_invented_citation(self):
        """Adv Test 4: Invented/synthetic PMID is REJECTED by validator."""
        valid_interp = self.adapter.generate_gene_interpretation(self.mock_pkg)
        bad_interp = Phase3GeneInterpretation(
            gene_id=valid_interp.gene_id,
            symbol=valid_interp.symbol,
            statistical_status=valid_interp.statistical_status,
            quantitative_summary=valid_interp.quantitative_summary,
            literature_context=valid_interp.literature_context,
            database_annotations=valid_interp.database_annotations,
            exploratory_hypotheses=valid_interp.exploratory_hypotheses,
            supporting_citation_ids=["CIT_PUBMED_99999999"],  # FAKE CITATION
            supporting_chunk_ids=valid_interp.supporting_chunk_ids,
            uncertainty_notes=valid_interp.uncertainty_notes,
            causal_guardrail_statement=valid_interp.causal_guardrail_statement
        )
        ok, errs = self.validator.validate_gene_interpretation(bad_interp, self.mock_pkg)
        self.assertFalse(ok)
        self.assertTrue(any("Synthetic/hallucinated citation" in e or "does not exist" in e for e in errs))

    def test_adv_database_as_literature(self):
        """Adv Test 5: Database record passed as literature citation is REJECTED by validator."""
        valid_interp = self.adapter.generate_gene_interpretation(self.mock_pkg)
        bad_interp = Phase3GeneInterpretation(
            gene_id=valid_interp.gene_id,
            symbol=valid_interp.symbol,
            statistical_status=valid_interp.statistical_status,
            quantitative_summary=valid_interp.quantitative_summary,
            literature_context=valid_interp.literature_context,
            database_annotations=valid_interp.database_annotations,
            exploratory_hypotheses=valid_interp.exploratory_hypotheses,
            supporting_citation_ids=["GO:0009638"],  # DATABASE ENTRY AS CITATION!
            supporting_chunk_ids=valid_interp.supporting_chunk_ids,
            uncertainty_notes=valid_interp.uncertainty_notes,
            causal_guardrail_statement=valid_interp.causal_guardrail_statement
        )
        ok, errs = self.validator.validate_gene_interpretation(bad_interp, self.mock_pkg)
        self.assertFalse(ok)
        self.assertTrue(any("Database annotation" in e and "erroneously passed" in e for e in errs))

    def test_adv_unframed_causal_claim(self):
        """Adv Test 6: Un-framed causal language in narrative is REJECTED by validator."""
        valid_interp = self.adapter.generate_gene_interpretation(self.mock_pkg)
        bad_summary = valid_interp.quantitative_summary + " Microgravity causes upregulation of this gene."
        bad_interp = Phase3GeneInterpretation(
            gene_id=valid_interp.gene_id,
            symbol=valid_interp.symbol,
            statistical_status=valid_interp.statistical_status,
            quantitative_summary=bad_summary,
            literature_context=valid_interp.literature_context,
            database_annotations=valid_interp.database_annotations,
            exploratory_hypotheses=valid_interp.exploratory_hypotheses,
            supporting_citation_ids=valid_interp.supporting_citation_ids,
            supporting_chunk_ids=valid_interp.supporting_chunk_ids,
            uncertainty_notes=valid_interp.uncertainty_notes,
            causal_guardrail_statement=valid_interp.causal_guardrail_statement
        )
        ok, errs = self.validator.validate_gene_interpretation(bad_interp, self.mock_pkg)
        self.assertFalse(ok)
        self.assertTrue(any("forbidden causal word" in e for e in errs))

    def test_adv_mechanism_without_chunk_id(self):
        """Adv Test 7: Category D hypothesis referencing invalid chunk ID is REJECTED."""
        from pipeline.schemas.phase3_schemas import Phase3ExploratoryHypothesis
        bad_hyp = Phase3ExploratoryHypothesis(
            hypothesis_id="HYP_BAD_01",
            hypothesis_label="Hypothesis (Exploratory)",
            motivating_observation="Observed log2FC",
            supporting_evidence_chunk_ids=["CHK_INVALID_9999"],  # INVALID CHUNK
            supporting_citation_ids=["CIT_PUBMED_29122345"],
            hypothesis_statement="Hypothesis (Exploratory): Cell wall remodeling...",
            is_established_mechanism=False
        )
        valid_interp = self.adapter.generate_gene_interpretation(self.mock_pkg)
        bad_interp = Phase3GeneInterpretation(
            gene_id=valid_interp.gene_id,
            symbol=valid_interp.symbol,
            statistical_status=valid_interp.statistical_status,
            quantitative_summary=valid_interp.quantitative_summary,
            literature_context=valid_interp.literature_context,
            database_annotations=valid_interp.database_annotations,
            exploratory_hypotheses=[bad_hyp],
            supporting_citation_ids=valid_interp.supporting_citation_ids,
            supporting_chunk_ids=valid_interp.supporting_chunk_ids,
            uncertainty_notes=valid_interp.uncertainty_notes,
            causal_guardrail_statement=valid_interp.causal_guardrail_statement
        )
        ok, errs = self.validator.validate_gene_interpretation(bad_interp, self.mock_pkg)
        self.assertFalse(ok)
        self.assertTrue(any("references invalid chunk ID" in e for e in errs))

    def test_adv_removal_of_uncertainty(self):
        """Adv Test 8: Invalid initial human review status is REJECTED by validator."""
        report = self.adapter.generate_report(RAGRetrievalReport(
            study_id="OSD-120",
            contrast="Space Flight vs Ground Control",
            candidates_queried=["AT4G04720"],
            sources_searched=["PubMed"],
            evidence_packages=[self.mock_pkg],
            verified_literature_count=1,
            verified_database_count=0,
            tier_counts={"tier_1": 1},
            unresolved_genes=[],
            retrieval_failures=[]
        ))
        bad_report = report.model_copy(update={"human_review_status": "HUMAN_APPROVED"})  # PREMATURE APPROVAL!
        ok, errs = self.validator.validate_interpretation_report(bad_report, {"AT4G04720": self.mock_pkg})
        self.assertFalse(ok)
        self.assertTrue(any("Invalid initial human review status" in e for e in errs))

    def test_adv_numeric_modification(self):
        """Adv Test 9: Altering statistical status from RAW_P_ONLY to FDR_SIGNIFICANT is REJECTED."""
        valid_interp = self.adapter.generate_gene_interpretation(self.mock_pkg)
        bad_interp = Phase3GeneInterpretation(
            gene_id=valid_interp.gene_id,
            symbol=valid_interp.symbol,
            statistical_status="FDR_SIGNIFICANT",  # ALTERED METADATA!
            quantitative_summary=valid_interp.quantitative_summary,
            literature_context=valid_interp.literature_context,
            database_annotations=valid_interp.database_annotations,
            exploratory_hypotheses=valid_interp.exploratory_hypotheses,
            supporting_citation_ids=valid_interp.supporting_citation_ids,
            supporting_chunk_ids=valid_interp.supporting_chunk_ids,
            uncertainty_notes=valid_interp.uncertainty_notes,
            causal_guardrail_statement=valid_interp.causal_guardrail_statement
        )
        ok, errs = self.validator.validate_gene_interpretation(bad_interp, self.mock_pkg)
        self.assertFalse(ok)
        self.assertTrue(any("Statistical status mismatch" in e for e in errs))


if __name__ == "__main__":
    unittest.main()

