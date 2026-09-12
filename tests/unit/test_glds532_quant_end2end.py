import os
import json
import shutil
import unittest
import pandas as pd
from pathlib import Path
from pipeline.project_manager import ProjectManager
from pipeline.nextflow_runner import NextflowRunner
from agent.tools.ingestion_tools import QuantifyReadsTool


class TestGLDS532QuantEnd2End(unittest.TestCase):

    def test_glds532_quantification(self):
        pm = ProjectManager()
        proj_id = "GLDS-532"

        proj_uploads = pm.projects_dir / proj_id / "data" / "uploads"
        proj_uploads.mkdir(parents=True, exist_ok=True)

        # Clean existing proj_uploads if any old duplicates remain
        for old in proj_uploads.glob("*"):
            if old.is_file() or old.is_symlink():
                old.unlink()

        source_uploads = Path("data/uploads")
        # Pick exact single paired FASTQ set
        r1_src = source_uploads / "A19DBFE0-A5A2-43B7-8348-D0D06748B8E8_GLDS-532_rna-seq_GSM6594657_R1_raw.fastq.gz"
        r2_src = source_uploads / "A19DBFE0-A5A2-43B7-8348-D0D06748B8E8_GLDS-532_rna-seq_GSM6594657_R2_raw.fastq.gz"

        for src in [r1_src, r2_src]:
            if src.exists():
                dest = proj_uploads / src.name
                try:
                    os.symlink(src.resolve(), dest)
                except Exception:
                    shutil.copy2(src, dest)

        project = pm.auto_derive_manifest_from_uploads(proj_id)

        self.assertEqual(project.project_id, "GLDS-532")
        self.assertGreaterEqual(project.manifest.total_samples, 1)

        s0 = project.manifest.samples[0]
        self.assertIsNotNone(s0.fastq_r1_path)
        self.assertIsNotNone(s0.fastq_r2_path)

        sample_ids = [s.sample_id for s in project.manifest.samples]
        proj_dir = pm.projects_dir / proj_id
        reads_dir = str(proj_dir / "data" / "uploads")
        out_dir = str(proj_dir)

        # Execute Nextflow / Salmon runner
        nf_runner = NextflowRunner()
        quant_map = nf_runner.run_pipeline(
            project_id=proj_id,
            sample_ids=sample_ids,
            reads_dir=reads_dir,
            output_dir=out_dir
        )

        self.assertIn(s0.sample_id, quant_map)
        quant_dir = Path(quant_map[s0.sample_id])
        sf_file = quant_dir / "quant.sf"
        self.assertTrue(sf_file.exists())

        # Aggregate counts matrix
        quant_tool = QuantifyReadsTool(projects_dir=str(pm.projects_dir))
        res = quant_tool.run({
            "project_id": proj_id,
            "quant_directories": quant_map
        })

        self.assertEqual(res.status, "success")
        counts_csv = Path(res.result["counts_matrix_path"])
        self.assertTrue(counts_csv.exists())

        df_counts = pd.read_csv(counts_csv)
        self.assertIn("gene_id", df_counts.columns)
        self.assertIn(s0.sample_id, df_counts.columns)
        self.assertGreater(len(df_counts), 0)


if __name__ == "__main__":
    unittest.main()
