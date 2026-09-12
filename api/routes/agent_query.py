"""
FastAPI route for Natural-Language Agent Query and UI Gateway.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.orchestrator.agent_runner import AgentOrchestrator, AgentResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Global Orchestrator instance for active sessions
orchestrator = AgentOrchestrator()


class QueryRequest(BaseModel):
    query: str
    dataset_id: Optional[str] = None
    session_id: Optional[str] = None


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def execute_agent_query(req: QueryRequest):
    """Execute natural-language query through AgentOrchestrator and return structured response."""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        response: AgentResponse = orchestrator.query(
            user_query=req.query.strip(),
            session_id=req.session_id,
            dataset_id=req.dataset_id
        )
        return response.dict()
    except Exception as e:
        logger.exception("Agent query execution failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Internal agent query execution failure: {str(e)}")
