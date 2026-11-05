from types import SimpleNamespace

import research_studio.providers as providers


def test_factory_defaults_to_gemini_and_duckduckgo():
    settings = SimpleNamespace(
        llm_provider="gemini",
        gemini_api_key="test-key",
        gemini_model="gemini-3.8-flash",
        openai_api_key="",
        openai_model="gpt-4.1-mini",
        tavily_api_key="",
    )

    assert isinstance(providers.create_llm_provider(settings), providers.GeminiLLMProvider)
    assert isinstance(providers.create_search_provider(settings), providers.DuckDuckGoSearchProvider)


def test_openai_and_tavily_remain_optional_choices():
    settings = SimpleNamespace(
        llm_provider="openai",
        gemini_api_key="",
        gemini_model="gemini-3.8-flash",
        openai_api_key="test-openai-key",
        openai_model="gpt-4.1-mini",
        tavily_api_key="test-tavily-key",
    )

    assert isinstance(providers.create_llm_provider(settings), providers.OpenAILLMProvider)
    assert isinstance(providers.create_search_provider(settings), providers.TavilySearchProvider)


def test_duckduckgo_results_are_normalized(monkeypatch):
    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def text(self, query, max_results):
            assert query == "agentic AI"
            assert max_results == 2
            return [{
                "title": "Research article",
                "href": "https://example.org/article",
                "body": "A short result snippet.",
            }]

    monkeypatch.setattr(providers, "DDGS", FakeDDGS)
    results = providers.DuckDuckGoSearchProvider().search("agentic AI", max_results=2)

    assert results == [{
        "title": "Research article",
        "url": "https://example.org/article",
        "content": "A short result snippet.",
    }]


def test_unknown_llm_provider_fails_with_actionable_message():
    settings = SimpleNamespace(llm_provider="unknown")
    try:
        providers.create_llm_provider(settings)
    except ValueError as exc:
        assert "Choose 'gemini' or 'openai'" in str(exc)
    else:
        raise AssertionError("Unsupported providers must be rejected.")
