"""
Unit tests for pipeline/osdr_client.py
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import pandas as pd
from pipeline.osdr_client import NASAOSDRClient

class TestNASAOSDRClient(unittest.TestCase):

    def setUp(self):
        self.client = NASAOSDRClient()
        self.mock_metadata = {
            "title": "Genetic dissection of the Arabidopsis spaceflight transcriptome",
            "samples": {
                "table": [
                    {
                        "Sample Name": "Atha_Col-0_root_GC_Alight_Rep1_GSM2493759_Day13",
                        "Factor Value[Ecotype]": "Col-0",
                        "Factor Value[Spaceflight]": "Ground Control",
                        "Factor Value[Treatment]": "Light Treatment",
                        "Parameter Value[Growth Time]": "13",
                        "Characteristics[organism part]": "Plant Roots"
                    },
                    {
                        "Sample Name": "Atha_Col-0_root_FLT_Alight_Rep1_GSM2493777_Day13",
                        "Factor Value[Ecotype]": "Col-0",
                        "Factor Value[Spaceflight]": "Space Flight",
                        "Factor Value[Treatment]": "Light Treatment",
                        "Parameter Value[Growth Time]": "13",
                        "Characteristics[organism part]": "Plant Roots"
                    }
                ]
            },
            "assays": [
                {
                    "measurementType": "transcription profiling",
                    "technologyType": "RNA-seq",
                    "technologyPlatform": "Illumina NextSeq 500",
                    "dataFiles": [
                        {"name": "sample_r1.fastq.gz", "type": "Raw Data File", "size": 1048576},
                        {"name": "GLDS-120_rna_seq_contrasts_GLbulkRNAseq.csv", "type": "Processed Data", "size": 2048}
                    ],
                    "table": {
                        "table": [
                            {
                                "Parameter Value[library layout]": "PAIRED",
                                "Parameter Value[stranded]": "UNSTRANDED",
                                "Parameter Value[Read Length]": "76"
                            }
                        ]
                    }
                }
            ]
        }

    def test_parse_sample_table(self):
        df = self.client.parse_sample_table(self.mock_metadata)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn("Factor Value[Spaceflight]", df.columns)

    def test_parse_assay_metadata(self):
        assays = self.client.parse_assay_metadata(self.mock_metadata)
        self.assertEqual(len(assays), 1)
        self.assertEqual(assays[0]["library_layout"], "PAIRED")
        self.assertEqual(assays[0]["strandedness"], "UNSTRANDED")

    def test_audit_file_inventory(self):
        inv = self.client.audit_file_inventory(self.mock_metadata)
        self.assertEqual(len(inv["raw_fastq_files"]), 1)
        self.assertEqual(len(inv["contrast_tables"]), 1)
        self.assertEqual(inv["total_raw_size_bytes"], 1048576)

if __name__ == "__main__":
    unittest.main()
