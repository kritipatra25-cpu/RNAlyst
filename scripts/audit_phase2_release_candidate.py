"""
Automated 100% Phase 2 Release Candidate Audit Script.
Audits all gene interpretations in interpretation_report.json against Phase 1 differential_expression.csv.
"""

import json
import math
import sys
import pandas as pd
from pathlib import Path

def run_release_candidate_audit():
    root_dir = Path("c:/Users/USER/.gemini/antigravity/scratch/rna-seq-ai-agent")
    de_csv = root_dir / "results/osd120_primary_analysis/differential_expression.csv"
    report_json = root_dir / "results/osd120_phase2_interpretation/interpretation_report.json"

    if not de_csv.exists():
        print(f"ERROR: Phase 1 DE CSV missing at {de_csv}")
        sys.exit(1)

    if not report_json.exists():
        print(f"ERROR: Phase 2 Report JSON missing at {report_json}")
        sys.exit(1)

    de_df = pd.read_csv(de_csv)
    de_map = {str(row["gene_id"]).strip(): row for _, row in de_df.iterrows()}

    with open(report_json, "r", encoding="utf-8") as f:
        report = json.load(f)

    audit_errors = []
    audited_genes_count = 0
    class_d_count = 0

    # 1. Audit Study-Level Warning & Causal Guardrail
    expected_causal = (
        "The analysis and interpretation describe spaceflight-associated transcriptional differences relative "
        "to ground control under light-treated root conditions at Day 13. They do NOT establish pure microgravity "
        "causality or biological replication."
    )
    if expected_causal not in report.get("causal_guardrail_statement", ""):
        audit_errors.append("Causal guardrail statement missing or modified")

    sample_warning = report.get("sample_size_warning", "")
    if "N=3 vs N=3" not in sample_warning or "exploratory" not in sample_warning.lower():
        audit_errors.append("Study-level sample size warning missing or incomplete")

    # 2. Audit Provenance Manifest
    manifest = report.get("provenance_manifest", {})
    if manifest.get("synthesis_mode") != "DETERMINISTIC_REFERENCE":
        audit_errors.append(f"Invalid synthesis_mode: {manifest.get('synthesis_mode')}")
    if manifest.get("provider_name") != "DETERMINISTIC_TEMPLATE_GENERATOR":
        audit_errors.append(f"Invalid provider_name: {manifest.get('provider_name')}")
    if manifest.get("temperature") is not None:
        audit_errors.append(f"Temperature must be None for deterministic mode, got {manifest.get('temperature')}")
    if manifest.get("seed") is not None:
        audit_errors.append(f"Seed must be None for deterministic mode, got {manifest.get('seed')}")

    # 3. Full-Dataset Audit of ALL Gene Interpretations
    forbidden_significance = [
        "significantly upregulated",
        "significantly downregulated",
        "differentially expressed",
        "statistically significant differential expression"
    ]
    forbidden_causal = [
        "causes",
        "drives",
        "mediates",
        "results in",
        "is responsible for",
        "demonstrates that",
        "establishes that"
    ]

    for ev in report.get("gene_interpretations", []):
        audited_genes_count += 1
        gene_id = ev.get("gene_id")

        if gene_id not in de_map:
            audit_errors.append(f"Gene '{gene_id}' in report does not exist in Phase 1 differential_expression.csv")
            continue

        src_row = de_map[gene_id]
        conf = ev.get("confidence_decomposition", {})
        stat = conf.get("statistical_significance", {})
        eff = conf.get("effect_size_precision", {})

        # Verify Numeric Immutability
        src_pval = float(src_row["pvalue"]) if pd.notna(src_row["pvalue"]) else 1.0
        src_padj = float(src_row["padj"]) if pd.notna(src_row["padj"]) else 1.0
        src_lfc = float(src_row["log2FoldChange"]) if pd.notna(src_row["log2FoldChange"]) else 0.0
        src_shrunk = float(src_row["shrunk_log2FoldChange"]) if pd.notna(src_row["shrunk_log2FoldChange"]) else src_lfc
        src_lfcse = float(src_row["lfcSE"]) if pd.notna(src_row["lfcSE"]) else 0.0

        if not math.isclose(stat.get("pvalue", 0.0), src_pval, rel_tol=1e-5):
            audit_errors.append(f"Gene '{gene_id}' pvalue mismatch: report {stat.get('pvalue')} vs source {src_pval}")

        if not math.isclose(stat.get("padj", 0.0), src_padj, rel_tol=1e-5):
            audit_errors.append(f"Gene '{gene_id}' padj mismatch: report {stat.get('padj')} vs source {src_padj}")

        if not math.isclose(eff.get("log2FC", 0.0), src_lfc, rel_tol=1e-5):
            audit_errors.append(f"Gene '{gene_id}' log2FC mismatch: report {eff.get('log2FC')} vs source {src_lfc}")

        if not math.isclose(eff.get("shrunk_log2FC", 0.0), src_shrunk, rel_tol=1e-5):
            audit_errors.append(f"Gene '{gene_id}' shrunk_log2FC mismatch: report {eff.get('shrunk_log2FC')} vs source {src_shrunk}")

        if not math.isclose(eff.get("lfcSE", 0.0), src_lfcse, rel_tol=1e-5):
            audit_errors.append(f"Gene '{gene_id}' lfcSE mismatch: report {eff.get('lfcSE')} vs source {src_lfcse}")

        # Verify Statistical Status Consistency
        stat_status = ev.get("statistical_status")
        if src_padj < 0.05:
            expected_status = "FDR_SIGNIFICANT"
        elif src_pval < 0.05:
            expected_status = "RAW_P_ONLY"
        else:
            expected_status = "NON_SIGNIFICANT"

        if stat_status != expected_status:
            audit_errors.append(f"Gene '{gene_id}' status mismatch: report '{stat_status}' vs expected '{expected_status}'")

        # Verify Confidence Label Consistency
        conf_label = conf.get("confidence_label")
        if stat_status == "FDR_SIGNIFICANT" and conf_label not in ["HIGH", "MEDIUM"]:
            audit_errors.append(f"Gene '{gene_id}' FDR_SIGNIFICANT should have HIGH/MEDIUM confidence, got '{conf_label}'")
        elif stat_status == "RAW_P_ONLY" and conf_label != "EXPLORATORY":
            audit_errors.append(f"Gene '{gene_id}' RAW_P_ONLY must have EXPLORATORY confidence, got '{conf_label}'")

        # Verify Narrative Language
        narrative = ev.get("narrative_summary", "")
        if stat_status != "FDR_SIGNIFICANT":
            text = narrative.lower()
            for phrase in forbidden_significance:
                if phrase in text and "not statistically significant" not in text:
                    audit_errors.append(f"Gene '{gene_id}' narrative contains forbidden phrase '{phrase}': {narrative}")

        # Audit Class D Hypotheses
        if "Class D" in ev.get("evidence_class", ""):
            class_d_count += 1
            if not ev.get("derived_from_class_a_gene_ids"):
                audit_errors.append(f"Class D for '{gene_id}' missing Class A gene links")
            if not ev.get("derived_from_class_c_citation_ids"):
                audit_errors.append(f"Class D for '{gene_id}' missing Class C citation links")
            if not narrative.startswith("Hypothesis"):
                audit_errors.append(f"Class D for '{gene_id}' does not start with 'Hypothesis': {narrative}")

            text = narrative.lower()
            for word in forbidden_causal:
                if word in text and "literature-supported" not in text:
                    audit_errors.append(f"Class D for '{gene_id}' contains forbidden causal word '{word}': {narrative}")

    print("=== PHASE 2 RELEASE CANDIDATE AUDIT RESULTS ===")
    print(f"Total Gene Interpretations Audited: {audited_genes_count}")
    print(f"Total Class D Hypotheses Audited:   {class_d_count}")
    print(f"Total Audit Errors Encountered:     {len(audit_errors)}")

    if audit_errors:
        print("\nERRORS DETECTED:")
        for err in audit_errors:
            print(f" - {err}")
        sys.exit(1)
    else:
        print("\nSUCCESS: 100% of generated gene interpretations passed all release candidate checks!")
        sys.exit(0)

if __name__ == "__main__":
    run_release_candidate_audit()
