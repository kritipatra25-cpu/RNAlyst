"""Unit tests for scientific guardrails validation gates."""
import unittest
from pipeline.schemas.input_schemas import SampleSheetInput, SampleMetadata, LayoutType
from scientific_guardrails.validators import run_pre_analysis_guardrails, ScientificGuardrailError
from scientific_guardrails.claim_guardrails import validate_ai_claim_text


class TestScientificGuardrails(unittest.TestCase):

    def test_biological_replicates_gate_n1(self):
        sheet = SampleSheetInput(
            organism="Arabidopsis thaliana",
            layout=LayoutType.PAIRED,
            samples=[
                SampleMetadata(sample_id="S1", biological_unit_id="B1", condition="ctrl"),
                SampleMetadata(sample_id="S2", biological_unit_id="B2", condition="treat")
            ],
            fastq_files={"S1": ["r1.fq", "r2.fq"], "S2": ["r1.fq", "r2.fq"]},
            reference_group="ctrl",
            comparison_group="treat"
        )
        status, warnings = run_pre_analysis_guardrails(sheet)
        self.assertEqual(status, "EXPLORATORY")
        self.assertTrue(any("N=1" in w for w in warnings))

    def test_batch_confounding_gate(self):
        sheet = SampleSheetInput(
            organism="Homo sapiens",
            layout=LayoutType.PAIRED,
            samples=[
                SampleMetadata(sample_id="S1", biological_unit_id="B1", condition="ctrl", batch="batch1"),
                SampleMetadata(sample_id="S2", biological_unit_id="B2", condition="ctrl", batch="batch1"),
                SampleMetadata(sample_id="S3", biological_unit_id="B3", condition="ctrl", batch="batch1"),
                SampleMetadata(sample_id="S4", biological_unit_id="B4", condition="treat", batch="batch2"),
                SampleMetadata(sample_id="S5", biological_unit_id="B5", condition="treat", batch="batch2"),
                SampleMetadata(sample_id="S6", biological_unit_id="B6", condition="treat", batch="batch2"),
            ],
            fastq_files={"S1": ["r1.fq"], "S2": ["r1.fq"], "S3": ["r1.fq"], "S4": ["r1.fq"], "S5": ["r1.fq"], "S6": ["r1.fq"]},
            reference_group="ctrl",
            comparison_group="treat"
        )
        with self.assertRaises(ScientificGuardrailError) as ctx:
            run_pre_analysis_guardrails(sheet)
        self.assertIn("treatment effect not identifiable", str(ctx.exception).lower())

    def test_ai_claim_guardrails(self):
        invalid_text = "This gene is activated and proves causality of the phenotype."
        is_valid, rejections = validate_ai_claim_text(invalid_text)
        self.assertFalse(is_valid)
        self.assertGreaterEqual(len(rejections), 1)

        valid_text = "Expression of CRY1 increased with shrunken log2FC = 2.1 (padj = 0.002)."
        is_valid_2, rejections_2 = validate_ai_claim_text(valid_text)
        self.assertTrue(is_valid_2)
        self.assertEqual(len(rejections_2), 0)


if __name__ == "__main__":
    unittest.main()

