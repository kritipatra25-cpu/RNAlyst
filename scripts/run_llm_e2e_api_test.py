import sys, json
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path('/home/kriti/rna-seq-ai-agent')
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from pipeline.llm_provider import MockLLMProvider
from pipeline.orchestrator import AnalysisOrchestrator

# Initialize client and orchestrator with MockLLMProvider
llm = MockLLMProvider(mode="standard")
orchestrator = AnalysisOrchestrator(llm_provider=llm)

client = TestClient(app)

# Setup E2E fixture
uploads_dir = PROJECT_ROOT / 'data' / 'uploads'
file_id = "llm_e2e_api_fixture"
counts_csv = uploads_dir / f"{file_id}_counts.csv"
meta_csv = uploads_dir / f"{file_id}_metadata.csv"

import numpy as np, pandas as pd
np.random.seed(42)
ctrl = np.random.randint(50, 150, size=(10, 3))
treat = np.random.randint(50, 150, size=(10, 3))
treat[:3, :] += 300
counts = np.hstack([ctrl, treat])
samples = ['S1_Ctrl', 'S2_Ctrl', 'S3_Ctrl', 'S4_Treat', 'S5_Treat', 'S6_Treat']
df_c = pd.DataFrame(counts, columns=samples)
df_c.insert(0, 'gene_id', [f'AT4G{i+10000:05d}' for i in range(10)])
df_c.to_csv(counts_csv, index=False)

df_m = pd.DataFrame({'sample': samples, 'condition': ['Control', 'Control', 'Control', 'Treated', 'Treated', 'Treated']})
df_m.to_csv(meta_csv, index=False)

# 1. Create job using Orchestrator with LLM Provider
question = "Compare treated vs control and find significantly different genes."
job = orchestrator.create_job(file_id=file_id, user_question=question)

print('[CREATE JOB SUCCESS]: Analysis ID =', job.analysis_id)
sp = job.structured_plan

print('\n=== AUTHORITATIVE STRUCTURED ANALYSIS PLAN ===')
print('User Question:', sp.user_question)
print('Canonical Intent:', sp.interpreted_intent)
print('Analysis Goal:', sp.analysis_goal)
print('Is Valid:', sp.is_valid)
print('Validation Errors:', sp.validation_errors)
print('Selected Steps:', sp.selected_steps)

print('\n=== RESOLVED INPUT SPECS ===')
for inp in sp.required_inputs:
    print(f"- Type: {inp.input_type}, Available: {inp.is_available}, Path: {inp.resolved_path}")

print('\n=== STEP RATIONALES ===')
for rat in sp.step_rationales:
    print(f"- Step: {rat.step} -> {rat.rationale}")

# 2. Execute job
executed_job = orchestrator.execute_job(job.analysis_id)
print('\n[EXECUTE JOB STATUS]:', executed_job.status.value)
print('Artifacts Generated:', len(executed_job.artifacts))
for art in executed_job.artifacts:
    print(f"  * Artifact: {art.name} ({art.type}) -> {art.path}")

assert executed_job.status.value == "completed"
assert len(executed_job.artifacts) >= 4
print('\n=== E2E LLM PLANNER INTEGRATION PASSED SUCCESSFULLY! ===')
