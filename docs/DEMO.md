# RNAlyst Local Reproducible Demo Guide

This guide provides step-by-step instructions for running a local scientific demonstration of RNAlyst using pre-loaded or uploaded bulk RNA-seq data.

---

## 1. Local Environment Setup

### 1.1 Activate Environment
Ensure Python 3.10+ and conda/mamba are installed.

```bash
conda activate rnaseq-ai-agent
# or
source .venv/bin/activate
```

### 1.2 Start the FastAPI Backend Server
Run the Uvicorn dev server from the repository root:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify that the API is running by accessing `http://localhost:8000/openapi.json` or `http://localhost:8000/api/v1/projects`.

---

## 2. Launching the Web Application Interface

Open `web/index.html` directly in Google Chrome, Firefox, or Safari, or serve it via Python's built-in HTTP server:

```bash
python -m http.server 3000 --directory web
```
Navigate to `http://localhost:3000`.

---

## 3. Step-by-Step Demo Workflow

### Step 1: Select or Create a Project
- In the top project dropdown, select `OSD-120` or click **New Project** to create a custom project workspace (e.g. `MY_RNASEQ_PROJECT`).

### Step 2: Upload Data
Choose one of the two supported scientific entry paths:

#### Entry Path A: Paired-End FASTQ Upload
- Drag and drop paired-end FASTQ files (`sample1_R1.fastq.gz` and `sample1_R2.fastq.gz`).
- Observe that RNAlyst automatically groups R1 and R2 into **1 paired biological sample** under `sample1`.

#### Entry Path B: Direct Count Matrix & Metadata Upload
- Upload `counts_matrix.csv` (rows = genes, columns = sample IDs).
- Upload `sample_table.csv` (containing `sample_id` and `condition` columns).

### Step 3: Enter Research Query
In the Research Composer input box, submit a scientific prompt:

> *"Perform differential expression analysis between Space Flight and Ground Control samples, generate PCA and volcano plots, and identify top biological pathways supported by literature."*

### Step 4: Execution & Artifact Inspection
RNAlyst will execute the following steps in sequence:
1. **Prerequisite Check**: Validates $N \ge 2$ biological replicates per group.
2. **PyDESeq2 Processing**: Computes log2FoldChanges and Benjamini-Hochberg adjusted $p$-values.
3. **Figure Generation**: Renders 2D PCA plot (`pca_plot.png`), Volcano plot (`volcano_plot.png`), and Heatmap (`heatmap_plot.png`).
4. **Literature Search**: Queries local RAG index for organism-matched publications.

Generated plots and DEG tables will render directly in the UI.

---

## 4. Automated Demo Verification Script

To run the complete scientific acceptance pipeline without launching the UI:

```bash
python scripts/run_scientific_acceptance_test.py
```

Generated outputs will be saved to `results/osd120_acceptance/`:
- `vst_counts.csv`
- `deseq2_results.csv`
- `pca_plot.png`
- `volcano_plot.png`
- `heatmap_plot.png`
