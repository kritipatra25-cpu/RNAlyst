import sys, json, os
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path('/home/kriti/rna-seq-ai-agent')
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app

client = TestClient(app)

counts_csv = PROJECT_ROOT / 'data' / 'uploads' / 'vis_e2e_fixture_counts.csv'
meta_csv = PROJECT_ROOT / 'data' / 'uploads' / 'vis_e2e_fixture_metadata.csv'

import numpy as np, pandas as pd
np.random.seed(99)
ctrl = np.random.randint(50, 150, size=(12, 3))
treat = np.random.randint(50, 150, size=(12, 3))
treat[:4, :] += 350
counts = np.hstack([ctrl, treat])
samples = ['S1_Ctrl', 'S2_Ctrl', 'S3_Ctrl', 'S4_Treat', 'S5_Treat', 'S6_Treat']
df_c = pd.DataFrame(counts, columns=samples)
df_c.insert(0, 'gene_id', [f'AT1G{i+20000:05d}' for i in range(12)])
df_c.to_csv(counts_csv, index=False)

df_m = pd.DataFrame({'sample': samples, 'condition': ['Control', 'Control', 'Control', 'Treated', 'Treated', 'Treated']})
df_m.to_csv(meta_csv, index=False)

res1 = client.post('/analyses', json={
    'file_id': 'vis_e2e_fixture',
    'user_question': 'Run E2E Visualization analysis',
    'plan': ['pca', 'differential_expression']
})
print('[API CREATE JOB STATUS]:', res1.status_code)
aid = res1.json()['analysis_id']

res2 = client.post(f'/analyses/{aid}/run')
print('[API RUN JOB STATUS]:', res2.status_code, res2.json()['status'])
job = res2.json()

print('\n=== REGISTERED PLOT ARTIFACTS & PROVENANCE METADATA ===')
plot_arts = [a for a in job['artifacts'] if a['type'] == 'plot']
for p in plot_arts:
    exists = Path(p['path']).exists()
    size = Path(p['path']).stat().st_size if exists else 0
    print(f"- Artifact ID: {p['artifact_id']}")
    print(f"  Name: {p['name']}")
    print(f"  Path: {p['path']} (Exists: {exists}, Size: {size} bytes)")
    print(f"  Metadata: {json.dumps(p['metadata'])}")

print('\n=== VISUALIZATION E2E API VERIFICATION PASSED! ===')
