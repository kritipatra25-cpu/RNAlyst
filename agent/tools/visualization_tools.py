"""
Visualization Agent Tool Contracts.

Wraps deterministic VisualizationEngine figure generation capabilities (Volcano plot, 
PCA plot, Row Z-score Heatmap, QC Plot) as BaseTool contracts with typed schemas, argument 
validation, dynamic project path auto-resolution, structured ToolResult output, and provenance tracking.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import pandas as pd
from pydantic import BaseModel, Field, validator

from agent.tools.base_tool import BaseTool, ToolResult, ToolArtifact
from visualization.plots_engine import VisualizationEngine


def _resolve_project_artifact(
    artifact_type: str,
    explicit_path: Optional[str] = None,
    project_id: Optional[str] = None
) -> Optional[Path]:
    """Helper to locate real artifact file paths for a given project_id or current workspace."""
    if explicit_path and isinstance(explicit_path, str) and explicit_path.strip():
        p = Path(explicit_path.strip())
        if p.exists():
            return p
        return None

    # Search project workspace directories strictly for the specified project_id
    project_dirs = []
    pid_clean = project_id.strip().upper() if project_id else ""

    if pid_clean in ("OSD-678", "OSD678"):
        project_dirs.extend([Path("results/osd678_validation"), Path("data/osd678")])
    elif pid_clean in ("OSD-120", "OSD120"):
        project_dirs.extend([Path("results/osd120_primary_analysis")])
    elif project_id:
        project_dirs.extend([Path(f"projects/{project_id}"), Path(f"data/projects/{project_id}")])
    else:
        project_dirs.extend([Path("projects")])

    file_names = {
        "de_results": ["differential_expression.csv", "A1_Col0_Light_Flight_vs_Ground.csv", "Primary_OSD120_Flight_vs_Ground.csv"],
        "vst_counts": ["vst_counts.csv", "normalized_counts.csv", "counts_matrix.csv"],
        "sample_table": ["sample_metadata.csv", "sample_sheet.csv", "samples.csv"]
    }

    targets = file_names.get(artifact_type, [])
    for p_dir in project_dirs:
        if not p_dir.exists():
            continue
        for target in targets:
            candidate = p_dir / target
            if candidate.exists():
                return candidate
            # Check subdirectories
            matches = list(p_dir.glob(f"**/{target}"))
            if matches:
                return matches[0]

    return None


class VolcanoPlotToolArgs(BaseModel):
    """Input argument schema for VolcanoPlotTool."""
    de_results_path: Optional[str] = Field(None, description="Optional path to differential expression results CSV file. Auto-resolved from active project if omitted.")
    output_path: Optional[str] = Field(None, description="Optional target PNG file path. Defaults to results/volcano_plot.png if omitted.")
    fdr_thresh: float = Field(0.05, description="FDR significance threshold for volcano plot (0.0 < fdr < 1.0).")
    lfc_thresh: float = Field(1.0, description="Absolute Log2 fold-change significance threshold (>= 0.0).")
    title: Optional[str] = Field("Volcano Plot (Differential Expression)", description="Title header for the plot figure.")
    project_id: Optional[str] = Field(None, description="Optional active project identifier for provenance.")

    @validator("fdr_thresh")
    def validate_fdr(cls, v):
        if v <= 0.0 or v >= 1.0:
            raise ValueError(f"fdr_thresh must be between 0.0 and 1.0 strictly. Got: {v}")
        return v

    @validator("lfc_thresh")
    def validate_lfc(cls, v):
        if v < 0.0:
            raise ValueError(f"lfc_thresh must be non-negative. Got: {v}")
        return v


class VolcanoPlotTool(BaseTool):
    """Deterministic Volcano Plot Generation Tool."""

    name = "generate_volcano_plot"
    description = "Generates a publication-ready volcano plot (-log10 padj vs shrunken log2 fold-change) from differential expression results."
    arguments_schema = VolcanoPlotToolArgs

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        args = validated_args or VolcanoPlotToolArgs(**arguments)
        proj_id = args.project_id or "CURRENT_PROJECT"

        de_path = _resolve_project_artifact("de_results", args.de_results_path, args.project_id)
        if not de_path or not de_path.exists():
            return ToolResult.error_result(
                tool_name=self.name,
                error_type="MissingPrerequisitesError",
                message="Differential expression results are missing. Differential expression analysis must be executed before generating a volcano plot.",
                provenance={
                    "project_id": proj_id,
                    "missing_prerequisites": ["de_results_path"],
                    "recommendation": "Configure experimental contrast conditions and run differential expression analysis."
                }
            )

        try:
            de_df = pd.read_csv(de_path)
            p_col = "padj" if "padj" in de_df.columns else ("pvalue" if "pvalue" in de_df.columns else None)
            lfc_col = "shrunk_log2FoldChange" if "shrunk_log2FoldChange" in de_df.columns else ("log2FoldChange" if "log2FoldChange" in de_df.columns else None)

            if not p_col or not lfc_col:
                return ToolResult.error_result(
                    tool_name=self.name,
                    error_type="InvalidArtifactError",
                    message=f"Differential expression CSV at {de_path} is missing required p-value / log2FoldChange columns.",
                    provenance={"project_id": proj_id, "source_artifact": str(de_path)}
                )

            if "shrunk_log2FoldChange" not in de_df.columns and "log2FoldChange" in de_df.columns:
                de_df["shrunk_log2FoldChange"] = de_df["log2FoldChange"]

            out_path = Path(args.output_path) if args.output_path else Path("results/volcano_plot.png")
            analysis_id = f"analysis_volcano_{int(time.time())}"

            res_path = VisualizationEngine.plot_volcano(
                de_data=de_df,
                output_path=out_path,
                fdr_thresh=args.fdr_thresh,
                lfc_thresh=args.lfc_thresh,
                title=args.title or "Volcano Plot (Differential Expression)"
            )

            out_str = str(res_path)
            prov = {
                "project_id": proj_id,
                "analysis_id": analysis_id,
                "source_artifact": str(de_path),
                "tool": self.name,
                "wrapped_class": "VisualizationEngine",
                "wrapped_method": "plot_volcano",
                "method": "VisualizationEngine.plot_volcano",
                "relevant_parameters": {
                    "fdr_thresh": args.fdr_thresh,
                    "lfc_thresh": args.lfc_thresh,
                    "title": args.title
                }
            }

            return ToolResult.success_result(
                tool_name=self.name,
                result={
                    "output_path": out_str,
                    "total_genes": len(de_df),
                    "fdr_thresh": args.fdr_thresh,
                    "lfc_thresh": args.lfc_thresh,
                    "title": args.title,
                    "provenance": prov
                },
                artifacts=[
                    ToolArtifact(
                        artifact_type="image",
                        path=out_str,
                        description="Volcano plot figure PNG"
                    )
                ],
                provenance=prov
            )
        except Exception as e:
            return ToolResult.error_result(
                tool_name=self.name,
                error_type=type(e).__name__,
                message=f"Volcano plot generation failed: {str(e)}",
                provenance={"project_id": proj_id, "de_results_path": str(de_path) if de_path else None}
            )


class PCAPlotToolArgs(BaseModel):
    """Input argument schema for PCAPlotTool."""
    vst_counts_path: Optional[str] = Field(None, description="Optional path to VST normalized counts CSV file. Auto-resolved from active project if omitted.")
    sample_table_path: Optional[str] = Field(None, description="Optional path to sample metadata CSV file. Auto-resolved from active project if omitted.")
    group_col: Optional[str] = Field("condition", description="Sample metadata column name used to group/color samples in PCA plot.")
    output_path: Optional[str] = Field(None, description="Optional target PNG file path. Defaults to results/pca_plot.png if omitted.")
    top_n_genes: int = Field(500, description="Number of top variable genes to use for PCA (>= 2).")
    project_id: Optional[str] = Field(None, description="Optional active project identifier for provenance.")

    @validator("top_n_genes")
    def validate_top_n(cls, v):
        if v < 2:
            raise ValueError(f"top_n_genes must be at least 2 for PCA decomposition. Got: {v}")
        return v


class PCAPlotTool(BaseTool):
    """Deterministic 2D PCA Plot Generation Tool."""

    name = "generate_pca_plot"
    description = "Generates a 2D Principal Component Analysis (PCA) scatter plot (PC1 vs PC2) from VST normalized expression data."
    arguments_schema = PCAPlotToolArgs

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        args = validated_args or PCAPlotToolArgs(**arguments)
        proj_id = args.project_id or "CURRENT_PROJECT"

        vst_path = _resolve_project_artifact("vst_counts", args.vst_counts_path, args.project_id)
        sample_path = _resolve_project_artifact("sample_table", args.sample_table_path, args.project_id)

        if not vst_path or not vst_path.exists():
            return ToolResult.error_result(
                tool_name=self.name,
                error_type="MissingPrerequisitesError",
                message="VST counts/normalized expression matrix CSV file not found. Quantification/normalization must be completed before generating a PCA plot.",
                provenance={
                    "project_id": proj_id,
                    "missing_prerequisites": ["vst_counts_path"],
                    "recommendation": "Execute quantification/normalization on dataset."
                }
            )

        try:
            vst_df = pd.read_csv(vst_path)
            if "gene_id" in vst_df.columns:
                vst_df = vst_df.set_index("gene_id")

            sample_cols = list(vst_df.columns)
            if len(sample_cols) < 2:
                return ToolResult.error_result(
                    tool_name=self.name,
                    error_type="MissingPrerequisitesError",
                    message=f"PCA requires at least 2 biological samples to calculate principal components. Found {len(sample_cols)} sample(s).",
                    provenance={
                        "project_id": proj_id,
                        "missing_prerequisites": ["multiple_biological_samples"],
                        "recommendation": "Upload FASTQ files or expression data for at least 2 distinct biological samples."
                    }
                )

            sample_meta = None
            if sample_path and sample_path.exists():
                sample_meta = pd.read_csv(sample_path)
                if "sample_id" in sample_meta.columns:
                    sample_meta = sample_meta.set_index("sample_id", drop=False)

            out_path = Path(args.output_path) if args.output_path else Path("results/pca_plot.png")
            group_col = args.group_col or "condition"
            analysis_id = f"analysis_pca_{int(time.time())}"

            pca_data = VisualizationEngine.plot_pca(
                pca_data=vst_df,
                sample_meta=sample_meta,
                group_col=group_col,
                output_path=out_path,
                top_n_genes=args.top_n_genes
            )

            out_str = str(out_path)
            prov = {
                "project_id": proj_id,
                "analysis_id": analysis_id,
                "source_artifact": str(vst_path),
                "sample_table_artifact": str(sample_path) if sample_path else None,
                "tool": self.name,
                "wrapped_class": "VisualizationEngine",
                "wrapped_method": "plot_pca",
                "method": "VisualizationEngine.plot_pca",
                "relevant_parameters": {
                    "group_col": group_col,
                    "top_n_genes": args.top_n_genes
                }
            }

            return ToolResult.success_result(
                tool_name=self.name,
                result={
                    "output_path": out_str,
                    "pc1_var": pca_data.get("pc1_var"),
                    "pc2_var": pca_data.get("pc2_var"),
                    "group_col": group_col,
                    "top_n_genes": args.top_n_genes,
                    "sample_count": len(sample_meta) if sample_meta is not None else len(vst_df.columns),
                    "provenance": prov
                },
                artifacts=[
                    ToolArtifact(
                        artifact_type="image",
                        path=out_str,
                        description="PCA plot figure PNG"
                    )
                ],
                provenance=prov
            )
        except Exception as e:
            return ToolResult.error_result(
                tool_name=self.name,
                error_type=type(e).__name__,
                message=f"PCA plot generation failed: {str(e)}",
                provenance={"project_id": proj_id, "vst_counts_path": str(vst_path) if vst_path else None}
            )


class HeatmapToolArgs(BaseModel):
    """Input argument schema for HeatmapTool."""
    vst_counts_path: Optional[str] = Field(None, description="Optional path to VST normalized counts CSV file. Auto-resolved from active project if omitted.")
    de_results_path: Optional[str] = Field(None, description="Optional path to differential expression results CSV file. Auto-resolved from active project if omitted.")
    sample_table_path: Optional[str] = Field(None, description="Optional path to sample metadata CSV file.")
    output_path: Optional[str] = Field(None, description="Optional target PNG file path. Defaults to results/heatmap_plot.png if omitted.")
    top_n: int = Field(40, description="Number of top DEGs (sorted by padj) to display in the heatmap (>= 1).")
    project_id: Optional[str] = Field(None, description="Optional active project identifier for provenance.")

    @validator("top_n")
    def validate_top_n(cls, v):
        if v < 1:
            raise ValueError(f"top_n must be at least 1 DEG for heatmap. Got: {v}")
        return v


class HeatmapTool(BaseTool):
    """Deterministic Row Z-score Expression Heatmap Generation Tool."""

    name = "generate_heatmap"
    description = "Generates a row Z-score normalized expression heatmap for top differentially expressed genes."
    arguments_schema = HeatmapToolArgs

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        args = validated_args or HeatmapToolArgs(**arguments)
        proj_id = args.project_id or "CURRENT_PROJECT"

        vst_path = _resolve_project_artifact("vst_counts", args.vst_counts_path, args.project_id)
        de_path = _resolve_project_artifact("de_results", args.de_results_path, args.project_id)
        sample_path = _resolve_project_artifact("sample_table", args.sample_table_path, args.project_id)

        if not vst_path or not vst_path.exists():
            return ToolResult.error_result(
                tool_name=self.name,
                error_type="MissingPrerequisitesError",
                message="VST counts/normalized expression matrix CSV file not found. Quantification/normalization must be completed before generating a heatmap.",
                provenance={
                    "project_id": proj_id,
                    "missing_prerequisites": ["vst_counts_path"],
                    "recommendation": "Execute quantification/normalization on dataset."
                }
            )

        if not de_path or not de_path.exists():
            return ToolResult.error_result(
                tool_name=self.name,
                error_type="MissingPrerequisitesError",
                message="Differential expression results CSV file not found. Differential expression must be executed before generating a DEG heatmap.",
                provenance={
                    "project_id": proj_id,
                    "missing_prerequisites": ["de_results_path"],
                    "recommendation": "Configure experimental contrast conditions and run differential expression analysis."
                }
            )

        try:
            vst_df = pd.read_csv(vst_path)
            if "gene_id" in vst_df.columns:
                vst_df = vst_df.set_index("gene_id")

            de_df = pd.read_csv(de_path)

            sample_meta = pd.DataFrame()
            if sample_path and sample_path.exists():
                sample_meta = pd.read_csv(sample_path)

            out_path = Path(args.output_path) if args.output_path else Path("results/heatmap_plot.png")
            analysis_id = f"analysis_heatmap_{int(time.time())}"

            res_path = VisualizationEngine.plot_heatmap(
                vst_df=vst_df,
                de_data=de_df,
                sample_meta=sample_meta,
                output_path=out_path,
                top_n=args.top_n
            )

            out_str = str(res_path)
            prov = {
                "project_id": proj_id,
                "analysis_id": analysis_id,
                "source_artifact": str(vst_path),
                "de_artifact": str(de_path),
                "tool": self.name,
                "wrapped_class": "VisualizationEngine",
                "wrapped_method": "plot_heatmap",
                "method": "VisualizationEngine.plot_heatmap",
                "relevant_parameters": {
                    "top_n": args.top_n
                }
            }

            return ToolResult.success_result(
                tool_name=self.name,
                result={
                    "output_path": out_str,
                    "top_n_requested": args.top_n,
                    "vst_counts_path": str(vst_path),
                    "de_results_path": str(de_path),
                    "provenance": prov
                },
                artifacts=[
                    ToolArtifact(
                        artifact_type="image",
                        path=out_str,
                        description="Expression heatmap figure PNG"
                    )
                ],
                provenance=prov
            )
        except Exception as e:
            return ToolResult.error_result(
                tool_name=self.name,
                error_type=type(e).__name__,
                message=f"Heatmap plot generation failed: {str(e)}",
                provenance={"project_id": proj_id, "vst_counts_path": str(vst_path) if vst_path else None, "de_results_path": str(de_path) if de_path else None}
            )


class QCPlotToolArgs(BaseModel):
    """Input argument schema for QCPlotTool."""
    project_id: Optional[str] = Field(None, description="Optional active project identifier for provenance.")
    output_path: Optional[str] = Field(None, description="Optional target PNG file path. Defaults to results/qc_plot.png if omitted.")


class QCPlotTool(BaseTool):
    """Deterministic Quality Control (QC) Plot Generation Tool."""

    name = "generate_qc_plot"
    description = "Generates a quality control summary bar plot (Total Reads, GC%, Phred Quality) from actual FASTQ QC outputs for the active project."
    arguments_schema = QCPlotToolArgs

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        args = validated_args or QCPlotToolArgs(**arguments)
        proj_id = args.project_id or "CURRENT_PROJECT"

        qc_metrics = None
        source_file = "FASTQ QC Output"
        try:
            from api.routes.qc import find_uploaded_file, calculate_fastq_qc
            uploaded_f = find_uploaded_file(proj_id)
            source_file = uploaded_f.name
            qc_metrics = calculate_fastq_qc(uploaded_f)
        except Exception as e:
            return ToolResult.error_result(
                tool_name=self.name,
                error_type="MissingPrerequisitesError",
                message=f"FASTQ Quality Control metrics missing or unavailable for project '{proj_id}': {str(e)}",
                provenance={"project_id": proj_id}
            )

        out_path = Path(args.output_path) if args.output_path else Path("results/qc_plot.png")
        analysis_id = f"analysis_qc_{int(time.time())}"

        try:
            res_path = VisualizationEngine.plot_qc(
                qc_metrics=qc_metrics,
                output_path=out_path
            )

            out_str = str(res_path)
            prov = {
                "project_id": proj_id,
                "analysis_id": analysis_id,
                "source_artifact": source_file,
                "tool": self.name,
                "method": "VisualizationEngine.generate_qc_plot",
                "relevant_parameters": qc_metrics
            }

            return ToolResult.success_result(
                tool_name=self.name,
                result={
                    "output_path": out_str,
                    "qc_metrics": qc_metrics,
                    "provenance": prov
                },
                artifacts=[
                    ToolArtifact(
                        artifact_type="image",
                        path=out_str,
                        description="QC summary plot figure PNG"
                    )
                ],
                provenance=prov
            )
        except Exception as e:
            return ToolResult.error_result(
                tool_name=self.name,
                error_type=type(e).__name__,
                message=f"QC plot generation failed: {str(e)}",
                provenance={"project_id": proj_id, "source_artifact": source_file}
            )
