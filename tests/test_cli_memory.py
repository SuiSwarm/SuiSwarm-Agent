import unittest

from langchain_core.messages import HumanMessage

from suiswarm_agent.cli import SESSION_MESSAGE_LIMIT, trim_session_messages


class CliMemoryTest(unittest.TestCase):
    def test_trim_session_messages_keeps_most_recent_100_messages(self) -> None:
        messages = [HumanMessage(content=f"message-{index}") for index in range(120)]

        trimmed = trim_session_messages(messages)

        self.assertEqual(len(trimmed), SESSION_MESSAGE_LIMIT)
        self.assertEqual(trimmed[0].content, "message-20")
        self.assertEqual(trimmed[-1].content, "message-119")


if __name__ == "__main__":
    unittest.main()

