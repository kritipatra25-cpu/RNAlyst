# OSD-678 Acquisition Specification & Reprocessing Plan

> **DOCUMENT TYPE**: Pre-Acquisition Specification & Reprocessing Protocol (Read-Only)
> **TARGET DATASET**: NASA OSDR OSD-678 / GLDS-678 (*Arabidopsis thaliana* spaceflight experiment)
> **METHODOLOGY**: Independent DESeq2 Processing (apeglm Shrinkage) $\to$ Candidate Verification $\to$ Summary-Statistic Integration
> **RELEASE STATUS**: **`DESIGN_REVIEW_ONLY` — DATA ACQUISITION PENDING**

---

## 1. Dataset Identity

- **Dataset Identifier**: NASA OSDR OSD-678 (GeneLab GLDS-678)
- **Organism**: *Arabidopsis thaliana* (Col-0 ecotype primary)
- **Experiment Title**: Biological Research in Canisters (BRIC-23) Spaceflight Root and Seedling Response
- **Target Tissues**: Whole Seedlings / Isolated Root Tissue
- **Primary Contrast**: Space Flight (FLT) vs 1g Ground Control (GC)
- **Feasibility Classification**: **`B. POTENTIALLY USEFUL BUT REQUIRES REPROCESSING`**

---

## 2. Required Files

Upon authorization to download OSD-678 assets, the following files MUST be acquired:
1. `raw_counts_matrix.csv` or `quant.sf` files (Salmon transcript/gene quantifications).
2. `sample_table.csv` / `sample_metadata.json` (Explicit sample annotations containing sample ID, factor values, hardware batch, run type, and replicate identifiers).
3. `fastq_checksums.txt` (NASA OSDR official SHA-256 / MD5 checksum manifest).

---

## 3. Required Metadata

Every acquired sample record MUST contain:
- **Organism / Ecotype**: *Arabidopsis thaliana* (Col-0 background).
- **Tissue Specification**: Explicit demarcation of Root vs Shoot vs Whole Seedling.
- **Illumination Regime**: Explicit verification of Light Condition (Continuous Light vs Complete Darkness vs Photoperiod).
- **Hardware Module**: BRIC canister hardware version and atmospheric telemetry.
- **Flight Condition**: Spaceflight (FLT) vs Matched 1g Ground Control (GC).
- **Replicate Type**: Explicit flag identifying **BIOLOGICAL REPLICATES** vs technical/sequencing replicates.

---

## 4. Required Experimental Contrasts

- **Primary Contrast Formula**: `~ Spaceflight` (or `~ Hardware_Batch + Spaceflight` if multi-batch).
- **Reference Level**: `Ground Control` (GC = Baseline level 0).
- **Treatment Level**: `Spaceflight` (FLT = Comparison level 1).
- **Direction Standard**: Positive $\text{log}_2\text{FC}$ indicates higher expression in Spaceflight relative to Ground Control.

---

## 5. Required Biological Replicate Structure

- **Sample Size Requirement**: $N \ge 3$ independent biological replicates for FLT; $N \ge 3$ independent biological replicates for GC.
- **Technical Replicates**: If technical sequencing replicates exist for a sample, they MUST be collapsed (`collapseReplicates()` in DESeq2) prior to differential expression modeling.
- **Replicate Pooling**: Treating technical/sequencing replicates as independent biological replicates is **STRICTLY PROHIBITED**.

---

## 6. Required Reference Genome & Annotation

- **Genome Reference**: TAIR10 (*Arabidopsis thaliana* reference genome).
- **Annotation Identifier Standard**: AGI locus identifiers (e.g., `AT2G04170`, `AT4G04720`, `AT3G17609`).
- **Identifier Compatibility**: Must pass validation through the existing repository `GeneIdentityVerifier` framework.

---

## 7. Download / Source Provenance & SHA-256 Hashing Requirements

- **Official Source**: NASA Open Science Data Repository (OSDR) API (`https://osdr.nasa.gov/genelab/api/`).
- **Immutability Requirement**: Immediately upon download, compute SHA-256 hashes of all raw count matrices, sample tables, and metadata JSON files. Record hashes in `results/osd678_validation/osd678_provenance.json`.

---

## 8. Expected Directory Structure

All acquired and generated files for OSD-678 MUST adhere to the following directory layout:

```
data/
└── osd678/
    ├── .gitkeep
    ├── raw_counts_matrix.csv
    ├── sample_table.csv
    └── checksums.sha256

results/
└── osd678_validation/
    ├── osd678_feasibility.json
    ├── osd678_reprocessing_plan.json
    ├── osd678_provenance.json               [Future Acquisition]
    ├── differential_expression.csv          [Future Reprocessing]
    └── candidate_validation_summary.csv     [Future Reprocessing]
```

---

## 9. Preprocessing & Reprocessing Requirements

The approved workflow for OSD-678 integration follows this strict sequential chain:

$$\text{OSD-678 Raw Data} \xrightarrow{\text{Quality Control}} \text{DESeq2 (apeglm shrinkage)} \xrightarrow{\text{Extract } \text{log}_2\text{FC} + \text{lfcSE}} \text{Candidate Validation} \xrightarrow{\text{Summary-Statistic Meta-Analysis}}$$

1. **Dataset-Specific DESeq2**: Fit DESeq2 independently on OSD-678 ($N \ge 3$ vs $N \ge 3$) using `design = ~ Spaceflight`.
2. **LFC Shrinkage**: Apply `lfcShrink(type="apeglm")` to obtain unbiased effect size estimates ($\text{shrunken\_log2FC}$) and standard errors ($\text{lfcSE}$).
3. **Candidate Validation**: Check fold-change direction and statistical status for core candidates (`AT2G04170`, `CPK21`, `HYH`, `LUX`, `CIPK21`, `ANAC001`, `RBOHA`, `CHS`).
4. **Summary-Statistic Meta-Analysis Integration**: If valid and comparable, integrate shrunk $\text{log}_2\text{FC}$ and $\text{lfcSE}$ into the existing inverse-variance meta-analysis matrix.

---

## 10. Explicit Exclusion Criteria & Prohibitions

To preserve scientific rigor, the following practices are **STRICTLY FORBIDDEN**:

1. **NO RAW COUNT POOLING**: Pooling raw count matrices of OSD-678 with OSD-120 or OSD-658 into a single DESeq2 matrix is **STRICTLY PROHIBITED** (violates statistical identifiability due to study/light collinearity).
2. **NO INCOMPATIBLE PIPELINE MIXING**: Do NOT mix preprocessed statistics from incompatible pipelines (e.g. raw un-shrunk Cuffdiff LFC vs apeglm DESeq2 LFC) without SE harmonization.
3. **NO REPLICATE INFLATION**: Do NOT treat technical sequencing runs as independent biological replicates.
4. **NO IMPUTATION**: Missing gene quantifications or standard errors MUST be classified as `NOT_META_ANALYZABLE` rather than imputed.
5. **NO SILENT SIGN FLIPPING**: Contrast direction transformations MUST be mathematically recorded in provenance.
6. **NO PREMATURE META-ANALYSIS**: Meta-analysis MUST NOT be executed until OSD-678 quality control and independent DESeq2 processing are verified.
7. **NO MUTATION OF LOCKED OUTPUTS**: Existing Phase 1, Phase 2, Phase 3, and OSD-120/OSD-658 meta-analysis files remain 100% IMMUTABLE.

---

OSD-678 ACQUISITION SPECIFICATION COMPLETE — RAW DATA REQUIRED BEFORE REPROCESSING.
