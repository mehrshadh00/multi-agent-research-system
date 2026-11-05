from __future__ import annotations

from typing import Protocol

import requests
from ddgs import DDGS
from google import genai
from google.genai import types
from openai import OpenAI


class SearchBackend(Protocol):
    def search(self, query: str, max_results: int = 5) -> list[dict]: ...


class LLMBackend(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class DuckDuckGoSearchProvider:
    """Credential-free web search using DuckDuckGo's public text results."""

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        with DDGS() as client:
            results = client.text(query, max_results=max_results)
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("href", ""),
                "content": item.get("body", ""),
            }
            for item in results
        ]


class TavilySearchProvider:
    """Optional Tavily adapter for users who already have a Tavily key."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self.api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("results", [])


class GeminiLLMProvider:
    """Google Gemini Developer API adapter (supports its free tier)."""

    def __init__(self, api_key: str, model: str = "gemini-3.8-flash"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing. Add a free Gemini API key to continue.")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.2,
            ),
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return text


class OpenAILLMProvider:
    """Optional paid OpenAI adapter retained for users with an API key."""

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


def create_search_provider(settings) -> SearchBackend:
    """Prefer Tavily when configured; otherwise use keyless DuckDuckGo search."""
    if settings.tavily_api_key:
        return TavilySearchProvider(settings.tavily_api_key)
    return DuckDuckGoSearchProvider()


def create_llm_provider(settings) -> LLMBackend:
    """Choose the configured model provider without coupling the orchestrator to an SDK."""
    provider = settings.llm_provider.strip().lower()
    if provider == "gemini":
        return GeminiLLMProvider(settings.gemini_api_key, settings.gemini_model)
    if provider == "openai":
        return OpenAILLMProvider(settings.openai_api_key, settings.openai_model)
    raise ValueError(
        f"Unsupported LLM_PROVIDER '{provider}'. Choose 'gemini' or 'openai'."
    )
