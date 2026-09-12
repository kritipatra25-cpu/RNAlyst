import sys
import io
import json
import os
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path('/home/kriti/rna-seq-ai-agent')
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api.routes.qc import find_uploaded_file

client = TestClient(app)

reports = []

def record(stage, endpoint, inp, status, resp, artifact, loc, passed):
    reports.append({
        'stage': stage,
        'endpoint': endpoint,
        'input': inp,
        'http_status': status,
        'response': resp,
        'artifact': artifact,
        'filesystem_location': loc,
        'passed': passed
    })

# 1. FASTQ Upload
fastq_content = "@READ1\nAGCTAGCTAGCT\n+\nIIIIIIIIIIII\n@READ2\nGCTAGCTAGCTA\n+\nIIIIIIIIIIII\n"
res1 = client.post(
    '/ingestion/upload',
    files={'file': ('stage1_test.fastq', io.BytesIO(fastq_content.encode('utf-8')), 'application/octet-stream')}
)
p1 = res1.status_code == 200 and 'file_id' in res1.json()
file_id = res1.json().get('file_id') if p1 else None
filename = res1.json().get('filename') if p1 else None
record('1. FASTQ Upload', 'POST /ingestion/upload', {'filename': 'stage1_test.fastq'}, res1.status_code, res1.json(), 'FASTQ file', f'data/uploads/{filename}' if p1 else None, p1)

# 2. file_id Resolution
try:
    resolved_path = find_uploaded_file(file_id) if file_id else None
    p2 = resolved_path is not None and resolved_path.exists()
    record('2. file_id Resolution', 'find_uploaded_file()', {'file_id': file_id}, 200 if p2 else 404, {'resolved_path': str(resolved_path)}, 'FASTQ file', str(resolved_path), p2)
except Exception as e:
    p2 = False
    record('2. file_id Resolution', 'find_uploaded_file()', {'file_id': file_id}, 404, {'error': str(e)}, None, None, False)

# 3. QC Execution
res3 = client.get(f'/qc/{file_id}')
p3 = res3.status_code == 200 and res3.json().get('status') == 'completed'
record('3. QC Execution', f'GET /qc/{file_id}', {'file_id': file_id}, res3.status_code, res3.json(), 'QC JSON payload', 'API endpoint response payload', p3)

# 4. AnalysisJob Creation
res4 = client.post('/analyses', json={'file_id': file_id, 'user_question': 'Run FASTQ QC', 'plan': ['validating_dataset', 'qc']})
p4 = res4.status_code == 201 and 'analysis_id' in res4.json()
analysis_id = res4.json().get('analysis_id') if p4 else None
record('4. AnalysisJob Creation', 'POST /analyses', {'file_id': file_id, 'plan': ['validating_dataset', 'qc']}, res4.status_code, res4.json(), 'AnalysisJob JSON', f'data/jobs/{analysis_id}.json' if p4 else None, p4)

# 5. AnalysisJob Execution (QC Plan)
res5 = client.post(f'/analyses/{analysis_id}/run')
p5 = res5.status_code == 200 and res5.json().get('status') == 'completed'
record('5. AnalysisJob Execution (QC)', f'POST /analyses/{analysis_id}/run', {'analysis_id': analysis_id}, res5.status_code, res5.json(), 'qc_summary.json', f'data/artifacts/{analysis_id}_qc_summary.json' if p5 else None, p5)

# 6. PCA Execution (Expression Matrix)
matrix_path = PROJECT_ROOT / 'data' / 'uploads' / 'stage6_matrix_counts.csv'
matrix_path.parent.mkdir(parents=True, exist_ok=True)
with open(matrix_path, 'w') as f:
    f.write('gene_id,Control1,Control2,Treat1,Treat2\nACTB,100,110,105,115\nGAPDH,500,520,510,530\nTP53,10,15,80,95\nMYC,5,8,40,48\n')

res6_create = client.post('/analyses', json={'file_id': 'stage6_matrix', 'plan': ['pca']})
aid6 = res6_create.json().get('analysis_id') if res6_create.status_code == 201 else None
res6_run = client.post(f'/analyses/{aid6}/run') if aid6 else None
p6 = res6_run is not None and res6_run.status_code == 200 and res6_run.json().get('status') == 'completed'
record('6. PCA Execution (Matrix)', f'POST /analyses/{aid6}/run', {'file_id': 'stage6_matrix', 'plan': ['pca']}, res6_run.status_code if res6_run else 500, res6_run.json() if res6_run else {}, 'pca_results.json & pca_plot.png', f'data/artifacts/{aid6}_pca_results.json', p6)

# 7. PCA Artifact Generation
json_art = PROJECT_ROOT / 'data' / 'artifacts' / f'{aid6}_pca_results.json'
png_art = PROJECT_ROOT / 'data' / 'artifacts' / f'{aid6}_pca_plot.png'
p7 = json_art.exists() and png_art.exists() and json_art.stat().st_size > 0 and png_art.stat().st_size > 0
record('7. PCA Artifact Generation', 'File system audit', {'analysis_id': aid6}, 200 if p7 else 404, {'json_exists': json_art.exists(), 'png_exists': png_art.exists()}, 'PCA JSON & PNG files', f'{json_art} and {png_art}', p7)

# 8. Artifact Retrieval
res8 = client.get(f'/analyses/{aid6}/artifacts')
p8 = res8.status_code == 200 and len(res8.json()) == 2
record('8. Artifact Retrieval', f'GET /analyses/{aid6}/artifacts', {'analysis_id': aid6}, res8.status_code, res8.json(), 'Artifact list', 'API endpoint payload', p8)

# 9. Missing Matrix PCA Failure Guardrail
res9_create = client.post('/analyses', json={'file_id': file_id, 'plan': ['pca']})
aid9 = res9_create.json().get('analysis_id') if res9_create.status_code == 201 else None
res9_run = client.post(f'/analyses/{aid9}/run') if aid9 else None
p9 = res9_run is not None and res9_run.status_code == 200 and res9_run.json().get('status') == 'failed'
record('9. PCA Missing Matrix Guardrail', f'POST /analyses/{aid9}/run', {'file_id': file_id, 'plan': ['pca']}, res9_run.status_code if res9_run else 500, res9_run.json() if res9_run else {}, 'Error trace', f'data/jobs/{aid9}.json', p9)

with open('/tmp/e2e_verification_report.json', 'w') as f:
    json.dump(reports, f, indent=2)

print("E2E_VERIFICATION_COMPLETE")
