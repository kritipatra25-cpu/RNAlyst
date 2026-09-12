"""
Execution runner for Phase 2 RAG / Knowledge Retrieval Layer.
Reads locked Phase 1 DE outputs, queries verified literature and database evidence sources,
builds VerifiedEvidencePackages for candidate genes, and exports structured RAG reports.
"""

import json
import logging
from pathlib import Path
import pandas as pd

from pipeline.schemas.rag_schemas import RAGRetrievalReport
from analysis.interpretation.gene_identity_verifier import GeneIdentityVerifier
from analysis.interpretation.rag_engine import ExtensibleRAGEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_rag_retrieval():
    logger.info("=== PHASE 2 RAG KNOWLEDGE RETRIEVAL LAYER EXECUTION ===")

    root_dir = Path("c:/Users/USER/.gemini/antigravity/scratch/rna-seq-ai-agent")
    phase1_dir = root_dir / "results/osd120_primary_analysis"
    output_dir = root_dir / "results/osd120_phase2_interpretation"
    output_dir.mkdir(parents=True, exist_ok=True)

    de_csv = phase1_dir / "differential_expression.csv"
    if not de_csv.exists():
        logger.error(f"Phase 1 DE CSV missing at {de_csv}")
        return

    de_df = pd.read_csv(de_csv)
    phase1_genes = set(de_df["gene_id"].astype(str)) if "gene_id" in de_df.columns else set()

    gene_verifier = GeneIdentityVerifier(phase1_genes)
    rag_engine = ExtensibleRAGEngine()

    # Prioritize candidate genes (including AT4G04720 and AT3G17609)
    top_genes = de_df.sort_values(by="pvalue").head(8)
    target_genes = de_df[de_df["gene_id"].isin(["AT4G04720", "AT3G17609"])]
    eval_df = pd.concat([top_genes, target_genes]).drop_duplicates(subset=["gene_id"]).copy()

    evidence_packages = []
    candidates_queried = []
    unresolved_genes = []
    lit_count = 0
    db_count = 0
    tier_counts = {"tier_1": 0, "tier_2": 0, "tier_3": 0}

    for idx, row in eval_df.iterrows():
        raw_gene = str(row["gene_id"]).strip()
        is_verified, clean_gene, symbol, annot_source = gene_verifier.verify_gene(raw_gene)

        candidates_queried.append(raw_gene)

        if not is_verified:
            unresolved_genes.append(raw_gene)
            continue

        pval = float(row["pvalue"]) if "pvalue" in row and pd.notna(row["pvalue"]) else 1.0
        padj = float(row["padj"]) if "padj" in row and pd.notna(row["padj"]) else 1.0

        if padj < 0.05:
            stat_status = "FDR_SIGNIFICANT"
        elif pval < 0.05:
            stat_status = "RAW_P_ONLY"
        else:
            stat_status = "NON_SIGNIFICANT"

        pkg = rag_engine.build_verified_evidence_package(
            gene_id=clean_gene,
            symbol=symbol,
            annot_source=annot_source,
            de_row=row,
            stat_status=stat_status
        )
        evidence_packages.append(pkg)

        for ev in pkg.evidence_records:
            if ev.evidence_type == "LITERATURE":
                lit_count += 1
            else:
                db_count += 1

            tier_key = f"tier_{ev.evidence_tier}"
            tier_counts[tier_key] = tier_counts.get(tier_key, 0) + 1

    sources_searched = ["PubMed", "PMC", "NASA OSDR", "TAIR", "GO", "KEGG", "Plant Reactome", "MapMan"]

    report = RAGRetrievalReport(
        study_id="OSD-120",
        contrast="Space Flight vs Ground Control",
        candidates_queried=candidates_queried,
        sources_searched=sources_searched,
        evidence_packages=evidence_packages,
        verified_literature_count=lit_count,
        verified_database_count=db_count,
        tier_counts=tier_counts,
        unresolved_genes=unresolved_genes,
        retrieval_failures=[]
    )

    # Save JSON report
    report_json_path = output_dir / "rag_retrieval_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
    logger.info(f"Saved RAG Retrieval Report JSON to: {report_json_path}")

    # Generate Markdown report
    report_md_path = output_dir / "rag_retrieval_report.md"
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Phase 2 RAG Knowledge Retrieval Report\n\n")
        f.write(f"- **Study ID**: {report.study_id}\n")
        f.write(f"- **Contrast**: {report.contrast}\n")
        f.write(f"- **Candidates Queried**: {len(report.candidates_queried)}\n")
        f.write(f"- **Verified Literature Records**: {report.verified_literature_count}\n")
        f.write(f"- **Verified Database Annotations**: {report.verified_database_count}\n")
        f.write(f"- **Evidence Tier Distribution**: Tier 1={tier_counts.get('tier_1',0)}, Tier 2={tier_counts.get('tier_2',0)}, Tier 3={tier_counts.get('tier_3',0)}\n\n")
        f.write("## Candidate Gene Evidence Packages\n\n")

        for pkg in report.evidence_packages:
            q = pkg.quantitative_metadata
            sym_str = f" ({pkg.symbol})" if pkg.symbol else ""
            f.write(f"### Gene: `{pkg.gene_id}`{sym_str}\n")
            f.write(f"- **Statistical Status**: `{q.statistical_status}`\n")
            f.write(f"- **Phase 1 Metrics**: pvalue={q.pvalue:.2e}, padj={q.padj:.4f}, log2FC={q.log2FoldChange:+.3f}, shrunk_log2FC={q.shrunk_log2FoldChange:+.3f}, lfcSE={q.lfcSE:.3f}\n")
            f.write(f"- **Retrieved Evidence Records**: {len(pkg.evidence_records)}\n\n")

            for ev in pkg.evidence_records:
                if ev.evidence_type == "LITERATURE" and ev.literature_citation:
                    cit = ev.literature_citation
                    f.write(f"  - **[Tier {ev.evidence_tier} Literature]** `{cit.citation_id}` (PMID: {cit.pmid}, DOI: {cit.doi})\n")
                    f.write(f"    - *Title*: {cit.title}\n")
                    f.write(f"    - *Chunk*: \"{ev.claim_text}\"\n")
                elif ev.database_record:
                    db = ev.database_record
                    f.write(f"  - **[Tier {ev.evidence_tier} {db.database} Record]** `{db.record_id}` ({db.association_type})\n")
                    f.write(f"    - *Annotation*: \"{db.annotation_text}\"\n")
            f.write("\n---\n\n")

    logger.info(f"Saved RAG Retrieval Report Markdown to: {report_md_path}")
    logger.info("=== RAG RETRIEVAL LAYER EXECUTION SUCCESSFULLY COMPLETED ===")

if __name__ == "__main__":
    run_rag_retrieval()
