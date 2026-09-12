import gzip
import io
import pandas as pd
import os

fpath = r"c:\Users\USER\.gemini\antigravity\scratch\rna-seq-ai-agent\data\GSE94983_11._LT_FLT_Col-0_to_LT_GC_Col-0.xlsx.gz"

print(f"Inspecting target reference file: {os.path.basename(fpath)}")
with gzip.open(fpath, "rb") as gz:
    df = pd.read_excel(io.BytesIO(gz.read()))

print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
print("\nColumns:")
for i, col in enumerate(df.columns):
    print(f"  [{i}] {col}")

print("\nFirst 10 rows:")
print(df.head(10).to_string())

print("\nSummary Statistics:")
print(f"Total genes in reference table: {len(df)}")
if "padj" in df.columns:
    print("Significant genes (padj < 0.05):", (df["padj"] < 0.05).sum())
elif "P.value.adj" in df.columns:
    print("Significant genes (P.value.adj < 0.05):", (df["P.value.adj"] < 0.05).sum())

lfc_col = [c for c in df.columns if "log" in c.lower() or "fold" in c.lower() or "lfc" in c.lower()]
print("LFC column(s) detected:", lfc_col)
pval_col = [c for c in df.columns if "p" in c.lower() or "fdr" in c.lower() or "adj" in c.lower()]
print("P-value / FDR column(s) detected:", pval_col)
