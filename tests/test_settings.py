import unittest

from suiswarm_agent.settings import Settings


class SettingsTest(unittest.TestCase):
    def test_openai_model_provider_prefix_is_normalized(self) -> None:
        settings = Settings(
            openai_api_key="test-key",
            openai_model="openai/gpt-4o-mini",
        )

        self.assertEqual(settings.openai_model, "gpt-4o-mini")


if __name__ == "__main__":
    unittest.main()

