"""
Unit tests for UploadHandler and Sandbox File Validation (Step 2).
"""

import os
import gzip
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.upload_handler import UploadHandler


class TestUploadHandler(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.sandbox_dir = Path(self.tmp_dir) / "uploads"
        self.handler = UploadHandler(sandbox_root=str(self.sandbox_dir))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_sanitize_filename(self):
        """Verify filename sanitization prevents path traversal."""
        clean1 = self.handler.sanitize_filename("sample1.fastq.gz")
        self.assertEqual(clean1, "sample1.fastq.gz")

        clean2 = self.handler.sanitize_filename("../../../etc/passwd")
        self.assertEqual(clean2, "passwd")

        clean3 = self.handler.sanitize_filename("subfolder\\sample2.fastq.gz")
        self.assertEqual(clean3, "sample2.fastq.gz")

    def test_save_uploaded_file(self):
        """Test saving file to project sandbox."""
        content = b"@READ1\nACGT\n+\nIIII\n"
        saved_path = self.handler.save_uploaded_file(
            project_id="PROJ_TEST",
            filename="sample_R1.fastq",
            content_bytes=content
        )

        self.assertTrue(saved_path.exists())
        self.assertEqual(saved_path.parent.name, "PROJ_TEST")
        with open(saved_path, "rb") as f:
            self.assertEqual(f.read(), content)

    def test_validate_uploaded_fastq_gzipped(self):
        """Test FASTQ file validation for valid gzipped file."""
        fastq_content = (
            "@SEQ1/1\nATGCATGCATGC\n+\nIIIIIIIIIIII\n"
            "@SEQ2/1\nGCTAGCTAGCTA\n+\nIIIIIIIIIIII\n"
        ).encode("utf-8")

        gz_path = Path(self.tmp_dir) / "test_valid.fastq.gz"
        with gzip.open(gz_path, "wb") as f:
            f.write(fastq_content)

        val_res = self.handler.validate_uploaded_fastq(gz_path)
        self.assertTrue(val_res["is_valid"])
        self.assertTrue(val_res["is_gzipped"])
        self.assertIsNone(val_res["error"])

    def test_validate_uploaded_fastq_pair(self):
        """Test paired-end FASTQ validation."""
        r1_content = "@READ_1/1\nATGC\n+\nIIII\n".encode("utf-8")
        r2_content = "@READ_1/2\nTACG\n+\nIIII\n".encode("utf-8")

        r1_path = Path(self.tmp_dir) / "r1.fastq.gz"
        r2_path = Path(self.tmp_dir) / "r2.fastq.gz"

        with gzip.open(r1_path, "wb") as f1, gzip.open(r2_path, "wb") as f2:
            f1.write(r1_content)
            f2.write(r2_content)

        res = self.handler.validate_uploaded_fastq_pair(r1_path, r2_path)
        self.assertTrue(res["is_valid"])
        self.assertIsNone(res["error"])

    def test_invalid_fastq_rejection(self):
        """Test rejection of corrupted/invalid FASTQ files."""
        bad_content = b"THIS IS NOT A FASTQ FILE\nJUST RANDOM TEXT\n"
        bad_path = Path(self.tmp_dir) / "bad.fastq"
        with open(bad_path, "wb") as f:
            f.write(bad_content)

        res = self.handler.validate_uploaded_fastq(bad_path)
        self.assertFalse(res["is_valid"])
        self.assertIsNotNone(res["error"])


if __name__ == "__main__":
    unittest.main()
