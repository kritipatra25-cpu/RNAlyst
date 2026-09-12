import os
import sys
import io
from pathlib import Path

os.environ["TMPDIR"] = "/home/kriti/tmp"
sys.path.insert(0, "/home/kriti/rna-seq-ai-agent")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

print("==================================================")
print("RUNNING FOCUSED UPLOAD CONTRACT & R1/R2 PAIRING REGRESSION TESTS")
print("==================================================")

fastq_content = b"@seq1\nACGTACGTACGTACGT\n+\nHHHHHHHHHHHHHHHH\n"

# Test A: POST /qc with single "file" parameter (legacy frontend compatibility)
print("\n[TEST A] POST /qc with single 'file' parameter")
resA = client.post("/qc", files={"file": ("single_sample.fastq", io.BytesIO(fastq_content), "application/octet-stream")})
assert resA.status_code == 200, f"Expected 200 OK, got {resA.status_code}: {resA.text}"
dA = resA.json()
assert dA["status"] == "completed" and dA["samples_count"] == 1
print("✓ Passed! Legacy single 'file' upload returns HTTP 200 OK.")

# Test B: R1 + R2 Upload -> 1 Paired-End Sample (Requirement 6 & 11)
print("\n[TEST B] R1 + R2 Upload -> 1 Paired-End Biological Sample")
filesB = [
    ("files", ("sampleA_R1.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("sampleA_R2.fastq", io.BytesIO(fastq_content), "application/octet-stream"))
]
resB = client.post("/qc", files=filesB)
assert resB.status_code == 200, f"Expected 200 OK, got {resB.status_code}: {resB.text}"
dB = resB.json()

assert dB["files_count"] == 2, f"Expected 2 uploaded files, got {dB['files_count']}"
assert dB["samples_count"] == 1, f"Expected 1 biological sample, got {dB['samples_count']}"

sampleB = dB["samples"][0]
assert sampleB["sample_id"] == "sampleA", f"Expected sample_id 'sampleA', got '{sampleB['sample_id']}'"
assert sampleB["layout"] == "PAIRED", f"Expected layout 'PAIRED', got '{sampleB['layout']}'"
assert sampleB["condition"] == "UNRESOLVED", f"Expected condition 'UNRESOLVED' (no inferred metadata), got '{sampleB['condition']}'"
assert sampleB["fastq_r1_path"] is not None and "sampleA_R1.fastq" in sampleB["fastq_r1_path"]
assert sampleB["fastq_r2_path"] is not None and "sampleA_R2.fastq" in sampleB["fastq_r2_path"]

print("✓ Passed! R1 + R2 correctly recognized as ONE paired-end biological sample without inferred metadata.")

# Test C: Multiple Biological Samples Distinction (Requirement 12)
print("\n[TEST C] Multiple Biological Samples Distinction (2 paired-end samples = 4 files)")
filesC = [
    ("files", ("sampleA_R1.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("sampleA_R2.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("sampleB_R1.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("sampleB_R2.fastq", io.BytesIO(fastq_content), "application/octet-stream"))
]
resC = client.post("/qc", files=filesC)
assert resC.status_code == 200, f"Expected 200 OK, got {resC.status_code}: {resC.text}"
dC = resC.json()

assert dC["files_count"] == 4, f"Expected 4 uploaded files, got {dC['files_count']}"
assert dC["samples_count"] == 2, f"Expected 2 distinct biological samples, got {dC['samples_count']}"

sample_ids = sorted([s["sample_id"] for s in dC["samples"]])
assert sample_ids == ["sampleA", "sampleB"], f"Expected samples ['sampleA', 'sampleB'], got {sample_ids}"
assert all(s["layout"] == "PAIRED" for s in dC["samples"])

print("✓ Passed! Multiple biological samples remain distinct and correctly paired.")

print("\n==================================================")
print("ALL UPLOAD CONTRACT & R1/R2 REGRESSION TESTS PASSED SUCCESSFULLY!")
print("==================================================")
