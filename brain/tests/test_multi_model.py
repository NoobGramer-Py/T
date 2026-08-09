"""
Unit tests for Multi-Model Brain, Task Classifier, Provider Health Tracker, and Model Router.
"""

import unittest
import asyncio
from typing import AsyncGenerator, Optional
from brain.core.providers.base import (
    AIProvider,
    AIRequest,
    ModelMetadata,
    RateLimitError,
    ServiceUnavailableError,
)
from brain.core.model_registry import ModelRegistry
from brain.core.task_classifier import TaskClassifier
from brain.core.provider_health import ProviderHealthTracker
from brain.core.model_router import ModelRouter


class MockProvider(AIProvider):
    def __init__(self, pid: str, name: str, models: list, fail_count: int = 0) -> None:
        super().__init__(pid, name)
        self._models = models
        self.fail_count = fail_count
        self.calls = 0

    async def is_available(self) -> bool:
        return True

    async def get_models(self) -> list:
        return self._models

    async def stream_chat(
        self,
        request: AIRequest,
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise RateLimitError(f"Mock rate limit for {self.provider_id}")
        yield f"Response from {self.name} ({model_name})"


class TestMultiModelBrain(unittest.TestCase):

    def test_model_registry(self):
        reg = ModelRegistry()
        m1 = ModelMetadata(provider="grok", model="grok-2-latest", capabilities=["coding"])
        m2 = ModelMetadata(provider="gemini", model="gemini-2.5-flash", capabilities=["reasoning"])
        reg.register_model(m1)
        reg.register_model(m2)

        self.assertEqual(len(reg.get_all_models()), 2)
        coding_models = reg.get_models_by_capability("coding")
        self.assertEqual(len(coding_models), 1)
        self.assertEqual(coding_models[0].provider, "grok")

    def test_task_classifier(self):
        classifier = TaskClassifier()

        res_coding = classifier.classify([{"role": "user", "content": "How do I fix this python code bug?"}])
        self.assertEqual(res_coding.type, "coding")

        res_reasoning = classifier.classify([{"role": "user", "content": "Why is the sky blue? Explain the logic."}])
        self.assertEqual(res_reasoning.type, "reasoning")

        res_fast = classifier.classify([{"role": "user", "content": "hello"}])
        self.assertEqual(res_fast.type, "fast_response")

        res_local = classifier.classify([{"role": "user", "content": "This is private local data."}])
        self.assertEqual(res_local.privacy, "local_only")

    def test_provider_health_tracker(self):
        tracker = ProviderHealthTracker(default_cooldown_seconds=0.2)
        tracker.record_success("grok", "grok-2-latest")
        self.assertTrue(tracker.is_healthy("grok"))

        tracker.record_failure("grok", "grok-2-latest", "rate_limit")
        self.assertFalse(tracker.is_healthy("grok"))

        # Wait for cooldown to expire
        asyncio.run(asyncio.sleep(0.25))
        self.assertTrue(tracker.is_healthy("grok"))

    def test_model_router_failover(self):
        router = ModelRouter()
        reg = ModelRegistry()
        router._initialized = True

        # Mock providers where candidate 1 fails with rate limit, candidate 2 succeeds
        p1 = MockProvider(
            "grok", "Grok",
            [ModelMetadata("grok", "grok-2-latest", ["general_chat"], priority=1)],
            fail_count=1,
        )
        p2 = MockProvider(
            "gemini", "Gemini",
            [ModelMetadata("gemini", "gemini-2.5-flash", ["general_chat"], priority=2)],
            fail_count=0,
        )

        reg.register_provider(p1)
        reg.register_provider(p2)
        for m in [p1._models[0], p2._models[0]]:
            reg.register_model(m)

        async def run_chat():
            chunks = []
            providers_used = []
            switches = []
            async for chunk, pid, switch_evt in router.stream_chat([{"role": "user", "content": "hello"}]):
                chunks.append(chunk)
                providers_used.append(pid)
                if switch_evt:
                    switches.append(switch_evt)
            return chunks, providers_used, switches

        # Note: We temporarily point global registry/health to our local setup
        from brain.core.model_registry import model_registry
        from brain.core.provider_health import health_tracker
        old_models = model_registry.get_all_models()
        model_registry.providers = reg.providers
        model_registry.models = reg.models

        chunks, providers_used, switches = asyncio.run(run_chat())

        # Reset global model_registry
        model_registry.models = old_models

        self.assertTrue(len(chunks) > 0)
        self.assertIn("Gemini", chunks[0])
        self.assertEqual(providers_used[0], "gemini")
        self.assertEqual(len(switches), 1)
        self.assertEqual(switches[0]["previous_provider"], "grok")
        self.assertEqual(switches[0]["active_provider"], "gemini")


if __name__ == "__main__":
    unittest.main()
