import os
import hashlib
import gzip
import json
import math
import numpy as np
import pandas as pd
from scipy.stats import norm, chi2

def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def bh_adjust_pvalues(pvalues: np.ndarray) -> np.ndarray:
    """Perform Benjamini-Hochberg FDR adjustment on p-values array."""
    pvals = np.asarray(pvalues, dtype=float)
    n = len(pvals)
    if n == 0:
        return np.array([])
    
    # Handle NaNs
    valid_mask = ~np.isnan(pvals)
    adjusted = np.full(n, np.nan)
    if not np.any(valid_mask):
        return adjusted
    
    valid_p = pvals[valid_mask]
    n_valid = len(valid_p)
    
    order = np.argsort(valid_p)
    ranks = np.empty(n_valid, dtype=int)
    ranks[order] = np.arange(1, n_valid + 1)
    
    q_valid = valid_p * float(n_valid) / ranks
    
    # Cumulative minimum from right to left
    q_sorted = q_valid[order]
    for i in range(n_valid - 2, -1, -1):
        q_sorted[i] = min(q_sorted[i], q_sorted[i + 1])
    q_valid[order] = q_sorted
    q_valid = np.clip(q_valid, 0.0, 1.0)
    
    adjusted[valid_mask] = q_valid
    return adjusted

def derive_cuffdiff_se(row) -> float:
    """Derive standard error from Cuffdiff row output."""
    lfc = row.get('log2(fold_change)', row.get('log2FC', 0.0))
    stat = row.get('test_stat', None)
    pval = row.get('p_value', row.get('pvalue', None))
    
    if pd.isna(lfc):
        return np.nan
    
    # Method 1: test_stat = LFC / SE => SE = |LFC / test_stat|
    if stat is not None and not pd.isna(stat) and abs(stat) > 1e-6:
        se = abs(lfc / stat)
        if se > 1e-8 and not np.isinf(se):
            return float(se)
            
    # Method 2: derive from p-value using normal distribution
    if pval is not None and not pd.isna(pval) and 0 < pval < 1.0:
        z = norm.ppf(1.0 - pval / 2.0)
        if z > 1e-6 and abs(lfc) > 1e-6:
            se = abs(lfc) / z
            if se > 1e-8 and not np.isinf(se):
                return float(se)
                
    return np.nan

def run_meta_analysis():
    """Run inverse-variance weighted meta-analysis on OSD-120 and OSD-658."""
    print("Starting Meta-Analysis Execution...")
    
    # Define source paths
    osd120_deseq2_path = 'results/osd120_primary_analysis/differential_expression.csv'
    osd120_gse_path = 'data/GSE94983_11._LT_FLT_Col-0_to_LT_GC_Col-0.xlsx.gz'
    osd658_gse_path = 'data/GSE94983_12._DK_FLT_Col-0_to_DK_GC_Col-0.xlsx.gz'
    
    # 1. Compute Provenance Hashes
    hashes = {
        'osd120_deseq2_csv': compute_sha256(osd120_deseq2_path),
        'osd120_gse94983_11_xlsx_gz': compute_sha256(osd120_gse_path),
        'osd658_gse94983_12_xlsx_gz': compute_sha256(osd658_gse_path)
    }
    
    # 2. Load OSD-120 (DESeq2 Primary)
    print("Loading OSD-120 DESeq2 results...")
    df_120 = pd.read_csv(osd120_deseq2_path)
    # Re-map columns if needed
    gene_col_120 = 'gene' if 'gene' in df_120.columns else ('gene_id' if 'gene_id' in df_120.columns else df_120.columns[0])
    df_120 = df_120.rename(columns={
        gene_col_120: 'gene_id',
        'log2FoldChange': 'lfc_120',
        'shrunken_log2FC': 'shrunk_lfc_120',
        'lfcSE': 'se_120',
        'pvalue': 'pval_120',
        'padj': 'padj_120'
    })
    
    # 3. Load OSD-658 (GSE94983_12 Cuffdiff)
    print("Loading OSD-658 Cuffdiff results...")
    with gzip.open(osd658_gse_path) as gz:
        df_658_raw = pd.read_excel(gz, engine='openpyxl')
        
    df_658_records = []
    for _, r in df_658_raw.iterrows():
        g = str(r['gene']).strip()
        lfc = r.get('log2(fold_change)', np.nan)
        pval = r.get('p_value', np.nan)
        qval = r.get('q_value', np.nan)
        se = derive_cuffdiff_se(r)
        df_658_records.append({
            'gene_id': g,
            'lfc_658': lfc,
            'se_658': se,
            'pval_658': pval,
            'padj_658': qval
        })
    df_658 = pd.DataFrame(df_658_records)
    
    # Deduplicate 658 if needed by smallest pval
    df_658 = df_658.sort_values('pval_658').groupby('gene_id', as_index=False).first()
    
    # 4. Merge datasets
    merged = pd.merge(df_120, df_658, on='gene_id', how='outer')
    
    meta_results = []
    
    for _, r in merged.iterrows():
        g = r['gene_id']
        
        # OSD-120 stats (prefer shrunken LFC if available, fallback to log2FoldChange)
        lfc1 = r.get('shrunk_lfc_120', r.get('lfc_120', np.nan))
        if pd.isna(lfc1):
            lfc1 = r.get('lfc_120', np.nan)
        se1 = r.get('se_120', np.nan)
        pval1 = r.get('pval_120', np.nan)
        padj1 = r.get('padj_120', np.nan)
        
        # OSD-658 stats
        lfc2 = r.get('lfc_658', np.nan)
        se2 = r.get('se_658', np.nan)
        pval2 = r.get('pval_658', np.nan)
        padj2 = r.get('padj_658', np.nan)
        
        has_120 = not (pd.isna(lfc1) or pd.isna(se1) or se1 <= 0)
        has_658 = not (pd.isna(lfc2) or pd.isna(se2) or se2 <= 0)
        
        if has_120 and has_658:
            w1 = 1.0 / (se1 ** 2)
            w2 = 1.0 / (se2 ** 2)
            w_sum = w1 + w2
            
            lfc_meta = (w1 * lfc1 + w2 * lfc2) / w_sum
            se_meta = math.sqrt(1.0 / w_sum)
            z_meta = lfc_meta / se_meta
            pval_meta = float(2.0 * (1.0 - norm.cdf(abs(z_meta))))
            ci_lower = lfc_meta - 1.96 * se_meta
            ci_upper = lfc_meta + 1.96 * se_meta
            
            # Heterogeneity Q
            q_stat = float(w1 * ((lfc1 - lfc_meta) ** 2) + w2 * ((lfc2 - lfc_meta) ** 2))
            pval_q = float(1.0 - chi2.cdf(q_stat, df=1)) if q_stat >= 0 else 1.0
            i2 = max(0.0, float((q_stat - 1.0) / q_stat * 100.0)) if q_stat > 1e-6 else 0.0
            
            # Convergence classification
            same_sign = (lfc1 * lfc2 > 0)
            if same_sign and i2 < 50.0 and pval_q >= 0.05:
                convergence = 'CONCORDANT'
            elif same_sign and (i2 >= 50.0 or pval_q < 0.05):
                convergence = 'HETEROGENEOUS'
            else:
                convergence = 'DISCORDANT'
                
            status = 'META_ANALYZED'
        else:
            lfc_meta = np.nan
            se_meta = np.nan
            z_meta = np.nan
            pval_meta = np.nan
            ci_lower = np.nan
            ci_upper = np.nan
            q_stat = np.nan
            pval_q = np.nan
            i2 = np.nan
            
            if has_120 or has_658:
                convergence = 'SINGLE_DATASET_ONLY'
                status = 'SINGLE_DATASET_ONLY'
            else:
                convergence = 'NOT_META_ANALYZABLE'
                status = 'NOT_META_ANALYZABLE'
                
        meta_results.append({
            'gene_id': g,
            'osd120_lfc': lfc1,
            'osd120_se': se1,
            'osd120_pval': pval1,
            'osd120_padj': padj1,
            'osd658_lfc': lfc2,
            'osd658_se': se2,
            'osd658_pval': pval2,
            'osd658_padj': padj2,
            'meta_lfc': lfc_meta,
            'meta_se': se_meta,
            'meta_z': z_meta,
            'meta_pval': pval_meta,
            'meta_ci_lower': ci_lower,
            'meta_ci_upper': ci_upper,
            'q_stat': q_stat,
            'pval_q': pval_q,
            'i2_percent': i2,
            'convergence_classification': convergence,
            'status': status
        })
        
    df_res = pd.DataFrame(meta_results)
    
    # Calculate FDR across meta-analyzed genes
    meta_mask = df_res['status'] == 'META_ANALYZED'
    df_res['meta_padj'] = np.nan
    if meta_mask.any():
        pvals_to_adjust = df_res.loc[meta_mask, 'meta_pval'].values
        df_res.loc[meta_mask, 'meta_padj'] = bh_adjust_pvalues(pvals_to_adjust)
        
    # Save outputs
    out_dir = 'results/meta_analysis'
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Full CSV
    csv_path = os.path.join(out_dir, 'meta_analysis_results.csv')
    df_res.to_csv(csv_path, index=False)
    print(f"Saved {csv_path}")
    
    # 2. Candidate Gene CSV
    candidate_genes = ['AT3G17609', 'AT4G04720', 'AT2G04170', 'AT1G01010', 'AT5G57630', 'AT3G46640', 'AT5G07390', 'AT5G13930']
    df_cand = df_res[df_res['gene_id'].isin(candidate_genes)].copy()
    cand_csv_path = os.path.join(out_dir, 'candidate_gene_meta_analysis.csv')
    df_cand.to_csv(cand_csv_path, index=False)
    print(f"Saved {cand_csv_path}")
    
    # 3. Provenance JSON
    prov_path = os.path.join(out_dir, 'meta_analysis_provenance.json')
    prov_data = {
        'analysis_type': 'INVERSE_VARIANCE_SUMMARY_STATISTIC_META_ANALYSIS',
        'source_file_hashes': hashes,
        'contrasts': {
            'OSD-120': 'Space Flight vs Ground Control (Light-Grown Roots)',
            'OSD-658': 'Space Flight vs Ground Control (Dark-Grown Roots)'
        },
        'direction_harmonization': 'Positive LFC indicates higher expression in Spaceflight relative to Ground Control in both datasets.',
        'formula': 'Inverse-variance weighted fixed-effects pooling with Cochran Q and I^2 heterogeneity estimation'
    }
    with open(prov_path, 'w') as f:
        json.dump(prov_data, f, indent=2)
    print(f"Saved {prov_path}")
    
    # 4. Report JSON
    n_analyzed = int(meta_mask.sum())
    n_concordant = int((df_res['convergence_classification'] == 'CONCORDANT').sum())
    n_heterogeneous = int((df_res['convergence_classification'] == 'HETEROGENEOUS').sum())
    n_discordant = int((df_res['convergence_classification'] == 'DISCORDANT').sum())
    n_single = int((df_res['convergence_classification'] == 'SINGLE_DATASET_ONLY').sum())
    
    report_json = {
        'meta_analysis_summary': {
            'total_genes_in_master': len(df_res),
            'genes_meta_analyzed': n_analyzed,
            'concordant_genes': n_concordant,
            'heterogeneous_genes': n_heterogeneous,
            'discordant_genes': n_discordant,
            'single_dataset_genes': n_single,
            'meta_fdr_sig_genes': int((df_res['meta_padj'] < 0.05).sum())
        },
        'candidate_gene_outcomes': df_cand[['gene_id', 'osd120_lfc', 'osd658_lfc', 'meta_lfc', 'meta_padj', 'i2_percent', 'convergence_classification']].to_dict(orient='records')
    }
    json_path = os.path.join(out_dir, 'meta_analysis_report.json')
    with open(json_path, 'w') as f:
        json.dump(report_json, f, indent=2)
    print(f"Saved {json_path}")
    
    print("Meta-Analysis Execution Complete!")

if __name__ == '__main__':
    run_meta_analysis()
