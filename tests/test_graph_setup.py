import unittest

from suiswarm_agent.graph.builder import route_after_plan
from suiswarm_agent.graph.nodes import execute_tools
from suiswarm_agent.schemas import PlanDecision, ToolPlanStep
from suiswarm_agent.graph import graph
from suiswarm_agent.tools import TOOL_REGISTRY


class GraphSetupTest(unittest.TestCase):
    def test_graph_imports(self) -> None:
        self.assertIsNotNone(graph)

    def test_expected_tools_are_registered(self) -> None:
        self.assertIn("coingecko_search_coin_market", TOOL_REGISTRY)
        self.assertIn("coingecko_search", TOOL_REGISTRY)
        self.assertIn("coingecko_trending", TOOL_REGISTRY)
        self.assertIn("coingecko_top_movers", TOOL_REGISTRY)
        self.assertIn("coingecko_token_price_by_contract", TOOL_REGISTRY)
        self.assertIn("coingecko_global_market", TOOL_REGISTRY)
        self.assertIn("coingecko_nft_details", TOOL_REGISTRY)
        self.assertIn("geckoterminal_onchain_token_price", TOOL_REGISTRY)
        self.assertIn("geckoterminal_trending_pools", TOOL_REGISTRY)
        self.assertIn("tavily_search", TOOL_REGISTRY)
        self.assertIn("get_utc_time", TOOL_REGISTRY)
        self.assertIn("describe_project", TOOL_REGISTRY)

    def test_route_after_plan_supports_multi_tool_plan(self) -> None:
        state = {
            "plan": PlanDecision(
                action="use_tools",
                reasoning="Need multiple tools.",
                tool_steps=[
                    ToolPlanStep(
                        tool_name="get_utc_time",
                        tool_input={},
                        reason="Need current UTC time.",
                    )
                ],
            )
        }

        self.assertEqual(route_after_plan(state), "execute_tools")

    def test_execute_tools_runs_multiple_steps(self) -> None:
        state = {
            "plan": PlanDecision(
                action="use_tools",
                reasoning="Use two simple local tools.",
                tool_steps=[
                    ToolPlanStep(
                        tool_name="get_utc_time",
                        tool_input={},
                        reason="Need current UTC time.",
                    ),
                    ToolPlanStep(
                        tool_name="describe_project",
                        tool_input={},
                        reason="Need project description.",
                    ),
                ],
            )
        }

        result = execute_tools(state)

        self.assertIsNone(result["tool_error"])
        self.assertEqual(len(result["tool_results"]), 2)
        self.assertEqual(result["tool_results"][0].tool_name, "get_utc_time")
        self.assertEqual(result["tool_results"][1].tool_name, "describe_project")


if __name__ == "__main__":
    unittest.main()
