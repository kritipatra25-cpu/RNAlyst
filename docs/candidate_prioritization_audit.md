# Read-Only Candidate Prioritization Audit: OSD-120 RNA-Seq Analysis

> **DOCUMENT TYPE**: Candidate Prioritization Audit (Read-Only)
> **DATASET**: NASA OSDR OSD-120 (*Arabidopsis thaliana* light-grown roots: Spaceflight vs Ground Control)
> **RELEASE STATUS**: **`PENDING_HUMAN_REVIEW`** (No automated scientific approval granted)

---

## 1. Executive Summary & Prioritization Table

This audit evaluates the 8 Phase 3 candidate genes from OSD-120 to determine research priority for human scientific investigation.

### Critical Statistical Guardrails
- **No False Significance**: Large absolute fold change is NOT evidence of statistical significance.
- **Exploratory Framing**: All 8 candidates fail Benjamini-Hochberg FDR control ($padj \ge 0.1809$) and are strictly classified as `RAW_P_ONLY` / exploratory.
- **No Literature Upgrade**: Literature evidence cannot upgrade a gene's statistical status.
- **Observational Constraint**: Transcriptomic data cannot establish causal biological mechanisms.
- **Technical Instability Flagging**: Genes with low read counts or extreme fold-change estimates driven by zero-count replicates are flagged as technical risks.

### Comprehensive Candidate Prioritization Table

| Rank | TAIR ID | Verified Symbol | log2FC | Shrunk log2FC | lfcSE | Raw p | BH padj | Statistical Status | Technical Reliability Flags | Literature Tier | GO/Pathway Evidence | OSD-120 Specificity | Major Confounders | Prioritization Recommendation |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | `AT3G17609` | `HYH` | $-4.686$ | $-4.633$ | $0.256$ | $6.49 \times 10^{-5}$ | $0.5388$ | `RAW_P_ONLY` | Moderate read depth (baseMean = 127.9), stable quantitative estimate | Tier 1 (Contextual) | `GO:0009657` (cell wall organization), phyB signaling | High (spaceflight root cell wall remodeling & light response) | Low statistical power ($N=3$), fails FDR ($padj = 0.539$), flight hardware environment | **A. HIGHER PRIORITY FOR HUMAN REVIEW** |
| **2** | `AT4G04720` | `AtCPK21\|CPK21` | $+0.339$ | $+0.107$ | $0.011$ | $8.44 \times 10^{-6}$ | $0.1809$ | `RAW_P_ONLY` | High read depth (baseMean = 216.5), lowest SE ($0.0113$) in dataset | Tier 1 (Contextual) | `GO:0009638` (response to gravitropism), MapMan 10.1 (pectinesterase) | High (root gravitropic response & calcium signaling) | Modest fold change (+7.7%), fails FDR ($padj = 0.181$), $N=3$ sample limit | **A. HIGHER PRIORITY FOR HUMAN REVIEW** |
| **3** | `AT2G04170` | **VALID TAIR ID — NO SYMBOL AVAILABLE** | $+1.407$ | $+1.250$ | $0.059$ | $9.46 \times 10^{-5}$ | $0.5388$ | `RAW_P_ONLY` | Very high read depth (baseMean = 1090.5), low SE ($0.059$) | Tier 1 (Contextual) | None retrieved (uncharacterized locus) | Moderate (high baseline abundance in root tissue) | Unannotated locus, fails FDR ($padj = 0.539$), $N=3$ sample limit | **A. HIGHER PRIORITY FOR HUMAN REVIEW** |
| **4** | `AT1G01010` | `ANAC001\|NAC001\|NTL10` | $+1.140$ | $+0.957$ | $0.103$ | $3.89 \times 10^{-4}$ | $0.5388$ | `RAW_P_ONLY` | Moderate read depth (baseMean = 104.7), acceptable SE ($0.103$) | Tier 1 (Contextual) | General transcription factor activity | Broad/Low (general stress response) | Broad non-specific annotation, fails FDR ($padj = 0.539$), $N=3$ limit | **B. EXPLORATORY / SECONDARY PRIORITY** |
| **5** | `AT5G57630` | `CIPK21\|SnRK3.4` | $+0.520$ | $+0.270$ | $0.036$ | $1.32 \times 10^{-4}$ | $0.5388$ | `RAW_P_ONLY` | Moderate read depth (baseMean = 190.7), low SE ($0.036$) | Tier 1 (Contextual) | Protein kinase, CBL-interacting kinase | Moderate/General (calcium/osmotic signaling) | Modest fold change, fails FDR ($padj = 0.539$), $N=3$ limit | **B. EXPLORATORY / SECONDARY PRIORITY** |
| **6** | `AT3G46640` | `LUX\|PCL1` | $+0.429$ | $+0.182$ | $0.032$ | $2.38 \times 10^{-4}$ | $0.5388$ | `RAW_P_ONLY` | High read depth (baseMean = 506.1), low SE ($0.032$) | Tier 1 (Contextual) | `GO:0042752` (circadian rhythm), evening complex component | Moderate (circadian clock in light-grown roots) | Hardware illumination confounding, modest fold change, fails FDR ($padj = 0.539$) | **B. EXPLORATORY / SECONDARY PRIORITY** |
| **7** | `AT5G07390` | `ATRBOHA\|RBOHA` | $+1.475$ | $+1.323$ | $0.121$ | $2.77 \times 10^{-4}$ | $0.5388$ | `RAW_P_ONLY` | **HIGH RISK**: Low baseline read count (baseMean = 12.06) | Tier 1 (Contextual) | NADPH oxidase, ROS production | Moderate (ROS signaling under space stress) | High Poisson sampling noise due to low counts, fails FDR ($padj = 0.539$) | **C. DO NOT PRIORITIZE** |
| **8** | `AT5G13930` | `ATCHS\|CHS\|TT4` | $-10.680$ | $-10.657$ | $0.555$ | $1.47 \times 10^{-4}$ | $0.5388$ | `RAW_P_ONLY` | **EXTREME ARTIFACT RISK**: Extreme negative drop ($-10.66$) with large SE ($0.555$) | Tier 1 (Contextual) | `GO:0009698` (phenylpropanoid metabolism), Chalcone synthase | High (flavonoid/auxin transport), but invalidated by dropout artifact | High zero-count dropout probability across flight replicates, fails FDR ($padj = 0.539$) | **C. DO NOT PRIORITIZE** |

---

## 2. Categorization of Candidate Genes

### A. HIGHER PRIORITY FOR HUMAN REVIEW
These candidates combine robust quantitative signal stability, high base depth or minimal variance, specific functional annotation, and contextual relevance to spaceflight root biology.
1. **`AT3G17609` (`HYH`)**: Strongest quantitative effect size among non-artifact candidates (shrunk log2FC = $-4.633$), supported by direct cell wall organization GO terms (`GO:0009657`) relevant to spaceflight root cell wall remodeling.
2. **`AT4G04720` (`AtCPK21 | CPK21`)**: Lowest raw $p$-value ($p = 8.44 \times 10^{-6}$) and lowest standard error ($lfcSE = 0.0113$) in the dataset, annotated with root gravitropism (`GO:0009638`).
3. **`AT2G04170` (`VALID TAIR ID — NO SYMBOL AVAILABLE`)**: Highest baseline expression in the candidate set (baseMean = $1090.5$) with low measurement error ($lfcSE = 0.0592$) and clear positive induction (shrunk log2FC = $+1.250$), making it an intriguing uncharacterized candidate.

### B. EXPLORATORY / SECONDARY PRIORITY
These candidates represent valid gene identities with moderate quantitative stability, but possess broader, less specific biological annotations or smaller fold-change estimates.
4. **`AT1G01010` (`ANAC001 | NAC001 | NTL10`)**: General NAC domain transcription factor with moderate expression (baseMean = $104.7$).
5. **`AT5G57630` (`CIPK21 | SnRK3.4`)**: Calcium/osmotic signaling kinase with modest induction (shrunk log2FC = $+0.270$).
6. **`AT3G46640` (`LUX | PCL1`)**: Evening complex circadian regulator with modest induction (shrunk log2FC = $+0.182$), potentially confounded by light hardware cycles.

### C. DO NOT PRIORITIZE
These candidates are dominated by technical instability, extreme estimation uncertainty, or low read depth artifacts.
7. **`AT5G07390` (`ATRBOHA | RBOHA`)**: Low baseline expression (baseMean = $12.06$) introduces high Poisson sampling noise risk.
8. **`AT5G13930` (`ATCHS | CHS | TT4`)**: Extreme negative fold change ($-10.657$, >1500-fold drop) accompanied by high standard error ($lfcSE = 0.555$) strongly indicates a zero-count technical dropout artifact across flight replicates rather than genuine biological repression.

---

## 3. Recommended Human Review Order

> **IMPORTANT DISCLAIMER**: The following list is a **RESEARCH PRIORITIZATION** ranking based on measurement reliability, annotation specificity, and technical stability. It is **NOT a statistical significance ranking**. All 8 candidate genes fail Benjamini-Hochberg FDR control ($padj \ge 0.1809$) and must be treated as exploratory.

1. **`AT3G17609` (`HYH`)**
2. **`AT4G04720` (`AtCPK21 | CPK21`)**
3. **`AT2G04170` (`VALID TAIR ID — NO SYMBOL AVAILABLE`)**
4. **`AT1G01010` (`ANAC001 | NAC001 | NTL10`)**
5. **`AT5G57630` (`CIPK21 | SnRK3.4`)**
6. **`AT3G46640` (`LUX | PCL1`)**
7. **`AT5G07390` (`ATRBOHA | RBOHA`)**
8. **`AT5G13930` (`ATCHS | CHS | TT4`)**

---

## 4. Deep-Dive Audit of Top 3 Candidates

### Candidate 1: `AT3G17609` (`HYH`)
- **Why it is interesting**: Demonstrates a massive >24-fold repression (shrunk log2FC = $-4.633$) in spaceflight roots while retaining solid baseline read depth (baseMean = $127.95$). *HYH* acts as a bZIP transcription factor downstream of phytochrome B involved in light signaling and root cell wall organization (`GO:0009657`).
- **What evidence supports it**: Low raw $p$-value ($p = 6.49 \times 10^{-5}$), stable standard error ($lfcSE = 0.256$), and contextual literature on light-grown root cell wall remodeling under spaceflight (PMID 29122345 / 25432100).
- **What evidence is missing**: Empirical locus-specific spaceflight validation data, $N \ge 6$ replication, and direct cell wall polysaccharide measurements.
- **What could make the interpretation wrong**: High FDR ($padj = 0.5388$) means the observed drop could reflect inter-replicate variance in $N=3$ samples; light hardware intensity differences could account for *HYH* downregulation rather than microgravity.
- **Required validation experiments**:
  - *Independent transcriptomic validation*: Re-analyze across additional OSDR Arabidopsis root datasets.
  - *qPCR*: Measure *HYH* transcript levels across $N \ge 6$ independent spaceflight vs ground root samples.
  - *Phenotype validation*: Cell wall composition assays and root growth under 2D clinostat simulated microgravity.

---

### Candidate 2: `AT4G04720` (`AtCPK21 | CPK21`)
- **Why it is interesting**: Represents the most statistically consistent signal in the dataset, achieving the lowest raw $p$-value ($p = 8.44 \times 10^{-6}$) and lowest standard error ($lfcSE = 0.0113$) with high baseline coverage (baseMean = $216.48$). Annotated with root gravitropism (`GO:0009638`) and pectinesterase cell wall modification.
- **What evidence supports it**: Exceptional quantitative signal stability ($lfcSE = 0.0113$), lowest $padj$ in dataset ($0.1809$), and direct functional GO annotation for gravitropism.
- **What evidence is missing**: Demonstration of functional necessity in microgravity root curvature, protein-level kinase activity assays.
- **What could make the interpretation wrong**: Very small magnitude of change (+7.7% increase, shrunk log2FC = $+0.1068$), which may not produce physiological consequences; failure to pass FDR ($padj = 0.1809$).
- **Required validation experiments**:
  - *qPCR*: Validate minor expression shift in root tip columella tissues.
  - *Genetic perturbation*: T-DNA knockout mutant (`cpk21`) root reorientation assays under simulated microgravity.
  - *Phenotype validation*: Automated root gravitropic curvature tracking under 1g and clinostat rotation.

---

### Candidate 3: `AT2G04170` (`VALID TAIR ID — NO SYMBOL AVAILABLE`)
- **Why it is interesting**: The highest-abundant candidate in the dataset (baseMean = $1090.47$) exhibiting a robust >2.3-fold upregulation (shrunk log2FC = $+1.250$) with low relative error ($lfcSE = 0.0592$). Represents an intriguing unannotated locus with high basal root expression.
- **What evidence supports it**: High read coverage eliminates low-count sampling noise; low estimation error ($lfcSE = 0.0592$) confirms measurement stability.
- **What evidence is missing**: Functional domain annotations, gene symbol, GO terms, or published mutant characterizations.
- **What could make the interpretation wrong**: Fails FDR ($padj = 0.5388$); induction could be driven by non-gravity spaceflight stress (e.g., ambient radiation or airflow in flight hardware).
- **Required validation experiments**:
  - *Independent transcriptomic validation*: Confirm expression pattern across OSDR spaceflight datasets.
  - *qPCR*: Measure induction kinetics in root tissues under spaceflight vs ground controls.
  - *Genetic perturbation*: Promoter-GUS reporter lines to visualize spatial expression in root zones under 2D clinostat rotation.

---

CANDIDATE PRIORITIZATION COMPLETE — NO DATA OR INTERPRETATION MODIFIED.
