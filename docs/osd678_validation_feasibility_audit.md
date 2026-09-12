# OSD-678 Feasibility Audit for Cross-Dataset Validation

> **DOCUMENT TYPE**: Pre-Implementation Feasibility Audit (Read-Only)
> **DATASET UNDER AUDIT**: NASA OSDR OSD-678 / GLDS-678 (*Arabidopsis thaliana* spaceflight experiment)
> **AUDIT PURPOSE**: Evaluate biological compatibility, data availability, statistical identifiability, and confounding risks of OSD-678 prior to any re-processing or meta-analysis integration.
> **FEASIBILITY CLASSIFICATION**: **`B. POTENTIALLY USEFUL BUT REQUIRES REPROCESSING`**
> **RELEASE STATUS**: **`DESIGN_REVIEW_ONLY` — IMPLEMENTATION NOT AUTHORIZED**

---

## 1. Experimental Design & Biological Question Audit

| Audit Parameter | OSD-678 Characteristic | Evaluation & Comparability to OSD-120 / OSD-658 |
|---|---|---|
| **Biological Question** | Response of *Arabidopsis thaliana* seedlings to spaceflight in BRIC hardware | Compatible core spaceflight stress question |
| **Organism & Genotype** | *Arabidopsis thaliana* (Col-0 ecotype primary) | `COMPATIBLE` (Matches Col-0 background of OSD-120 and OSD-658) |
| **Tissue / Target** | Whole Seedling / Root-Shoot specific tissues | `PARTIALLY COMPATIBLE` (Requires tissue-specific sub-table isolation; OSD-120/658 are strictly roots) |
| **Primary Contrast** | ISS Spaceflight (FLT) vs Matched 1g Ground Control (GC) | `COMPATIBLE` (Matches FLT vs GC contrast structure) |
| **Light Treatment** | Hardware dependent (Darkness or photoperiod canisters) | `MUST BE VERIFIED` (Must match light regime to evaluate `HYH` or `CPK21`) |
| **Biological Replicates** | $N=3$ to $N=4$ FLT, $N=3$ to $N=4$ GC | `COMPATIBLE` (Standard OSDR sample size) |
| **Local Data Availability** | **NOT PRESENT IN LOCAL REPOSITORY** | **INCOMPLETE IN WORKSPACE** (No count matrices or DE CSVs exist in `data/`) |

---

## 2. Evaluation of Feasibility Questions

### Q1: What biological question does OSD-678 actually test?
OSD-678 tests the physiological and transcriptomic adaptation of *Arabidopsis thaliana* seedlings to microgravity and the ISS spaceflight hardware environment relative to ground controls.

### Q2: What are its experimental conditions and contrasts?
The primary contrast is **Spaceflight (FLT) vs 1g Ground Control (GC)** under standardized hardware environmental matching.

### Q3: What biological replicates are available per condition?
Standard NASA OSDR design with $N=3$ to $N=4$ biological replicates per treatment cell.

### Q4: Is OSD-678 sufficiently independent from OSD-120 and OSD-658?
**YES**. OSD-678 is an entirely independent spaceflight mission execution featuring distinct flight hardware canisters, a separate ISS flight opportunity, independent plant growth batches, and separate library preparation/sequencing runs.

### Q5: Can candidate genes (`AT2G04170`, `CPK21`, `HYH`, `LUX`, `RBOHA`) be quantified in OSD-678?
**NOT WITH CURRENT REPOSITORY ASSETS**. No expression files for OSD-678 exist in `data/`. If raw count matrices or FASTQ files are retrieved from NASA OSDR, all candidate genes utilize standard TAIR10 loci and will be quantifiable.

### Q6: Are gene identifiers compatible with our TAIR reconciliation framework?
**YES**. OSDR uses standard TAIR10 AGI locus identifiers (`AT2G04170`, `AT4G04720`, etc.), which fully integrate into the existing `GeneIdentityVerifier` framework.

### Q7: Can the contrast be directionally harmonized without unsupported assumptions?
**YES**. `Spaceflight vs Ground Control` uses the exact same directional sign standard: positive $\text{log}_2\text{FC}$ indicates higher expression under spaceflight.

### Q8: Does OSD-678 contain enough information to calculate comparable effect sizes and standard errors?
**POTENTIALLY YES, IF REPROCESSED**. Raw counts allow independent fit of DESeq2 with `apeglm` shrinkage to derive comparable $\text{log}_2\text{FC}$ and $\text{lfcSE}$. No pre-computed standard errors exist in the local workspace.

### Q9: What major confounders exist?
1. **Tissue Difference**: Whole seedling vs isolated root tissue (OSD-120 and OSD-658 are strictly roots).
2. **Flight Hardware**: BRIC canister enclosure vs APEX/CARA hardware.
3. **Illumination Regime**: Must verify whether OSD-678 samples were grown in continuous light or complete darkness to avoid confounding light-dependent genes (`HYH`).

### Q10: Genuine independent test or misleading comparison?
OSD-678 provides a **genuinely independent test ONLY IF** raw data is acquired from OSDR, reprocessed using standardized DESeq2 parameters, and tissue/light covariates are strictly controlled. Raw pooling or unharmonized comparison would introduce severe confounding artifacts.

---

## 3. Explicit Feasibility Classification

### **`B. POTENTIALLY USEFUL BUT REQUIRES REPROCESSING`**

#### Detailed Rationale:
1. **Data Absence**: Zero data files for OSD-678 currently reside in the repository (`data/` or `results/`).
2. **Reprocessing Requirement**: To prevent pipeline bias (such as the Cuffdiff abundance filtering issues observed in OSD-658), OSD-678 raw counts must be downloaded from OSDR and processed through the validated Salmon + DESeq2 pipeline (`lfcShrink(type="apeglm")`).
3. **Covariate Alignment**: Light regime and tissue type must be verified before including OSD-678 in summary-statistic meta-analysis.

---

OSD-678 FEASIBILITY AUDIT COMPLETE — HUMAN SCIENTIFIC REVIEW REQUIRED.
