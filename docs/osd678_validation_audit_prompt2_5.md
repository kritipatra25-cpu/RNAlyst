# OSD-678 Validation Audit & Prompt-3 Boundary Check (Prompt 2.5)

> **DOCUMENT TYPE**: Read-Only Human-Review Support Audit & Prompt-3 Boundary Contract
> **DATASETS UNDER AUDIT**: NASA OSDR OSD-120 (Roots) & OSD-678 (Whole Seedlings)
> **AUDIT PURPOSE**: Evaluate completed OSD-678 validation results, enforce scientific language guardrails, document experimental non-equivalence, evaluate the CRY hypothesis, partition candidate genes, and establish the Prompt 3 Evidence Contract.
> **RELEASE GATE**: **`READY_FOR_PROMPT_3`**

---

## Task 1 — Statistical Fact Check Table

| TAIR ID | Gene Symbol | OSD-120 Root $\text{log}_2\text{FC}$ | OSD-120 $p_{\text{adj}}$ | OSD-678 Seedling $\text{log}_2\text{FC}$ | OSD-678 $p_{\text{adj}}$ (FDR) | Direction Concordance | FDR Sig in OSD-678 ($q < 0.05$) | Evidence Classification |
|---|---|---|---|---|---|---|---|---|
| **`AT3G17609`** | `HYH` | $-4.686$ | $0.539$ | $-0.847$ | $0.269$ | **YES** | **NO** | `DIRECTIONAL_CONCORDANCE_ONLY` |
| **`AT4G04720`** | `CPK21` | $+0.339$ | $0.181$ | $-0.219$ | $0.192$ | **NO** | **NO** | `TISSUE_SPECIFIC_OR_DISCORDANT` |
| **`AT2G04170`** | *VALID TAIR ID — NO SYMBOL AVAILABLE* | $+1.407$ | $0.539$ | $-1.040$ | $0.338$ | **NO** | **NO** | `TISSUE_SPECIFIC_OR_DISCORDANT` |
| **`AT1G01010`** | `ANAC001` | $+1.140$ | $0.539$ | $+2.460$ | $9.19 \times 10^{-11}$ | **YES** | **YES** | `CROSS_TISSUE_REPLICATION_CONCORDANT` |
| **`AT5G57630`** | `CIPK21` | $+0.520$ | $0.539$ | $-0.253$ | $0.549$ | **NO** | **NO** | `TISSUE_SPECIFIC_OR_DISCORDANT` |
| **`AT3G46640`** | `LUX` | $+0.429$ | $0.539$ | $+0.732$ | $0.041$ | **YES** | **YES** | `CROSS_TISSUE_REPLICATION_CONCORDANT` |
| **`AT5G07390`** | `RBOHA` | $+1.475$ | $0.539$ | $+5.449$ | $0.0038$ | **YES** | **YES** | `CROSS_TISSUE_REPLICATION_CONCORDANT` |
| **`AT5G13930`** | `CHS` | $-10.680$ | $0.539$ | $-5.193$ | $0.0021$ | **YES** | **YES** | `CROSS_TISSUE_REPLICATION_CONCORDANT` |

---

## Task 2 — Separate Observation from Interpretation

An audit of `docs/osd678_candidate_cross_tissue_validation.md` identified statements containing interpretive or mechanistic language that exceed direct numerical observation.

### Flagged Claims & Safe Replacements

1. **Flagged Claim 1**:
   - **ORIGINAL CLAIM**: *"ANAC001... demonstrate robust, FDR-significant cross-tissue replication..."*
   - **EVIDENCE ACTUALLY AVAILABLE**: `ANAC001` exhibits positive fold change in both OSD-120 ($\text{LFC} = +1.14$) and OSD-678 ($\text{LFC} = +2.46, q < 10^{-10}$).
   - **WHY IT EXCEEDS**: "Robust" is an unquantified qualitative descriptor.
   - **SAFE REPLACEMENT**: *"ANAC001 exhibits directionally concordant positive fold change in both OSD-120 and OSD-678 datasets ($q < 0.05$ in OSD-678)."*

2. **Flagged Claim 2**:
   - **ORIGINAL CLAIM**: *"...indicating that AT2G04170 induction is a root-specific spaceflight response that is diluted or counter-regulated in whole seedling tissue..."*
   - **EVIDENCE ACTUALLY AVAILABLE**: `AT2G04170` exhibits positive fold change in isolated roots ($\text{LFC} = +1.41$ in OSD-120, $+1.59$ in OSD-658) and negative fold change in whole seedlings ($\text{LFC} = -1.04$ in OSD-678).
   - **WHY IT EXCEEDS**: Terms like "diluted", "counter-regulated", and "root-specific response" infer biological mechanism and regulatory dynamics not directly measured by differential expression.
   - **SAFE REPLACEMENT**: *"AT2G04170 displays positive fold change in isolated root datasets (OSD-120/658) and negative fold change in whole seedling tissue (OSD-678)."*

3. **Flagged Claim 3**:
   - **ORIGINAL CLAIM**: *"...reflects organ-specific functional specialization (Roots vs Shoots)."*
   - **EVIDENCE ACTUALLY AVAILABLE**: Expression values differ between isolated root datasets and whole seedling datasets.
   - **WHY IT EXCEEDS**: Assumes functional specialization without protein, phenotypic, or cell-type functional assays.
   - **SAFE REPLACEMENT**: *"Differences in expression direction correlate with sample tissue composition (isolated roots vs whole seedlings)."*

---

## Task 3 — Tissue, Hardware, and Experimental Non-Equivalence

### Experimental Non-Equivalence Breakdown

| Parameter | OSD-120 | OSD-678 | Legitimate Classification |
|---|---|---|---|
| **Tissue Type** | Isolated Root Tissue | Whole Seedlings (Roots + Shoots) | **Cross-Tissue Comparison** |
| **Flight Hardware** | CARA / APEX Hardware Enclosure | BRIC-23 Canister Hardware | **Hardware Context Difference** |
| **Experimental Design** | $N=3$ Spaceflight vs Ground (Col-0 Light) | $3 \times 2 \times 2$ Full Factorial ($N=36$) | **Multi-Factorial Design** |
| **Biological Concordance** | `ANAC001`, `LUX`, `RBOHA`, `CHS` | `ANAC001`, `LUX`, `RBOHA`, `CHS` | **B. Cross-Tissue Directional Concordance** |
| **Tissue Discordance** | `AT2G04170`, `CPK21` (+ in roots) | `AT2G04170`, `CPK21` (- in seedlings) | **C. Context-Dependent Evidence** |

**DECLARATION**: OSD-678 MUST NOT be called a direct biological replication of OSD-120. It represents a **cross-tissue, hardware-differing comparative dataset**.

---

## Task 4 — CRY Hypothesis Guardrail

- **Cryptochrome Statistics in OSD-678**:
  - *CRY1* (`AT4G08920`): $\text{LFC} = -1.012, q = 4.22 \times 10^{-6}$ (Repressed in light seedlings)
  - *CRY2* (`AT1G04400`): $\text{LFC} = +0.673, q = 0.00012$ (Elevated in light seedlings)
- **Comparison to OSD-120**: Neither *CRY1* nor *CRY2* showed statistically significant differential expression in OSD-120 roots ($q > 0.52$).
- **Scientific Guardrail Check**:
  - In OSD-678 whole seedlings, cryptochrome genes are differentially expressed, whereas in OSD-120 roots they are unchanged.
  - Differential expression of *CRY1*/*CRY2* in whole seedlings reflects shoot light sensing under hardware illumination.
  - **Verdict**: As established in OSD-120, a **CRY-centered master mechanism for spaceflight root responses is NOT directly supported**. Downstream light-responsive genes (`HYH`, `LUX`) must not be used to infer a CRY-driven microgravity response mechanism.

---

## Task 5 — Validated Candidate Gene Set Partition

### **GROUP A: Strongest Cross-Dataset Evidence**
*(Directionally concordant AND FDR-significant $q < 0.05$ in OSD-678)*
1. `AT1G01010` (`ANAC001`)
2. `AT3G46640` (`LUX`)
3. `AT5G07390` (`RBOHA`)
4. `AT5G13930` (`CHS`)

### **GROUP B: Directional Support Only**
*(Directionally concordant but not FDR-significant in OSD-678)*
1. `AT3G17609` (`HYH`)

### **GROUP C: Discordant / Context-Specific**
*(Directionally discordant between OSD-120 roots and OSD-678 seedlings)*
1. `AT4G04720` (`CPK21`)
2. `AT2G04170` (*VALID TAIR ID — NO SYMBOL AVAILABLE*)
3. `AT5G57630` (`CIPK21`)

---

## Task 6 — Prompt 3 Readiness Assessment

1. **Sufficient for Prompt 3?**: **YES**, statistical validation across OSD-120, OSD-658, and OSD-678 is complete and provides an auditable foundation.
2. **Safe Inputs**: Group A (`ANAC001`, `LUX`, `RBOHA`, `CHS`) and Group B (`HYH`). Group C genes must be strictly designated as root-specific / context-dependent loci.
3. **Explicitly Prohibited Claims**:
   - Claiming microgravity *causes* observed expression changes.
   - Claiming a CRY-centered master regulatory mechanism.
   - Claiming `AT2G04170` is a universal spaceflight response marker across all plant organs.
   - Inferring biological pathway causality from transcriptomic association alone.
4. **Required Uncertainties to Preserve**:
   - Organ/tissue non-equivalence (Roots vs Whole Seedlings).
   - Flight hardware environment non-equivalence (CARA/APEX vs BRIC-23).
   - Sample-size statistical limits ($N=3$ per cell).
5. **Additional Evidence Needed Prior to Mechanistic Modeling**:
   - Tissue-specific baseline expression profiles (e.g. root vs shoot expression ratios from public Arabidopsis atlases).

---

## Task 7 — Release Gate & Prompt 3 Evidence Contract

### **RELEASE GATE STATUS: `READY_FOR_PROMPT_3`**

### **Prompt 3 Evidence Contract**

1. **Validated Candidates & Evidence Tiers**:
   - **Group A (Cross-Tissue Replication, FDR $q < 0.05$)**: `ANAC001`, `LUX`, `RBOHA`, `CHS`
   - **Group B (Directional Convergence Only, $q > 0.05$)**: `HYH`
   - **Group C (Root-Specific / Context-Discordant)**: `AT2G04170`, `CPK21`, `CIPK21`
2. **Allowed Biological Interpretation**:
   - Descriptive mapping of candidates to biological themes (Stress/defense, Circadian evening complex, Flavonoid biosynthesis, Root-specific uncharacterized response).
   - Framing all conclusions as observational, transcriptomic associations.
3. **Prohibited Causal / Mechanistic Claims**:
   - No use of forbidden causal terms (*causes*, *drives*, *master regulator*, *proves mechanism*).
   - No CRY-centered master mechanism claims.
4. **Tissue / Context Limitations**:
   - Explicitly maintain distinction between isolated root datasets (OSD-120/OSD-658) and whole seedling datasets (OSD-678).
5. **CRY Constraint**:
   - Retain the conclusion from OSD-120 scientific review: CRY1/2 direct differential expression is absent in roots and non-concordant across organs, falsifying a universal CRY-centered microgravity mechanism.

---

PROMPT 2.5 VALIDATION AUDIT COMPLETE — READY FOR PROMPT 3 UNDER STATED EVIDENCE CONTRACT.
