"""
Automated Unit Tests for T AI OS Reasoning & Planning Subsystems.
"""

import unittest
import asyncio
from brain.reasoning.engine import ReasoningEngine
from brain.planning.planner import TaskPlanner


class TestReasoningSubsystem(unittest.TestCase):

    def test_reasoning_eval(self):
        async def _test():
            re = ReasoningEngine()
            decision = await re.evaluate("Please execute terminal command", {})
            self.assertTrue(decision.requires_execution)
            self.assertEqual(decision.intent, "execute_action")

        asyncio.run(_test())

    def test_task_planner(self):
        async def _test():
            tp = TaskPlanner()
            plan = await tp.create_plan("Deploy distributed node", {})
            self.assertGreater(len(plan.steps), 0)
            self.assertEqual(plan.goal, "Deploy distributed node")

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
