# Meta-Analysis Summary Report: OSD-120 & OSD-658

## 1. Study Overview & Provenance

- **OSD-120 Contrast**: Space Flight vs Ground Control (Light-Grown Roots, $N=3$ vs $N=3$)
- **OSD-658 Contrast**: Space Flight vs Ground Control (Dark-Grown Roots, $N=3$ vs $N=3$)
- **Meta-Analysis Method**: Inverse-Variance Weighted Summary-Statistic Integration (Fixed-Effects with Cochran $Q$ and $\text{I}^2$ Heterogeneity Evaluation)

## 2. Candidate Gene Integration Table

| Gene ID | Symbol | OSD-120 LFC | OSD-658 LFC | Meta LFC | Meta SE | Meta $p$-value | Meta FDR ($q$) | $\text{I}^2$ (%) | Convergence Classification |
|---|---|---|---|---|---|---|---|---|---|
| `AT2G04170` | Unassigned | $+1.4074$ | $+1.5853$ | $+1.4093$ | $0.0588$ | $< 10^{-15}$ | $< 10^{-12}$ | $0.0\%$ | **`CONCORDANT`** |
| `AT4G04720` | CPK21 | $+0.3391$ | $+0.0989$ | $+0.3391$ | $0.0113$ | $< 10^{-15}$ | $< 10^{-12}$ | $0.0\%$ | **`CONCORDANT`** |
| `AT3G46640` | LUX | $+0.4286$ | $+0.5146$ | $+0.4289$ | $0.0322$ | $< 10^{-15}$ | $< 10^{-12}$ | $0.0\%$ | **`CONCORDANT`** |
| `AT5G57630` | CIPK21 | $+0.5196$ | $+0.4634$ | $+0.5194$ | $0.0357$ | $< 10^{-15}$ | $< 10^{-12}$ | $0.0\%$ | **`CONCORDANT`** |
| `AT1G01010` | ANAC001 | $+1.1404$ | $-0.2479$ | $+1.1218$ | $0.1026$ | $< 10^{-15}$ | $< 10^{-12}$ | $58.7\%$ | **`DISCORDANT`** |
| `AT3G17609` | HYH | $-4.6856$ | *Unquantified* | N/A | N/A | N/A | N/A | N/A | **`SINGLE_DATASET_ONLY`** |
| `AT5G07390` | RBOHA | $+1.4755$ | *Unquantified* | N/A | N/A | N/A | N/A | N/A | **`SINGLE_DATASET_ONLY`** |
| `AT5G13930` | CHS | $-10.6800$ | *Unquantified* | N/A | N/A | N/A | N/A | N/A | **`SINGLE_DATASET_ONLY`** |

## 3. Genome-Wide Metrics

- Total Loci in Master Dataset: 32,833
- Meta-Analyzed Loci (Present in both datasets with valid SE): 23,773
- Concordant Genes ($\text{I}^2 < 50\%$, same sign): 18,421
- Heterogeneous Genes ($\text{I}^2 \ge 50\%$, same sign): 1,240
- Discordant Genes (opposite signs): 4,112
- Single Dataset Only (filtered by Cuffdiff): 9,060

META-ANALYSIS REPORT GENERATED DETERMINISTICALLY.
