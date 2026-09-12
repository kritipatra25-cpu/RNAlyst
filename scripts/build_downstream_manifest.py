"""
Script to build downstream statistical engine validation manifest for OSD-120
using NASA official GLDS-120_rna_seq_Unnormalized_Counts.csv.
"""

import json
import urllib.request
import pandas as pd
import io
from pathlib import Path

def main():
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)
    manifest_path = out_dir / "glds120_downstream_validation_manifest.json"

    # URL to GLDS-120_rna_seq_Unnormalized_Counts.csv
    count_matrix_url = "https://osdr.nasa.gov/geode-py/ws/studies/OSD-120/download?file=GLDS-120_rna_seq_Unnormalized_Counts.csv&version=1"
    sample_table_url = "https://osdr.nasa.gov/geode-py/ws/studies/OSD-120/download?file=GLDS-120_rna_seq_SampleTable_GLbulkRNAseq.csv&version=1"
    nasa_de_results_url = "https://osdr.nasa.gov/geode-py/ws/studies/OSD-120/download?file=GLDS-120_rna_seq_differential_expression.csv&version=1"

    manifest_data = {
        "validation_type": "DOWNSTREAM STATISTICAL ENGINE VALIDATION — NOT RAW FASTQ VALIDATION",
        "accession": "OSD-120 / GLDS-120",
        "organism": "Arabidopsis thaliana",
        "ecotype": "Col-0",
        "tissue": "Plant Roots",
        "growth_time": "Day 13",
        "treatment_light": "Light Treatment",
        "contrast": {
            "factor_name": "Spaceflight",
            "numerator_level": "Space Flight",
            "reference_level": "Ground Control",
            "design_formula": "~ Spaceflight",
        },
        "gene_id_namespace": "AGI Locus ID (e.g. AT1G01010)",
        "total_genes_in_matrix": 32833,
        "input_count_matrix_url": count_matrix_url,
        "input_sample_table_url": sample_table_url,
        "nasa_reference_de_url": nasa_de_results_url,
        "samples": [
            {
                "sample_id": "Atha_Col-0_root_GC_Alight_Rep1_GSM2493759",
                "gsm_id": "GSM2493759",
                "condition": "Ground Control",
                "group": "Ground Control",
            },
            {
                "sample_id": "Atha_Col-0_root_GC_Alight_Rep2_GSM2493760",
                "gsm_id": "GSM2493760",
                "condition": "Ground Control",
                "group": "Ground Control",
            },
            {
                "sample_id": "Atha_Col-0_root_GC_Alight_Rep3_GSM2493761",
                "gsm_id": "GSM2493761",
                "condition": "Ground Control",
                "group": "Ground Control",
            },
            {
                "sample_id": "Atha_Col-0_root_FLT_Alight_Rep1_GSM2493777",
                "gsm_id": "GSM2493777",
                "condition": "Space Flight",
                "group": "Space Flight",
            },
            {
                "sample_id": "Atha_Col-0_root_FLT_Alight_Rep2_GSM2493778",
                "gsm_id": "GSM2493778",
                "condition": "Space Flight",
                "group": "Space Flight",
            },
            {
                "sample_id": "Atha_Col-0_root_FLT_Alight_Rep3_GSM2493779",
                "gsm_id": "GSM2493779",
                "condition": "Space Flight",
                "group": "Space Flight",
            },
        ],
        "scope_limitations": [
            "Does NOT test FASTQ read quality control (FastQC/fastp)",
            "Does NOT test FASTQ read alignment or pseudo-alignment (Salmon)",
            "Does NOT test read mapping efficiency or transcript abundance generation",
            "Tests strictly count matrix input validation, DESeq2 statistical modeling, LFC shrinkage (apeglm), VST normalization, visualization (PCA, Volcano, Heatmap), and benchmark comparison against NASA published DE results."
        ]
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"Downstream validation manifest saved to: {manifest_path}")

if __name__ == "__main__":
    main()
