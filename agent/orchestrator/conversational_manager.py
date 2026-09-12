"""
Conversational State Manager for AI Agent Platform.

Preserves analysis session context across multi-turn user conversations
without allowing conversation history to bypass backend validation boundaries.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from agent.orchestrator.intent_parser import AnalysisIntent, NaturalLanguageIntentParser
from agent.orchestrator.analysis_plan import AnalysisPlan, PlanValidator
from pipeline.backend_api import RNASeqBackendAPI

logger = logging.getLogger(__name__)


class ConversationalTurn(BaseModel):
    """Single turn in a conversational scientific analysis session."""
    turn_id: str
    user_query: str
    intent: AnalysisIntent
    plan: Optional[AnalysisPlan] = None
    response_text: str = ""
    is_validated: bool = True


class ConversationalSession(BaseModel):
    """Stateful analysis context manager tracking conversation turns and active dataset state."""
    session_id: str
    active_dataset_id: Optional[str] = None
    active_contrast_id: Optional[str] = None
    active_candidate_genes: List[str] = Field(default_factory=list)
    turns: List[ConversationalTurn] = Field(default_factory=list)


class ConversationalManager:
    """Manages active ConversationalSessions and contextual intent resolution."""

    def __init__(self, backend_api: Optional[RNASeqBackendAPI] = None):
        self.api = backend_api or RNASeqBackendAPI()
        self.parser = NaturalLanguageIntentParser()
        self.validator = PlanValidator(backend_api=self.api)
        self.sessions: Dict[str, ConversationalSession] = {}

    def create_session(self, session_id: Optional[str] = None) -> ConversationalSession:
        """Create new conversational analysis session."""
        sid = session_id or f"session_{uuid.uuid4().hex[:8]}"
        session = ConversationalSession(session_id=sid)
        self.sessions[sid] = session
        return session

    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationalSession:
        """Retrieve existing session or create a new session if missing."""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self.create_session(session_id=session_id)

    def process_turn(self, query: str, session_id: Optional[str] = None) -> ConversationalTurn:
        """Process conversational query, updating session context and building validated AnalysisPlan."""
        session = self.get_or_create_session(session_id)
        turn_id = f"turn_{len(session.turns) + 1:03d}"

        # Parse intent using session's active dataset as context fallback
        intent = self.parser.parse(query, active_dataset_id=session.active_dataset_id)

        # Retain conversational context if query lacks explicit values
        if not intent.contrast_id and session.active_contrast_id:
            intent.contrast_id = session.active_contrast_id
        if not intent.candidate_genes and session.active_candidate_genes:
            intent.candidate_genes = session.active_candidate_genes.copy()

        # Update session active state
        if intent.dataset_id:
            session.active_dataset_id = intent.dataset_id
        if intent.contrast_id:
            session.active_contrast_id = intent.contrast_id
        if intent.candidate_genes:
            session.active_candidate_genes = list(set(session.active_candidate_genes + intent.candidate_genes))

        # Build & validate plan
        plan = self.validator.build_plan(intent)

        turn = ConversationalTurn(
            turn_id=turn_id,
            user_query=query,
            intent=intent,
            plan=plan,
            is_validated=plan.is_validated
        )

        session.turns.append(turn)
        return turn
