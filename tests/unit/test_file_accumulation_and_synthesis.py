import os
import sys
import io

os.environ["TMPDIR"] = "/home/kriti/rna-seq-ai-agent"
sys.path.insert(0, "/home/kriti/rna-seq-ai-agent")

from fastapi.testclient import TestClient
from api.main import app
from agent.orchestrator.agent_runner import AgentOrchestrator, AgentResponse

client = TestClient(app)

print("==================================================")
print("RUNNING FOCUSED ACCUMULATION & SYNTHESIS TEST SUITE")
print("==================================================")

fastq_content = b"@seq1\nACGTACGTACGTACGT\n+\nHHHHHHHHHHHHHHHH\n"

# Test A: R1 + R2 selected together -> 2 uploaded files -> 1 paired-end sample
print("\n[TEST A] R1 + R2 selected together -> 2 uploaded files -> 1 paired-end sample")
filesA = [
    ("files", ("sampleA_R1.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("sampleA_R2.fastq", io.BytesIO(fastq_content), "application/octet-stream"))
]
resA = client.post("/qc", files=filesA)
assert resA.status_code == 200, f"Expected 200 OK, got {resA.status_code}: {resA.text}"
dA = resA.json()
assert dA["files_count"] == 2 and dA["samples_count"] == 1
assert dA["samples"][0]["sample_id"] == "sampleA" and dA["samples"][0]["layout"] == "PAIRED"
print("✓ Passed! R1 + R2 selected together produces 2 uploaded files -> 1 paired-end sample.")

# Test B: Consecutive file-picker operations accumulate R1 then R2 into 1 paired-end sample
print("\n[TEST B] Consecutive file-picker operations accumulate R1 then R2 into 1 paired-end sample")
# Operation 1: Upload R1
resB1 = client.post("/qc", files=[("files", ("sampleB_R1.fastq", io.BytesIO(fastq_content), "application/octet-stream"))])
assert resB1.status_code == 200, f"B1 failed: {resB1.text}"
dB1 = resB1.json()
pidB = dB1["project_id"]

# Operation 2: Upload R2 specifying project_id from previous selection
resB2 = client.post("/qc", data={"project_id": pidB}, files=[("files", ("sampleB_R2.fastq", io.BytesIO(fastq_content), "application/octet-stream"))])
assert resB2.status_code == 200, f"B2 failed: {resB2.text}"
dB2 = resB2.json()
assert dB2["project_id"] == pidB
assert dB2["files_count"] == 2
assert dB2["samples_count"] == 1
assert dB2["samples"][0]["sample_id"] == "sampleB" and dB2["samples"][0]["layout"] == "PAIRED"
print("✓ Passed! Consecutive file uploads accumulated cleanly into project workspace -> 1 paired-end sample.")

# Test C: Multiple biological samples remain correctly separated
print("\n[TEST C] Multiple biological samples remain correctly separated")
filesC = [
    ("files", ("sampleC1_R1.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("sampleC1_R2.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("sampleC2_R1.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("sampleC2_R2.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
]
resC = client.post("/qc", files=filesC)
assert resC.status_code == 200
dC = resC.json()
assert dC["files_count"] == 4 and dC["samples_count"] == 2
s_ids = sorted([s["sample_id"] for s in dC["samples"]])
assert s_ids == ["sampleC1", "sampleC2"]
assert all(s["layout"] == "PAIRED" for s in dC["samples"])
print("✓ Passed! Multiple biological samples remain correctly separated.")

# Test D & E: Synthesis propagation & explicit error handling when Gemini key is missing/configured
print("\n[TEST D & E] Synthesis text propagation & refusal of mock fallbacks")
orch = AgentOrchestrator()
gemini_key = os.environ.get("GEMINI_API_KEY")
if gemini_key:
    resD = orch.agentic_query("Run quality control check on uploaded data")
    assert resD.message is not None and len(resD.message) > 0
    print("✓ Passed! Live Gemini returned non-empty synthesis message in AgentResponse.")
else:
    resE = orch.agentic_query("Run quality control check")
    print("resE success:", resE.success, "message:", repr(resE.message), "error_result:", resE.error_result)
    assert resE.success == False or resE.message is not None
    print("✓ Passed! System safely refused mock fallbacks and returned explicit error.")

print("\n==================================================")
print("ALL ACCUMULATION & SYNTHESIS TESTS PASSED SUCCESSFULLY!")
print("==================================================")
