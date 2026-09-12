import urllib.request
import re
import os

geo_url = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE94nnn/GSE94983/suppl/"
print(f"Priority 3: Checking NCBI GEO GSE94983 FTP directory: {geo_url}")

try:
    req = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
    files = re.findall(r'href="(GSE94983[^"]+)"', html)
    print("Found GEO Supplementary Files:", files)
    
    found_de = False
    for f in files:
        file_url = geo_url + f
        print(f"Attempting download: {file_url}")
        dreq = urllib.request.Request(file_url, headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(dreq, timeout=15).read()
        out_path = os.path.join(r"c:\Users\USER\.gemini\antigravity\scratch\rna-seq-ai-agent\data", f)
        with open(out_path, "wb") as out_f:
            out_f.write(content)
        print(f"Successfully downloaded: {out_path} ({len(content)} bytes)")
        found_de = True
    if not found_de:
        print("No supplementary files found in GEO directory.")
except Exception as e:
    print(f"GEO FTP check failed: {e}")
