# OSD-120 Scientific Synthesis & Biological Model

> **DOCUMENT TYPE**: Scientific Synthesis & Biological Model (Read-Only)
> **DATASET**: NASA OSDR OSD-120 (*Arabidopsis thaliana* light-grown roots: Spaceflight vs Ground Control)
> **RELEASE STATUS**: **`PENDING_HUMAN_REVIEW`** (No automated scientific approval granted)

---

## 1. Executive Summary & Evidence Hierarchy

This document performs the final scientific synthesis for the OSD-120 RNA-seq candidate gene set. The analysis establishes a structured biological model while preserving strict statistical boundaries:
- **Phase 1 Quantitative Immutability**: All numerical values ($p$-value, $p_{\text{adj}}$, $\text{log}_2\text{FC}$, $\text{lfcSE}$) remain identical to Phase 1 DESeq2 primary outputs.
- **Statistical Reality**: All candidate genes fail Benjamini-Hochberg FDR control ($p_{\text{adj}} \ge 0.1809$) and are strictly classified as `RAW_P_ONLY` / exploratory.
- **Evidence Hierarchy**:
  - `[OBSERVED]`: Directly measured in OSD-120 transcriptomic data.
  - `[EVIDENCE-SUPPORTED]`: Backed by verified database annotations or peer-reviewed literature.
  - `[INFERRED]`: Biologically plausible connection not directly demonstrated.
  - `[HYPOTHESIS]`: Proposed testable mechanistic link requiring orthogonal experiment.

---

## 2. Candidate-to-Theme Mapping

The 6 candidates passing technical reliability screening map into three distinct biological themes:

### Theme A: Cell-Wall Remodeling & Light Signaling
- **`AT3G17609` (`HYH`)** [`CORE CANDIDATE`]: Strongest non-artifact quantitative repression (shrunk $\text{log}_2\text{FC} = -4.6329$, $p = 6.49 \times 10^{-5}$). Directly annotated to `GO:0009657` (*cell wall organization*) and phyB light signaling. Supported by literature on spaceflight root cell wall modification (PMID 29122345, PMID 25432100).
- **`AT2G04170` (`Unassigned`)** [`CORE CANDIDATE`]: High-abundance uncharacterized locus ($\text{baseMean} = 1090.47$, shrunk $\text{log}_2\text{FC} = +1.2497$). Included provisionally as an abundant root-expressed transcript with potential cell wall or structural links.

### Theme B: Gravitropism & Calcium Signaling
- **`AT4G04720` (`AtCPK21 | CPK21`)** [`CORE CANDIDATE`]: Most statistically consistent signal ($p = 8.44 \times 10^{-6}$, $\text{lfcSE} = 0.0113$, $p_{\text{adj}} = 0.1809$). Directly annotated to `GO:0009638` (*response to gravitropism*) and pectinesterase modification.
- **`AT5G57630` (`CIPK21 | SnRK3.4`)** [`EXPLORATORY CANDIDATE`]: Calcium/osmotic signaling kinase (shrunk $\text{log}_2\text{FC} = +0.270$). Participates in CBL-mediated calcium signaling cascades.
- **`AT1G01010` (`ANAC001 | NAC001`)** [`EXPLORATORY CANDIDATE`]: Broad stress transcription factor (shrunk $\text{log}_2\text{FC} = +0.957$). Connected to general stress and calcium-mediated transcriptional pathways.

### Theme C: Circadian-Clock Integration
- **`AT3G46640` (`LUX | PCL1`)** [`EXPLORATORY CANDIDATE`]: Evening complex transcription factor (shrunk $\text{log}_2\text{FC} = +0.1815$, $p = 2.38 \times 10^{-4}$). Directly annotated to `GO:0042752` (*circadian rhythm*).

### Excluded Candidates
- **`AT5G07390` (`RBOHA`)**: Excluded from core model due to low read depth ($\text{baseMean} = 12.06$) and high Poisson sampling noise risk.
- **`AT5G13930` (`CHS`)**: Excluded from core model due to extreme negative fold drop ($-10.657$, $\text{lfcSE} = 0.555$) caused by zero-count technical dropout artifacts in flight replicates.

---

## 3. Test of the Working Hypothesis

We evaluate the working hypothesis:
> *"Spaceflight-associated environmental conditions alter light/cryptochrome-associated signaling and downstream cellular signaling, which may influence root developmental programs including cell-wall remodeling, gravitropism, calcium signaling, and circadian regulation."*

### Proposed Link 1: Spaceflight $\to$ Light / Cryptochrome Signaling
- **Classification**: `PARTIALLY SUPPORTED`
- **Rationale**: Supported by significant raw downregulation of *HYH* ($p = 6.49 \times 10^{-5}$), a bZIP transcription factor downstream of phytochrome B (phyB). However, no direct differential expression of CRY1 or CRY2 is observed.

### Proposed Link 2: Light / Cryptochrome Signaling $\to$ Calcium / Signaling Responses
- **Classification**: `PLAUSIBLE BUT UNTESTED`
- **Rationale**: Crosstalk between light signaling and calcium signaling is established in literature, but no direct regulatory connection between *HYH* and *CPK21* or *CIPK21* is demonstrated in OSD-120 data.

### Proposed Link 3: Calcium / Signaling Responses $\to$ Circadian Regulation
- **Classification**: `PLAUSIBLE BUT UNTESTED`
- **Rationale**: Calcium waves can modulate circadian period length, and *LUX* shows minor induction ($p = 2.38 \times 10^{-4}$), but zero direct regulatory evidence links *CPK21* to *LUX* in this dataset.

### Proposed Link 4: Circadian Regulation $\to$ Cell-Wall / Root Developmental Responses
- **Classification**: `PARTIALLY SUPPORTED`
- **Rationale**: Circadian clock control of cell wall extension is documented in literature. Both *LUX* (circadian) and *HYH* (cell wall) show raw expression shifts, but their functional co-regulation in OSD-120 roots is unproven.

---

## 4. CRY-Centered Hypothesis Check

- **Direct Evidence for CRY1 / CRY2**: **NONE**. Neither *CRY1* (`AT4G08920`) nor *CRY2* (`AT1G04400`) are present among the OSD-120 candidate DE genes, nor do they pass raw nominal significance in primary DESeq2 outputs.
- **Indirect Evidence Consistent with Light Signaling**: **PRESENT**. *HYH* (`AT3G17609`), a key bZIP factor working in tandem with *HY5* downstream of phytochrome B (phyB), is heavily repressed (shrunk $\text{log}_2\text{FC} = -4.633$).
- **Downstream Light-Related Evidence**: *LUX* (`AT3G46640`), a circadian clock gene coregulated by light/dark cycles, is weakly induced.
- **Contradictory Evidence**: None; however, the lack of CRY1/CRY2 differential expression means a *specifically cryptochrome-mediated* mechanism is **NOT supported by OSD-120 data alone**.

> **SCIENTIFIC CONCLUSION ON CRY**: The OSD-120 dataset provides evidence for **phyB/HYH light-response pathway alteration**, but does NOT provide direct support for a CRY-centered mechanism. Manufacturing a CRY connection for OSD-120 would be scientifically invalid.

---

## 5. Mechanistic Hypothesis Graph

```
========================================================================================
                      OSD-120 OBSERVATIONAL TRANSCRIPTOMIC SIGNAL
========================================================================================
                                           │
                                           │ [OBSERVED]
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ CANDIDATE GENES: AT3G17609 (HYH), AT4G04720 (CPK21), AT2G04170, AT1G01010, AT5G57630 │
└──────────────────────────────────────────────────────────────────────────────────────┘
                   │                                      │
                   │ [EVIDENCE-SUPPORTED]                 │ [EVIDENCE-SUPPORTED]
                   ▼                                      ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────────────────┐
│ THEME A: CELL WALL & LIGHT SIGNALING │  │ THEME B: GRAVITROPISM & CALCIUM SIGNALING│
│ - HYH (phyB downstream, GO:0009657)  │  │ - CPK21 (lfcSE=0.011, GO:0009638)        │
│ - AT2G04170 (High abundance root DE) │  │ - CIPK21 (Calcium-interacting kinase)    │
└──────────────────────────────────────┘  └──────────────────────────────────────────┘
                   │                                      │
                   │ [INFERRED]                           │ [INFERRED]
                   ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ PLAUSIBLE DOWNSTREAM PROCESSES                                                       │
│ - Root cell wall loosening & remodeling under spaceflight                            │
│ - Altered calcium-mediated gravity vector perception                                 │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ [HYPOTHESIS]
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ TESTABLE BIOLOGICAL HYPOTHESES                                                        │
│ H1: HYH repression reduces cell wall crosslinking in microgravity root tips         │
│ H2: CPK21 fine-tunes calcium flux during gravistimulation disorientation             │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Narrative Evaluation

- **Narrative A ("Spaceflight alters cell-wall remodeling")**: **BEST SUPPORTED**. Driven by `AT3G17609` (*HYH*), which exhibits the largest effect size (shrunk $\text{log}_2\text{FC} = -4.633$) and direct cell wall GO annotations.
- **Narrative B ("Spaceflight alters gravitropism/calcium signaling")**: **WELL SUPPORTED**. Driven by `AT4G04720` (*CPK21*), which has the lowest nominal $p$-value ($8.44 \times 10^{-6}$) and lowest estimation error ($\text{lfcSE} = 0.0113$) in the dataset.
- **Narrative C ("Spaceflight alters circadian regulation")**: **WEAKLY SUPPORTED**. Driven only by minor *LUX* induction ($+0.1815$ shrunk fold change).
- **Narrative D ("Coordinated multi-pathway integration across light, calcium, and cell wall")**: **PLAUSIBLE HYPOTHESIS, UNPROVEN AS MECHANISM**. While biologically attractive, connecting these themes into a single coordinated network is NOT statistically or causally proven by OSD-120.

---

## 7. OSD-120 vs Broader Project Integration

### OSD-120 Standalone Evidence
- Demonstrates raw transcript shifts in root cell wall remodeling (*HYH*), calcium/gravitropism signaling (*CPK21*), and uncharacterized root transcripts (`AT2G04170`).
- Fails FDR control ($p_{\text{adj}} \ge 0.1809$) due to $N=3$ sample power limits.
- Proves association, NOT causation.

### Cross-Dataset Integration (OSD-678 / OSD-658)
- **Proposed Comparison**: Evaluate whether *HYH* downregulation and *CPK21* consistency replicate in:
  - **OSD-678** (*Arabidopsis* spaceflight vs ground control roots).
  - **OSD-658** (*Arabidopsis* dark-grown vs light-grown spaceflight roots).
- **Falsification Criteria**:
  - If *HYH* is downregulated in OSD-678 roots $\to$ **Strengthens** spaceflight cell wall hypothesis.
  - If *HYH* downregulation occurs ONLY in light-grown spaceflight datasets (OSD-120) but NOT dark-grown spaceflight datasets (OSD-658) $\to$ **Confirms** light/hardware confounding rather than microgravity response.

---

## 8. Three-Layer Final Scientific Model

```
========================================================================================
LAYER 1: ESTABLISHED (Direct OSD-120 Data)
- 8 candidate genes show raw nominal differential expression (p < 0.0004).
- 0 candidates pass Benjamini-Hochberg FDR control (padj >= 0.1809; N=3 power limit).
- AT3G17609 (HYH) is heavily downregulated (shrunk log2FC = -4.633, lfcSE = 0.256).
- AT4G04720 (CPK21) shows minor, highly consistent upregulation (lfcSE = 0.0113).
- AT2G04170 is a highly abundant, unannotated upregulated root locus (baseMean = 1090.5).
========================================================================================
                                           │
                                           ▼
========================================================================================
LAYER 2: EVIDENCE-SUPPORTED INTERPRETATION (Database & Literature Verification)
- HYH regulates phyB-dependent light response and cell wall organization (GO:0009657).
- CPK21 is a calcium-dependent kinase involved in gravitropism (GO:0009638).
- Spaceflight roots undergo cell wall remodeling and calcium signaling (PMID 29122345).
========================================================================================
                                           │
                                           ▼
========================================================================================
LAYER 3: TESTABLE MECHANISTIC HYPOTHESES (Requires Orthogonal Validation)
- H1: Spaceflight microgravity represses HYH expression, impairing root cell wall rigidity.
- H2: CPK21 modulates columella cell calcium signaling during gravistimulation loss.
- H3: HYH repression is driven by light hardware spectral differences rather than microgravity.
========================================================================================
```

---

## 9. Final Conclusion

1. **Strongest biological signal in OSD-120**: Severe downregulation of *HYH* (`AT3G17609`, cell wall remodeling) and high quantitative consistency of *CPK21* (`AT4G04720`, gravitropism/calcium signaling).
2. **Weakest part of the proposed mechanism**: High FDR ($p_{\text{adj}} \ge 0.1809$), small sample size ($N=3$), lack of direct CRY1/CRY2 differential expression, and inability to rule out hardware light/environmental confounding.
3. **Does the dataset support a CRY-centered hypothesis?**: **NO**. CRY1 and CRY2 are absent from the candidate DE list. Current data supports phyB/HYH light signaling context, not a direct CRY mechanism.
4. **Top 2–3 genes for downstream validation**: `AT3G17609` (*HYH*), `AT4G04720` (*CPK21*), and `AT2G04170` (Unassigned).
5. **Genes to exclude from core story**: `AT5G07390` (*RBOHA*, low count noise) and `AT5G13930` (*CHS*, zero-count dropout artifact).
6. **Single next analysis providing greatest confidence boost**: Independent qPCR validation of *HYH* and *CPK21* across $N \ge 6$ spaceflight vs 1g ground control samples, combined with cross-dataset evaluation against dark-grown spaceflight roots (OSD-658).

---

SCIENTIFIC SYNTHESIS COMPLETE — MECHANISTIC CLAIMS REMAIN HYPOTHESES UNTIL ORTHOGONALLY VALIDATED.
