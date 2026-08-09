"""
Central Operating System Kernel for T AI Operating System.
Orchestrates all OS modules, handles request lifecycles, enforces permissions,
and manages event routing across the system.
"""

import asyncio
from typing import Dict, Any, AsyncGenerator, Optional

from brain.config.config import config
from brain.core.event_bus import event_bus, Event
from brain.core.state_manager import state_manager
from brain.core.health_monitor import health_monitor
from brain.core.module_loader import module_loader
from brain.core.llm import llm_router
from brain.security.permission_manager import permission_manager
from brain.memory.manager import memory_manager
from brain.reasoning.engine import reasoning_engine
from brain.planning.planner import task_planner
from brain.execution.runner import execution_engine
from brain.conversation.manager import dialogue_manager
from brain.telemetry.metrics import metrics
from brain.logging.logger import get_logger

log = get_logger("core.engine")


class SystemKernel:
    """Core Brain Engine coordinating all subsystems for T AI OS."""

    def __init__(self) -> None:
        self.initialized = False

    async def boot(self) -> None:
        """Boots up the T AI Operating System Kernel and initializes modules."""
        if self.initialized:
            return

        log.info("Booting T AI Operating System Kernel...")
        state_manager.set("status", "booting", sender="kernel")

        # Register core modules with module loader
        module_loader.register("memory", memory_manager)
        module_loader.register("reasoning", reasoning_engine)
        module_loader.register("planning", task_planner)
        module_loader.register("execution", execution_engine)

        await module_loader.initialize_all()
        await llm_router.initialize()

        health_monitor.update_status("kernel", "operational", "ok")
        state_manager.set("status", "operational", sender="kernel")
        self.initialized = True
        log.info("T AI Operating System Kernel is operational.")

        await event_bus.publish(Event(name="kernel_boot_complete", sender="kernel", data=state_manager.snapshot()))

    async def process_user_query(
        self,
        query: str,
        user_authorized: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main request pipeline:
        1. Context assembly (Memory)
        2. Cognitive evaluation (Reasoning)
        3. Step generation (Planning - if needed)
        4. Safe execution (Execution - if needed)
        5. Streamed response generation (LLM Router)
        """
        metrics.increment("user_queries_total")
        start_time = asyncio.get_event_loop().time()

        # 1. Assemble memory context
        memory_ctx = await memory_manager.build_context(query)
        memory_manager.short_term.add_message("user", query)

        # 2. Reasoning decision
        decision = await reasoning_engine.evaluate(query, memory_ctx)

        # 3. Planning & Execution if required
        if decision.requires_execution:
            yield {"type": "status", "content": "Evaluating execution safety & policy permissions..."}
            exec_res = await execution_engine.execute_action(
                action_type="open_url" if "http" in query or "youtube" in query.lower() or "google" in query.lower() else "system_execution",
                resource=query,
                params={"query": query},
                user_authorized=user_authorized
            )
            yield {
                "type": "execution_result",
                "success": exec_res.success,
                "action": exec_res.action_type,
                "output": exec_res.output,
                "error": exec_res.error
            }

        # 4. Stream language response from LLM router
        prompt_ctx = dialogue_manager.format_prompt_context(memory_ctx)
        full_response = ""

        yield {"type": "status", "content": "Generating response..."}
        try:
            messages = memory_manager.short_term.get_messages(limit=10)
            async for chunk, provider, switch_evt in llm_router.stream_chat(
                messages=messages,
                system_prompt=prompt_ctx if prompt_ctx else "You are T AI OS."
            ):
                if switch_evt:
                    yield switch_evt
                full_response += chunk
                yield {"type": "token", "chunk": chunk, "provider": provider}
        except Exception as e:
            log.error("Error generating LLM stream response", exc_info=True)
            yield {"type": "error", "message": str(e)}

        if full_response:
            memory_manager.short_term.add_message("assistant", full_response)

        duration = asyncio.get_event_loop().time() - start_time
        metrics.record_latency("user_query_processing", duration)

    async def shutdown(self) -> None:
        """Gracefully shuts down the OS Kernel."""
        log.info("Shutting down T AI Operating System Kernel...")
        state_manager.set("status", "shutting_down", sender="kernel")
        await module_loader.shutdown_all()
        health_monitor.update_status("kernel", "shutdown", "ok")
        log.info("Shutdown complete.")


kernel = SystemKernel()
