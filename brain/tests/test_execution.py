"""
Automated Unit Tests for T AI OS Execution Subsystem.
"""

import unittest
import asyncio
from brain.execution.runner import ExecutionEngine


class TestExecutionSubsystem(unittest.TestCase):

    def test_execution_permission_denied(self):
        async def _test():
            ee = ExecutionEngine()
            res = await ee.execute_action("file_write", "test.txt", {}, user_authorized=False)
            self.assertFalse(res.success)
            self.assertIn("denied", res.error.lower())

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
