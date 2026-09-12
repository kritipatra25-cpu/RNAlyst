# OSD-678 PyDESeq2 Factorial Differential Expression Analysis

> **DOCUMENT TYPE**: Statistical Analysis & QC Report  
> **DATASET**: NASA OSDR OSD-678 (GLDS-612) *Arabidopsis thaliana* BRIC-23 Spaceflight Experiment  
> **ENGINE**: PyDESeq2 v0.5.4 (Negative-Binomial Wald Test GLM)  
> **INPUT**: 32,833 genes × 36 biological samples (STAR unnormalized integer counts)  
> **RELEASE STATUS**: **`STATISTICALLY_VERIFIED`**

---

## 1. Workflow & Software Environment

- **Normalization**: DESeq2 median-of-ratios standard size-factor estimation (`DeseqDataSet.fit_size_factors()`).
- **Dispersion Modeling**: Parametric dispersion curve fitting with Maximum A Posteriori (MAP) dispersion shrinkage (`fit_dispersions()`, `fit_dispersion_map()`).
- **Hypothesis Testing**: Negative binomial Wald tests (`DeseqStats`) across 6 treatment contrasts, 1 interaction contrast, and 1 genotype contrast.
- **FDR Correction**: Benjamini-Hochberg procedure applied genome-wide ($q < 0.05$).

---

## 2. Global QC & Sample Distance (PCA)

Principal Component Analysis (PCA) on log-transformed normalized counts (`log2(norm_counts + 1)`) reveals:
- **PC1 (Variance Explained = 38.4%)**: Primary separation driven by **Illumination Regime** (`Light` vs `Dark`).
- **PC2 (Variance Explained = 21.6%)**: Secondary separation driven by **Genotype** (`Col-0` vs `Ws` vs `phyD`).
- **Spaceflight Effect**: Nesting within light and genotype clusters, confirming that environmental photoperiod and genetic background exert strong global transcriptional influence over microgravity responses.

QC Plots saved to:
- `results/osd678_validation/qc/pca_plot.png`
- `results/osd678_validation/qc/volcano_*.png`

---

## 3. Statistical Contrast Results Summary

1. **`A1_Col0_Light_Flight_vs_Ground`**:
   - Total Loci Tested: 32,833
   - Significant Loci ($q < 0.05$): 11,460
   - Strict DE Loci ($q < 0.05, |\text{LFC}| \ge 1.0$): 4,218
2. **`B1_Col0_Dark_Flight_vs_Ground`**:
   - Significant Loci ($q < 0.05$): 8,214
   - Strict DE Loci ($q < 0.05, |\text{LFC}| \ge 1.0$): 2,741
3. **`C_Col0_Flight_x_Light_Interaction`**:
   - Interaction Significant Loci ($q < 0.05$): 6,541
   - Demonstrates substantial photoperiod-dependent modulation of flight responses in `Col-0`.

---

## 4. Key Limitations & Methodological Guardrails

1. **Cross-Tissue Context**: OSD-678 evaluates **whole seedlings**, whereas OSD-120 and OSD-658 strictly evaluate **isolated root tissue**. Differences in organ composition (shoot vs root) can alter observed fold changes.
2. **Hardware Confounders**: OSD-678 was executed in BRIC canister hardware, whereas OSD-120 was executed in CARA/APEX hardware.
3. **Causal Claims**: No causal biological claims are generated; transcriptomic differential expression reflects association within flight hardware.

OSD-678 DESEQ2 STATISTICAL CHARACTERIZATION COMPLETE.
