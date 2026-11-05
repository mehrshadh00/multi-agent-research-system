from research_studio.demo import demo_result

def test_demo_is_explicitly_labelled():
    result=demo_result("AI in science","Standard","Researchers")
    assert result["mode"]=="demo"
    assert "NOT REAL RESEARCH" in result["report"]
    assert len(result["tracks"])>=3
    assert all("example.com" in source["url"] for source in result["sources"])
    assert [source["id"] for source in result["sources"]] == ["S1", "S2", "S3"]

def test_demo_has_trace_for_each_agent():
    result=demo_result("AI in science","Quick scan","General audience")
    agents={event["agent"] for event in result["events"]}
    assert agents=={"Research Director","Evidence Researcher","Fact & Bias Auditor","Synthesis Writer"}
