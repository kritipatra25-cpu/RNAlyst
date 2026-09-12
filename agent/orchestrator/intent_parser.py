"""
Natural-Language Intent Parser for Bulk RNA-seq AI Agent Platform.

Parses free-form scientific user queries into explicit, machine-readable AnalysisIntent schemas.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class AnalysisIntent(BaseModel):
    """Explicit, machine-readable representation of user analytical intent."""
    dataset_id: Optional[str] = Field(None, description="Target dataset ID (e.g. OSD-678, OSD-120)")
    action: str = Field("run_analysis", description="Target action: list_datasets, list_contrasts, validate, run_analysis, filter_candidates, literature_search")
    contrast_id: Optional[str] = Field(None, description="Target contrast ID if specified")
    factor: Optional[str] = Field(None, description="Target experimental factor (e.g. Spaceflight, Light, Genotype)")
    condition_numerator: Optional[str] = Field(None, description="Experimental condition (e.g. Flight, Spaceflight)")
    condition_denominator: Optional[str] = Field(None, description="Reference condition (e.g. Ground, Control)")
    fdr_cutoff: float = Field(0.05, description="False Discovery Rate significance threshold")
    lfc_cutoff: float = Field(1.0, description="Log2 fold change threshold")
    candidate_genes: Optional[List[str]] = Field(None, description="Target gene identifiers or symbols")
    require_interpretation: bool = Field(True, description="Whether to include biological interpretation")
    require_literature: bool = Field(False, description="Whether to perform RAG literature retrieval")
    raw_user_query: str = Field("", description="Original natural-language query string")

    @validator("action")
    def validate_action(cls, v):
        allowed = ["list_datasets", "list_contrasts", "validate", "run_analysis", "filter_candidates", "literature_search"]
        v_clean = v.strip().lower()
        if v_clean not in allowed:
            raise ValueError(f"Action '{v}' is unsupported. Allowed: {allowed}")
        return v_clean


class NaturalLanguageIntentParser:
    """Parser translating natural-language queries into structured AnalysisIntent objects."""

    DATASET_PATTERNS = {
        r"\bOSD[-_]?678\b": "OSD-678",
        r"\bOSD[-_]?120\b": "OSD-120",
        r"\bGLDS[-_]?612\b": "OSD-678",
        r"\bGLDS[-_]?120\b": "OSD-120",
    }

    ACTION_KEYWORDS = {
        "list_datasets": ["list datasets", "available datasets", "show datasets", "what datasets", "what dataset", "which dataset", "currently selected", "active dataset", "selected dataset"],
        "list_contrasts": ["list contrasts", "available contrasts", "show contrasts", "what contrasts", "comparisons"],
        "validate": ["validate", "check metadata", "replicate check", "preflight", "audit replicates"],
        "literature_search": ["literature", "pubmed", "citations", "papers", "previous studies", "rag"],
        "filter_candidates": ["filter genes", "candidate genes", "top genes", "focus on"],
        "run_analysis": ["run", "analyze", "differential expression", "compare", "deseq2", "differentially expressed", "significantly different"]
    }

    CONTRAST_MAPPINGS = {
        "OSD-678": {
            "light": "A1_Col0_Light_Flight_vs_Ground",
            "dark": "B1_Col0_Dark_Flight_vs_Ground",
            "ws_light": "A2_Ws_Light_Flight_vs_Ground",
            "phyd_light": "A3_phyD_Light_Flight_vs_Ground",
            "interaction": "C_Col0_Flight_x_Light_Interaction",
        },
        "OSD-120": {
            "primary": "Primary_OSD120_Flight_vs_Ground",
            "flight": "Primary_OSD120_Flight_vs_Ground",
        }
    }

    GENE_SYMBOL_PATTERNS = [
        r"\b(AT[1-5MG]G\d{5})\b",  # TAIR Locus ID format
        r"\b(CRY1|CRY2|HYH|CPK21|ANAC001|CIPK21|LUX|RBOHA|CHS|ABI3|WRKY33|PR1|EXPA1|HSP70)\b",
        r"\b(ENSMUSG\d{11})\b"  # Mouse Ensembl ID
    ]

    def parse(self, query: str, active_dataset_id: Optional[str] = None) -> AnalysisIntent:
        """Parse query string into structured AnalysisIntent."""
        q_clean = query.strip()
        q_upper = q_clean.upper()

        # 1. Resolve Dataset ID
        dataset_id = active_dataset_id
        for pattern, did in self.DATASET_PATTERNS.items():
            if re.search(pattern, q_clean, re.IGNORECASE):
                dataset_id = did
                break

        # Do not default to OSD-678 if no dataset specified
        # Keep dataset_id as active_dataset_id (may be None)

        # 2. Resolve Action
        q_lower = q_clean.lower()
        resolved_action = "run_analysis"
        for act, kw_list in self.ACTION_KEYWORDS.items():
            if any(kw in q_lower for kw in kw_list):
                resolved_action = act
                break

        # 3. Resolve Contrast ID if dataset_id known
        contrast_id = None
        if dataset_id in self.CONTRAST_MAPPINGS:
            for kw, cid in self.CONTRAST_MAPPINGS[dataset_id].items():
                if kw in q_lower:
                    contrast_id = cid
                    break

        # 4. Extract Candidate Genes
        genes_found = []
        for g_pat in self.GENE_SYMBOL_PATTERNS:
            matches = re.findall(g_pat, q_upper, re.IGNORECASE)
            for m in matches:
                g_str = m[0] if isinstance(m, tuple) else m
                if g_str.upper() not in [g.upper() for g in genes_found]:
                    genes_found.append(g_str.upper())

        # 5. Determine Literature & Interpretation flags
        req_lit = "literature" in q_lower or "citation" in q_lower or "paper" in q_lower or resolved_action == "literature_search"
        req_interp = "why" in q_lower or "pathway" in q_lower or "function" in q_lower or "mechanism" in q_lower or True

        return AnalysisIntent(
            dataset_id=dataset_id,
            action=resolved_action,
            contrast_id=contrast_id,
            fdr_cutoff=0.05,
            lfc_cutoff=1.0,
            candidate_genes=genes_found if genes_found else None,
            require_interpretation=req_interp,
            require_literature=req_lit,
            raw_user_query=q_clean
        )
