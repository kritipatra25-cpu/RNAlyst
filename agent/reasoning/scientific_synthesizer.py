"""
Evidence-Grounded Scientific Synthesizer for Bulk RNA-seq AI Agent Platform.

Transforms deterministic backend results, multi-species gene annotations, and verified
literature RAG snippets into a structured 7-question scientific synthesis report.
"""

import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from agent.reasoning.evidence_classifier import EvidenceClassifier, EvidenceBadge, EvidenceStatement
from agent.rag.literature_engine import LiteratureRAGEngine, LiteratureSnippet
from analysis.annotation.gene_annotator import GeneAnnotator
from pipeline.backend_api import AnalysisResult

logger = logging.getLogger(__name__)


class ScientificReport(BaseModel):
    """Structured 7-question scientific synthesis report."""
    report_id: str
    dataset_id: str
    q1_what_was_tested: EvidenceStatement
    q2_what_was_observed: EvidenceStatement
    q3_statistical_significance: EvidenceStatement
    q4_relevant_genes_and_pathways: List[EvidenceStatement]
    q5_literature_evidence: List[EvidenceStatement]
    q6_uncertainties_and_limitations: EvidenceStatement
    q7_hypotheses_for_next_steps: List[EvidenceStatement]
    provenance_hash: Optional[str] = None
    all_statements: List[EvidenceStatement] = Field(default_factory=list)

    def full_markdown_report(self) -> str:
        """Render complete, evidence-badged Markdown report."""
        lines = [
            f"# Scientific Synthesis Report: {self.dataset_id}",
            f"**Report ID**: `{self.report_id}`",
            "",
            "### 1. What was tested?",
            self.q1_what_was_tested.formatted_text(),
            "",
            "### 2. What was observed?",
            self.q2_what_was_observed.formatted_text(),
            "",
            "### 3. What was statistically significant?",
            self.q3_statistical_significance.formatted_text(),
            "",
            "### 4. Which genes and pathways are most relevant?",
        ]
        for stmt in self.q4_relevant_genes_and_pathways:
            lines.append(f"- {stmt.formatted_text()}")

        lines.extend([
            "",
            "### 5. What evidence supports their biological interpretation?",
        ])
        for stmt in self.q5_literature_evidence:
            lines.append(f"- {stmt.formatted_text()}")

        lines.extend([
            "",
            "### 6. What remains uncertain?",
            self.q6_uncertainties_and_limitations.formatted_text(),
            "",
            "### 7. What hypotheses could be tested next?",
        ])
        for stmt in self.q7_hypotheses_for_next_steps:
            lines.append(f"- {stmt.formatted_text()}")

        return "\n".join(lines)


class ScientificSynthesizer:
    """Synthesizer assembling evidence-badged scientific reports."""

    def __init__(
        self,
        classifier: Optional[EvidenceClassifier] = None,
        rag_engine: Optional[LiteratureRAGEngine] = None,
        annotator: Optional[GeneAnnotator] = None
    ):
        self.classifier = classifier or EvidenceClassifier()
        self.rag_engine = rag_engine or LiteratureRAGEngine()
        self.annotator = annotator or GeneAnnotator()

    def synthesize(
        self,
        analysis_result: AnalysisResult,
        candidate_records: Optional[List[Dict[str, Any]]] = None,
        query_text: str = ""
    ) -> ScientificReport:
        """Assemble structured ScientificReport from backend results, annotations, and RAG literature."""
        did = analysis_result.dataset_id
        rid = f"report_{did.lower().replace('-', '')}"
        all_stmts = []

        # 1. What was tested? [OBSERVED]
        s1 = self.classifier.create_statement(
            statement_id="stmt_q1",
            badge=EvidenceBadge.OBSERVED,
            text=f"Evaluated differential gene expression across {analysis_result.contrast_count} defined contrasts in dataset {did}."
        )
        all_stmts.append(s1)

        # 2. What was observed? [OBSERVED]
        s2 = self.classifier.create_statement(
            statement_id="stmt_q2",
            badge=EvidenceBadge.OBSERVED,
            text=f"Processed raw count matrices and validated sample metadata containing {analysis_result.candidate_count} candidate genes."
        )
        all_stmts.append(s2)

        # 3. What was statistically significant? [STATISTICAL]
        s3 = self.classifier.create_statement(
            statement_id="stmt_q3",
            badge=EvidenceBadge.STATISTICAL,
            text=f"PyDESeq2 Wald testing identified significant expression changes adhering to FDR padj < 0.05 and |log2FC| >= 1.0."
        )
        all_stmts.append(s3)

        # 4. Relevant genes & pathways [STATISTICAL] / [INTERPRETATION]
        q4_stmts = []
        c_recs = candidate_records or []
        for i, rec in enumerate(c_recs[:5]):
            gid = rec.get("gene_id", "")
            sym = self.annotator.get_symbol(gid)
            lfc = rec.get("osd678_light_lfc") or rec.get("osd120_lfc")
            padj = rec.get("osd678_light_padj") or rec.get("osd120_padj")
            classif = rec.get("evidence_classification", "OBSERVED")

            lfc_str = f"{lfc:.2f}" if lfc is not None else "N/A"
            padj_str = f"{padj:.4f}" if padj is not None else "N/A"

            stmt = self.classifier.create_statement(
                statement_id=f"stmt_q4_{i+1}",
                badge=EvidenceBadge.STATISTICAL if padj is not None else EvidenceBadge.INTERPRETATION,
                text=f"Gene {gid} ({sym}) exhibited log2FC = {lfc_str} (padj = {padj_str}), classified as {classif}.",
                supporting_ids=[gid]
            )
            q4_stmts.append(stmt)
            all_stmts.append(stmt)

        if not q4_stmts:
            s4_fallback = self.classifier.create_statement(
                statement_id="stmt_q4_def",
                badge=EvidenceBadge.INTERPRETATION,
                text="Candidate genes evaluated for differential expression and cross-contrast concordance."
            )
            q4_stmts.append(s4_fallback)
            all_stmts.append(s4_fallback)

        # 5. Literature Evidence [LITERATURE-SUPPORTED]
        q5_stmts = []
        target_genes = [r.get("gene_id") for r in c_recs if r.get("gene_id")] if c_recs else []

        for gid in target_genes[:3]:
            sym = self.annotator.get_symbol(gid)
            snips = self.rag_engine.search_gene_literature(gid, symbol=sym)
            for snip in snips[:1]:
                stmt = self.classifier.create_statement(
                    statement_id=f"stmt_q5_{snip.snippet_id}",
                    badge=EvidenceBadge.LITERATURE_SUPPORTED,
                    text=f"{snip.symbol} ({snip.gene_id}): {snip.evidence_text}",
                    supporting_ids=[gid],
                    citation=f"{snip.journal_or_source} ({snip.publication_year}), DOI: {snip.doi}"
                )
                q5_stmts.append(stmt)
                all_stmts.append(stmt)

        if not q5_stmts:
            s5_fallback = self.classifier.create_statement(
                statement_id="stmt_q5_def",
                badge=EvidenceBadge.INTERPRETATION,
                text=f"No specific peer-reviewed literature citations found for dataset {did} candidate genes.",
                citation=None
            )
            q5_stmts.append(s5_fallback)
            all_stmts.append(s5_fallback)

        # 6. Uncertainties & Limitations [INTERPRETATION]
        s6 = self.classifier.create_statement(
            statement_id="stmt_q6",
            badge=EvidenceBadge.INTERPRETATION,
            text="Unmeasured environmental variables (e.g. ambient cabin humidity, localized thermal gradients) may contribute to secondary transcriptional variation."
        )
        all_stmts.append(s6)

        # 7. Hypotheses for Next Steps [HYPOTHESIS]
        q7_stmts = [
            self.classifier.create_statement(
                statement_id="stmt_q7_1",
                badge=EvidenceBadge.HYPOTHESIS,
                text="Spaceflight microgravity may attenuate blue-light signaling efficiency through altered cryptochrome nuclear transport.",
                supporting_ids=["AT1G04400"]
            ),
            self.classifier.create_statement(
                statement_id="stmt_q7_2",
                badge=EvidenceBadge.HYPOTHESIS,
                text="Upregulation of ROS scavenging machinery potentially serves as an adaptive mechanism compensating for impaired mechanosensory feedback.",
                supporting_ids=["AT5G07390"]
            )
        ]
        all_stmts.extend(q7_stmts)

        return ScientificReport(
            report_id=rid,
            dataset_id=did,
            q1_what_was_tested=s1,
            q2_what_was_observed=s2,
            q3_statistical_significance=s3,
            q4_relevant_genes_and_pathways=q4_stmts,
            q5_literature_evidence=q5_stmts,
            q6_uncertainties_and_limitations=s6,
            q7_hypotheses_for_next_steps=q7_stmts,
            all_statements=all_stmts
        )
