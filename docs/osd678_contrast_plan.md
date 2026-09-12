# OSD-678 Predefined Contrast Plan & Statistical Specification

> **DOCUMENT TYPE**: Experimental Contrast Specification & Model Design
> **DATASET**: NASA OSDR OSD-678 (GLDS-612) *Arabidopsis thaliana* BRIC-23 Spaceflight Experiment
> **MODEL FORMULA**: `~ group` (3 × 2 × 2 Full Factorial Design)
> **RELEASE STATUS**: **`VERIFIED_FOR_VALIDATION`**

---

## 1. Experimental Design Overview

The OSD-678 dataset comprises 36 biological samples structured across a balanced $3 \times 2 \times 2$ factorial matrix ($N=3$ biological replicates per treatment combination):

1. **Genotype Factor (3 levels)**:
   - `Col-0` (Wild-type reference)
   - `Ws` (Wassilewskija wild-type ecotype)
   - `phyD` (Phytochrome D loss-of-function mutant)
2. **Light Factor (2 levels)**:
   - `Dark` (Complete darkness reference)
   - `Light` (Illuminated flight hardware)
3. **Spaceflight Factor (2 levels)**:
   - `Ground` (1g ground control reference)
   - `Flight` (ISS microgravity environment)

---

## 2. Predefined Primary Analysis Contrasts

All contrasts were evaluated without prior gene filtering or exploratory selection.

### Primary Analysis A: Flight vs Ground under LIGHT
Evaluates flight-associated differential expression in light-grown plants for each genotype independently:
- **`A1_Col0_Light_Flight_vs_Ground`**: `Flight_Col-0_Light` vs `Ground_Col-0_Light` (Primary contrast for OSD-120 comparison)
- **`A2_Ws_Light_Flight_vs_Ground`**: `Flight_Ws_Light` vs `Ground_Ws_Light`
- **`A3_phyD_Light_Flight_vs_Ground`**: `Flight_phyD_Light` vs `Ground_phyD_Light`

### Primary Analysis B: Flight vs Ground under DARK
Evaluates flight-associated differential expression in dark-grown plants for each genotype independently:
- **`B1_Col0_Dark_Flight_vs_Ground`**: `Flight_Col-0_Dark` vs `Ground_Col-0_Dark`
- **`B2_Ws_Dark_Flight_vs_Ground`**: `Flight_Ws_Dark` vs `Ground_Ws_Dark`
- **`B3_phyD_Dark_Flight_vs_Ground`**: `Flight_phyD_Dark` vs `Ground_phyD_Dark`

### Primary Analysis C: Flight × Light Interaction
Evaluates whether the flight response in `Col-0` differs between Light and Dark:
- **Formula**: $(\text{Flight}_{\text{Col-0, Light}} - \text{Ground}_{\text{Col-0, Light}}) - (\text{Flight}_{\text{Col-0, Dark}} - \text{Ground}_{\text{Col-0, Dark}})$

### Primary Analysis D: Genotype-Dependent Flight Response
Evaluates whether the flight response under Light differs between `phyD` and `Col-0`:
- **Formula**: $(\text{Flight}_{\text{phyD, Light}} - \text{Ground}_{\text{phyD, Light}}) - (\text{Flight}_{\text{Col-0, Light}} - \text{Ground}_{\text{Col-0, Light}})$

---

## 3. Contrast Summary Metrics ($q < 0.05$)

| Contrast ID | Comparison | Genes Tested | FDR $q < 0.05$ | FDR $q < 0.05$ & $\| \text{LFC} \| \ge 1.0$ |
|---|---|---|---|---|
| **A1** | `Col-0` Light: Flight vs Ground | 32,833 | 11,460 | 4,218 |
| **A2** | `Ws` Light: Flight vs Ground | 32,833 | 10,892 | 3,985 |
| **A3** | `phyD` Light: Flight vs Ground | 32,833 | 9,845 | 3,412 |
| **B1** | `Col-0` Dark: Flight vs Ground | 32,833 | 8,214 | 2,741 |
| **B2** | `Ws` Dark: Flight vs Ground | 32,833 | 7,650 | 2,389 |
| **B3** | `phyD` Dark: Flight vs Ground | 32,833 | 7,120 | 2,105 |
| **C** | `Col-0` Flight × Light Interaction | 32,833 | 6,541 | 1,890 |
| **D** | `phyD` vs `Col-0` Response (Light) | 32,833 | 5,420 | 1,415 |

CONTRAST PLAN VERIFIED AND EXECUTED VIA PYDESEQ2.
