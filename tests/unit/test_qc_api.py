"""
Unit and Integration Tests for Direct FASTQ File Upload QC Endpoint (POST /qc).

Verifies:
1. POST /qc with valid uncompressed FASTQ file returns HTTP 200 and QC metrics.
2. POST /qc with valid gzipped FASTQ file returns HTTP 200 and QC metrics.
3. POST /qc with unsupported file extension returns HTTP 400.
4. POST /qc with corrupted/invalid FASTQ payload returns HTTP 400.
5. POST /qc with empty file (0 bytes) returns HTTP 400.
6. Existing GET /qc/{file_id} endpoint resolves files uploaded via POST /qc.
7. OpenAPI schema exposes POST /qc with multipart/form-data upload control.
8. /qc and /api/v1/qc prefixes are both functional and consistent.
"""

import gzip
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestQCApiFileUpload(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def create_valid_fastq_bytes(self) -> bytes:
        return (
            "@READ1/1\n"
            "ATGCATGCATGC\n"
            "+\n"
            "IIIIIIIIIIII\n"
            "@READ2/1\n"
            "GCTAGCTAGCTA\n"
            "+\n"
            "IIIIIIIIIIII\n"
        ).encode("utf-8")

    def create_valid_fastq_gz_bytes(self) -> bytes:
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode="wb") as gz:
            gz.write(self.create_valid_fastq_bytes())
        return out.getvalue()

    def test_post_qc_valid_fastq(self):
        """Test POST /qc with valid uncompressed FASTQ file."""
        fastq_content = self.create_valid_fastq_bytes()
        files = {"file": ("sample_test.fastq", fastq_content, "application/octet-stream")}

        res = client.post("/qc", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"].upper(), "COMPLETED")
        self.assertEqual(data["total_reads"], 2)
        self.assertEqual(data["total_bases"], 24)
        self.assertEqual(data["gc_content_pct"], 50.0)
        self.assertEqual(data["quality_status"], "PASS")
        self.assertIn("file_id", data)
        self.assertTrue(data["validation"]["is_valid"])

    def test_post_qc_valid_fastq_gz(self):
        """Test POST /qc with valid gzipped FASTQ file."""
        gz_content = self.create_valid_fastq_gz_bytes()
        files = {"file": ("sample_test.fastq.gz", gz_content, "application/gzip")}

        res = client.post("/qc", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"].upper(), "COMPLETED")
        self.assertEqual(data["total_reads"], 2)
        self.assertEqual(data["quality_status"], "PASS")
        self.assertTrue(data["validation"]["is_gzipped"])

    def test_post_qc_api_v1_prefix(self):
        """Test POST /api/v1/qc prefix works identically."""
        fastq_content = self.create_valid_fastq_bytes()
        files = {"file": ("sample_v1.fastq", fastq_content, "application/octet-stream")}

        res = client.post("/api/v1/qc", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"].upper(), "COMPLETED")

    def test_post_qc_invalid_extension(self):
        """Test POST /qc rejection of non-FASTQ extensions."""
        files = {"file": ("invalid_file.txt", b"some text content", "text/plain")}
        res = client.post("/qc", files=files)

        self.assertEqual(res.status_code, 400)
        self.assertIn("Unsupported file format", res.json()["detail"])

    def test_post_qc_corrupted_fastq(self):
        """Test POST /qc rejection of corrupted FASTQ file."""
        bad_content = b"NOT_A_FASTQ_HEADER\nACGT\nINVALID_STRUCTURE\n"
        files = {"file": ("corrupted.fastq", bad_content, "application/octet-stream")}

        res = client.post("/qc", files=files)
        self.assertEqual(res.status_code, 400)
        self.assertIn("validation failed", res.json()["detail"].lower())

    def test_post_qc_empty_file(self):
        """Test POST /qc rejection of empty 0-byte file."""
        files = {"file": ("empty.fastq", b"", "application/octet-stream")}
        res = client.post("/qc", files=files)

        self.assertEqual(res.status_code, 400)
        self.assertIn("empty", res.json()["detail"].lower())

    def test_get_qc_file_id_backwards_compatibility(self):
        """Test that uploaded files via POST /qc are retrievable via GET /qc/{file_id}."""
        fastq_content = self.create_valid_fastq_bytes()
        files = {"file": ("compat_sample.fastq", fastq_content, "application/octet-stream")}

        post_res = client.post("/qc", files=files)
        self.assertEqual(post_res.status_code, 200)
        post_data = post_res.json()
        file_id = post_data["file_id"]

        get_res = client.get(f"/qc/{file_id}")
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.json()

        self.assertEqual(get_data["status"].upper(), "COMPLETED")
        self.assertEqual(get_data["total_reads"], post_data["total_reads"])
        self.assertEqual(get_data["gc_content_pct"], post_data["gc_content_pct"])

    def test_openapi_schema_multipart_upload_control(self):
        """Verify OpenAPI schema defines POST /qc with multipart/form-data UploadFile parameter."""
        res = client.get("/openapi.json")
        self.assertEqual(res.status_code, 200)
        schema = res.json()

        # Check /qc POST path
        qc_path_post = schema["paths"]["/qc"]["post"]
        self.assertIn("requestBody", qc_path_post)
        content_types = qc_path_post["requestBody"]["content"]
        self.assertIn("multipart/form-data", content_types)

        form_schema = content_types["multipart/form-data"]["schema"]
        # Retrieve referenced schema or properties
        if "$ref" in form_schema:
            ref_name = form_schema["$ref"].split("/")[-1]
            props = schema["components"]["schemas"][ref_name]["properties"]
        else:
            props = form_schema.get("properties", {})

        self.assertIn("file", props)
        file_prop = props["file"]
        # UploadFile property format is binary or type string
        self.assertTrue(
            "anyOf" in file_prop or "oneOf" in file_prop or file_prop.get("format") == "binary" or file_prop.get("type") == "string" or "$ref" in file_prop
        )


if __name__ == "__main__":
    unittest.main()
