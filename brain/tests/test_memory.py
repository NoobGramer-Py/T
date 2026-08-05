"""
Automated Unit Tests for T AI OS Memory Subsystem.
"""

import unittest
import asyncio
from brain.memory.short_term import ShortTermMemory
from brain.memory.working_memory import WorkingMemory
from brain.memory.long_term import LongTermMemory


class TestMemorySubsystem(unittest.TestCase):

    def test_short_term_memory(self):
        st = ShortTermMemory(max_messages=5)
        for i in range(10):
            st.add_message("user", f"msg_{i}")
        msgs = st.get_messages()
        self.assertEqual(len(msgs), 5)
        self.assertEqual(msgs[-1]["content"], "msg_9")

    def test_working_memory(self):
        wm = WorkingMemory()
        wm.set_variable("current_step", 2)
        self.assertEqual(wm.get_variable("current_step"), 2)

    def test_long_term_memory(self):
        async def _test():
            lt = LongTermMemory()
            doc_id = await lt.store_doc("OS Architecture", "Ultron design patterns")
            results = await lt.search("Ultron")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["id"], doc_id)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
