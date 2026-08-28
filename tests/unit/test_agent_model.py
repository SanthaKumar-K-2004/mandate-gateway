"""
S02.1 — Model Adapter & Test Model Unit Tests.
"""

import unittest

from agent.graph.errors import AgentModelError, AgentTimeoutError
from agent.graph.types import AgentMessage, AgentMessageType
from agent.models.interface import ModelRequest, ModelResponse
from agent.models.test_model import TestModelAdapter


class TestModelAdapterUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = TestModelAdapter()

    def test_scripted_responses(self) -> None:
        r1 = ModelResponse(content="Step 1 response", finish_reason="stop")
        r2 = ModelResponse(content="Step 2 response", finish_reason="stop")
        self.adapter.set_scripted_responses([r1, r2])

        req = ModelRequest(
            messages=[AgentMessage(message_type=AgentMessageType.USER, content="Hello")]
        )

        res1 = self.adapter.generate(req)
        self.assertEqual(res1.content, "Step 1 response")

        res2 = self.adapter.generate(req)
        self.assertEqual(res2.content, "Step 2 response")

        self.assertEqual(len(self.adapter.request_history), 2)

    def test_simulated_timeout(self) -> None:
        self.adapter.set_simulate_timeout(True)
        req = ModelRequest(
            messages=[AgentMessage(message_type=AgentMessageType.USER, content="Hello")]
        )
        with self.assertRaises(AgentTimeoutError):
            self.adapter.generate(req)

    def test_simulated_model_error(self) -> None:
        self.adapter.set_simulate_model_failure(True, "API rate limit exceeded")
        req = ModelRequest(
            messages=[AgentMessage(message_type=AgentMessageType.USER, content="Hello")]
        )
        with self.assertRaises(AgentModelError) as ctx:
            self.adapter.generate(req)
        self.assertIn("API rate limit exceeded", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
