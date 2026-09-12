"""Validator prohibiting hallucinated biological or clinical claims in AI interpretation."""
import re
from typing import List, Tuple


PROHIBITED_TERMS = [
    r"\bdiagnos(e|is|tic)\b",
    r"\btherapeutically proven\b",
    r"\bproves causality\b",
    r"\bcauses (the|a) phenotype\b",
    r"\bpathway is activated\b",  # Must use overrepresented/enriched
    r"\bgene is activated\b",     # Must use increased expression / upregulated
]


def validate_ai_claim_text(text: str) -> Tuple[bool, List[str]]:
    """Scans proposed LLM interpretation text against prohibited scientific claim rules."""
    rejections = []
    
    for pattern in PROHIBITED_TERMS:
        if re.search(pattern, text, re.IGNORECASE):
            rejections.append(f"Prohibited language match: '{pattern}'. Use evidence-grounded scientific terminology.")

    if rejections:
        return False, rejections
    return True, []
