"""
Deterministic FASTQ Read Pairing & Filename Parsing Engine.

Identifies R1/R2 technical read mates from FASTQ filenames without
inferring experimental conditions or biological replicates.
Supports single-end and paired-end data. Produces explicit validation
errors for ambiguous or conflicting file structures.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from pipeline.schemas.project_schemas import Sample, LayoutType


EXTENSIONS = [".fastq.gz", ".fq.gz", ".fastq", ".fq"]

EXPLICIT_R1_SUFFIXES = ["_R1", ".R1", "_r1", ".r1"]
EXPLICIT_R2_SUFFIXES = ["_R2", ".R2", "_r2", ".r2"]

UUID_PREFIX_REGEX = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}_")


def strip_fastq_extensions(filename: str) -> str:
    """Strip FASTQ and compression extensions from a filename."""
    name = Path(filename).name
    lower = name.lower()
    for ext in EXTENSIONS:
        if lower.endswith(ext):
            return name[:-len(ext)]
    return name


def strip_uuid_prefix(name: str) -> str:
    """Strip all leading UUID prefixes from filename stem if present."""
    stem = name
    while UUID_PREFIX_REGEX.match(stem):
        stem = UUID_PREFIX_REGEX.sub("", stem)
    return stem


# Patterns for explicit R1/R2 mate matching with optional trailing qualifiers (e.g. _raw, _001, _trimmed, _val_1)
R1_EXPLICIT_PATTERNS = [
    re.compile(r"^(.*?)[._-][rR]1([._-](?:raw|001|trimmed|val_1|filtered|reads))?$", re.IGNORECASE),
    re.compile(r"^(.*?)[._-](?:1)([._-](?:raw|001|trimmed|val_1|filtered|reads))$", re.IGNORECASE),
]

R2_EXPLICIT_PATTERNS = [
    re.compile(r"^(.*?)[._-][rR]2([._-](?:raw|001|trimmed|val_2|filtered|reads))?$", re.IGNORECASE),
    re.compile(r"^(.*?)[._-](?:2)([._-](?:raw|001|trimmed|val_2|filtered|reads))$", re.IGNORECASE),
]

# Patterns for simple numeric mate matching (_1, _2)
R1_NUMERIC_PATTERNS = [
    re.compile(r"^(.*?)[._-]1$", re.IGNORECASE),
]

R2_NUMERIC_PATTERNS = [
    re.compile(r"^(.*?)[._-]2$", re.IGNORECASE),
]


def parse_fastq_read_pairs(file_paths: List[Path]) -> Tuple[List[Sample], List[str]]:
    """
    Parse a list of FASTQ file paths into biological Sample instances.
    Returns (samples, validation_errors).

    Rules:
    - R1 and R2 from the same sample form ONE biological sample (paired-end).
    - Single FASTQ files without mate suffix form ONE single-end biological sample.
    - Ambiguous pairing (e.g. multiple R1s for same sample, or unmatched R2) produces an explicit validation error.
    - Does NOT infer experimental conditions from filenames.
    """
    if not file_paths:
        return [], ["No FASTQ files provided."]

    errors: List[str] = []

    # Pre-check if any files match explicit R1/R2 mate patterns
    stems = [strip_uuid_prefix(strip_fastq_extensions(p.name)) for p in file_paths]
    has_explicit_r1_r2 = any(
        any(p.match(st) for p in R1_EXPLICIT_PATTERNS + R2_EXPLICIT_PATTERNS)
        for st in stems
    )

    grouped: Dict[str, Dict[str, List[Path]]] = {}

    for path in file_paths:
        raw_stem = strip_fastq_extensions(path.name)
        stem = strip_uuid_prefix(raw_stem)
        explicit_mate = None
        base = stem

        # Try explicit R1 / R2 pattern matching
        for pat in R1_EXPLICIT_PATTERNS:
            m = pat.match(stem)
            if m:
                base = f"{m.group(1)}{m.group(2) or ''}"
                explicit_mate = "r1"
                break

        if not explicit_mate:
            for pat in R2_EXPLICIT_PATTERNS:
                m = pat.match(stem)
                if m:
                    base = f"{m.group(1)}{m.group(2) or ''}"
                    explicit_mate = "r2"
                    break

        numeric_mate = None
        if not explicit_mate and not has_explicit_r1_r2:
            for pat in R1_NUMERIC_PATTERNS:
                m = pat.match(stem)
                if m:
                    base = m.group(1)
                    numeric_mate = "r1"
                    break
            if not numeric_mate:
                for pat in R2_NUMERIC_PATTERNS:
                    m = pat.match(stem)
                    if m:
                        base = m.group(1)
                        numeric_mate = "r2"
                        break

        if base not in grouped:
            grouped[base] = {"r1": [], "r2": [], "unmatched": [], "stems": {}}

        mate = explicit_mate or numeric_mate
        if mate == "r1":
            grouped[base]["r1"].append(path)
        elif mate == "r2":
            grouped[base]["r2"].append(path)
        else:
            grouped[base]["unmatched"].append(path)

        grouped[base]["stems"][path] = stem

    samples: List[Sample] = []
    seen_sample_ids = set()

    for sample_id, mates in sorted(grouped.items()):
        r1_list = mates["r1"]
        r2_list = mates["r2"]
        unmatched_list = mates["unmatched"]

        if not has_explicit_r1_r2 and (len(r1_list) + len(r2_list) + len(unmatched_list) > 2):
            all_paths = r1_list + r2_list + unmatched_list
            for p in all_paths:
                st = mates["stems"][p]
                samples.append(Sample(
                    sample_id=st,
                    condition="UNRESOLVED",
                    layout=LayoutType.SINGLE,
                    fastq_r1_path=str(p),
                    fastq_r2_path=None
                ))
                seen_sample_ids.add(st)
            continue

        if len(r1_list) > 1:
            errors.append(f"Multiple R1 files detected for sample '{sample_id}': {[p.name for p in r1_list]}")
            continue
        if len(r2_list) > 1:
            errors.append(f"Multiple R2 files detected for sample '{sample_id}': {[p.name for p in r2_list]}")
            continue
        if len(r1_list) == 0 and len(r2_list) == 1:
            errors.append(f"Unmatched R2 file detected for sample '{sample_id}': {r2_list[0].name} (missing corresponding R1 file)")
            continue
        if len(r1_list) == 1 and len(r2_list) == 0:
            samples.append(Sample(
                sample_id=sample_id,
                condition="UNRESOLVED",
                layout=LayoutType.SINGLE,
                fastq_r1_path=str(r1_list[0]),
                fastq_r2_path=None
            ))
            seen_sample_ids.add(sample_id)
            continue


        if not r1_list and not r2_list and len(unmatched_list) == 1:
            samples.append(Sample(
                sample_id=sample_id,
                condition="UNRESOLVED",
                layout=LayoutType.SINGLE,
                fastq_r1_path=str(unmatched_list[0]),
                fastq_r2_path=None
            ))
            seen_sample_ids.add(sample_id)
            continue

        if len(r1_list) == 1 and len(r2_list) == 1 and not unmatched_list:
            samples.append(Sample(
                sample_id=sample_id,
                condition="UNRESOLVED",
                layout=LayoutType.PAIRED,
                fastq_r1_path=str(r1_list[0]),
                fastq_r2_path=str(r2_list[0])
            ))
            seen_sample_ids.add(sample_id)
            continue

        if len(unmatched_list) > 1:
            for p in unmatched_list:
                st = mates["stems"][p]
                samples.append(Sample(
                    sample_id=st,
                    condition="UNRESOLVED",
                    layout=LayoutType.SINGLE,
                    fastq_r1_path=str(p),
                    fastq_r2_path=None
                ))
                seen_sample_ids.add(st)

    return samples, errors
