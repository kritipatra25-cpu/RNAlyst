import sys
import io
import json
import os
import unittest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

PROJECT_ROOT = Path('/home/kriti/rna-seq-ai-agent')
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
client = TestClient(app)

results = {}

# 1. Run complete unit test suite
loader = unittest.TestLoader()
suite = loader.discover(str(PROJECT_ROOT / 'tests'), pattern='test_*.py')
runner = unittest.TextTestRunner(verbosity=0)
test_res = runner.run(suite)

results['unit_tests'] = {
    'command': "wsl /home/kriti/rna-seq-ai-agent/.venv/bin/python -m unittest discover -s /home/kriti/rna-seq-ai-agent/tests -p 'test_*.py'",
    'tests_run': test_res.testsRun,
    'failures': len(test_res.failures),
    'errors': len(test_res.errors),
    'passed': test_res.testsRun - len(test_res.failures) - len(test_res.errors),
    'success': test_res.wasSuccessful()
}

# 2. Run E2E API lifecycle test for FASTQ QC + Count Matrix PCA/DE plots
# 2a. FASTQ Upload & QC Plot job
fastq_content = "@READ_1\nAGCTAGCTAGCTAGCT\n+\nIIIIIIIIIIIIIIII\n@READ_2\nAGCTAGCTAGCTAGCT\n+\nIIIIIIIIIIIIIIII\n"
res_up_fq = client.post(
    '/ingestion/upload',
    files={'file': ('vis_audit_test.fastq', io.BytesIO(fastq_content.encode('utf-8')), 'application/octet-stream')}
)
fq_id = res_up_fq.json()['file_id']

res_fq_job = client.post('/analyses', json={'file_id': fq_id, 'plan': ['validating_dataset']})
aid_fq = res_fq_job.json()['analysis_id']
res_fq_run = client.post(f'/analyses/{aid_fq}/run')
job_fq = res_fq_run.json()

# 2b. Count Matrix + Metadata PCA & DE plots job
counts_csv = PROJECT_ROOT / 'data' / 'uploads' / 'vis_audit_fixture_counts.csv'
meta_csv = PROJECT_ROOT / 'data' / 'uploads' / 'vis_audit_fixture_metadata.csv'

import numpy as np, pandas as pd
np.random.seed(101)
ctrl = np.random.randint(50, 150, size=(10, 3))
treat = np.random.randint(50, 150, size=(10, 3))
treat[:3, :] += 300
counts = np.hstack([ctrl, treat])
samples = ['S1_Ctrl', 'S2_Ctrl', 'S3_Ctrl', 'S4_Treat', 'S5_Treat', 'S6_Treat']
df_c = pd.DataFrame(counts, columns=samples)
df_c.insert(0, 'gene_id', [f'AT2G{i+10000:05d}' for i in range(10)])
df_c.to_csv(counts_csv, index=False)

df_m = pd.DataFrame({'sample': samples, 'condition': ['Control', 'Control', 'Control', 'Treated', 'Treated', 'Treated']})
df_m.to_csv(meta_csv, index=False)

res_mat_job = client.post('/analyses', json={'file_id': 'vis_audit_fixture', 'plan': ['pca', 'differential_expression']})
aid_mat = res_mat_job.json()['analysis_id']
res_mat_run = client.post(f'/analyses/{aid_mat}/run')
job_mat = res_mat_run.json()

results['e2e_api_lifecycle'] = {
    'command': "POST /analyses -> POST /analyses/{id}/run -> GET /analyses/{id}/artifacts",
    'qc_job_id': aid_fq,
    'qc_job_status': job_fq.get('status'),
    'matrix_job_id': aid_mat,
    'matrix_job_status': job_mat.get('status'),
}

# 3. Verify physical PNG artifacts and PIL Image parsing
all_artifacts = job_fq.get('artifacts', []) + job_mat.get('artifacts', [])
png_artifacts = [a for a in all_artifacts if a['type'] == 'plot']

png_audit = []
for art in png_artifacts:
    path = Path(art['path'])
    exists = path.exists()
    size = path.stat().st_size if exists else 0

    valid_png = False
    format_name = None
    image_size = None

    if exists and size > 0:
        try:
            with Image.open(path) as img:
                img.verify()
                valid_png = True
                format_name = img.format
                image_size = img.size
        except Exception as e:
            valid_png = False

    png_audit.append({
        'artifact_id': art['artifact_id'],
        'name': art['name'],
        'step': art['step'],
        'path': str(path),
        'exists': exists,
        'size_bytes': size,
        'valid_png': valid_png,
        'format': format_name,
        'dimensions': image_size,
        'metadata': art.get('metadata', {})
    })

results['png_artifacts_audit'] = png_audit

with open('/tmp/vis_audit_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("VIS_AUDIT_COMPLETE")
