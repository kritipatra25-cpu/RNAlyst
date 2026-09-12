import urllib.request
import json

def test_api():
    print("1. Testing GET /api/v1/projects...")
    req = urllib.request.Request("http://localhost:8000/api/v1/projects")
    with urllib.request.urlopen(req) as resp:
        print("Status:", resp.status)
        data = json.loads(resp.read().decode())
        print("Projects count:", len(data))

    print("\n2. Testing GET /api/v1/analyses...")
    req = urllib.request.Request("http://localhost:8000/api/v1/analyses")
    with urllib.request.urlopen(req) as resp:
        print("Status:", resp.status)
        data = json.loads(resp.read().decode())
        print("Analyses response:", data)

    print("\n3. Testing POST /api/v1/query with missing prerequisites...")
    payload = json.dumps({"query": "Generate volcano plot for project UNKNOWN_PROJECT_999"}).encode()
    req = urllib.request.Request("http://localhost:8000/api/v1/query", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        print("Status:", resp.status)
        data = json.loads(resp.read().decode())
        print("Operation:", data.get("operation"))
        print("Success:", data.get("success"))
        print("Response Message:\n", data.get("message"))

if __name__ == "__main__":
    test_api()
