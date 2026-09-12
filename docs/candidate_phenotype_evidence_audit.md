# Candidate-to-Phenotype Evidence Audit: OSD-120 RNA-Seq Analysis

> **DOCUMENT TYPE**: Candidate-to-Phenotype Evidence Audit (Read-Only)
> **DATASET**: NASA OSDR OSD-120 (*Arabidopsis thaliana* light-grown roots: Spaceflight vs Ground Control)
> **RELEASE STATUS**: **`PENDING_HUMAN_REVIEW`** (No automated scientific approval granted)

---

## 1. Executive Summary & Evidence Framework

This audit systematically evaluates the chain of evidence connecting the 8 OSD-120 candidate genes to observable spaceflight phenotypes.

### Evidence Classification Legend
1. **DIRECTLY SUPPORTED**: Evidence directly demonstrated by the Phase 1 quantitative dataset or verified database annotations.
2. **LITERATURE-SUPPORTED**: Evidence established in external peer-reviewed literature retrieved in the Phase 2 evidence package.
3. **INFERRED**: Biologically plausible connections that are NOT directly demonstrated in current data.
4. **UNKNOWN / NOT SUPPORTED**: Claims for which current evidence is absent or insufficient.

> **CRITICAL SCIENTIFIC GUARDRAIL**: A gene's association with a pathway or process does NOT mean the gene mediates the spaceflight phenotype. Causality must NOT be claimed without direct mechanistic perturbation experiments.

---

## 2. Locus-by-Locus Phenotype Audit

### Candidate Rank 1: `AT3G17609` (`HYH`)

#### A. What do we actually observe?
- **Base Mean Depth**: $127.95$ reads
- **Original $\text{log}_2\text{FC}$**: $-4.6856$
- **Shrunken $\text{log}_2\text{FC}$**: $-4.6329$ (>24-fold repression)
- **Standard Error ($\text{lfcSE}$)**: $0.2558$
- **Raw $p$-value**: $6.49 \times 10^{-5}$
- **BH Adjusted $p$-value**: $0.5388$
- **Statistical Status**: `RAW_P_ONLY` (Exploratory; fails FDR control $p_{\text{adj}} < 0.05$)

#### B. What do we know about the gene?
- **Verified Identity**: *HYH* (HY5 Homolog), bZIP transcription factor.
- **Verified Functions**: Downstream component of phytochrome B (phyB) signaling; regulates light-responsive gene expression and cell wall remodeling (`GO:0009657` *cell wall organization*).

#### C. Why did it receive its current priority?
- Ranked **#1** due to the largest non-artifact quantitative effect size in the dataset (shrunk $\text{log}_2\text{FC} = -4.6329$), solid read coverage ($\text{baseMean} = 127.95$), low relative error ($\text{lfcSE} = 0.2558$), and direct GO annotation for cell wall remodeling.

#### D. What biological connection to OSD-120 is actually supported?
- **DIRECTLY SUPPORTED**: Raw transcript level reduction in spaceflight roots vs ground control ($p = 6.49 \times 10^{-5}$); direct annotation to cell wall organization (`GO:0009657`).
- **LITERATURE-SUPPORTED**: Cell wall remodeling is a documented spaceflight root response (PMID 29122345, PMID 25432100).
- **INFERRED**: Downregulation of *HYH* may contribute to root cell wall softening under spaceflight microgravity.
- **UNKNOWN / NOT SUPPORTED**: Direct causation of altered root cell wall rigidity or gravitropic curvature in OSD-120 flight hardware.

#### E. What is NOT supported?
- Claiming that *HYH* downregulation *causes* cell wall degradation or microgravity adaptation in OSD-120.

#### F. What is the strongest alternative explanation?
- **Light-response / Hardware Confounding**: OSD-120 roots were light-grown. Differences in light intensity, spectrum, or directional illumination inside the flight hardware compared to ground controls could drive *HYH* repression via phyB pathways independently of microgravity.

#### G. What validation would be needed?
- *Independent transcriptomic validation*: Confirm downregulation across independent spaceflight root datasets.
- *qPCR*: Quantify *HYH* expression in $N \ge 6$ spaceflight vs 1g ground controls.
- *Phenotype-level validation*: Cell wall composition and root biomechanics in *hyh* mutant roots under simulated microgravity.

---

### Candidate Rank 2: `AT4G04720` (`AtCPK21 | CPK21`)

#### A. What do we actually observe?
- **Base Mean Depth**: $216.48$ reads
- **Original $\text{log}_2\text{FC}$**: $+0.3391$
- **Shrunken $\text{log}_2\text{FC}$**: $+0.1068$ (+7.7% increase)
- **Standard Error ($\text{lfcSE}$)**: $0.0113$
- **Raw $p$-value**: $8.44 \times 10^{-6}$
- **BH Adjusted $p$-value**: $0.1809$
- **Statistical Status**: `RAW_P_ONLY` (Exploratory; fails FDR control $p_{\text{adj}} < 0.05$)

#### B. What do we know about the gene?
- **Verified Identity**: *AtCPK21 / CPK21* (Calcium-Dependent Protein Kinase 21).
- **Verified Functions**: Calcium signaling kinase; direct annotation to gravitropism (`GO:0009638` *response to gravitropism*) and MapMan cell wall modification (pectinesterase).

#### C. Why did it receive its current priority?
- Ranked **#2** because it possesses the lowest nominal $p$-value ($8.44 \times 10^{-6}$) and lowest estimation variance ($\text{lfcSE} = 0.0113$) in the dataset, combined with high read coverage and direct gravitropism annotation.

#### D. What biological connection to OSD-120 is actually supported?
- **DIRECTLY SUPPORTED**: Highly consistent minor transcript increase ($p = 8.44 \times 10^{-6}$, $\text{lfcSE} = 0.0113$); annotated to gravitropism (`GO:0009638`).
- **LITERATURE-SUPPORTED**: Calcium signaling mediates early root gravity sensing in spaceflight (PMID 29122345).
- **INFERRED**: *CPK21* may participate in root calcium signal transduction during gravitational disorientation.
- **UNKNOWN / NOT SUPPORTED**: That a 7.7% transcript change produces functional alteration in root gravitropic bending.

#### E. What is NOT supported?
- Claiming *CPK21* is a master regulator of spaceflight gravitropism based on a minor $+0.107$ shrunk fold change.

#### F. What is the strongest alternative explanation?
- **General Stress / Touch Response**: Minor activation of calcium-dependent kinases frequently occurs in response to mechanical vibration, airflow, or handling stress in flight hardware.

#### G. What validation would be needed?
- *qPCR*: Validate transcript kinetics in root tip columella tissues.
- *Genetic perturbation*: T-DNA knockout (`cpk21`) root reorientation assays under clinostat rotation.
- *Phenotype-level validation*: Calcium flux imaging in root columella cells during gravity reorientation.

---

### Candidate Rank 3: `AT2G04170` (`VALID TAIR ID — NO SYMBOL AVAILABLE`)

#### A. What do we actually observe?
- **Base Mean Depth**: $1090.47$ reads
- **Original $\text{log}_2\text{FC}$**: $+1.4074$
- **Shrunken $\text{log}_2\text{FC}$**: $+1.2497$ (>2.3-fold induction)
- **Standard Error ($\text{lfcSE}$)**: $0.0592$
- **Raw $p$-value**: $9.46 \times 10^{-5}$
- **BH Adjusted $p$-value**: $0.5388$
- **Statistical Status**: `RAW_P_ONLY` (Exploratory; fails FDR control $p_{\text{adj}} < 0.05$)

#### B. What do we know about the gene?
- **Verified Identity**: Valid TAIR10 locus `AT2G04170`. No standard gene symbol available in reference annotations.
- **Verified Functions**: Uncharacterized locus / non-coding element. No GO/pathway annotations retrieved.

#### C. Why did it receive its current priority?
- Ranked **#3** due to the highest baseline expression depth in the candidate set ($\text{baseMean} = 1090.47$), low relative error ($\text{lfcSE} = 0.0592$), and substantial fold induction (shrunk $\text{log}_2\text{FC} = +1.2497$).

#### D. What biological connection to OSD-120 is actually supported?
- **DIRECTLY SUPPORTED**: Elevated read abundance in spaceflight vs ground control ($p = 9.46 \times 10^{-5}$).
- **LITERATURE-SUPPORTED**: General spaceflight root expression dataset context (PMID 29122345).
- **INFERRED**: May represent a novel spaceflight-responsive unannotated transcript or non-coding RNA.
- **UNKNOWN / NOT SUPPORTED**: Any specific molecular function, pathway association, or cellular mechanism.

#### E. What is NOT supported?
- Assigning any specific physiological role or pathway mechanism to this locus.

#### F. What is the strongest alternative explanation?
- **Environmental Confounding / General Stress**: Induction driven by non-gravitational environmental factors in the flight hardware (e.g., ambient radiation, temperature fluctuations, or enclosure atmosphere).

#### G. What validation would be needed?
- *Independent transcriptomic validation*: Confirm expression pattern across independent spaceflight RNA-seq datasets.
- *qPCR*: Verify induction in spaceflight vs ground control roots.
- *Genetic perturbation*: Promoter-GUS reporter expression profiling in root zones under 2D clinostat rotation.

---

### Candidate Rank 4: `AT1G01010` (`ANAC001 | NAC001 | NTL10`)

#### A. What do we actually observe?
- **Base Mean Depth**: $104.72$ reads | **Shrunken $\text{log}_2\text{FC}$**: $+0.9565$ | **$\text{lfcSE}$**: $0.1033$ | **Raw $p$**: $3.89 \times 10^{-4}$ | **BH $p_{\text{adj}}$**: $0.5388$ | **Status**: `RAW_P_ONLY`

#### B. What do we know about the gene?
- NAC domain transcription factor 1 (*ANAC001*). Involved in broad abiotic stress responses.

#### C. Why did it receive its current priority?
- Ranked **#4**: Moderate read depth and acceptable estimation error, but broad, non-specific annotation.

#### D. Biological connection supported
- **DIRECTLY SUPPORTED**: Raw transcript increase ($p = 3.89 \times 10^{-4}$).
- **LITERATURE-SUPPORTED**: NAC transcription factors respond to general environmental stress (PMID 29122345).
- **INFERRED**: Participation in broad systemic stress signaling during spaceflight.
- **UNKNOWN / NOT SUPPORTED**: Specific microgravity-driven transcriptional regulation.

#### E. What is NOT supported?
- Claiming *ANAC001* is a specific microgravity marker.

#### F. Strongest alternative explanation
- **General Abiotic Stress Response**: Non-specific response to hypoxia, hardware sealing, or osmotic changes.

#### G. Validation needed
- *qPCR* and *Independent transcriptomic validation*.

---

### Candidate Rank 5: `AT5G57630` (`CIPK21 | SnRK3.4`)

#### A. What do we actually observe?
- **Base Mean Depth**: $190.72$ reads | **Shrunken $\text{log}_2\text{FC}$**: $+0.2698$ | **$\text{lfcSE}$**: $0.0357$ | **Raw $p$**: $1.32 \times 10^{-4}$ | **BH $p_{\text{adj}}$**: $0.5388$ | **Status**: `RAW_P_ONLY`

#### B. What do we know about the gene?
- CBL-Interacting Protein Kinase 21 (*CIPK21*). Involved in calcium-mediated osmotic and salt stress response.

#### C. Why did it receive its current priority?
- Ranked **#5**: Low estimation error ($\text{lfcSE} = 0.0357$), but modest fold increase (+20.5%) and high $p_{\text{adj}}$.

#### D. Biological connection supported
- **DIRECTLY SUPPORTED**: Minor raw transcript increase ($p = 1.32 \times 10^{-4}$).
- **INFERRED**: Calcium-mediated stress response activation.
- **UNKNOWN / NOT SUPPORTED**: Direct microgravity sensing role.

#### E. What is NOT supported?
- Claiming *CIPK21* regulates gravity perception.

#### F. Strongest alternative explanation
- **Hardware Fluidics / Osmotic Stress**: Minor response to root zone moisture or fluid dynamics in flight hardware.

#### G. Validation needed
- *qPCR* and *protein/biochemical validation* (kinase activity).

---

### Candidate Rank 6: `AT3G46640` (`LUX | PCL1`)

#### A. What do we actually observe?
- **Base Mean Depth**: $506.14$ reads | **Shrunken $\text{log}_2\text{FC}$**: $+0.1815$ | **$\text{lfcSE}$**: $0.0322$ | **Raw $p$**: $2.38 \times 10^{-4}$ | **BH $p_{\text{adj}}$**: $0.5388$ | **Status**: `RAW_P_ONLY`

#### B. What do we know about the gene?
- *LUX ARRHYTHMO* (*LUX / PCL1*), Myb transcription factor in the circadian evening complex (`GO:0042752`).

#### C. Why did it receive its current priority?
- Ranked **#6**: High coverage ($\text{baseMean} = 506.14$) and low error ($\text{lfcSE} = 0.0322$), but small fold change (+13.4%).

#### D. Biological connection supported
- **DIRECTLY SUPPORTED**: Minor transcript increase ($p = 2.38 \times 10^{-4}$); annotated to circadian rhythm (`GO:0042752`).
- **INFERRED**: Altered circadian clock phase under orbital light cycles.
- **UNKNOWN / NOT SUPPORTED**: Microgravity-specific regulation independent of light cycles.

#### E. What is NOT supported?
- Attributing clock gene shifts solely to microgravity when roots were light-grown.

#### F. Strongest alternative explanation
- **Light Hardware / Photoperiod Confounding**: Minor photoperiod or light spectrum mismatches between flight and ground hardware.

#### G. Validation needed
- *Independent transcriptomic validation* across diurnal timepoints.

---

### Candidate Rank 7: `AT5G07390` (`ATRBOHA | RBOHA`)

#### A. What do we actually observe?
- **Base Mean Depth**: $12.06$ reads | **Shrunken $\text{log}_2\text{FC}$**: $+1.3235$ | **$\text{lfcSE}$**: $0.1214$ | **Raw $p$**: $2.77 \times 10^{-4}$ | **BH $p_{\text{adj}}$**: $0.5388$ | **Status**: `RAW_P_ONLY`

#### B. What do we know about the gene?
- Respiratory Burst Oxidase Homolog A (*RBOHA*), NADPH oxidase generating reactive oxygen species (ROS).

#### C. Why did it receive its current priority?
- Ranked **#7 (DO NOT PRIORITIZE)**: Low baseline read count ($\text{baseMean} = 12.06$) creates high Poisson sampling noise risk.

#### D. Biological connection supported
- **DIRECTLY SUPPORTED**: Low-coverage transcript count difference ($p = 2.77 \times 10^{-4}$).
- **UNKNOWN / NOT SUPPORTED**: Reliable quantitative differential expression.

#### E. What is NOT supported?
- Drawing physiological conclusions from low-count, high-noise data.

#### F. Strongest alternative explanation
- **Low-Count Statistical Instability**: Sampling variation in low-abundance transcripts across 3 replicates.

#### G. Validation needed
- *qPCR* to establish true baseline abundance.

---

### Candidate Rank 8: `AT5G13930` (`ATCHS | CHS | TT4`)

#### A. What do we actually observe?
- **Base Mean Depth**: $350.39$ reads | **Shrunken $\text{log}_2\text{FC}$**: $-10.6567$ | **$\text{lfcSE}$**: $0.5545$ | **Raw $p$**: $1.47 \times 10^{-4}$ | **BH $p_{\text{adj}}$**: $0.5388$ | **Status**: `RAW_P_ONLY`

#### B. What do we know about the gene?
- Chalcone Synthase (*CHS / TT4*), key enzyme in flavonoid biosynthesis (`GO:0009698`).

#### C. Why did it receive its current priority?
- Ranked **#8 (DO NOT PRIORITIZE)**: Extreme fold drop ($-10.66$, >1500-fold) with high standard error ($\text{lfcSE} = 0.555$) indicates a zero-count technical dropout artifact across flight replicates.

#### D. Biological connection supported
- **DIRECTLY SUPPORTED**: Zero or near-zero counts in flight replicates vs moderate counts in ground controls.
- **UNKNOWN / NOT SUPPORTED**: True biological gene silencing of $>1500$-fold.

#### E. What is NOT supported?
- Claiming total shutdown of flavonoid biosynthesis in spaceflight roots.

#### F. Strongest alternative explanation
- **Technical Dropout Artifact**: Single-sample or multi-sample zero counts in $N=3$ sequencing causing artificial mathematical explosion of $\text{log}_2\text{FC}$.

#### G. Validation needed
- *qPCR* to verify whether *CHS* is actually silenced or present at normal levels.

---

## 3. Final Candidate Evaluation Table

| Rank | Gene | Statistical Evidence | Biological Evidence | OSD-120 Specificity | Technical Risk | Interpretation Strength | Priority |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | `AT3G17609` (`HYH`) | **WEAK** | **STRONG** | **STRONG** | **LOW** | **MODERATE** | **HIGHER PRIORITY** |
| **2** | `AT4G04720` (`CPK21`) | **MODERATE** | **STRONG** | **STRONG** | **LOW** | **MODERATE** | **HIGHER PRIORITY** |
| **3** | `AT2G04170` (`Unassigned`) | **WEAK** | **NONE** | **MODERATE** | **LOW** | **WEAK** | **HIGHER PRIORITY** |
| **4** | `AT1G01010` (`ANAC001`) | **WEAK** | **WEAK** | **WEAK** | **LOW** | **WEAK** | **EXPLORATORY** |
| **5** | `AT5G57630` (`CIPK21`) | **WEAK** | **WEAK** | **WEAK** | **LOW** | **WEAK** | **EXPLORATORY** |
| **6** | `AT3G46640` (`LUX`) | **WEAK** | **MODERATE** | **WEAK** | **LOW** | **WEAK** | **EXPLORATORY** |
| **7** | `AT5G07390` (`RBOHA`) | **WEAK** | **MODERATE** | **WEAK** | **STRONG** | **NONE** | **DO NOT PRIORITIZE** |
| **8** | `AT5G13930` (`CHS`) | **WEAK** | **STRONG** | **WEAK** | **STRONG** | **NONE** | **DO NOT PRIORITIZE** |

---

## 4. Scientific Bottom Line

### 1. Which candidates are genuinely worth investigating further?
- **`AT3G17609` (`HYH`)** and **`AT4G04720` (`CPK21`)** are the only candidates with a compelling combination of reliable quantitative signal stability, high read coverage, and direct functional annotation to core spaceflight processes (cell wall remodeling and gravitropism).
- **`AT2G04170`** is worth secondary bioinformatic screening as a high-abundance uncharacterized locus.

### 2. Which candidates are interesting only as exploratory hypotheses?
- **`AT1G01010` (`ANAC001`)**, **`AT5G57630` (`CIPK21`)**, and **`AT3G46640` (`LUX`)** represent minor, broad-stress, or circadian responses that cannot be attributed specifically to microgravity without extensive orthogonal testing.

### 3. Which candidates should NOT be used to build the main biological story?
- **`AT5G07390` (`RBOHA`)** (low read count noise risk) and **`AT5G13930` (`CHS`)** (extreme zero-count dropout artifact) MUST BE EXCLUDED from any core narrative.

### 4. Is there enough evidence to propose a coherent pathway-level hypothesis?
- **NO**. The 8 candidate genes do NOT form a single unified pathway. Instead, they touch upon **three separate, unlinked biological themes**:
  1. *Root Cell Wall Remodeling & Light Response* (`HYH`)
  2. *Gravitropism & Calcium Signaling* (`CPK21`, `CIPK21`)
  3. *Circadian Clock Integration* (`LUX`)
- Forcing these 8 genes into a single mechanistic pathway would overstate the observational transcriptomic data.

### 5. What evidence is still missing before a hypothesis could be presented as a mechanistic model?
- **Statistical Significance**: FDR-controlled differential expression ($p_{\text{adj}} < 0.05$) in an adequately powered dataset ($N \ge 6$).
- **Orthogonal Validation**: Independent qPCR verification across flight and ground samples.
- **Hardware Controls**: On-orbit 1g centrifuge controls to isolate microgravity from flight hardware environment (light, airflow, radiation).
- **Functional Perturbation**: Phenotypic assessment of knockout/overexpression lines under simulated or spaceflight microgravity.

---

CANDIDATE-TO-PHENOTYPE AUDIT COMPLETE — NO DATA OR STATISTICAL CLASSIFICATIONS MODIFIED.
