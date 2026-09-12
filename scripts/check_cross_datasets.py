import gzip
import os
import pandas as pd

genes = ['AT3G17609', 'AT4G04720', 'AT2G04170', 'AT1G01010', 'AT5G57630', 'AT3G46640', 'AT4G08920', 'AT1G04400']

files = {
    'OSD-120 (LT_FLT_Col0 vs LT_GC_Col0)': 'data/GSE94983_11._LT_FLT_Col-0_to_LT_GC_Col-0.xlsx.gz',
    'OSD-658 (DK_FLT_Col0 vs DK_GC_Col0)': 'data/GSE94983_12._DK_FLT_Col-0_to_DK_GC_Col-0.xlsx.gz',
    'LT_FLT_WS vs LT_GC_WS': 'data/GSE94983_9._LT_FLT_WS_to_LT_GC_WS.xlsx.gz',
    'DK_FLT_WS vs DK_GC_WS': 'data/GSE94983_10._DK_FLT_WS_to_DK_GC_WS.xlsx.gz',
    'LT_FLT_PhyD vs LT_GC_PhyD': 'data/GSE94983_13._LT_FLT_PhyD_to_LT_GC_PhyD.xlsx.gz',
    'DK_FLT_Col0 vs LT_FLT_Col0 (Dark vs Light FLT)': 'data/GSE94983_18._DK_FLT_Col-0_to_LT_FLT_Col-0.xlsx.gz'
}

for label, fpath in files.items():
    print(f"=== {label} ===")
    if not os.path.exists(fpath):
        print("  File not found.")
        continue
    try:
        with gzip.open(fpath) as gz:
            df = pd.read_excel(gz, engine='openpyxl')
            sub = df[df['gene'].isin(genes)]
            if sub.empty:
                print("  No candidate genes found.")
            for _, r in sub.iterrows():
                g = r['gene']
                lfc = r.get('log2(fold_change)', r.get('log2FC', None))
                pval = r.get('p_value', r.get('pvalue', None))
                qval = r.get('q_value', r.get('qvalue', None))
                sig = r.get('significant', None)
                print(f"  Gene: {g:<10} | log2FC: {lfc:>8.4f} | p-val: {pval:>10.4e} | q-val: {qval:>8.4f} | sig: {sig}")
    except Exception as e:
        print(f"  Error: {e}")
