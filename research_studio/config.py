from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st


def _secret(name: str, default: str = "") -> str:
    """Read an environment variable first, then Streamlit secrets."""
    value = os.getenv(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, KeyError):
        return default


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    openai_api_key: str
    tavily_api_key: str
    llm_provider: str = "gemini"
    gemini_model: str = "gemini-3.8-flash"
    openai_model: str = "gpt-4.1-mini"

    @property
    def active_llm_api_key(self) -> str:
        if self.llm_provider == "openai":
            return self.openai_api_key
        return self.gemini_api_key

    @property
    def active_llm_model(self) -> str:
        if self.llm_provider == "openai":
            return self.openai_model
        return self.gemini_model


settings = Settings(
    gemini_api_key=_secret("GEMINI_API_KEY"),
    openai_api_key=_secret("OPENAI_API_KEY"),
    tavily_api_key=_secret("TAVILY_API_KEY"),
    llm_provider=_secret("LLM_PROVIDER", "gemini").strip().lower(),
    gemini_model=_secret("GEMINI_MODEL", "gemini-3.8-flash"),
    openai_model=_secret("OPENAI_MODEL", "gpt-4.1-mini"),
)
