# OSD-678 Input Integrity Audit Report

> **DOCUMENT TYPE**: Read-Only Input Integrity Audit
> **DATASET**: NASA OSDR OSD-678 (GLDS-612) STAR Unnormalized Integer Count Matrix & Sample Metadata
> **AUDIT STATUS**: **`PASSED`** (10/10 Integrity Checks Verified)
> **RELEASE STATUS**: **`VERIFIED_FOR_DESEQ2`**

---

## 1. Provenance & File Hashes

| Asset | File Path | SHA-256 Hash |
|---|---|---|
| **Raw Count Matrix** | `data/osd678/GLDS-612_rna_seq_STAR_Unnormalized_Counts_GLbulkRNAseq.csv` | `008e6e056e1904fa70e172e9b67a05ca0c2cf4acada0aebaf2c59c464d5aeced` |
| **Sample Metadata** | `data/osd678/osd678_sample_metadata.csv` | `0716489a3a3d2a95a01187fe6515d9a30f653e8d53569a39bf2bd853c1116f21` |

---

## 2. 10-Point Input Integrity Check Results

| Check # | Audit Item | Target / Requirement | Observed Status | Audit Result |
|---|---|---|---|---|
| **1** | Count Matrix File | Exists in `data/osd678/` | Verified ($32,833 \times 37$) | **`PASSED`** |
| **2** | Sample Metadata File | Exists in `data/osd678/` | Verified ($36 \times 6$) | **`PASSED`** |
| **3** | Unique Gene IDs | 0 duplicate gene IDs | 32,833 unique loci | **`PASSED`** |
| **4** | Unique Sample IDs | 0 duplicate sample columns | 36 unique sample IDs | **`PASSED`** |
| **5** | 1-to-1 Sample Reconciliation | Every count matrix sample in metadata | 36/36 matched 100% | **`PASSED`** |
| **6** | Exact Sample Count | Exactly 36 samples | 36 count samples, 36 meta samples | **`PASSED`** |
| **7** | Count Data Integrity | Non-negative integers only | 100% non-negative integers | **`PASSED`** |
| **8** | Missing Value Check | 0 missing condition labels | 0 NaN values across factors | **`PASSED`** |
| **9** | Experimental Factors | Explicit Genotype, Light, Spaceflight | 3 Genotypes, 2 Light, 2 Flight | **`PASSED`** |
| **10** | Factorial Balance | Balanced $3 \times 2 \times 2 \times 3$ design | 12 groups, $N=3$ per group | **`PASSED`** |

---

## 3. Experimental Factor Structure

Reference levels configured for DESeq2 modeling:
- **`genotype`**: Reference = `Col-0` (Levels: `Col-0`, `Ws`, `phyD`)
- **`light`**: Reference = `Dark` (Levels: `Dark`, `Light`)
- **`spaceflight`**: Reference = `Ground` (Levels: `Ground`, `Flight`)

Full Factorial Groups ($N=3$ biological replicates per group):
1. `Col-0_Dark_Ground` (Baseline reference)
2. `Col-0_Dark_Flight`
3. `Col-0_Light_Ground`
4. `Col-0_Light_Flight`
5. `Ws_Dark_Ground`
6. `Ws_Dark_Flight`
7. `Ws_Light_Ground`
8. `Ws_Light_Flight`
9. `phyD_Dark_Ground`
10. `phyD_Dark_Flight`
11. `phyD_Light_Ground`
12. `phyD_Light_Flight`

INPUT INTEGRITY AUDIT PASSED — READY FOR DESEQ2 FACTORIAL MODELING.
