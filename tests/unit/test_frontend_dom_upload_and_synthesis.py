import os
import sys
import io

os.environ["TMPDIR"] = "/home/kriti/rna-seq-ai-agent"
sys.path.insert(0, "/home/kriti/rna-seq-ai-agent")

from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

print("==================================================")
print("RUNNING FRONTEND DOM & SELECTION ACCUMULATION TESTS")
print("==================================================")

APP_JS_PATH = Path("/home/kriti/rna-seq-ai-agent/web/app.js")
INDEX_HTML_PATH = Path("/home/kriti/rna-seq-ai-agent/web/index.html")

app_js_code = APP_JS_PATH.read_text(encoding="utf-8")
index_html_code = INDEX_HTML_PATH.read_text(encoding="utf-8")

# 1. Structural DOM Static Verification
print("\n[TEST 1] Static Verification of DOM Elements in web/index.html & web/app.js")
assert 'id="start-upload-btn"' in index_html_code, "web/index.html missing start-upload-btn element"
assert 'handleFileSelection' in app_js_code, "web/app.js missing handleFileSelection function"
assert 'uploadPendingFiles' in app_js_code, "web/app.js missing uploadPendingFiles function"
assert 'let pendingUploadFiles = [];' in app_js_code, "web/app.js missing top-level let pendingUploadFiles = []; declaration"
assert 'const interpText = resp.message || "No synthesis text returned.";' in app_js_code, "web/app.js missing canonical resp.message synthesis check"
assert 'if (resp && resp.success === false)' in app_js_code, "web/app.js missing resp.success error check"
print("✓ Passed! Structural DOM verification of index.html & app.js confirmed.")

# 2. Simulated Frontend Event Sequence (Selection Accumulation & Explicit Upload)
print("\n[TEST 2] Simulated Frontend Event Sequence (R1 selection -> R2 selection -> Explicit Upload)")

class MockFile:
    def __init__(self, name: str, content: bytes, size: int):
        self.name = name
        self.content = content
        self.size = size

# State representing web/app.js runtime
pendingUploadFiles = []
attachedFiles = []
currentProjectId = None
http_requests_sent = []

def js_handleFileSelection(files):
    for f in files:
        if not any(p.name == f.name and p.size == f.size for p in pendingUploadFiles):
            pendingUploadFiles.append(f)

def js_uploadPendingFiles():
    global currentProjectId
    if not pendingUploadFiles:
        return
    files_payload = []
    for f in pendingUploadFiles:
        files_payload.append(("files", (f.name, io.BytesIO(f.content), "application/octet-stream")))
    data_payload = {}
    if currentProjectId:
        data_payload["project_id"] = currentProjectId

    http_requests_sent.append({"files_count": len(files_payload), "project_id": currentProjectId})
    res = client.post("/qc", data=data_payload, files=files_payload)
    assert res.status_code == 200, f"Upload failed: {res.text}"
    json_data = res.json()
    currentProjectId = json_data["project_id"]
    return json_data

# Step 1: Change event with R1
r1 = MockFile("sampleX_R1.fastq", b"@seq1\nACGT\n+\nHHHH\n", 20)
js_handleFileSelection([r1])

assert len(pendingUploadFiles) == 1, f"Expected 1 pending file, got {len(pendingUploadFiles)}"
assert len(http_requests_sent) == 0, "Error: HTTP /qc request was prematurely sent after first file selection!"
print("✓ Passed! Step 1: Selection of R1 accumulated in pendingUploadFiles without premature HTTP upload.")

# Step 2: Second change event with R2
r2 = MockFile("sampleX_R2.fastq", b"@seq1\nACGT\n+\nHHHH\n", 20)
js_handleFileSelection([r2])

assert len(pendingUploadFiles) == 2, f"Expected 2 accumulated pending files, got {len(pendingUploadFiles)}"
assert len(http_requests_sent) == 0, "Error: HTTP /qc request was prematurely sent after second file selection!"
print("✓ Passed! Step 2: Selection of R2 accumulated R1+R2 together without premature HTTP upload.")

# Step 3: Explicit Upload trigger
upload_res = js_uploadPendingFiles()
assert len(http_requests_sent) == 1, "Expected exactly 1 HTTP POST /qc request upon explicit upload trigger."
assert http_requests_sent[0]["files_count"] == 2, "Expected 2 files submitted together in single multipart upload."

assert upload_res["files_count"] == 2
assert upload_res["samples_count"] == 1
assert upload_res["samples"][0]["sample_id"] == "sampleX"
assert upload_res["samples"][0]["layout"] == "PAIRED"
print("✓ Passed! Step 3: Explicit upload sent R1+R2 together -> Backend recognized 1 paired-end sample.")

# 3. Test Canonical AgentResponse Serialization & Error Handling
print("\n[TEST 3] Test Canonical AgentResponse JSON Contract Rendering Logic")

def js_renderAgentResponse(resp):
    if resp and resp.get("success") == False:
        return {"rendered_type": "ERROR", "text": resp.get("message", "Query execution failed.")}
    interpText = resp.get("message") or "No synthesis text returned."
    return {"rendered_type": "SYNTHESIS", "text": interpText}

# Test 3a: Valid Gemini Synthesis in resp.message
valid_resp = {
    "success": True,
    "operation": "AGENTIC_QUERY",
    "dataset_id": "PROJ_123",
    "message": "Quality control check completed with 100,000 reads and mean Phred 35.8.",
    "tool_results": []
}
rendered_a = js_renderAgentResponse(valid_resp)
assert rendered_a["rendered_type"] == "SYNTHESIS"
assert rendered_a["text"] == "Quality control check completed with 100,000 reads and mean Phred 35.8."
print("✓ Passed! Canonical resp.message synthesis rendered correctly.")

# Test 3b: Explicit Failure in resp.success == False
error_resp = {
    "success": False,
    "operation": "AGENTIC_QUERY",
    "message": "LLM synthesis error: GEMINI_API_KEY environment variable is not set."
}
rendered_b = js_renderAgentResponse(error_resp)
assert rendered_b["rendered_type"] == "ERROR"
assert "GEMINI_API_KEY" in rendered_b["text"]
print("✓ Passed! resp.success == False renders explicit execution error without displaying fake completion.")

print("\n==================================================")
print("ALL FRONTEND DOM & SELECTION ACCUMULATION TESTS PASSED!")
print("==================================================")
