# Meta-Analysis Design Audit: OSD-120 & OSD-658 Integration

> **DOCUMENT TYPE**: Pre-Implementation Meta-Analysis Design Audit (Read-Only)  
> **DATASETS UNDER AUDIT**: NASA OSDR OSD-120 (*Arabidopsis* light-grown roots) & OSD-658 (*Arabidopsis* dark-grown roots)  
> **AUDIT PURPOSE**: Evaluate statistical identifiability, experimental comparability, and confounding risks before any re-quantification or meta-analysis implementation.  
> **RELEASE STATUS**: **`DESIGN_REVIEW_ONLY` — IMPLEMENTATION NOT YET AUTHORIZED**

---

## 1. Experimental Design Audit

| Experimental Variable | OSD-120 (GLDS-120) | OSD-658 (GLDS-658 / GSE94983_12) |
|---|---|---|
| **Organism & Genotype** | *Arabidopsis thaliana* (Col-0 ecotype) | *Arabidopsis thaliana* (Col-0 ecotype) |
| **Tissue / Target** | Plant Roots | Plant Roots |
| **Spaceflight Condition** | ISS Spaceflight (Hardware module) | ISS Spaceflight (Hardware module) |
| **Ground Control Condition** | Ground Control hardware (1g ambient matching) | Ground Control hardware (1g ambient matching) |
| **Light Treatment** | **Continuous / Light-Grown** | **Continuous Darkness / Dark-Grown** |
| **Radiation Exposure** | ISS Ambient Cosmic Radiation | ISS Ambient Cosmic Radiation |
| **Biological Replicates** | $N=3$ Spaceflight, $N=3$ Ground Control | $N=3$ Spaceflight, $N=3$ Ground Control |
| **Developmental Stage** | 13-day old root tissues | 13-day old dark root tissues |
| **Sequencing Platform** | Illumina Bulk RNA-seq | Illumina Bulk RNA-seq |
| **Primary Repo Pipeline** | Salmon + DESeq2 (apeglm LFC shrinkage) | Cuffdiff (in GSE94983) / Salmon + DESeq2 |
| **Known Confounders** | Illumination inside flight hardware | Total darkness; hardware atmospheric enclosure |

---

## 2. Comparability Assessment

- **Tissue Type**: `COMPATIBLE` (*Arabidopsis* root tissue in both datasets).
- **Genotype / Ecotype**: `COMPATIBLE` (Col-0 background in both).
- **Primary Factor (Spaceflight)**: `COMPATIBLE` (Spaceflight vs 1g Ground Control contrast).
- **Light Condition**: `INCOMPATIBLE` (OSD-120 is light-grown; OSD-658 is dark-grown).
- **Study / Batch ID**: `INCOMPATIBLE` (Distinct mission experiments and hardware runs).
- **Sequencing & Software Pipeline**: `PARTIALLY COMPATIBLE` (Can be harmonized via raw FASTQ re-quantification, but primary published tables differ).

---

## 3. What Question a Combined Analysis Would Answer

### Model A: Simple Pooled Model (`~ Spaceflight`)
- **Biological Question**: "What is the overall average effect of spaceflight across light and dark roots?"
- **Assumptions**: Zero batch effect between OSD-120 and OSD-658; light condition has zero main effect or interaction.
- **Validity Verdict**: **INVALID / SCIENTIFICALLY MISLEADING**. Ignoring study batch and light condition introduces severe confounding.

### Model B: Study-Blocked Model (`~ Study + Spaceflight`)
- **Biological Question**: "What is the spaceflight effect controlling for additive study baseline differences?"
- **Assumptions**: The spaceflight response is identical in light and dark conditions; no Light $\times$ Spaceflight interaction exists.
- **Validity Verdict**: **PARTIALLY VALID FOR ADDITIVE SIGNAL ONLY**, but fails to test light-dependent spaceflight responses.

### Model C: Spaceflight $\times$ Light Interaction Model (`~ Light + Spaceflight + Light:Spaceflight`)
- **Biological Question**: "Which spaceflight responses depend on light exposure versus being light-independent?"
- **Assumptions**: `Study ID` is completely identical to `Light Condition` (OSD-120 = Light, OSD-658 = Dark).
- **Validity Verdict**: **PERFECTLY COLLINEAR / UNIDENTIFIABLE IN POOLED RAW COUNTS**. In a raw pooled dataset, `Study` and `Light` cannot be separated.

### Model D: Multi-Factor Meta-Analytic Model (Option B/C: Dataset-Specific DESeq2 $\to$ Meta-Analysis)
- **Biological Question**: "What is the combined effect size of spaceflight across independent experiments, and what proportion of variance ($\text{I}^2$) represents study-specific/light heterogeneity?"
- **Assumptions**: Each study estimates its internal spaceflight vs ground contrast independently ($N=3$ vs $N=3$).
- **Validity Verdict**: **STATISTICALLY SOUND & IDENTIFIABLE**. Eliminates cross-study raw count batch risks.

---

## 4. Critical Confounding Audit

### Collinearity Analysis
In the current project structure:
$$\text{Study\_OSD120} \equiv \text{Light\_Grown}$$
$$\text{Study\_OSD658} \equiv \text{Dark\_Grown}$$

Because `Study ID` and `Light Treatment` are 100% collinear, **no statistical software (including DESeq2) can estimate a Study Batch Effect and a Light Effect simultaneously from pooled raw counts**. 

If raw count matrices of OSD-120 and OSD-658 are pooled into a single DESeq2 design matrix, any difference attributed to "Light" could equally be an artifact of sequencing run, RNA extraction kit, hardware lot, or temperature drift.

> **CRITICAL SCIENTIFIC VERDICT**: Pooling raw counts across OSD-120 and OSD-658 into a single DESeq2 matrix (Option A) is **STATISTICALLY UNIDENTIFIABLE and SCIENTIFICALLY INVALID**.

---

## 5. Replicate and Power Assessment

- **Sample Size**: OSD-120 has $N=3$ FLT / $N=3$ GC ($N=6$ total); OSD-658 has $N=3$ FLT / $N=3$ GC ($N=6$ total). Total pooled $N=12$.
- **Effective Degrees of Freedom**: In a 2-study pooled design, $N=12$ provides only 8 residual degrees of freedom after fitting main effects.
- **Statistical Power**: $N=3$ per cell is insufficient for fitting complex 3-way interactions (`Spaceflight : Light : Study`).
- **Meta-Analysis vs Pooling**: Summary-statistic meta-analysis (inverse-variance weighting of independent DESeq2 $\text{log}_2\text{FC}$ and $\text{lfcSE}$) preserves the strict $N=3$ internal randomization of each experiment without introducing unidentifiable cross-study baseline parameters.

---

## 6. Candidate-Gene Validation Design

| Gene | Cross-Dataset Validation Status | Recommended Meta-Analytic Treatment |
|---|---|---|
| **`AT2G04170` (Unassigned)** | **VALID** | Pool effect sizes via inverse-variance meta-analysis. Significantly induced in both OSD-120 ($q = 0.0047$) and OSD-658 ($q = 0.0068$). |
| **`AT4G04720` (`CPK21`)** | **VALID WITH COVARIATE CONTROL** | Evaluate via random-effects meta-analysis. Positive trend in both Col-0 datasets. |
| **`AT3G46640` (`LUX`)** | **VALID WITH COVARIATE CONTROL** | Evaluate via random-effects meta-analysis. Positive trend across light and dark flight roots. |
| **`AT5G57630` (`CIPK21`)** | **VALID WITH COVARIATE CONTROL** | Evaluate via random-effects meta-analysis. Positive trend in both datasets. |
| **`AT1G01010` (`ANAC001`)** | **NOT VALID FOR POOLED CLAIM** | Directionally inconsistent (positive in OSD-120 light, negative in OSD-658 dark). Flagged as condition-dependent. |
| **`AT3G17609` (`HYH`)** | **NOT VALID FOR POOLED RAW CLAIM** | Heavy repression specific to light-grown OSD-120. Must be modeled as light-conditioned, not general spaceflight response. |

---

## 7. Recommended Strategy Ranking

1. **Rank 1: Option B/C — Dataset-Specific DESeq2 Followed by Summary-Statistic Meta-Analysis** [`APPROVED / RECOMMENDED`]
   - Perform DESeq2 with apeglm shrinkage independently on OSD-120 ($N=3$ vs $N=3$) and OSD-658 ($N=3$ vs $N=3$).
   - Integrate shrunk $\text{log}_2\text{FC}$ and $\text{lfcSE}$ using inverse-variance fixed/random-effects meta-analysis (e.g., metafor/meta R packages).
   - *Why*: Mathematically sound, identifiable, preserves internal experimental control, quantifies heterogeneity ($\text{I}^2$).
2. **Rank 2: Option F — Retain Datasets Independently with Qualitative Synthesis** [`SAFE ALTERNATIVE`]
   - Maintain independent DESeq2 outputs and report cross-dataset findings as qualitative biological convergence.
3. **Rank 3: Option D/E — Pathway Enrichment Meta-Analysis** [`CONDITIONALLY ACCEPTABLE`]
   - Compare GSEA / GO term enrichment scores across datasets rather than gene-level fold changes.
4. **Rank 4: Option A — Pooled Raw-Count DESeq2 Model** [`REJECTED / UNIDENTIFIABLE`]
   - Pooling raw count matrices into a single DESeq2 call. *Rejected due to perfect collinearity of Study and Light condition.*

---

## 8. Exact Pre-Registration Specification

If meta-analysis implementation is authorized in a future turn, it MUST follow this pre-registered specification:

### Specification Outline
- **Input Datasets**: 
  - OSD-120 raw count matrix ($N=3$ FLT, $N=3$ GC, Col-0 light roots).
  - OSD-658 raw count matrix ($N=3$ FLT, $N=3$ GC, Col-0 dark roots).
- **Primary Pipeline per Dataset**: 
  - DESeq2 (v1.40+) fit independently per study using design formula `~ Spaceflight`.
  - Effect size shrinkage applied via `lfcShrink(type="apeglm")`.
- **Meta-Analytic Integration**:
  - For each gene present in both datasets, extract $\hat{\beta}_1, \text{SE}_1$ (OSD-120) and $\hat{\beta}_2, \text{SE}_2$ (OSD-658).
  - Weighted meta-analytic mean effect:
    $$w_i = \frac{1}{\text{SE}_i^2}, \quad \hat{\beta}_{\text{meta}} = \frac{\sum w_i \hat{\beta}_i}{\sum w_i}, \quad \text{SE}_{\text{meta}} = \frac{1}{\sqrt{\sum w_i}}$$
  - Heterogeneity test ($Q$ statistic and $\text{I}^2$) calculated per gene.
- **Multiple Testing Correction**: Benjamini-Hochberg FDR applied to meta-analytic $p$-values.
- **Failure Criteria**: If $\text{I}^2 > 75\%$, report gene as "Heterogeneous / Study-Specific" rather than pooled spaceflight DE.

---

## 9. Go / No-Go Decision

### **`CONDITIONAL GO`**

#### Conditions for Authorization:
1. **NO RAW COUNT POOLING**: The proposed pooled raw-count DESeq2 model (Option A) is **STRICTLY REJECTED**.
2. **APPROVED PATHWAY**: Meta-analysis MUST be conducted via **independent dataset DESeq2 processing followed by inverse-variance summary-statistic integration (Option B/C)**.
3. **READ-ONLY PRESERVATION**: No code or pipeline outputs are modified during this audit phase.

---

META-ANALYSIS DESIGN AUDIT COMPLETE — IMPLEMENTATION NOT YET AUTHORIZED.
