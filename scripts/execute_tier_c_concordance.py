import gzip
import io
import json
import os
import pandas as pd
import numpy as np
from scipy import stats

ref_path = r"c:\Users\USER\.gemini\antigravity\scratch\rna-seq-ai-agent\data\GSE94983_11._LT_FLT_Col-0_to_LT_GC_Col-0.xlsx.gz"
pipe_path = r"c:\Users\USER\.gemini\antigravity\scratch\rna-seq-ai-agent\results\osd120_primary_analysis\differential_expression.csv"
out_dir = r"c:\Users\USER\.gemini\antigravity\scratch\rna-seq-ai-agent\results\osd120_primary_analysis"

# Load datasets
with gzip.open(ref_path, "rb") as gz:
    ref_df = pd.read_excel(io.BytesIO(gz.read()))

pipe_df = pd.read_csv(pipe_path)

# Parse reference AGI gene IDs
parsed_rows = []
for idx, row in ref_df.iterrows():
    raw_gene = str(row["gene"]).strip() if pd.notna(row["gene"]) else ""
    lfc = float(row["log2(fold_change)"]) if pd.notna(row["log2(fold_change)"]) else 0.0
    pval = float(row["p_value"]) if pd.notna(row["p_value"]) else 1.0
    qval = float(row["q_value"]) if pd.notna(row["q_value"]) else 1.0
    sig = str(row["significant"]).strip().lower() if pd.notna(row["significant"]) else "no"

    for sub in raw_gene.split(","):
        sub_gene = sub.strip()
        if sub_gene.startswith("AT") and "G" in sub_gene:
            parsed_rows.append({
                "agi_id": sub_gene,
                "ref_lfc": lfc,
                "ref_pval": pval,
                "ref_qval": qval,
                "ref_sig": sig
            })

ref_parsed_df = pd.DataFrame(parsed_rows)
# Deduplicate by lowest q_value per AGI ID
ref_parsed_df.sort_values(by="ref_qval", inplace=True)
ref_dedup = ref_parsed_df.drop_duplicates(subset=["agi_id"], keep="first").copy()

# Merge shared genes
merged_df = pd.merge(
    pipe_df,
    ref_dedup,
    left_on="gene_id",
    right_on="agi_id",
    how="inner"
)

n_shared = len(merged_df)
print(f"=== TIER C CONCORDANCE ANALYSIS ({n_shared:,} SHARED AGI GENES) ===")

# 1. PRIMARY METRICS: CONTINUOUS LFC CORRELATION
clean_lfc = merged_df[["shrunk_log2FoldChange", "ref_lfc"]].dropna()
# Exclude zero-variance rows for Pearson calculation
var_mask = (clean_lfc["shrunk_log2FoldChange"] != 0) | (clean_lfc["ref_lfc"] != 0)
clean_var = clean_lfc[var_mask]

spearman_rho, spearman_p = stats.spearmanr(clean_lfc["shrunk_log2FoldChange"], clean_lfc["ref_lfc"])
pearson_r, pearson_p = stats.pearsonr(clean_var["shrunk_log2FoldChange"], clean_var["ref_lfc"])

print("\n--- PRIMARY METRIC 1: CONTINUOUS LFC CORRELATION ---")
print(f"Spearman rank correlation (rho): {spearman_rho:.4f} (p-value: {spearman_p:.2e})")
print(f"Pearson correlation (r):          {pearson_r:.4f} (p-value: {pearson_p:.2e})")

# 2. PRIMARY METRIC 2: DIRECTIONAL AGREEMENT MATRIX
pipe_pos = merged_df["shrunk_log2FoldChange"] > 0
pipe_neg = merged_df["shrunk_log2FoldChange"] < 0
ref_pos = merged_df["ref_lfc"] > 0
ref_neg = merged_df["ref_lfc"] < 0

up_up = (ref_pos & pipe_pos).sum()
down_down = (ref_neg & pipe_neg).sum()
up_down = (ref_pos & pipe_neg).sum() # Ref UP, Pipe DOWN
down_up = (ref_neg & pipe_pos).sum() # Ref DOWN, Pipe UP

total_non_zero = up_up + down_down + up_down + down_up
concordant_cnt = up_up + down_down
dir_concordance_rate = (concordant_cnt / total_non_zero) * 100.0 if total_non_zero > 0 else 0.0

print("\n--- PRIMARY METRIC 2: DIRECTIONAL AGREEMENT MATRIX ---")
print(f"  UP / UP       (Ref +, Pipe +): {up_up:,}")
print(f"  DOWN / DOWN   (Ref -, Pipe -): {down_down:,}")
print(f"  UP / DOWN     (Ref +, Pipe -): {up_down:,}")
print(f"  DOWN / UP     (Ref -, Pipe +): {down_up:,}")
print(f"  Total Non-Zero LFC Genes:    {total_non_zero:,}")
print(f"  Directional Concordance Rate: {dir_concordance_rate:.2f}%")

# 3. SECONDARY / EXPLORATORY ANALYSIS: THRESHOLDED DEG SETS
ref_degs = set(merged_df[merged_df["ref_qval"] < 0.05]["gene_id"])
pipe_degs_strict = set(merged_df[merged_df["padj"] < 0.05]["gene_id"])
pipe_degs_exp = set(merged_df[merged_df["pvalue"] < 0.01]["gene_id"])

# Strict threshold overlap
overlap_strict = ref_degs.intersection(pipe_degs_strict)
jaccard_strict = len(overlap_strict) / len(ref_degs.union(pipe_degs_strict)) if ref_degs.union(pipe_degs_strict) else 0.0

# Exploratory threshold overlap
overlap_exp = ref_degs.intersection(pipe_degs_exp)
jaccard_exp = len(overlap_exp) / len(ref_degs.union(pipe_degs_exp)) if ref_degs.union(pipe_degs_exp) else 0.0

# Directional concordance among exploratory overlapping DEGs
exp_overlap_df = merged_df[merged_df["gene_id"].isin(overlap_exp)]
exp_up_up = ((exp_overlap_df["ref_lfc"] > 0) & (exp_overlap_df["shrunk_log2FoldChange"] > 0)).sum()
exp_down_down = ((exp_overlap_df["ref_lfc"] < 0) & (exp_overlap_df["shrunk_log2FoldChange"] < 0)).sum()
exp_dir_concordance = ((exp_up_up + exp_down_down) / len(exp_overlap_df)) * 100.0 if len(exp_overlap_df) > 0 else 0.0

print("\n--- SECONDARY EXPLORATORY / SENSITIVITY METRICS (THRESHOLDED SETS) ---")
print("Threshold Disparity Note: Pipeline padj uses BH FDR on N=3; Reference q_value uses Storey q-value on Cuffdiff.")
print(f"Strict Threshold (Pipe padj < 0.05 vs Ref qval < 0.05):")
print(f"  Pipe DEGs: {len(pipe_degs_strict)} | Ref DEGs: {len(ref_degs)} | Overlap: {len(overlap_strict)} | Jaccard: {jaccard_strict:.4f}")
print(f"Exploratory Threshold (Pipe unadjusted p < 0.01 vs Ref qval < 0.05):")
print(f"  Pipe DEGs: {len(pipe_degs_exp)} | Ref DEGs: {len(ref_degs)} | Overlap: {len(overlap_exp)} | Jaccard: {jaccard_exp:.4f}")
print(f"  Exploratory Overlapping DEGs Directional Concordance: {exp_dir_concordance:.2f}% ({exp_up_up + exp_down_down}/{len(exp_overlap_df)})")

# 4. TOP-50 REFERENCE DEGS AUDIT
ref_top50 = merged_df.sort_values(by="ref_qval").head(50)
top50_same_dir = (((ref_top50["ref_lfc"] > 0) & (ref_top50["shrunk_log2FoldChange"] > 0)) |
                  ((ref_top50["ref_lfc"] < 0) & (ref_top50["shrunk_log2FoldChange"] < 0))).sum()
top50_rho, _ = stats.spearmanr(ref_top50["shrunk_log2FoldChange"], ref_top50["ref_lfc"])

print("\n--- TOP-50 REFERENCE DEGS CONCORDANCE ---")
print(f"Directional concordance among Top-50 Reference DEGs: {top50_same_dir}/50 ({(top50_same_dir/50)*100:.1f}%)")
print(f"Top-50 LFC Spearman rank correlation (rho): {top50_rho:.4f}")

# Classification Rule:
# A. Concordant: Spearman rho >= 0.50 & Directional Concordance >= 70%
# B. Partially Concordant: Spearman rho >= 0.20 & Directional Concordance >= 55%
# C. Discordant: Spearman rho < 0.20 or Directional Concordance < 55%
if spearman_rho >= 0.50 and dir_concordance_rate >= 70.0:
    tier_c_class = "A. CONCORDANT"
elif spearman_rho >= 0.20 and dir_concordance_rate >= 55.0:
    tier_c_class = "B. PARTIALLY CONCORDANT"
else:
    tier_c_class = "C. DISCORDANT"

print(f"\n==================================================")
print(f"=== FINAL TIER C CONCORDANCE CLASSIFICATION: {tier_c_class} ===")
print(f"==================================================")

# Save concordance metrics JSON
concordance_data = {
    "reference_file": "GSE94983_11._LT_FLT_Col-0_to_LT_GC_Col-0.xlsx.gz",
    "reference_provenance": "NCBI GEO GSE94983 (CARA Experiment, Kruse et al.)",
    "shared_genes_analyzed": n_shared,
    "primary_metrics": {
        "spearman_rho": float(spearman_rho),
        "spearman_pvalue": float(spearman_p),
        "pearson_r": float(pearson_r),
        "pearson_pvalue": float(pearson_p),
        "directional_agreement_matrix": {
            "up_up": int(up_up),
            "down_down": int(down_down),
            "up_down": int(up_down),
            "down_up": int(down_up)
        },
        "directional_concordance_rate_pct": float(dir_concordance_rate)
    },
    "secondary_exploratory_metrics": {
        "strict_padj05_jaccard": float(jaccard_strict),
        "exploratory_p01_jaccard": float(jaccard_exp),
        "exploratory_overlapping_degs_count": int(len(overlap_exp)),
        "exploratory_overlapping_degs_directional_concordance_pct": float(exp_dir_concordance)
    },
    "top50_reference_degs": {
        "directional_concordance_count": int(top50_same_dir),
        "directional_concordance_pct": float((top50_same_dir / 50) * 100),
        "top50_spearman_rho": float(top50_rho)
    },
    "final_tier_c_classification": tier_c_class,
    "causal_claim_guardrail": "Describes spaceflight-associated transcriptional differences relative to ground control; does NOT establish pure microgravity causality or biological replication."
}

with open(os.path.join(out_dir, "tier_c_concordance_report.json"), "w", encoding="utf-8") as f:
    json.dump(concordance_data, f, indent=2)

print(f"Saved Tier C concordance report to: {os.path.join(out_dir, 'tier_c_concordance_report.json')}")
