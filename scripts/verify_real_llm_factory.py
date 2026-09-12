import sys
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

PROJECT_ROOT = Path('/home/kriti/rna-seq-ai-agent')
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.llm_factory import LLMProviderFactory
from pipeline.llm_provider import OpenAILLMProvider, GeminiLLMProvider, MockLLMProvider
from pipeline.planner import AnalysisPlanner

print("=== VERIFYING LLM PROVIDER FACTORY ===")
p_none = LLMProviderFactory.get_provider("none")
print("Provider 'none':", p_none)
assert p_none is None

p_mock = LLMProviderFactory.get_provider("mock")
print("Provider 'mock':", type(p_mock).__name__)
assert isinstance(p_mock, MockLLMProvider)

p_openai = LLMProviderFactory.get_provider("openai", api_key="sk-fake")
print("Provider 'openai':", type(p_openai).__name__)
assert isinstance(p_openai, OpenAILLMProvider)

p_gemini = LLMProviderFactory.get_provider("gemini", api_key="gm-fake")
print("Provider 'gemini':", type(p_gemini).__name__)
assert isinstance(p_gemini, GeminiLLMProvider)

print("\n=== MOCKED OPENAI API EXECUTION THROUGH PLANNER ===")
uploads_dir = PROJECT_ROOT / "data" / "uploads"
file_id = "real_llm_verif_fixture"

import pandas as pd
pd.DataFrame({"gene_id": ["G1"], "C1": [10], "T1": [100]}).to_csv(uploads_dir / f"{file_id}_counts.csv", index=False)
pd.DataFrame({"sample": ["C1", "T1"], "condition": ["Control", "Treated"]}).to_csv(uploads_dir / f"{file_id}_metadata.csv", index=False)

with patch("urllib.request.urlopen") as mock_urlopen:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "choices": [{
            "message": {
                "content": json.dumps({
                    "proposed_goal": "Perform DE on treated vs control",
                    "proposed_steps": ["pca", "differential_expression"],
                    "suggested_intent": "DIFFERENTIAL_EXPRESSION",
                    "reasoning": "User asked for DE analysis"
                })
            }
        }]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    planner = AnalysisPlanner(uploads_dir=uploads_dir, llm_provider=p_openai)
    plan = planner.create_analysis_plan(
        file_id=file_id,
        user_question="Compare treated vs control and find DE genes"
    )

    print("Plan Valid:", plan.is_valid)
    print("Canonical Intent:", plan.interpreted_intent)
    print("Selected Steps:", plan.selected_steps)
    assert plan.is_valid is True
    assert "differential_expression" in plan.selected_steps

print("\n=== REAL LLM FACTORY VERIFICATION SUCCESSFUL! ===")
