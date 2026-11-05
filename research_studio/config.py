from __future__ import annotations
import os
from dataclasses import dataclass
import streamlit as st

def _secret(name: str) -> str:
    value=os.getenv(name,"")
    if value: return value
    try: return str(st.secrets.get(name,""))
    except (FileNotFoundError,KeyError): return ""

@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    tavily_api_key: str
    openai_model: str="gpt-4.1-mini"

settings=Settings(_secret("OPENAI_API_KEY"),_secret("TAVILY_API_KEY"),os.getenv("OPENAI_MODEL","gpt-4.1-mini"))
