"""
AI Model Abstraction and Multi-Provider Routing Subsystem for T AI Operating System.
Re-exports the central ModelRouter and provider components.
"""

from brain.core.providers.base import DEFAULT_SYSTEM_PROMPT, AIProvider
from brain.core.model_router import model_router, ModelRouter

# Backward compatible singleton reference
llm_router = model_router

__all__ = ["DEFAULT_SYSTEM_PROMPT", "AIProvider", "ModelRouter", "llm_router"]
