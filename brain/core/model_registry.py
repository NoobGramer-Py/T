"""
Central Model Registry for T AI Operating System.
Manages registered AI model capabilities, priorities, local/cloud attributes, and metadata.
"""

from typing import Dict, List, Optional
from brain.core.providers.base import AIProvider, ModelMetadata
from brain.logging.logger import get_logger

log = get_logger("core.model_registry")


class ModelRegistry:
    """Central registry holding metadata and provider references for all supported models."""

    def __init__(self) -> None:
        self.providers: Dict[str, AIProvider] = {}
        self.models: List[ModelMetadata] = []

    def register_provider(self, provider: AIProvider) -> None:
        """Register an AIProvider instance."""
        self.providers[provider.provider_id] = provider
        log.debug(f"Registered provider: {provider.name} ({provider.provider_id})")

    def register_model(self, model_meta: ModelMetadata) -> None:
        """Register or update a model metadata entry."""
        # Replace if model with same provider & name exists
        self.models = [
            m for m in self.models if not (m.provider == model_meta.provider and m.model == model_meta.model)
        ]
        self.models.append(model_meta)

    def get_provider(self, provider_id: str) -> Optional[AIProvider]:
        return self.providers.get(provider_id)

    def get_all_models(self) -> List[ModelMetadata]:
        return list(self.models)

    def get_models_for_provider(self, provider_id: str) -> List[ModelMetadata]:
        return [m for m in self.models if m.provider == provider_id]

    def get_models_by_capability(self, capability: str) -> List[ModelMetadata]:
        """Find models supporting specific capability (e.g., 'coding', 'reasoning', 'local')."""
        return [m for m in self.models if capability in m.capabilities and m.enabled]

    def set_model_enabled(self, provider_id: str, model_name: str, enabled: bool) -> None:
        for m in self.models:
            if m.provider == provider_id and m.model == model_name:
                m.enabled = enabled


model_registry = ModelRegistry()
