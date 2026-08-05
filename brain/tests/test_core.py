"""
Automated Unit Tests for T AI OS Core Subsystems.
"""

import unittest
import asyncio
from brain.core.event_bus import EventBus, Event
from brain.core.state_manager import StateManager
from brain.security.permission_manager import PermissionManager


class TestCoreSubsystem(unittest.TestCase):

    def test_event_bus(self):
        bus = EventBus()
        received = []

        async def handler(evt: Event):
            received.append(evt.data.get("val"))

        bus.subscribe("test_event", handler)
        asyncio.run(bus.publish(Event(name="test_event", sender="test", data={"val": 42})))
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], 42)

    def test_state_manager(self):
        sm = StateManager()
        sm.set("status", "running")
        self.assertEqual(sm.get("status"), "running")

    def test_permission_manager(self):
        pm = PermissionManager()
        allowed = pm.is_action_allowed("file_read", "test.txt", user_authorized=True)
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
