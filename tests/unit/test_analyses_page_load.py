import os
import sys

os.environ["TMPDIR"] = "/home/kriti/tmp"
sys.path.insert(0, "/home/kriti/rna-seq-ai-agent")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

print("==================================================")
print("RUNNING ANALYSES PAGE-LOAD ENDPOINT REGRESSION TEST")
print("==================================================")

# 1. Test GET /api/v1/analyses on page load
print("\n[TEST 1] GET /api/v1/analyses on page load")
res = client.get("/api/v1/analyses")
assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"
data = res.json()
assert "analyses" in data, f"Expected 'analyses' in response JSON, got {data}"
assert isinstance(data["analyses"], list), f"Expected list for analyses, got {type(data['analyses'])}"
print("✓ Passed! GET /api/v1/analyses returns HTTP 200 OK with valid list.")

# 2. Test GET /api/v1/analyses/ trailing slash compatibility
print("\n[TEST 2] GET /api/v1/analyses/ with trailing slash")
res_slash = client.get("/api/v1/analyses/")
assert res_slash.status_code == 200, f"Expected 200 OK, got {res_slash.status_code}: {res_slash.text}"
print("✓ Passed! GET /api/v1/analyses/ returns HTTP 200 OK.")

print("\n==================================================")
print("ANALYSES PAGE-LOAD REGRESSION TEST PASSED SUCCESSFULLY!")
print("==================================================")
