"""
Scientific Evidence Hierarchy Classifier for Bulk RNA-seq AI Agent Platform.

Enforces strict evidence hierarchy badges:
  [OBSERVED]              - Raw or normalized observation data
  [STATISTICAL]           - PyDESeq2 differential expression metrics (LFC, p-value, padj)
  [LITERATURE-SUPPORTED] - Verified peer-reviewed literature snippets & citations
  [INTERPRETATION]        - Grounded biological pathway interpretation
  [HYPOTHESIS]           - Speculative cellular or physiological mechanism
"""

import enum
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from scientific_guardrails.claim_guardrails import validate_ai_claim_text

logger = logging.getLogger(__name__)


class EvidenceBadge(str, enum.Enum):
    OBSERVED = "[OBSERVED]"
    STATISTICAL = "[STATISTICAL]"
    LITERATURE_SUPPORTED = "[LITERATURE-SUPPORTED]"
    INTERPRETATION = "[INTERPRETATION]"
    HYPOTHESIS = "[HYPOTHESIS]"


class EvidenceStatement(BaseModel):
    """Structured, evidence-badged statement with guardrail validation."""
    statement_id: str
    badge: EvidenceBadge
    text: str
    supporting_ids: List[str] = Field(default_factory=list)
    citation: Optional[str] = None
    guardrail_passed: bool = True
    rejection_reason: Optional[str] = None

    def formatted_text(self) -> str:
        """Return badge-prefixed formatted statement string."""
        cite_suffix = f" (Citation: {self.citation})" if self.citation else ""
        return f"{self.badge.value} {self.text}{cite_suffix}"


class EvidenceClassifier:
    """Classifies, formats, and validates scientific statements against evidence rules."""

    def create_statement(
        self,
        statement_id: str,
        badge: EvidenceBadge,
        text: str,
        supporting_ids: Optional[List[str]] = None,
        citation: Optional[str] = None
    ) -> EvidenceStatement:
        """Construct EvidenceStatement and validate against scientific claim guardrails."""
        sup_ids = supporting_ids or []
        is_valid, rejections = validate_ai_claim_text(text)

        # Enforce rule: Hypotheses must not present as observed facts
        if badge == EvidenceBadge.HYPOTHESIS:
            assertive_terms = ["is proven that", "demonstrates conclusively that", "causes"]
            for term in assertive_terms:
                if term in text.lower():
                    is_valid = False
                    rejections.append(f"Hypothesis statement contains over-assertive term '{term}'. Must use speculative language.")

        return EvidenceStatement(
            statement_id=statement_id,
            badge=badge,
            text=text,
            supporting_ids=sup_ids,
            citation=citation,
            guardrail_passed=is_valid,
            rejection_reason="; ".join(rejections) if rejections else None
        )
