import unittest

from suiswarm_agent.graph import graph
from suiswarm_agent.tools import TOOL_REGISTRY


class GraphSetupTest(unittest.TestCase):
    def test_graph_imports(self) -> None:
        self.assertIsNotNone(graph)

    def test_expected_tools_are_registered(self) -> None:
        self.assertIn("tavily_search", TOOL_REGISTRY)
        self.assertIn("get_utc_time", TOOL_REGISTRY)
        self.assertIn("describe_project", TOOL_REGISTRY)


if __name__ == "__main__":
    unittest.main()

