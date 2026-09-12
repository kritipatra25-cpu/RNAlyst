from pipeline.read_pairing import parse_fastq_read_pairs
"""
Dataset-Agnostic RNA-Seq Project Manager.

Provides project lifecycle management: project creation, JSON state persistence,
directory initialization, and automatic generation of dataset YAML configurations
for seamless registration with RNASeqBackendAPI.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import pandas as pd

from pipeline.schemas.project_schemas import (
    Project,
    SampleManifest,
    ExperimentalDesign,
    Reference,
    DataOrigin,
    LayoutType,
    Sample,
    ContrastSpec,
    Artifact,
    Provenance
)

logger = logging.getLogger(__name__)


class ProjectManager:
    """Manager for dataset-agnostic RNA-seq projects and workspace state."""

    def __init__(self, projects_dir: str = "projects", configs_dir: str = "configs"):
        self.projects_dir = Path(projects_dir).resolve()
        self.configs_dir = Path(configs_dir).resolve()
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.configs_dir.mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        project_id: str,
        name: str,
        origin: DataOrigin,
        organism: str,
        manifest: SampleManifest,
        design: ExperimentalDesign,
        reference: Optional[Reference] = None
    ) -> Project:
        """Initialize a new RNA-seq project, directory layout, and project.json manifest."""
        clean_id = project_id.strip().upper()
        if " " in clean_id:
            raise ValueError(f"Invalid project_id '{project_id}': spaces are not allowed.")

        proj_dir = self.projects_dir / clean_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "data").mkdir(exist_ok=True)
        (proj_dir / "results").mkdir(exist_ok=True)
        (proj_dir / "qc").mkdir(exist_ok=True)

        # Build default reference if not provided
        if reference is None:
            reference = Reference(
                organism=organism,
                transcriptome_fasta=str(proj_dir / "data" / "transcriptome.fasta"),
                tx2gene_csv=str(proj_dir / "data" / "tx2gene.csv"),
                salmon_index_dir=str(proj_dir / "data" / "salmon_index"),
                version_build="DEFAULT_BUILD"
            )

        project = Project(
            project_id=clean_id,
            name=name,
            origin=origin,
            organism=organism,
            manifest=manifest,
            design=design,
            reference=reference
        )

        self.save_project(project)
        self.generate_dataset_yaml(clean_id)
        logger.info("Created project %s at %s", clean_id, proj_dir)
        return project

    def auto_derive_manifest_from_uploads(self, project_id: str) -> Project:
        """
        Scans projects/<project_id>/data/uploads for uploaded FASTQ files,
        derives sample IDs and paired-end structure from filenames, checks
        for OSDR/GLDS metadata accessions, and populates project manifest.
        If OSDR metadata is absent, organism and contrast parameters are left
        UNRESOLVED without biological metadata fabrication.
        """
        clean_id = project_id.strip().upper()
        try:
            project = self.get_project(clean_id)
        except Exception:
            project = self.create_project(
                project_id=clean_id,
                name=f"Project Workspace ({clean_id})",
                origin=DataOrigin.LOCAL_FASTQ,
                organism="Custom Organism",
                manifest=SampleManifest(organism="Custom Organism", layout=LayoutType.PAIRED, samples=[]),
                design=ExperimentalDesign(factors={"condition": ["control", "treatment"]}, reference_levels={"condition": "control"})
            )
        uploads_dir = self.projects_dir / clean_id / "data" / "uploads"

        if not uploads_dir.exists():
            return project

        fastq_files = sorted([
            p for p in uploads_dir.rglob("*")
            if p.is_file() and any(p.name.endswith(ext) for ext in [".fastq.gz", ".fq.gz", ".fastq", ".fq"])
        ])

        if not fastq_files:
            return project

        parsed_samples, pairing_errors = parse_fastq_read_pairs(fastq_files)
        if pairing_errors:
            logger.warning("Read pairing errors for project %s: %s", project_id, pairing_errors)

        # Preserve existing conditions if already set
        existing_conds = {s.sample_id: s.condition for s in project.manifest.samples}
        samples = []
        is_paired = False

        for ps in parsed_samples:
            if ps.sample_id in existing_conds and existing_conds[ps.sample_id] != "UNRESOLVED":
                ps.condition = existing_conds[ps.sample_id]
            if ps.layout == LayoutType.PAIRED:
                is_paired = True
            samples.append(ps)

        project.manifest.samples = samples
        project.manifest.total_samples = len(samples)
        project.manifest.layout = LayoutType.PAIRED if is_paired else LayoutType.SINGLE

        # Check OSDR/GLDS accession in project name or title
        import re
        acc_match = re.search(r"(OSD-\d+|GLDS-\d+)", f"{project.project_id} {project.name}", re.IGNORECASE)
        if acc_match:
            try:
                from pipeline.osdr_client import NASAOSDRClient
                client = NASAOSDRClient()
                osd_id = acc_match.group(1).upper()
                meta = client.fetch_study_metadata(osd_id)
                df_meta = client.parse_sample_table(meta)
                if not df_meta.empty and "organism" in df_meta.columns:
                    project.organism = df_meta["organism"].iloc[0]
                    project.manifest.organism = project.organism
            except Exception as e:
                logger.warning("OSDR metadata lookup for %s failed: %s", project.project_id, e)

        if project.organism == "UNRESOLVED" or any(s.condition == "UNRESOLVED" for s in samples):
            project.workspace_state.is_ready_for_deseq2 = False
            project.workspace_state.unresolved_reason = "Experimental contrast configuration required before differential expression"

        self.save_project(project)
        self.generate_dataset_yaml(clean_id)
        return project

    def get_project(self, project_id: str) -> Project:
        """Load and parse project state from projects/<project_id>/project.json."""
        clean_id = project_id.strip().upper()
        json_path = self.projects_dir / clean_id / "project.json"

        if not json_path.exists():
            raise FileNotFoundError(f"Project '{clean_id}' not found at {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Project.model_validate(data)

    def save_project(self, project: Project) -> Path:
        """Persist project state back to project.json."""
        proj_dir = self.projects_dir / project.project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        json_path = proj_dir / "project.json"

        # Export Pydantic v2 dict
        data = project.model_dump(mode="json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return json_path

    def list_projects(self) -> List[Project]:
        """Discover and load all registered projects in projects_dir."""
        projects = []
        if not self.projects_dir.exists():
            return projects

        for child in sorted(self.projects_dir.iterdir()):
            if child.is_dir() and (child / "project.json").exists():
                try:
                    proj = self.get_project(child.name)
                    projects.append(proj)
                except Exception as e:
                    logger.warning("Failed to load project at %s: %s", child, e)

        return projects

    def generate_dataset_yaml(self, project_id: str) -> Path:
        """Generate a DatasetConfig-compatible YAML config in configs_dir for RNASeqBackendAPI integration."""
        project = self.get_project(project_id)
        proj_dir = self.projects_dir / project.project_id

        # 1. Create sample metadata CSV if not present
        sample_csv_path = proj_dir / "data" / "sample_metadata.csv"
        sample_rows = []
        for s in project.manifest.samples:
            row = {
                "sample_id": s.sample_id,
                project.manifest.condition_column: s.condition
            }
            if s.batch:
                row["batch"] = s.batch
            if s.genotype:
                row["genotype"] = s.genotype
            if s.tissue:
                row["tissue"] = s.tissue
            sample_rows.append(row)

        df_samples = pd.DataFrame(sample_rows)
        sample_csv_path.parent.mkdir(parents=True, exist_ok=True)
        df_samples.to_csv(sample_csv_path, index=False)

        # 2. Build counts matrix path
        counts_path = proj_dir / "data" / "counts_matrix.csv"
        if not counts_path.exists():
            # Create a placeholder CSV header if counts matrix not yet generated
            with open(counts_path, "w", encoding="utf-8") as f:
                header = ["gene_id"] + [s.sample_id for s in project.manifest.samples]
                f.write(",".join(header) + "\n")

        # 3. Build contrast yaml objects
        contrasts_yaml = []
        for c in project.design.contrasts:
            contrasts_yaml.append({
                "id": c.id,
                "factor": c.factor,
                "numerator": c.numerator,
                "denominator": c.denominator,
                "description": c.description or f"{c.numerator} vs {c.denominator}"
            })

        # Build factors dictionary
        factors_dict = {}
        for c in project.design.contrasts:
            unique_levels = sorted(list(set([c.numerator, c.denominator])))
            factors_dict[c.factor] = unique_levels

        yaml_dict = {
            "dataset_id": project.project_id,
            "organism": project.organism,
            "counts_matrix_path": str(counts_path),
            "sample_metadata_path": str(sample_csv_path),
            "output_dir": str(proj_dir / "results"),
            "combined_group_column": project.manifest.condition_column,
            "factors": factors_dict if factors_dict else {project.manifest.condition_column: ["Treatment", "Control"]},
            "reference_levels": project.design.reference_levels or {project.manifest.condition_column: "Control"},
            "contrasts": contrasts_yaml if contrasts_yaml else [{
                "id": "Primary_Contrast",
                "factor": project.manifest.condition_column,
                "numerator": "Treatment",
                "denominator": "Control",
                "description": "Primary treatment vs control"
            }],
            "candidate_selection": {
                "mode": "TOP_N_DEGS",
                "top_n": 50,
                "specified_genes": []
            }
        }

        yaml_filename = f"{project.project_id.lower()}.yaml"
        yaml_out_path = self.configs_dir / yaml_filename
        with open(yaml_out_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_dict, f, default_flow_style=False, sort_keys=False)

        logger.info("Generated dataset YAML config at %s", yaml_out_path)
        return yaml_out_path

    def record_execution_step(self, project_id: str, step: Any) -> Path:
        """
        Appends a ToolExecutionStep to project execution history and updates workspace readiness state.
        Persists trace to projects/<project_id>/execution_history.json and updates project.json.
        """
        project = self.get_project(project_id)

        # Convert dict or ToolExecutionStep instance
        if isinstance(step, dict):
            from pipeline.schemas.project_schemas import ToolExecutionStep
            step_obj = ToolExecutionStep.model_validate(step)
        else:
            step_obj = step

        # Append step
        project.execution_history.append(step_obj)

        # Dynamically update workspace state based on project artifacts & execution steps
        proj_dir = self.projects_dir / project.project_id
        counts_csv = proj_dir / "data" / "counts_matrix.csv"
        de_csv = proj_dir / "results"

        has_counts = counts_csv.exists() and counts_csv.stat().st_size > 100
        has_de = any(de_csv.glob("*_deseq2_results.csv")) if de_csv.exists() else False

        if has_de:
            readiness = "ANALYZED"
        elif has_counts:
            readiness = "QUANTIFIED"
        elif any(s.fastq_r1_path for s in project.manifest.samples):
            readiness = "FASTQ_UPLOADED"
        else:
            readiness = "INITIALIZED"

        project.workspace_state.readiness_stage = readiness
        project.workspace_state.has_counts_matrix = has_counts
        project.workspace_state.has_de_results = has_de
        project.workspace_state.total_samples = len(project.manifest.samples)
        project.workspace_state.replicate_status = project.manifest.replicate_status

        # Save project.json
        self.save_project(project)

        # Save dedicated execution_history.json
        history_path = proj_dir / "execution_history.json"
        history_data = [s.model_dump(mode="json") for s in project.execution_history]
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=2)

        return history_path

    def get_execution_history(self, project_id: str) -> List[Dict[str, Any]]:
        """Returns step-by-step tool execution history for a project workspace."""
        clean_id = project_id.strip().upper()
        history_path = self.projects_dir / clean_id / "execution_history.json"

        if not history_path.exists():
            return []

        try:
            with open(history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load execution history at %s: %s", history_path, e)
            return []

    def assign_sample_metadata(self, project_id: str, metadata_list: List[Dict[str, Any]]) -> Project:
        """Assign sample condition and replicate metadata to project manifest."""
        clean_id = project_id.strip().upper()
        project = self.get_project(clean_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        meta_map = {item["sample_id"]: item for item in metadata_list if "sample_id" in item}

        manifest_samples = project.manifest.samples
        manifest_sample_ids = {s.sample_id for s in manifest_samples}

        # Normalize sample ID matching (exact match OR suffix match removing file_id prefix)
        resolved_meta_map = {}
        for user_sid, meta_item in meta_map.items():
            matched_sid = None
            if user_sid in manifest_sample_ids:
                matched_sid = user_sid
            else:
                for real_sid in manifest_sample_ids:
                    if real_sid.endswith(f"_{user_sid}") or real_sid.endswith(user_sid):
                        matched_sid = real_sid
                        break
            if not matched_sid:
                raise ValueError(f"Metadata sample ID '{user_sid}' does not match any uploaded sample in project (uploaded samples: {sorted(list(manifest_sample_ids))})")
            resolved_meta_map[matched_sid] = meta_item

        updated_samples = []
        for sample in manifest_samples:
            if sample.sample_id in resolved_meta_map:
                info = resolved_meta_map[sample.sample_id]
                if "condition" in info and info["condition"]:
                    sample.condition = str(info["condition"]).strip()
                if "replicate_id" in info and info["replicate_id"]:
                    sample.replicate_id = str(info["replicate_id"]).strip()
            updated_samples.append(sample)

        project.manifest.samples = updated_samples

        conditions = [s.condition for s in updated_samples if s.condition and s.condition.upper() != "UNRESOLVED"]
        unique_groups = sorted(list(set(conditions)))
        if len(unique_groups) >= 2:
            project.workspace_state.is_ready_for_deseq2 = True
            project.workspace_state.unresolved_reason = None
            project.design.factors = {"condition": unique_groups}
            project.design.reference_levels = {"condition": unique_groups[0]}

        self.save_project(project)
        self.generate_dataset_yaml(clean_id)
        return project
