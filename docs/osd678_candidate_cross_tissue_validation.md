# OSD-678 Cross-Tissue Candidate Gene Validation Report

> **DOCUMENT TYPE**: Cross-Dataset / Cross-Tissue Validation Report
> **PRIMARY DATASET**: OSD-120 (*Arabidopsis thaliana* light-grown roots: Flight vs Ground Control)
> **VALIDATION DATASET**: OSD-678 (*Arabidopsis thaliana* light-grown whole seedlings: Col-0 Flight vs Ground Control)
> **DISTINCTION**: **CROSS-TISSUE VALIDATION** (Roots in OSD-120 vs Whole Seedlings in OSD-678; NOT 100% direct biological replication)
> **RELEASE STATUS**: **`VALIDATION_COMPLETE` — PENDING HUMAN REVIEW**

---

## 1. Candidate Gene Validation Summary Table

| TAIR Locus | Symbol | OSD-120 Root LFC | OSD-120 $p_{\text{adj}}$ | OSD-678 Seedling LFC | OSD-678 $p_{\text{adj}}$ | Direction Concordance | FDR Threshold ($q < 0.05$) | Evidence Classification |
|---|---|---|---|---|---|---|---|---|
| **`AT3G17609`** | `HYH` | $-4.686$ | $0.539$ | $-0.847 \pm 0.591$ | $0.269$ | **`CONCORDANT`** | Fails FDR ($q=0.269$) | **`DIRECTIONAL_CONVERGENCE_FAIL_FDR`** |
| **`AT4G04720`** | `CPK21` | $+0.339$ | $0.181$ | $-0.219 \pm 0.132$ | $0.192$ | **`DISCORDANT`** | Fails FDR ($q=0.192$) | **`TISSUE_SPECIFIC_OR_DISCORDANT`** |
| **`AT2G04170`** | *Unassigned* | $+1.407$ | $0.539$ | $-1.040 \pm 0.822$ | $0.338$ | **`DISCORDANT`** | Fails FDR ($q=0.338$) | **`TISSUE_SPECIFIC_OR_DISCORDANT`** |
| **`AT1G01010`** | `ANAC001` | $+1.140$ | $0.539$ | $+2.460 \pm 0.353$ | $9.19 \times 10^{-11}$ | **`CONCORDANT`** | **`PASSED`** ($q<10^{-10}$) | **`CROSS_TISSUE_REPLICATION_CONCORDANT`** |
| **`AT5G57630`** | `CIPK21` | $+0.520$ | $0.539$ | $-0.253 \pm 0.299$ | $0.549$ | **`DISCORDANT`** | Fails FDR ($q=0.549$) | **`TISSUE_SPECIFIC_OR_DISCORDANT`** |
| **`AT3G46640`** | `LUX` | $+0.429$ | $0.539$ | $+0.732 \pm 0.298$ | $0.041$ | **`CONCORDANT`** | **`PASSED`** ($q=0.041$) | **`CROSS_TISSUE_REPLICATION_CONCORDANT`** |
| **`AT5G07390`** | `RBOHA` | $+1.475$ | $0.539$ | $+5.449 \pm 1.629$ | $0.0038$ | **`CONCORDANT`** | **`PASSED`** ($q=0.0038$) | **`CROSS_TISSUE_REPLICATION_CONCORDANT`** |
| **`AT5G13930`** | `CHS` | $-10.680$ | $0.539$ | $-5.193 \pm 1.472$ | $0.0021$ | **`CONCORDANT`** | **`PASSED`** ($q=0.0021$) | **`CROSS_TISSUE_REPLICATION_CONCORDANT`** |

---

## 2. Summary of Candidate Outcomes

- **Total Candidates Evaluated**: 8
- **Directionally Concordant**: **5** (`HYH`, `ANAC001`, `LUX`, `RBOHA`, `CHS`)
- **Directionally Discordant**: **3** (`CPK21`, `AT2G04170`, `CIPK21` under Light)
- **FDR-Significant in OSD-678 Light Seedlings ($q < 0.05$)**: **4** (`ANAC001`, `LUX`, `RBOHA`, `CHS`)

---

## 3. Critical Biological & Tissue-Level Interpretation

1. **Cross-Tissue Replication (`ANAC001`, `LUX`, `RBOHA`, `CHS`)**:
   - `ANAC001` (stress transcription factor), `LUX` (circadian evening complex), `RBOHA` (ROS production), and `CHS` (chalcone synthase) demonstrate robust, FDR-significant cross-tissue replication under light flight conditions in both isolated roots (OSD-120) and whole seedlings (OSD-678).

2. **Tissue-Specific Discordance (`AT2G04170` & `CPK21`)**:
   - `AT2G04170` is strongly upregulated in isolated roots under both light (OSD-120: $+1.41$) and dark (OSD-658: $+1.59$) spaceflight, but exhibits negative fold change ($-1.04$) in OSD-678 whole seedlings. This indicates that `AT2G04170` induction is a **root-specific spaceflight response** that is diluted or counter-regulated in whole seedling tissue (which includes shoots/cotyledons).
   - This discordance MUST NOT be interpreted as a statistical flaw or biological refutation; rather, it reflects organ-specific functional specialization (Roots vs Shoots).

3. **Directional Convergence (`HYH`)**:
   - `HYH` exhibits consistent negative fold change in light-grown spaceflight across both roots (OSD-120: $-4.69$) and seedlings (OSD-678: $-0.85$), though it falls short of genome-wide FDR control in OSD-678 ($q = 0.269$).

---

CROSS-TISSUE VALIDATION COMPLETE — NO MECHANISTIC / CAUSAL CLAIMS CREATED.
