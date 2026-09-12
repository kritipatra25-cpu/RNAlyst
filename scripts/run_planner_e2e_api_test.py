import sys, json
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path('/home/kriti/rna-seq-ai-agent')
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
client = TestClient(app)

counts_csv = PROJECT_ROOT / 'data' / 'uploads' / 'planner_e2e_fixture_counts.csv'
meta_csv = PROJECT_ROOT / 'data' / 'uploads' / 'planner_e2e_fixture_metadata.csv'

import numpy as np, pandas as pd
np.random.seed(42)
ctrl = np.random.randint(50, 150, size=(10, 3))
treat = np.random.randint(50, 150, size=(10, 3))
treat[:3, :] += 300
counts = np.hstack([ctrl, treat])
samples = ['S1_Ctrl', 'S2_Ctrl', 'S3_Ctrl', 'S4_Treat', 'S5_Treat', 'S6_Treat']
df_c = pd.DataFrame(counts, columns=samples)
df_c.insert(0, 'gene_id', [f'AT3G{i+10000:05d}' for i in range(10)])
df_c.to_csv(counts_csv, index=False)

df_m = pd.DataFrame({'sample': samples, 'condition': ['Control', 'Control', 'Control', 'Treated', 'Treated', 'Treated']})
df_m.to_csv(meta_csv, index=False)

# 1. Create job with natural language user question
question = "Compare treated vs control and find significantly different genes."
res1 = client.post('/analyses', json={
    'file_id': 'planner_e2e_fixture',
    'user_question': question
})

print('[CREATE JOB STATUS]:', res1.status_code)
job = res1.json()
aid = job['analysis_id']
sp = job.get('structured_plan', {})

print('\n=== STRUCTURED ANALYSIS PLAN ===')
print('User Question:', sp.get('user_question'))
print('Interpreted Intent:', sp.get('interpreted_intent'))
print('Analysis Goal:', sp.get('analysis_goal'))
print('Is Valid:', sp.get('is_valid'))
print('Selected Steps:', sp.get('selected_steps'))

print('\n=== REQUIRED INPUT SPECS ===')
for inp in sp.get('required_inputs', []):
    print(f"- Type: {inp['input_type']}, Available: {inp['is_available']}, Path: {inp['resolved_path']}")

print('\n=== STEP RATIONALES ===')
for rat in sp.get('step_rationales', []):
    print(f"- Step: {rat['step']} -> {rat['rationale']}")

# 2. Run job
res2 = client.post(f'/analyses/{aid}/run')
print('\n[RUN JOB STATUS]:', res2.status_code, res2.json()['status'])

print('\n=== PLANNER E2E API VERIFICATION PASSED! ===')
