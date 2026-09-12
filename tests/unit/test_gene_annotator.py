"""
Unit tests for Multi-Species Gene Annotation Boundary (analysis/annotation/gene_annotator.py).
"""

import unittest
import pandas as pd

from analysis.annotation.gene_annotator import (
    GeneAnnotator,
    TAIR10AnnotationProvider,
    MouseGENCODEAnnotationProvider,
    ConfigMapAnnotationProvider,
)
from analysis.interpretation.candidate_prioritizer import CandidatePrioritizer
from pipeline.config_parser import DatasetConfig, CandidateSelectionConfig, ContrastConfig


class TestGeneAnnotator(unittest.TestCase):
    """Test suite for GeneAnnotator and species-specific annotation providers."""

    def test_tair10_provider_defaults(self):
        provider = TAIR10AnnotationProvider()
        self.assertEqual(provider.organism, "Arabidopsis thaliana")
        self.assertEqual(provider.annotation_source, "TAIR10")
        self.assertEqual(provider.get_symbol("AT1G01010"), "ANAC001")
        self.assertEqual(provider.get_symbol("AT3G17609"), "HYH")
        self.assertEqual(provider.get_symbol("AT9G99999"), "VALID TAIR ID — NO SYMBOL AVAILABLE")

    def test_mouse_gencode_provider(self):
        provider = MouseGENCODEAnnotationProvider()
        self.assertEqual(provider.organism, "Mus musculus")
        self.assertEqual(provider.annotation_source, "GENCODE_M34")
        self.assertEqual(provider.get_symbol("ENSMUSG00000000001"), "Gai2")
        self.assertEqual(provider.get_symbol("ENSMUSG00000000001.4"), "Gai2")
        self.assertEqual(provider.get_symbol("ENSMUSG99999999999"), "ENSMUSG99999999999")

    def test_config_map_provider(self):
        custom_map = {"ENSG00000141510": "TP53", "ENSG00000012048": "BRCA1"}
        provider = ConfigMapAnnotationProvider(
            symbol_map=custom_map,
            organism="Homo sapiens",
            annotation_source="Ensemble_v105"
        )
        self.assertEqual(provider.organism, "Homo sapiens")
        self.assertEqual(provider.get_symbol("ENSG00000141510"), "TP53")
        self.assertEqual(provider.get_symbol("ENSG00000012048"), "BRCA1")
        self.assertEqual(provider.get_symbol("ENSG00000999999"), "ENSG00000999999")

    def test_gene_annotator_factory(self):
        # 1. Arabidopsis Config
        config_tair = DatasetConfig(
            dataset_id="TEST-TAIR",
            organism="Arabidopsis thaliana",
            annotation_source="TAIR10",
            counts_matrix_path="data/osd678/GLDS-612_rna_seq_STAR_Unnormalized_Counts_GLbulkRNAseq.csv",
            sample_metadata_path="data/osd678/osd678_sample_metadata.csv",
            factors={"genotype": ["Col-0"]},
            reference_levels={"genotype": "Col-0"},
            contrasts=[ContrastConfig(id="c1", factor="genotype", numerator="Col-0", denominator="Col-0")]
        )
        annotator_tair = GeneAnnotator.from_config(config_tair)
        self.assertIsInstance(annotator_tair.provider, TAIR10AnnotationProvider)
        self.assertEqual(annotator_tair.get_symbol("AT1G01010"), "ANAC001")

        # 2. Mouse Config
        config_mouse = DatasetConfig(
            dataset_id="TEST-MOUSE",
            organism="Mus musculus",
            annotation_source="GENCODE_M34",
            counts_matrix_path="data/osd678/GLDS-612_rna_seq_STAR_Unnormalized_Counts_GLbulkRNAseq.csv",
            sample_metadata_path="data/osd678/osd678_sample_metadata.csv",
            factors={"genotype": ["WT"]},
            reference_levels={"genotype": "WT"},
            contrasts=[ContrastConfig(id="c1", factor="genotype", numerator="WT", denominator="WT")]
        )
        annotator_mouse = GeneAnnotator.from_config(config_mouse)
        self.assertIsInstance(annotator_mouse.provider, MouseGENCODEAnnotationProvider)
        self.assertEqual(annotator_mouse.get_symbol("ENSMUSG00000000001"), "Gai2")

    def test_candidate_prioritizer_integration(self):
        # Verify CandidatePrioritizer works with default TAIR10 GeneAnnotator
        cp_default = CandidatePrioritizer()
        self.assertEqual(cp_default.get_symbol("AT1G01010"), "ANAC001")

        # Verify CandidatePrioritizer works with custom Mouse GeneAnnotator
        mouse_annotator = GeneAnnotator(
            organism="Mus musculus",
            annotation_source="GENCODE_M34"
        )
        cp_mouse = CandidatePrioritizer(annotator=mouse_annotator)
        self.assertEqual(cp_mouse.get_symbol("ENSMUSG00000000001"), "Gai2")


if __name__ == "__main__":
    unittest.main()
