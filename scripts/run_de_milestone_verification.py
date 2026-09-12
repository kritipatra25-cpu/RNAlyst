import sys
import io
import json
import os
import unittest
import numpy as np
import pandas as pd
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path('/home/kriti/rna-seq-ai-agent')
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from pipeline.job_models import AnalysisJob, JobStatus, StepStatus, ArtifactType
from pipeline.orchestrator import AnalysisOrchestrator

client = TestClient(app)
orchestrator = AnalysisOrchestrator()

results = {}

# ---------------------------------------------------------
# 1 & 2. Identify Test/Fixture Files
# ---------------------------------------------------------
uploads_dir = PROJECT_ROOT / 'data' / 'uploads'
fixture_counts_path = uploads_dir / 'verify_de_e2e_spec_counts.csv'
fixture_meta_path = uploads_dir / 'verify_de_e2e_spec_metadata.csv'

np.random.seed(42)
ctrl_c = np.random.randint(40, 180, size=(15, 3))
treat_c = np.random.randint(40, 180, size=(15, 3))
# Top 4 genes strongly upregulated
treat_c[:4, :] += 350
counts_matrix = np.hstack([ctrl_c, treat_c])
samples = ['S1_Ctrl', 'S2_Ctrl', 'S3_Ctrl', 'S4_Treat', 'S5_Treat', 'S6_Treat']

df_counts = pd.DataFrame(counts_matrix, columns=samples)
df_counts.insert(0, 'gene_id', [f'AT1G{i+10000:05d}' for i in range(15)])
df_counts.to_csv(fixture_counts_path, index=False)

df_meta = pd.DataFrame({
    'sample': samples,
    'condition': ['Control', 'Control', 'Control', 'Treated', 'Treated', 'Treated']
})
df_meta.to_csv(fixture_meta_path, index=False)

results['item1_2_fixtures'] = {
    'count_matrix': str(fixture_counts_path),
    'sample_metadata': str(fixture_meta_path),
    'exists': fixture_counts_path.exists() and fixture_meta_path.exists(),
    'pass': fixture_counts_path.exists() and fixture_meta_path.exists()
}

# ---------------------------------------------------------
# 3. Complete Test Suite Execution
# ---------------------------------------------------------
loader = unittest.TestLoader()
suite = loader.discover(str(PROJECT_ROOT / 'tests'), pattern='test_*.py')
runner = unittest.TextTestRunner(verbosity=0)
test_res = runner.run(suite)

results['item3_test_suite'] = {
    'tests_run': test_res.testsRun,
    'failures': len(test_res.failures),
    'errors': len(test_res.errors),
    'pass': test_res.wasSuccessful()
}

# ---------------------------------------------------------
# 4. Explicit E2E DE API Test
# ---------------------------------------------------------
# Step 4a: POST /analyses
res_create = client.post('/analyses', json={
    'file_id': 'verify_de_e2e_spec',
    'user_question': 'Run DE verification test',
    'plan': ['pca', 'differential_expression']
})
status_create = res_create.status_code
analysis_id = res_create.json().get('analysis_id') if status_create == 201 else None

# Step 4b: POST /analyses/{id}/run
res_run = client.post(f'/analyses/{analysis_id}/run') if analysis_id else None
status_run = res_run.status_code if res_run else None

# Step 4c: GET /analyses/{id}/status
res_stat = client.get(f'/analyses/{analysis_id}/status') if analysis_id else None
status_stat = res_stat.status_code if res_stat else None

# Step 4d: GET /analyses/{id}/artifacts
res_arts = client.get(f'/analyses/{analysis_id}/artifacts') if analysis_id else None
status_arts = res_arts.status_code if res_arts else None

pass_api = (status_create == 201) and (status_run == 200) and (status_stat == 200) and (status_arts == 200)

results['item4_e2e_api_test'] = {
    'create_status': status_create,
    'run_status': status_run,
    'get_status_code': status_stat,
    'get_artifacts_code': status_arts,
    'analysis_id': analysis_id,
    'pass': pass_api
}

# ---------------------------------------------------------
# 5. Confirm Actual Execution Trace of DE Step
# ---------------------------------------------------------
job_status_payload = res_stat.json() if res_stat else {}
de_step_trace = next((s for s in job_status_payload.get('steps', []) if s['step'] == 'differential_expression'), {})

exec_confirmed = (
    de_step_trace.get('status') == 'completed' and
    de_step_trace.get('started_at') is not None and
    de_step_trace.get('completed_at') is not None and
    'completed successfully' in de_step_trace.get('message', '')
)

results['item5_actual_execution'] = {
    'step_status': de_step_trace.get('status'),
    'started_at': de_step_trace.get('started_at'),
    'completed_at': de_step_trace.get('completed_at'),
    'message': de_step_trace.get('message'),
    'pass': exec_confirmed
}

# ---------------------------------------------------------
# 6. Confirm Physical Artifact Existence in data/artifacts/
# ---------------------------------------------------------
artifacts_payload = res_arts.json().get('artifacts', []) if res_arts else []
de_json_art = next((a for a in artifacts_payload if 'de_summary' in a['name']), None)
de_csv_art = next((a for a in artifacts_payload if 'de_results' in a['name']), None)

json_exists = de_json_art is not None and Path(de_json_art['path']).exists() and Path(de_json_art['path']).stat().st_size > 0
csv_exists = de_csv_art is not None and Path(de_csv_art['path']).exists() and Path(de_csv_art['path']).stat().st_size > 0

results['item6_physical_artifacts'] = {
    'de_json_artifact': de_json_art['path'] if de_json_art else None,
    'de_json_exists': json_exists,
    'de_csv_artifact': de_csv_art['path'] if de_csv_art else None,
    'de_csv_exists': csv_exists,
    'pass': json_exists and csv_exists
}

# ---------------------------------------------------------
# 7. Report Gene Metrics (Total, Significant, Up, Down)
# ---------------------------------------------------------
de_summary_data = {}
if de_json_art and json_exists:
    with open(de_json_art['path']) as f:
        de_summary_data = json.load(f)

tot_genes = de_summary_data.get('total_genes', 0)
sig_genes = de_summary_data.get('significant_genes', 0)
up_genes = de_summary_data.get('upregulated_genes', 0)
down_genes = de_summary_data.get('downregulated_genes', 0)

results['item7_gene_metrics'] = {
    'total_genes': tot_genes,
    'significant_genes': sig_genes,
    'upregulated_genes': up_genes,
    'downregulated_genes': down_genes,
    'contrast': de_summary_data.get('contrast'),
    'pass': tot_genes == 15 and sig_genes >= 1
}

# ---------------------------------------------------------
# 8. Verify Table Schema (baseMean, log2FoldChange, pvalue, padj/FDR)
# ---------------------------------------------------------
has_schema_cols = False
if de_csv_art and csv_exists:
    df_res_csv = pd.read_csv(de_csv_art['path'])
    req_cols = ['gene_id', 'baseMean', 'log2FoldChange', 'pvalue', 'padj', 'significant']
    has_schema_cols = all(col in df_res_csv.columns for col in req_cols)

results['item8_schema_verification'] = {
    'required_columns': ['gene_id', 'baseMean', 'log2FoldChange', 'pvalue', 'padj', 'significant'],
    'has_required_columns': has_schema_cols,
    'pass': has_schema_cols
}

# ---------------------------------------------------------
# 9. Verify FASTQ-Only Failure Guardrail
# ---------------------------------------------------------
# Upload FASTQ only (no matrix/meta)
fastq_text = "@READ_1\nAGCTAGCTAGCT\n+\nIIIIIIIIIIII\n"
res_up = client.post(
    '/ingestion/upload',
    files={'file': ('fastq_only_test.fastq', io.BytesIO(fastq_text.encode('utf-8')), 'application/octet-stream')}
)
fastq_id = res_up.json().get('file_id')

res_fq_job = client.post('/analyses', json={'file_id': fastq_id, 'plan': ['differential_expression']})
aid_fq = res_fq_job.json().get('analysis_id')

res_fq_run = client.post(f'/analyses/{aid_fq}/run')
job_fq = res_fq_run.json()

fq_guardrail_pass = (
    res_fq_run.status_code == 200 and
    job_fq.get('status') == 'failed' and
    'Differential expression requires a gene-by-sample count matrix' in job_fq.get('errors', [''])[0]
)

results['item9_fastq_guardrail'] = {
    'fastq_file_id': fastq_id,
    'job_status': job_fq.get('status'),
    'error_message': job_fq.get('errors', [''])[0],
    'pass': fq_guardrail_pass
}

with open('/tmp/de_milestone_verification_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("DE_VERIFICATION_COMPLETE")
