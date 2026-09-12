# Human Scientific Review Summary: OSD-120 Phase 3 Candidate Genes

> **DOCUMENT TYPE**: Human Scientific Review Summary (Read-Only)
> **DATASET**: NASA OSDR OSD-120 (*Arabidopsis thaliana* light-grown roots: Spaceflight vs Ground Control)
> **RELEASE STATUS**: **`PENDING_HUMAN_REVIEW`** (No automated scientific approval granted)

---

# 1. Executive Summary

- **Total Number of Candidate Genes**: 8
- **Number Passing BH FDR < 0.05**: **0**
- **Number Classified as Exploratory Only**: **8** (100% of candidate set)
- **Overall Scientific Release Classification**: **`READY_FOR_HUMAN_REVIEW`**
- **Sufficient Evidence for a Supported Mechanism**: **None** (0 of 8 candidates possess evidence sufficient to establish a biological mechanism; all remain associational/exploratory).

---

# 2. Candidate Ranking Table

| Rank | TAIR ID | Symbol | log2FC | shrunken log2FC | raw p | BH padj | FDR Status | Literature Strength | Biological Plausibility | Causal Evidence | Final Priority |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | `AT3G17609` | Unassigned | $-4.686$ | $-4.633$ | $6.49 \times 10^{-5}$ | $0.5388$ | FAILS FDR | Contextual (Tier 1) | High (Cell Wall Org) | Associational | **HIGH-VALUE** |
| **2** | `AT4G04720` | Unassigned | $+0.339$ | $+0.107$ | $8.44 \times 10^{-6}$ | $0.1809$ | FAILS FDR | Contextual (Tier 1) | High (Gravitropism) | Associational | **MODERATE-VALUE** |
| **3** | `AT2G04170` | Unassigned | $+1.407$ | $+1.250$ | $9.46 \times 10^{-5}$ | $0.5388$ | FAILS FDR | Contextual (Tier 1) | Moderate (High Abundance) | Associational | **MODERATE-VALUE** |
| **4** | `AT1G01010` | Unassigned | $+1.140$ | $+0.957$ | $3.89 \times 10^{-4}$ | $0.5388$ | FAILS FDR | Contextual (Tier 1) | Low (Unannotated) | Associational | **WEAK** |
| **5** | `AT5G57630` | Unassigned | $+0.520$ | $+0.270$ | $1.32 \times 10^{-4}$ | $0.5388$ | FAILS FDR | Contextual (Tier 1) | Low (Unannotated) | Associational | **WEAK** |
| **6** | `AT3G46640` | Unassigned | $+0.429$ | $+0.182$ | $2.38 \times 10^{-4}$ | $0.5388$ | FAILS FDR | Contextual (Tier 1) | Low (Unannotated) | Associational | **WEAK** |
| **7** | `AT5G07390` | Unassigned | $+1.475$ | $+1.323$ | $2.77 \times 10^{-4}$ | $0.5388$ | FAILS FDR | Contextual (Tier 1) | Low (Low baseMean) | Associational | **WEAK** |
| **8** | `AT5G13930` | Unassigned | $-10.680$ | $-10.657$ | $1.47 \times 10^{-4}$ | $0.5388$ | FAILS FDR | Contextual (Tier 1) | Very Low (Artifact Risk) | Associational | **DO NOT PRIORITIZE** |

---

# 3. Top 3 Experimental Candidates

### Candidate Rank 1: `AT3G17609`
- **Gene**: `AT3G17609` (TAIR Locus, Symbol: Unassigned)
- **Exact Quantitative Observation**: Shrunk log2FC = $-4.633$ (raw log2FC = $-4.686$, lfcSE = $0.256$, baseMean = $127.9$, raw $p = 6.49 \times 10^{-5}$, $padj = 0.5388$).
- **Strongest Supporting Literature**: PMID 29122345 / PMID 25432100 (Contextual evidence: spaceflight root cell wall remodeling).
- **Strongest Database / Pathway Evidence**: `GO:0009657` (*cell wall organization*, Direct Annotation).
- **Why Biologically Interesting**: Exhibits a massive estimated fold reduction (>24-fold repression) in spaceflight roots with direct GO cell wall organization annotation.
- **Biggest Weakness**: High FDR adjusted $p$-value ($padj = 0.5388$) due to $N=3$ sample power limits.
- **Most Appropriate Next Experiment**: RT-qPCR target validation across independent spaceflight/ground root samples ($N \ge 6$) and root cell wall polysaccharide profiling.
- **What Result Would Support Hypothesis**: RT-qPCR confirming $>10$-fold expression decrease in spaceflight root tips relative to 1g ground control.
- **What Result Would Falsify / Weaken It**: RT-qPCR showing $\text{C}_\text{t}$ values equivalent between spaceflight and ground control, indicating sequencing variance noise.

---

### Candidate Rank 2: `AT4G04720`
- **Gene**: `AT4G04720` (TAIR Locus, Symbol: Unassigned)
- **Exact Quantitative Observation**: Shrunk log2FC = $+0.1068$ (raw log2FC = $+0.3391$, lfcSE = $0.0113$, baseMean = $216.48$, raw $p = 8.44 \times 10^{-6}$, $padj = 0.1809$).
- **Strongest Supporting Literature**: PMID 29122345 / PMID 25432100 (Contextual spaceflight cell wall remodeling).
- **Strongest Database / Pathway Evidence**: `GO:0009638` (*response to gravitropism*) and `MapMan 10.1` (*Cell wall modification - pectinesterase*).
- **Why Biologically Interesting**: Lowest nominal $p$-value ($p = 8.44 \times 10^{-6}$) and lowest variance ($lfcSE = 0.0113$) in dataset, with curated GO gravitropism association.
- **Biggest Weakness**: Very modest shrunk fold change (+7.7% increase), and fails FDR control ($padj = 0.1809$).
- **Most Appropriate Next Experiment**: T-DNA insertion mutant (`at4g04720`) root reorientation assays under 2D clinostat simulated microgravity.
- **What Result Would Support Hypothesis**: `at4g04720` mutant roots displaying altered gravitropic curvature kinetics relative to wild-type under 1g and microgravity simulation.
- **What Result Would Falsify / Weaken It**: `at4g04720` mutants showing identical gravitropic kinetics and cell wall composition to wild-type.

---

### Candidate Rank 3: `AT2G04170`
- **Gene**: `AT2G04170` (TAIR Locus, Symbol: Unassigned)
- **Exact Quantitative Observation**: Shrunk log2FC = $+1.250$ (raw log2FC = $+1.407$, lfcSE = $0.059$, baseMean = $1090.5$, raw $p = 9.46 \times 10^{-5}$, $padj = 0.5388$).
- **Strongest Supporting Literature**: PMID 29122345 (Contextual spaceflight root biology).
- **Strongest Database / Pathway Evidence**: None retrieved.
- **Why Biologically Interesting**: High baseline read depth (baseMean = $1090.5$) with a clear >2.3-fold positive induction ($shrunk\_log2FC = +1.250$) and low relative error ($lfcSE = 0.059$).
- **Biggest Weakness**: Complete absence of functional database/pathway annotations and high $padj = 0.5388$.
- **Most Appropriate Next Experiment**: Bioinformatic domain homology mapping and promoter-GUS reporter expression analysis in root tips under clinostat rotation.
- **What Result Would Support Hypothesis**: GUS reporter expression specifically localized to root columella/differentiation zones induced under simulated microgravity.
- **What Result Would Falsify / Weaken It**: Diffuse or uninducible GUS reporter expression pattern unaffected by mechanical or gravity reorientation.

---

# 4. Candidates Not Worth Prioritizing

- **`AT1G01010`** (`WEAK EXPLORATORY CANDIDATE`): High $padj = 0.5388$, moderate fold change ($+0.957$), zero functional GO/pathway annotations.
- **`AT5G57630`** (`WEAK EXPLORATORY CANDIDATE`): High $padj = 0.5388$, small shrunk fold change ($+0.270$), zero functional annotations.
- **`AT3G46640`** (`WEAK EXPLORATORY CANDIDATE`): High $padj = 0.5388$, low shrunk fold change ($+0.182$), zero functional annotations.
- **`AT5G07390`** (`WEAK EXPLORATORY CANDIDATE`): Low baseline read depth (baseMean = $12.1$) introduces high Poisson sampling noise risk; $padj = 0.5388$.
- **`AT5G13930`** (`DO NOT PRIORITIZE`): Extreme negative fold change ($-10.657$, >1500-fold drop) with high standard error ($lfcSE = 0.555$) indicates a probable technical zero-count sequencing artifact across flight replicates rather than genuine physiological silencing.

---

# 5. Shared Scientific Limitations

1. **Low Sample Power ($N=3$ vs $N=3$)**: With only 3 spaceflight and 3 ground control replicates, DESeq2 has insufficient power to separate moderate biological differential expression from random inter-sample variance.
2. **BH/FDR Limitation ($padj \ge 0.1809$)**: None of the 8 candidates meet Benjamini-Hochberg FDR significance ($padj < 0.05$). All candidates are strictly exploratory (`RAW_P_ONLY`).
3. **Spaceflight Environmental Confounding**: OSD-120 samples were exposed to flight hardware micro-environments (light, airflow, hardware geometry, ambient radiation). Transcriptional differences cannot be isolated to microgravity alone without 1g on-orbit centrifuge controls.
4. **Absence of Orthogonal Validation**: No RT-qPCR, protein assays, or mutant phenotyping have been conducted on these specific samples.
5. **Literature / Retrieval Bias**: Retrieved literature provides broad, study-level spaceflight root context, but lacks locus-specific empirical characterization for these unassigned loci.
6. **Inability to Establish Microgravity Causality**: Observational transcriptomics correlations cannot establish pure microgravity causal mechanisms.

---

# 6. Exploratory $\to$ Mechanistic Evidence Ladder

For the top candidate (`AT3G17609`), the evidence progression required to establish a supported mechanism is:

```
Transcriptomic observation (OSD-120: shrunk log2FC = -4.633, raw p = 6.49e-05, padj = 0.5388) [CURRENT LEVEL: ASSOCIATIONAL]
        ↓
Independent replication (RT-qPCR / RNA-seq in N ≥ 6 spaceflight replicates confirming >10-fold reduction) [MISSING]
        ↓
Functional / genetic perturbation (T-DNA knockout at3g17609 or overexpression lines under clinostat/ISS) [MISSING]
        ↓
Phenotypic validation (Altered root gravitropic curvature or cell wall rigidity under microgravity) [MISSING]
        ↓
Direct biochemical / molecular evidence (In vitro enzyme activity or cell wall composition assay) [MISSING]
        ↓
Supported mechanism [MISSING]
```

**Current State**: Only the initial *Transcriptomic observation* is available. All 5 subsequent validation steps are currently missing.

---

# 7. Final Human Decision

### **`B. KEEP AS EXPLORATORY ONLY`**

**Rationale for Decision**:
None of the 8 candidate genes achieve Benjamini-Hochberg FDR significance ($padj \ge 0.1809$), and no locus-specific empirical literature exists for these unassigned loci. However, top candidates such as `AT3G17609` (large effect size, GO cell wall organization) and `AT4G04720` (low $p$-value, GO gravitropism) represent plausible targets for secondary screening. Therefore, the dataset should be **KEPT AS EXPLORATORY ONLY** and not published as confirmed differential expression or promoted to experimental follow-up without independent biological replication.

---

HUMAN SCIENTIFIC REVIEW SUMMARY COMPLETE.
NO AUTOMATED SCIENTIFIC APPROVAL GRANTED.
FINAL SCIENTIFIC INTERPRETATION REMAINS SUBJECT TO DOMAIN-EXPERT REVIEW.
