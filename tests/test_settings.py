import unittest

from suiswarm_agent.settings import Settings


class SettingsTest(unittest.TestCase):
    def test_openai_model_provider_prefix_is_normalized(self) -> None:
        settings = Settings(
            openai_api_key="test-key",
            openai_model="openai/gpt-4o-mini",
        )

        self.assertEqual(settings.openai_model, "gpt-4o-mini")

    def test_coingecko_api_key_alias_is_supported(self) -> None:
        settings = Settings(
            openai_api_key="test-key",
            COINGECKO_API_KEY="demo-key",
        )

        self.assertEqual(settings.coingecko_demo_api_key, "demo-key")


if __name__ == "__main__":
    unittest.main()
