import gzip
import io
import pandas as pd
import os

fpath = r"c:\Users\USER\.gemini\antigravity\scratch\rna-seq-ai-agent\data\GSE94983_11._LT_FLT_Col-0_to_LT_GC_Col-0.xlsx.gz"

with gzip.open(fpath, "rb") as gz:
    df = pd.read_excel(io.BytesIO(gz.read()))

print("=== GSE94983 FILE 11 DETAILED AUDIT ===")
print("Total rows:", len(df))

sig_yes = df[df["significant"] == "yes"]
print("Rows with significant == 'yes':", len(sig_yes))

q_05 = df[df["q_value"] < 0.05]
print("Rows with q_value < 0.05:", len(q_05))

if len(sig_yes) > 0:
    up = sig_yes[sig_yes["log2(fold_change)"] > 0]
    down = sig_yes[sig_yes["log2(fold_change)"] < 0]
    print(f"  Significant Upregulated (log2FC > 0): {len(up)}")
    print(f"  Significant Downregulated (log2FC < 0): {len(down)}")

print("\nTop 10 Significant DEGs in Reference Table:")
if len(sig_yes) > 0:
    print(sig_yes[["gene", "locus", "value_1", "value_2", "log2(fold_change)", "p_value", "q_value"]].head(10).to_string(index=False))
