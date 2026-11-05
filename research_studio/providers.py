from __future__ import annotations
import requests
from openai import OpenAI

class SearchProvider:
    """Tavily adapter kept separate so the search backend is replaceable."""
    def __init__(self,api_key:str): self.api_key=api_key
    def search(self,query:str,max_results:int=5)->list[dict]:
        response=requests.post("https://api.tavily.com/search",json={"api_key":self.api_key,"query":query,"search_depth":"advanced","max_results":max_results,"include_answer":False},timeout=30)
        response.raise_for_status()
        return response.json().get("results",[])

class LLMProvider:
    def __init__(self,api_key:str,model:str):
        self.client=OpenAI(api_key=api_key);self.model=model
    def complete(self,system:str,user:str)->str:
        response=self.client.chat.completions.create(model=self.model,temperature=0.2,messages=[{"role":"system","content":system},{"role":"user","content":user}])
        return response.choices[0].message.content or ""
