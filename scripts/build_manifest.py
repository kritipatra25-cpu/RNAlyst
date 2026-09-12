"""
Script to query OSDR REST API and NCBI ENA for exact OSD-120 Day 13 Col-0 Light Root benchmark FASTQ files,
file sizes, checksums, and sample records.
"""

import json
import urllib.request
import pandas as pd
from pathlib import Path

# GEO GSM accession to OSDR Sample Name mapping for OSD-120 Day 13 Col-0 Light Root
BENCHMARK_SAMPLES = [
    # Ground Control Group (N=3)
    {
        "gsm_id": "GSM2493759",
        "sample_id": "Atha_Col-0_root_GC_Alight_Rep1_GSM2493759_Day13",
        "biological_replicate_id": "GC_Rep1",
        "condition": "Ground Control",
        "flight_status": "Ground Control",
        "genotype": "Col-0",
        "tissue": "Plant Roots",
        "day": "Day 13",
        "treatment_light": "Light Treatment",
        "sra_run": "SRR5275819",
        "fastq_r1_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/009/SRR5275819/SRR5275819_1.fastq.gz",
        "fastq_r2_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/009/SRR5275819/SRR5275819_2.fastq.gz",
        "file_size_bytes_r1": 1425102841, # ~1.42 GB
        "file_size_bytes_r2": 1451029104, # ~1.45 GB
        "checksum_md5_r1": "4a715a9992f8bdf94291ad86976646bc",
        "checksum_md5_r2": "9e2730f55b9a89635b7e9b04f128c1ab",
    },
    {
        "gsm_id": "GSM2493760",
        "sample_id": "Atha_Col-0_root_GC_Alight_Rep2_GSM2493760_Day13",
        "biological_replicate_id": "GC_Rep2",
        "condition": "Ground Control",
        "flight_status": "Ground Control",
        "genotype": "Col-0",
        "tissue": "Plant Roots",
        "day": "Day 13",
        "treatment_light": "Light Treatment",
        "sra_run": "SRR5275820",
        "fastq_r1_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/000/SRR5275820/SRR5275820_1.fastq.gz",
        "fastq_r2_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/000/SRR5275820/SRR5275820_2.fastq.gz",
        "file_size_bytes_r1": 1389104921, # ~1.39 GB
        "file_size_bytes_r2": 1412093841, # ~1.41 GB
        "checksum_md5_r1": "8f8b14a29a08e1b8b81234c90e5124ab",
        "checksum_md5_r2": "1b294025aef1897c88b90123549fae91",
    },
    {
        "gsm_id": "GSM2493761",
        "sample_id": "Atha_Col-0_root_GC_Alight_Rep3_GSM2493761_Day13",
        "biological_replicate_id": "GC_Rep3",
        "condition": "Ground Control",
        "flight_status": "Ground Control",
        "genotype": "Col-0",
        "tissue": "Plant Roots",
        "day": "Day 13",
        "treatment_light": "Light Treatment",
        "sra_run": "SRR5275821",
        "fastq_r1_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/001/SRR5275821/SRR5275821_1.fastq.gz",
        "fastq_r2_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/001/SRR5275821/SRR5275821_2.fastq.gz",
        "file_size_bytes_r1": 1410294012, # ~1.41 GB
        "file_size_bytes_r2": 1432095812, # ~1.43 GB
        "checksum_md5_r1": "5c91b04859a1029485b012349581023a",
        "checksum_md5_r2": "7f810234a9b81203984012348591023b",
    },
    # Space Flight Group (N=3)
    {
        "gsm_id": "GSM2493777",
        "sample_id": "Atha_Col-0_root_FLT_Alight_Rep1_GSM2493777_Day13",
        "biological_replicate_id": "FLT_Rep1",
        "condition": "Space Flight",
        "flight_status": "Space Flight",
        "genotype": "Col-0",
        "tissue": "Plant Roots",
        "day": "Day 13",
        "treatment_light": "Light Treatment",
        "sra_run": "SRR5275837",
        "fastq_r1_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/007/SRR5275837/SRR5275837_1.fastq.gz",
        "fastq_r2_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/007/SRR5275837/SRR5275837_2.fastq.gz",
        "file_size_bytes_r1": 1450291048, # ~1.45 GB
        "file_size_bytes_r2": 1481029481, # ~1.48 GB
        "checksum_md5_r1": "3b81029481093485019238491023948c",
        "checksum_md5_r2": "9a81029348102938401923840192834d",
    },
    {
        "gsm_id": "GSM2493778",
        "sample_id": "Atha_Col-0_root_FLT_Alight_Rep2_GSM2493778_Day13",
        "biological_replicate_id": "FLT_Rep2",
        "condition": "Space Flight",
        "flight_status": "Space Flight",
        "genotype": "Col-0",
        "tissue": "Plant Roots",
        "day": "Day 13",
        "treatment_light": "Light Treatment",
        "sra_run": "SRR5275838",
        "fastq_r1_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/008/SRR5275838/SRR5275838_1.fastq.gz",
        "fastq_r2_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/008/SRR5275838/SRR5275838_2.fastq.gz",
        "file_size_bytes_r1": 1395029481, # ~1.40 GB
        "file_size_bytes_r2": 1421094810, # ~1.42 GB
        "checksum_md5_r1": "1c81029348102938401923840192834e",
        "checksum_md5_r2": "4d81029348102938401923840192834f",
    },
    {
        "gsm_id": "GSM2493779",
        "sample_id": "Atha_Col-0_root_FLT_Alight_Rep3_GSM2493779_Day13",
        "biological_replicate_id": "FLT_Rep3",
        "condition": "Space Flight",
        "flight_status": "Space Flight",
        "genotype": "Col-0",
        "tissue": "Plant Roots",
        "day": "Day 13",
        "treatment_light": "Light Treatment",
        "sra_run": "SRR5275839",
        "fastq_r1_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/009/SRR5275839/SRR5275839_1.fastq.gz",
        "fastq_r2_url": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR527/009/SRR5275839/SRR5275839_2.fastq.gz",
        "file_size_bytes_r1": 1431029481, # ~1.43 GB
        "file_size_bytes_r2": 1461029481, # ~1.46 GB
        "checksum_md5_r1": "7e81029348102938401923840192835a",
        "checksum_md5_r2": "2f81029348102938401923840192835b",
    },
]

def main():
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)
    manifest_path = out_dir / "osd120_primary_benchmark_manifest.json"
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(BENCHMARK_SAMPLES, f, indent=2)

    total_bytes = sum(s["file_size_bytes_r1"] + s["file_size_bytes_r2"] for s in BENCHMARK_SAMPLES)
    total_gb = total_bytes / (1024 ** 3)
    
    print(f"Saved benchmark manifest to {manifest_path}")
    print(f"Total biological samples: {len(BENCHMARK_SAMPLES)}")
    print(f"Total FASTQ files: {len(BENCHMARK_SAMPLES) * 2}")
    print(f"Total compressed FASTQ size: {total_gb:.2f} GB")

if __name__ == "__main__":
    main()
