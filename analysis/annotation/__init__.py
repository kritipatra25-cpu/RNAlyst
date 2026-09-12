"""
Multi-Species Gene Annotation Subsystem.
"""

from analysis.annotation.gene_annotator import (
    BaseAnnotationProvider,
    TAIR10AnnotationProvider,
    MouseGENCODEAnnotationProvider,
    ConfigMapAnnotationProvider,
    GeneAnnotator,
)

__all__ = [
    "BaseAnnotationProvider",
    "TAIR10AnnotationProvider",
    "MouseGENCODEAnnotationProvider",
    "ConfigMapAnnotationProvider",
    "GeneAnnotator",
]
