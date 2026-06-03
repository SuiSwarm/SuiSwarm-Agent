from dotenv import load_dotenv
from langchain_tavily import TavilySearch


load_dotenv()


tavily_search = TavilySearch(
    max_results=5,
    topic="general",
    include_answer=True,
    search_depth="basic",
)

