"""
Task Planning & Step Decomposition Subsystem for T AI Operating System.
Transforms high-level decisions into structured, executable step graphs (DAGs).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from brain.logging.logger import get_logger

log = get_logger("planning.planner")


@dataclass
class PlanStep:
    """Individual executable step within a TaskPlan."""
    step_id: int
    title: str
    action_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    completed: bool = False
    error: Optional[str] = None


@dataclass
class TaskPlan:
    """Structured plan composed of ordered PlanSteps."""
    plan_id: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)

    def is_complete(self) -> bool:
        return all(s.completed for s in self.steps)


class TaskPlanner:
    """Decomposes goal intents into structured execution plans."""

    async def create_plan(self, goal: str, context: Dict[str, Any]) -> TaskPlan:
        """Generates a multi-step task plan for a given goal."""
        log.info(f"Generating task plan for goal: '{goal}'")
        
        # Prototype step decomposition (expandable via model reasoning)
        steps = [
            PlanStep(step_id=1, title="Validate security policy & permissions", action_type="permission_check"),
            PlanStep(step_id=2, title="Simulate execution sandbox", action_type="simulate_action"),
            PlanStep(step_id=3, title="Execute target operation", action_type="run_execution"),
        ]

        plan = TaskPlan(
            plan_id=f"plan_{int(context.get('timestamp', 1000))}",
            goal=goal,
            steps=steps,
        )
        return plan


task_planner = TaskPlanner()
