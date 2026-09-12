import os
import sys
import io
from pathlib import Path

# Ensure TMPDIR environment variable compatibility
os.environ["TMPDIR"] = "/home/kriti/tmp"
sys.path.insert(0, "/home/kriti/rna-seq-ai-agent")

from fastapi.testclient import TestClient
from api.main import app

from pipeline.read_pairing import parse_fastq_read_pairs
from pipeline.schemas.project_schemas import LayoutType, Project, SampleManifest, Sample, ExperimentalDesign, WorkspaceState
from pipeline.input_validation import ExperimentDesignValidator
from pipeline.project_manager import ProjectManager

client = TestClient(app)

print("==================================================")
print("RUNNING MULTI-SAMPLE FASTQ UPLOAD TEST SUITE")
print("==================================================")

# 1. One single-end FASTQ -> 1 sample
print("\n[TEST 1] 1 single-end FASTQ -> 1 sample")
s1, e1 = parse_fastq_read_pairs([Path("sampleA.fastq.gz")])
assert len(s1) == 1 and not e1
assert s1[0].sample_id == "sampleA" and s1[0].layout == LayoutType.SINGLE
print("✓ Passed!")

# 2. R1 + R2 -> 1 paired-end sample
print("\n[TEST 2] R1 + R2 -> 1 paired-end sample")
s2, e2 = parse_fastq_read_pairs([Path("sampleA_R1.fastq.gz"), Path("sampleA_R2.fastq.gz")])
assert len(s2) == 1 and not e2
assert s2[0].sample_id == "sampleA" and s2[0].layout == LayoutType.PAIRED
assert s2[0].fastq_r1_path.endswith("sampleA_R1.fastq.gz")
assert s2[0].fastq_r2_path.endswith("sampleA_R2.fastq.gz")
print("✓ Passed!")

# 3. 3 paired-end biological samples -> 3 samples
print("\n[TEST 3] 3 paired-end biological samples -> 3 samples")
pe_files = [
    Path("c1_R1.fq.gz"), Path("c1_R2.fq.gz"),
    Path("c2_R1.fq.gz"), Path("c2_R2.fq.gz"),
    Path("t1_R1.fq.gz"), Path("t1_R2.fq.gz")
]
s3, e3 = parse_fastq_read_pairs(pe_files)
assert len(s3) == 3 and not e3
assert [s.sample_id for s in s3] == ["c1", "c2", "t1"]
assert all(s.layout == LayoutType.PAIRED for s in s3)
print("✓ Passed!")

# 4. 6 single-end FASTQs -> 6 samples
print("\n[TEST 4] 6 single-end FASTQs -> 6 samples")
se_files = [Path(f"sample{i}.fastq") for i in range(1, 7)]
s4, e4 = parse_fastq_read_pairs(se_files)
assert len(s4) == 6 and not e4
assert all(s.layout == LayoutType.SINGLE for s in s4)
print("✓ Passed!")

# 5. Multiple samples with metadata -> valid experiment
print("\n[TEST 5] Multiple samples with metadata -> valid experiment")
proj5 = Project(
    project_id="PROJ_TEST5",
    name="Test 5",
    origin="LOCAL_FASTQ",
    organism="Arabidopsis thaliana",
    manifest=SampleManifest(
        organism="Arabidopsis thaliana",
        samples=[
            Sample(sample_id="c1", condition="Control"),
            Sample(sample_id="c2", condition="Control"),
            Sample(sample_id="t1", condition="Treated"),
            Sample(sample_id="t2", condition="Treated")
        ]
    ),
    design=ExperimentalDesign(factors={"condition": ["Control", "Treated"]}, reference_levels={"condition": "Control"})
)
val5, errs5 = ExperimentDesignValidator.validate_experiment_design(proj5, require_deg=True)
assert val5 and not errs5
print("✓ Passed!")

# 6. Missing metadata for DEG -> structured validation failure
print("\n[TEST 6] Missing metadata for DEG -> structured validation failure")
proj6 = Project(
    project_id="PROJ_TEST6",
    name="Test 6",
    origin="LOCAL_FASTQ",
    organism="Arabidopsis thaliana",
    manifest=SampleManifest(
        organism="Arabidopsis thaliana",
        samples=[
            Sample(sample_id="c1", condition="UNRESOLVED"),
            Sample(sample_id="c2", condition="UNRESOLVED")
        ]
    ),
    design=ExperimentalDesign()
)
val6, errs6 = ExperimentDesignValidator.validate_experiment_design(proj6, require_deg=True)
assert not val6 and any("condition metadata missing" in e for e in errs6)
print(f"✓ Passed! Validation error caught: {errs6[0]}")

# 7. One biological sample -> DEG refused
print("\n[TEST 7] 1 biological sample -> DEG refused")
proj7 = Project(
    project_id="PROJ_TEST7",
    name="Test 7",
    origin="LOCAL_FASTQ",
    organism="Arabidopsis thaliana",
    manifest=SampleManifest(
        organism="Arabidopsis thaliana",
        samples=[Sample(sample_id="c1", condition="Control")]
    ),
    design=ExperimentalDesign()
)
val7, errs7 = ExperimentDesignValidator.validate_experiment_design(proj7, require_deg=True)
assert not val7 and any("at least 2 biological samples" in e for e in errs7)
print(f"✓ Passed! Refusal reason caught: {errs7[0]}")

# 8. One group only -> comparison refused
print("\n[TEST 8] 1 group only -> comparison refused")
proj8 = Project(
    project_id="PROJ_TEST8",
    name="Test 8",
    origin="LOCAL_FASTQ",
    organism="Arabidopsis thaliana",
    manifest=SampleManifest(
        organism="Arabidopsis thaliana",
        samples=[
            Sample(sample_id="c1", condition="Control"),
            Sample(sample_id="c2", condition="Control"),
            Sample(sample_id="c3", condition="Control")
        ]
    ),
    design=ExperimentalDesign()
)
val8, errs8 = ExperimentDesignValidator.validate_experiment_design(proj8, require_deg=True)
assert not val8 and any("at least 2 distinct condition groups" in e for e in errs8)
print(f"✓ Passed! Refusal reason caught: {errs8[0]}")

# 9. Ambiguous R1/R2 pairing -> validation failure
print("\n[TEST 9] Ambiguous R1/R2 pairing -> validation failure")
s9, errs9 = parse_fastq_read_pairs([Path("sampleX_R2.fastq.gz")])
assert len(errs9) > 0 and any("Unmatched R2" in e for e in errs9)
print(f"✓ Passed! Ambiguity error caught: {errs9[0]}")

# 10. Metadata sample mismatch -> validation failure
print("\n[TEST 10] Metadata sample mismatch -> validation failure")
pm = ProjectManager()
p10_id = "PROJ_TEST10"
proj10 = None
try:
    proj10 = pm.get_project(p10_id)
except Exception:
    proj10 = None

if not proj10:
    pm.create_project(
        project_id=p10_id,
        name="Test 10",
        origin="LOCAL_FASTQ",
        organism="Arabidopsis thaliana",
        manifest=SampleManifest(organism="Arabidopsis thaliana", samples=[Sample(sample_id="c1", condition="UNRESOLVED")]),
        design=ExperimentalDesign()
    )
try:
    pm.assign_sample_metadata(p10_id, [{"sample_id": "nonexistent_sample", "condition": "Treated"}])
    assert False, "Expected ValueError for sample ID mismatch"
except ValueError as ve:
    assert "does not match any uploaded sample" in str(ve)
    print(f"✓ Passed! Mismatch caught: {str(ve)}")

# 11. Duplicate sample IDs -> validation failure
print("\n[TEST 11] Duplicate sample IDs -> validation failure")
proj11 = Project(
    project_id="PROJ_TEST11",
    name="Test 11",
    origin="LOCAL_FASTQ",
    organism="Arabidopsis thaliana",
    manifest=SampleManifest(
        organism="Arabidopsis thaliana",
        samples=[
            Sample(sample_id="c1", condition="Control"),
            Sample(sample_id="c1", condition="Treated")
        ]
    ),
    design=ExperimentalDesign()
)
val11, errs11 = ExperimentDesignValidator.validate_experiment_design(proj11)
assert not val11 and any("Duplicate sample IDs" in e for e in errs11)
print(f"✓ Passed! Duplicate error caught: {errs11[0]}")

# 12. Provenance preserves sample/file relationships
print("\n[TEST 12] Provenance preserves sample/file relationships")
s12, _ = parse_fastq_read_pairs([Path("sampleP_R1.fq"), Path("sampleP_R2.fq")])
assert s12[0].fastq_r1_path == "sampleP_R1.fq" and s12[0].fastq_r2_path == "sampleP_R2.fq"
print("✓ Passed! R1/R2 paths correctly preserved in Sample model.")

# 13. Single-file upload backward compatibility
print("\n[TEST 13] Single-file upload backward compatibility (POST /qc)")
fastq_content = b"@seq1\nACGTACGTACGTACGT\n+\nHHHHHHHHHHHHHHHH\n"
res13 = client.post("/qc", files=[("files", ("single_sample.fastq", io.BytesIO(fastq_content), "application/octet-stream"))])
assert res13.status_code == 200, f"Expected 200, got {res13.status_code}: {res13.text}"
d13 = res13.json()
assert d13["status"] == "completed" and d13["samples_count"] == 1
print("✓ Passed! Single-file upload returns HTTP 200 OK.")

# 14. Multi-file paired-end upload + Metadata assignment endpoint
print("\n[TEST 14] Multi-file paired-end upload + Metadata CSV assignment")
files14 = [
    ("files", ("ctrl1_R1.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("ctrl1_R2.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("treat1_R1.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", ("treat1_R2.fastq", io.BytesIO(fastq_content), "application/octet-stream")),
]
res14 = client.post("/qc", files=files14)
assert res14.status_code == 200, f"Expected 200, got {res14.status_code}: {res14.text}"
d14 = res14.json()
assert d14["samples_count"] == 2 and len(d14["files"]) == 4
pid14 = d14["project_id"]

# Assign metadata via CSV endpoint
csv_content = b"sample_id,condition\nctrl1,Control\ntreat1,Treatment\n"
res_meta = client.post(f"/api/v1/projects/{pid14}/metadata/csv", files={"file": ("meta.csv", io.BytesIO(csv_content), "text/csv")})
assert res_meta.status_code == 200, f"Expected 200, got {res_meta.status_code}: {res_meta.text}"
d_meta = res_meta.json()
assert d_meta["workspace_state"]["is_ready_for_deseq2"] == True
print("✓ Passed! Multi-file upload + metadata CSV assignment executed cleanly.")

# 15. Exact GLDS-532 R1/R2 Filename Pattern Pairing (Multiple UUID Prefixes + _R1_raw/_R2_raw Suffix)
print("\n[TEST 15] Exact GLDS-532 R1/R2 Filename Pattern Pairing")
glds532_r1 = Path("3862DEF1-9D01-4D21-AA0C-1DDB3D1346F3_122843a8-e411-4e6b-b96c-774b5df23b55_GLDS-532_rna-seq_GSM6594657_R1_raw.fastq.gz")
glds532_r2 = Path("3862DEF1-9D01-4D21-AA0C-1DDB3D1346F3_122843a8-e411-4e6b-b96c-774b5df23b55_GLDS-532_rna-seq_GSM6594657_R2_raw.fastq.gz")
s15, e15 = parse_fastq_read_pairs([glds532_r1, glds532_r2])
assert len(s15) == 1 and not e15, f"Expected 1 sample, got {len(s15)}: errors={e15}"
assert s15[0].layout == LayoutType.PAIRED, f"Expected PAIRED, got {s15[0].layout}"
assert s15[0].fastq_r1_path == str(glds532_r1), f"Expected R1 path {glds532_r1}, got {s15[0].fastq_r1_path}"
assert s15[0].fastq_r2_path == str(glds532_r2), f"Expected R2 path {glds532_r2}, got {s15[0].fastq_r2_path}"

# Also test POST /qc endpoint with exact GLDS-532 filenames
files15 = [
    ("files", (glds532_r1.name, io.BytesIO(fastq_content), "application/octet-stream")),
    ("files", (glds532_r2.name, io.BytesIO(fastq_content), "application/octet-stream")),
]
res15 = client.post("/qc", files=files15)
assert res15.status_code == 200, f"Expected 200, got {res15.status_code}: {res15.text}"
d15 = res15.json()
assert d15["files_count"] == 2, f"Expected 2 files, got {d15['files_count']}"
assert d15["samples_count"] == 1, f"Expected 1 biological sample, got {d15['samples_count']}"
sample15 = d15["samples"][0]
assert sample15["layout"] == "PAIRED", f"Expected PAIRED layout, got {sample15['layout']}"
assert sample15["fastq_r1_path"] is not None and "GSM6594657_R1_raw" in sample15["fastq_r1_path"]
assert sample15["fastq_r2_path"] is not None and "GSM6594657_R2_raw" in sample15["fastq_r2_path"]
print("✓ Passed! Exact GLDS-532 R1/R2 paired-end sample correctly paired into 1 biological sample with layout=PAIRED and fastq_r2_path populated.")

print("\n==================================================")
print("ALL 15 MULTI-SAMPLE UPLOAD TESTS PASSED SUCCESSFULLY!")
print("==================================================")

