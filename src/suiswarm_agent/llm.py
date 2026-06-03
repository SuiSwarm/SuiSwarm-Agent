from langchain_openai import ChatOpenAI

from suiswarm_agent.settings import get_settings


def build_chat_model(*, temperature: float = 0.2) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
    )

