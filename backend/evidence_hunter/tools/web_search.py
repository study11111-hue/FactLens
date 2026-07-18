"""
WebSearch Tool
Searches the web for evidence using the Tavily AI API.
"""

import json
import os

from pydantic import BaseModel, Field


class WebSearch(BaseModel):
    """
    Searches the web for evidence related to a factual claim
    using the Tavily AI API. Returns structured search results
    with titles, URLs, and content snippets.
    """

    query: str = Field(
        ...,
        description=(
            "The search query to find evidence. Should be focused on "
            "the core factual assertion of the claim."
        ),
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of search results to return.",
    )

    def run(self) -> str:
        """Execute web search via Tavily AI."""
        api_key = os.getenv("TAVILY_API_KEY", "")

        if not api_key:
            return json.dumps({
                "error": "TAVILY_API_KEY not set",
                "results": [],
            })

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)

            response = client.search(
                query=self.query,
                max_results=self.max_results,
                search_depth="basic",
                include_answer=True,
            )

            results = []
            for r in response.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                })

            output = {
                "query": self.query,
                "answer": response.get("answer", ""),
                "results": results,
            }

            return json.dumps(output, indent=2)

        except Exception as e:
            return json.dumps({
                "error": str(e),
                "query": self.query,
                "results": [],
            })
