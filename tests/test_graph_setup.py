import unittest

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


if __name__ == "__main__":
    unittest.main()
