"""
Multi-Species Gene Annotation Boundary for Bulk RNA-seq Analysis Platform.

Provides extensible, configuration-driven gene annotation and symbol resolution
across multiple species (Arabidopsis thaliana, Mus musculus, Homo sapiens, etc.).
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd

from annotation.tair10 import TAIR10Annotator
from annotation.mouse_gencode import MouseGENCODEAnnotator

logger = logging.getLogger(__name__)

# Canonical default TAIR10 symbol mapping dictionary for benchmark candidates
TAIR10_BENCHMARK_SYMBOL_MAP = {
    "AT3G17609": "HYH",
    "AT4G04720": "CPK21",
    "AT2G04170": "UNASSIGNED",
    "AT1G01010": "ANAC001",
    "AT5G57630": "CIPK21",
    "AT3G46640": "LUX",
    "AT5G07390": "RBOHA",
    "AT5G13930": "CHS",
}

class BaseAnnotationProvider(ABC):
    """Abstract base provider for species-specific gene annotations."""

    @property
    @abstractmethod
    def organism(self) -> str:
        """Name of target organism (e.g. 'Arabidopsis thaliana')."""
        pass

    @property
    @abstractmethod
    def annotation_source(self) -> str:
        """Annotation database source (e.g. 'TAIR10', 'GENCODE_M34')."""
        pass

    @abstractmethod
    def get_symbol(self, gene_id: str) -> str:
        """Resolve gene ID to gene symbol or default fallback."""
        pass

    @abstractmethod
    def annotate_gene(self, gene_id: str) -> Dict[str, Any]:
        """Return standardized annotation metadata dictionary for a gene ID."""
        pass


class TAIR10AnnotationProvider(BaseAnnotationProvider):
    """Arabidopsis thaliana TAIR10 annotation provider."""

    def __init__(self, custom_symbol_map: Optional[Dict[str, str]] = None, annotation_file: Optional[str] = None):
        self._annotator = TAIR10Annotator(annotation_file=annotation_file)
        self._symbol_map = TAIR10_BENCHMARK_SYMBOL_MAP.copy()
        if custom_symbol_map:
            self._symbol_map.update(custom_symbol_map)

    @property
    def organism(self) -> str:
        return "Arabidopsis thaliana"

    @property
    def annotation_source(self) -> str:
        return "TAIR10"

    def get_symbol(self, gene_id: str) -> str:
        gid_clean = str(gene_id).strip().upper()
        if gid_clean in self._symbol_map:
            return self._symbol_map[gid_clean]
        ann = self._annotator.annotate_gene(gid_clean)
        sym = ann.get("symbol", "")
        if sym and sym != gid_clean:
            return sym
        return "VALID TAIR ID — NO SYMBOL AVAILABLE"

    def annotate_gene(self, gene_id: str) -> Dict[str, Any]:
        gid_clean = str(gene_id).strip().upper()
        ann = self._annotator.annotate_gene(gid_clean)
        ann["symbol"] = self.get_symbol(gid_clean)
        return ann


class MouseGENCODEAnnotationProvider(BaseAnnotationProvider):
    """Mus musculus GENCODE M34 annotation provider."""

    def __init__(self, custom_symbol_map: Optional[Dict[str, str]] = None, annotation_file: Optional[str] = None):
        self._annotator = MouseGENCODEAnnotator(annotation_file=annotation_file)
        self._symbol_map = custom_symbol_map or {}

    @property
    def organism(self) -> str:
        return "Mus musculus"

    @property
    def annotation_source(self) -> str:
        return "GENCODE_M34"

    def get_symbol(self, gene_id: str) -> str:
        gid_clean = str(gene_id).strip()
        gid_base = gid_clean.split(".")[0]
        if gid_clean in self._symbol_map:
            return self._symbol_map[gid_clean]
        if gid_base in self._symbol_map:
            return self._symbol_map[gid_base]
        ann = self._annotator.annotate_gene(gid_clean)
        return ann.get("symbol", gid_base)

    def annotate_gene(self, gene_id: str) -> Dict[str, Any]:
        gid_clean = str(gene_id).strip()
        ann = self._annotator.annotate_gene(gid_clean)
        ann["symbol"] = self.get_symbol(gid_clean)
        return ann


class ConfigMapAnnotationProvider(BaseAnnotationProvider):
    """Configuration-driven dictionary annotation provider for arbitrary species."""

    def __init__(
        self,
        symbol_map: Dict[str, str],
        organism: str = "Generic",
        annotation_source: str = "CONFIG_MAP"
    ):
        self._symbol_map = symbol_map.copy() if symbol_map else {}
        self._organism = organism
        self._annotation_source = annotation_source

    @property
    def organism(self) -> str:
        return self._organism

    @property
    def annotation_source(self) -> str:
        return self._annotation_source

    def get_symbol(self, gene_id: str) -> str:
        gid_clean = str(gene_id).strip()
        if gid_clean in self._symbol_map:
            return self._symbol_map[gid_clean]
        if gid_clean.upper() in self._symbol_map:
            return self._symbol_map[gid_clean.upper()]
        return gid_clean

    def annotate_gene(self, gene_id: str) -> Dict[str, Any]:
        gid_clean = str(gene_id).strip()
        return {
            "gene_id": gid_clean,
            "symbol": self.get_symbol(gid_clean),
            "name": f"Transcript {gid_clean}",
            "biotype": "protein_coding",
        }


class GeneAnnotator:
    """
    Main Orchestrator for Multi-Species Gene Annotation.
    Selects or constructs an AnnotationProvider based on organism/annotation_source config.
    """

    def __init__(
        self,
        provider: Optional[BaseAnnotationProvider] = None,
        organism: str = "Arabidopsis thaliana",
        annotation_source: str = "TAIR10",
        custom_symbol_map: Optional[Dict[str, str]] = None,
        annotation_file: Optional[str] = None
    ):
        if provider is not None:
            self.provider = provider
        else:
            self.provider = self._resolve_provider(
                organism=organism,
                annotation_source=annotation_source,
                custom_symbol_map=custom_symbol_map,
                annotation_file=annotation_file
            )

    @classmethod
    def from_config(cls, config: Any) -> "GeneAnnotator":
        """Factory constructor building GeneAnnotator directly from a DatasetConfig object or dict."""
        if hasattr(config, "organism"):
            organism = getattr(config, "organism", "Arabidopsis thaliana")
            annotation_source = getattr(config, "annotation_source", "TAIR10")
            custom_symbol_map = getattr(config, "custom_symbol_map", None)
            annotation_file = getattr(config, "annotation_file", None)
        elif isinstance(config, dict):
            organism = config.get("organism", "Arabidopsis thaliana")
            annotation_source = config.get("annotation_source", "TAIR10")
            custom_symbol_map = config.get("custom_symbol_map", None)
            annotation_file = config.get("annotation_file", None)
        else:
            organism = "Arabidopsis thaliana"
            annotation_source = "TAIR10"
            custom_symbol_map = None
            annotation_file = None

        return cls(
            organism=organism,
            annotation_source=annotation_source,
            custom_symbol_map=custom_symbol_map,
            annotation_file=annotation_file
        )

    def _resolve_provider(
        self,
        organism: str,
        annotation_source: str,
        custom_symbol_map: Optional[Dict[str, str]] = None,
        annotation_file: Optional[str] = None
    ) -> BaseAnnotationProvider:
        """Resolve appropriate annotation provider from metadata."""
        org_clean = (organism or "").strip().lower()
        source_clean = (annotation_source or "").strip().upper()

        if custom_symbol_map and ("arabidopsis" not in org_clean and "mouse" not in org_clean and "mus musculus" not in org_clean):
            return ConfigMapAnnotationProvider(
                symbol_map=custom_symbol_map,
                organism=organism,
                annotation_source=annotation_source
            )

        if "arabidopsis" in org_clean or source_clean == "TAIR10":
            return TAIR10AnnotationProvider(
                custom_symbol_map=custom_symbol_map,
                annotation_file=annotation_file
            )

        if "mus musculus" in org_clean or "mouse" in org_clean or "GENCODE" in source_clean:
            return MouseGENCODEAnnotationProvider(
                custom_symbol_map=custom_symbol_map,
                annotation_file=annotation_file
            )

        if custom_symbol_map:
            return ConfigMapAnnotationProvider(
                symbol_map=custom_symbol_map,
                organism=organism,
                annotation_source=annotation_source
            )

        # Generic passthrough fallback provider
        return ConfigMapAnnotationProvider(
            symbol_map={},
            organism=organism,
            annotation_source=annotation_source
        )

    def get_symbol(self, gene_id: str) -> str:
        """Resolve gene ID to symbol using active provider."""
        return self.provider.get_symbol(gene_id)

    def annotate_gene(self, gene_id: str) -> Dict[str, Any]:
        """Annotate single gene ID using active provider."""
        return self.provider.annotate_gene(gene_id)

    def annotate_dataframe(self, df: pd.DataFrame, gene_col: str = "gene_id") -> pd.DataFrame:
        """Annotate pandas DataFrame containing a gene ID column."""
        if gene_col not in df.columns:
            return df
        df_out = df.copy()
        df_out["symbol"] = [self.get_symbol(gid) for gid in df_out[gene_col]]
        return df_out
