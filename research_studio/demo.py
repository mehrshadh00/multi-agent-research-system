from __future__ import annotations

def demo_result(topic:str,depth:str,audience:str)->dict:
    """Fictional preview data: deliberately not represented as factual research."""
    tracks=["Landscape and key concepts","Current approaches and capabilities","Limitations, risks and open questions","Practical implications"]
    sources=[
      {"title":"Illustrative source card — research overview","url":"https://example.com/research-overview","snippet":"Placeholder evidence used to demonstrate the interface. This is not a real source.","domain":"example.com","quality":"DEMO · fictional"},
      {"title":"Illustrative source card — technical perspective","url":"https://example.com/technical-perspective","snippet":"A sample card showing evidence snippets, provenance and links.","domain":"example.com","quality":"DEMO · fictional"},
      {"title":"Illustrative source card — limitations","url":"https://example.com/limitations","snippet":"A placeholder showing how caveats and uncertainty appear alongside evidence.","domain":"example.com","quality":"DEMO · fictional"}]
    audit=["Demo evidence is fictional; no factual conclusion can be drawn.","Live research should verify dates, primary sources and independent corroboration.","Generated summaries can omit context or misinterpret evidence."]
    report=f"""# Research brief: {topic}

> **DEMO MODE — NOT REAL RESEARCH.** This preview illustrates report layout only. It contains no verified findings.

## Executive summary
This sample demonstrates how Aether organizes a question for **{audience}**. Run Live Research before relying on conclusions.

## Research tracks
"""+"\n".join(f"- {track}" for track in tracks)+"""

## Findings
No findings are asserted in Demo Mode. A live run synthesizes claims from retrieved sources and links each claim to evidence IDs.

## Risks and limitations
- Search coverage may be incomplete.
- Source quality and dates require human review.
- Generated summaries can omit context.

## Conclusion
Aether makes the research process inspectable. Human verification remains essential.

## Source register
- [S1] Illustrative source card — not real.
- [S2] Illustrative source card — not real.
- [S3] Illustrative source card — not real.
"""
    events=[{"agent":"Research Director","message":"Split the question into four tracks."},{"agent":"Evidence Researcher","message":"Loaded three illustrative cards (Demo Mode)."},{"agent":"Fact & Bias Auditor","message":"Flagged placeholder evidence and verification requirements."},{"agent":"Synthesis Writer","message":"Generated report preview with explicit disclaimer."}]
    return {"topic":topic,"tracks":tracks,"sources":sources,"audit":audit,"report":report,"events":events,"mode":"demo"}
