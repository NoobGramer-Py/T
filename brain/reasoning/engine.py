"""
Cognitive Reasoning Engine for T AI Operating System.
Evaluates queries and contexts to generate objective decisions, tool selections, and intent analysis,
completely decoupled from natural language dialogue generation.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from brain.logging.logger import get_logger

log = get_logger("reasoning.engine")


@dataclass
class Decision:
    """Represents a discrete cognitive decision made by the reasoning engine."""
    intent: str
    requires_planning: bool
    requires_execution: bool
    suggested_tools: List[str]
    confidence: float
    rationale: str


class ReasoningEngine:
    """Evaluates context to produce objective decisions and operational intents."""

    async def evaluate(self, user_query: str, context: Dict[str, Any]) -> Decision:
        """Analyzes a request and produces a structured Decision object."""
        q_lower = user_query.lower()
        log.info(f"Evaluating query for cognitive decision: '{user_query[:60]}...'")

        suggested_tools: List[str] = []
        requires_execution = False
        requires_planning = False

        if any(w in q_lower for w in ["run", "execute", "open", "launch", "create", "file", "build"]):
            requires_execution = True
            suggested_tools.append("system_execution")

        if any(w in q_lower for w in ["plan", "how to", "multi-step", "deploy", "build app"]):
            requires_planning = True

        intent = "query_information"
        if requires_execution:
            intent = "execute_action"
        elif requires_planning:
            intent = "create_plan"

        decision = Decision(
            intent=intent,
            requires_planning=requires_planning,
            requires_execution=requires_execution,
            suggested_tools=suggested_tools,
            confidence=0.95,
            rationale=f"Evaluated query intent as '{intent}' based on contextual keyword and capability state."
        )

        log.info(f"Reasoning decision: intent='{decision.intent}', planning={decision.requires_planning}, execution={decision.requires_execution}")
        return decision


reasoning_engine = ReasoningEngine()
