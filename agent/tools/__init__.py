"""
Agent Tools Package.
Exposes generic BaseTool, ToolResult, ToolArtifact, ToolError contracts,
DESeq2Tool, LiteratureTool, GeneAnnotationTool, VisualizationTools, CandidatePrioritizationTool,
and Data Ingestion Tools (CreateProjectTool, ValidateFASTQTool, QuantifyReadsTool, FetchOSDRStudyTool).
"""

from agent.tools.base_tool import BaseTool, ToolResult, ToolArtifact, ToolError
from agent.tools.deseq2_tool import DESeq2Tool, DESeq2ToolArgs
from agent.tools.literature_tool import LiteratureTool, LiteratureToolArgs
from agent.tools.gene_annotation_tool import GeneAnnotationTool, GeneAnnotationToolArgs
from agent.tools.visualization_tools import (
    VolcanoPlotTool,
    VolcanoPlotToolArgs,
    PCAPlotTool,
    PCAPlotToolArgs,
    HeatmapTool,
    HeatmapToolArgs
)
from agent.tools.candidate_prioritization_tool import (
    CandidatePrioritizationTool,
    CandidatePrioritizationToolArgs
)
from agent.tools.ingestion_tools import (
    CreateProjectTool,
    CreateProjectInput,
    ValidateFASTQTool,
    ValidateFASTQInput,
    QuantifyReadsTool,
    QuantifyReadsInput,
    FetchOSDRStudyTool,
    FetchOSDRStudyInput
)
from agent.tools.registry import ToolRegistry

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolArtifact",
    "ToolError",
    "DESeq2Tool",
    "DESeq2ToolArgs",
    "LiteratureTool",
    "LiteratureToolArgs",
    "GeneAnnotationTool",
    "GeneAnnotationToolArgs",
    "VolcanoPlotTool",
    "VolcanoPlotToolArgs",
    "PCAPlotTool",
    "PCAPlotToolArgs",
    "HeatmapTool",
    "HeatmapToolArgs",
    "CandidatePrioritizationTool",
    "CandidatePrioritizationToolArgs",
    "CreateProjectTool",
    "CreateProjectInput",
    "ValidateFASTQTool",
    "ValidateFASTQInput",
    "QuantifyReadsTool",
    "QuantifyReadsInput",
    "FetchOSDRStudyTool",
    "FetchOSDRStudyInput",
    "ToolRegistry"
]
