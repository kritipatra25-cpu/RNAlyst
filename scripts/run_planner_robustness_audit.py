import sys, json, io, os
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

PROJECT_ROOT = Path('/home/kriti/rna-seq-ai-agent')
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from pipeline.orchestrator import AnalysisOrchestrator

client = TestClient(app)
orchestrator = AnalysisOrchestrator()

# Set up test files
uploads_dir = PROJECT_ROOT / 'data' / 'uploads'
uploads_dir.mkdir(parents=True, exist_ok=True)

# 1. Setup valid matrix + metadata
mat_id = "audit_mat_fixture"
counts_csv = uploads_dir / f"{mat_id}_counts.csv"
meta_csv = uploads_dir / f"{mat_id}_metadata.csv"

import numpy as np, pandas as pd
np.random.seed(2026)
ctrl = np.random.randint(50, 150, size=(10, 3))
treat = np.random.randint(50, 150, size=(10, 3))
treat[:3, :] += 300
counts = np.hstack([ctrl, treat])
samples = ['S1_Ctrl', 'S2_Ctrl', 'S3_Ctrl', 'S4_Treat', 'S5_Treat', 'S6_Treat']
df_c = pd.DataFrame(counts, columns=samples)
df_c.insert(0, 'gene_id', [f'AT5G{i+10000:05d}' for i in range(10)])
df_c.to_csv(counts_csv, index=False)

df_m = pd.DataFrame({'sample': samples, 'condition': ['Control', 'Control', 'Control', 'Treated', 'Treated', 'Treated']})
df_m.to_csv(meta_csv, index=False)

# 2. Setup FASTQ only file
fq_id = "audit_fq_only_fixture"
fastq_path = uploads_dir / f"{fq_id}.fastq"
fastq_path.write_text("@READ1\nAGCT\n+\nIIII\n", encoding="utf-8")

cases = [
    {
        "case_num": 1,
        "question": "Compare treated vs control and identify significantly different genes.",
        "file_id": mat_id,
        "description": "Full DE query with valid count matrix + metadata"
    },
    {
        "case_num": 2,
        "question": "Do PCA to see whether my samples cluster by condition.",
        "file_id": mat_id,
        "description": "PCA-only query with valid count matrix"
    },
    {
        "case_num": 3,
        "question": "Run differential expression between treated and control.",
        "file_id": mat_id,
        "description": "Explicit DE query"
    },
    {
        "case_num": 4,
        "question": "Show me a heatmap of the most differentially expressed genes.",
        "file_id": mat_id,
        "description": "Heatmap / DE visual query"
    },
    {
        "case_num": 5,
        "question": "Perform differential expression on my raw FASTQ reads",
        "file_id": fq_id,
        "description": "FASTQ-only dataset requesting differential expression"
    },
    {
        "case_num": 6,
        "question": "Run PCA and differential expression analysis",
        "file_id": "non_existent_file_id_999",
        "description": "Request requiring unavailable inputs"
    },
    {
        "case_num": 7,
        "question": "Analyze the weather.",
        "file_id": mat_id,
        "description": "Unrelated / unsupported out-of-scope query"
    }
]

audit_results = []

for c in cases:
    job = orchestrator.create_job(file_id=c["file_id"], user_question=c["question"])
    sp = job.structured_plan

    attempted = False
    exec_status = None
    exec_errors = []

    if sp.is_valid:
        attempted = True
        try:
            executed_job = orchestrator.execute_job(job.analysis_id)
            exec_status = executed_job.status.value
            exec_errors = executed_job.errors
        except Exception as e:
            exec_status = "exception"
            exec_errors = [str(e)]
    else:
        # Attempt execute_job to verify clean failure handling
        attempted = True
        try:
            executed_job = orchestrator.execute_job(job.analysis_id)
            exec_status = executed_job.status.value
            exec_errors = executed_job.errors
        except Exception as e:
            exec_status = "exception"
            exec_errors = [str(e)]

    audit_entry = {
        "case_num": c["case_num"],
        "description": c["description"],
        "original_question": c["question"],
        "interpreted_intent": sp.interpreted_intent,
        "analysis_goal": sp.analysis_goal,
        "required_inputs": [i.model_dump() for i in sp.required_inputs],
        "selected_steps": sp.selected_steps,
        "step_rationales": [r.model_dump() for r in sp.step_rationales],
        "expected_artifacts": [a.model_dump() for a in sp.expected_artifacts],
        "is_valid": sp.is_valid,
        "validation_errors": sp.validation_errors,
        "execution_attempted": attempted,
        "execution_status": exec_status,
        "execution_errors": exec_errors
    }
    audit_results.append(audit_entry)

with open('/tmp/planner_robustness_audit.json', 'w') as f:
    json.dump(audit_results, f, indent=2)

print("AUDIT_COMPLETE")
