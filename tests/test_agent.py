import agent
from agent import _parse_query, run_agent


def test_parse_query_extracts_description_size_and_price():
    parsed = _parse_query(
        "I'm looking for a vintage graphic tee under $30, size M. "
        "I mostly wear baggy jeans."
    )

    assert parsed == {
        "description": "a vintage graphic tee",
        "size": "M",
        "max_price": 30.0,
    }


def test_run_agent_happy_path_passes_state(monkeypatch):
    selected_item = {
        "title": "Vintage Graphic Tee",
        "price": 24.0,
        "platform": "depop",
    }
    wardrobe = {"items": [{"name": "Baggy jeans", "category": "bottoms"}]}
    calls = {}

    def fake_search(description, size, max_price):
        calls["search"] = (description, size, max_price)
        return [selected_item]

    def fake_outfit(new_item, passed_wardrobe):
        calls["outfit"] = (new_item, passed_wardrobe)
        return "Pair it with Baggy jeans and chunky sneakers."

    def fake_fit_card(outfit, new_item):
        calls["fit_card"] = (outfit, new_item)
        return "Thrifted tee fit card."

    monkeypatch.setattr(agent, "search_listings", fake_search)
    monkeypatch.setattr(agent, "suggest_outfit", fake_outfit)
    monkeypatch.setattr(agent, "create_fit_card", fake_fit_card)

    session = run_agent("vintage graphic tee under $30", wardrobe)

    assert session["error"] is None
    assert calls["search"] == ("vintage graphic tee", None, 30.0)
    assert session["selected_item"] is selected_item
    assert calls["outfit"] == (selected_item, wardrobe)
    assert calls["fit_card"] == (session["outfit_suggestion"], selected_item)
    assert session["fit_card"] == "Thrifted tee fit card."


def test_run_agent_stops_after_empty_search(monkeypatch):
    def fake_search(description, size, max_price):
        return []

    def should_not_run(*args, **kwargs):
        raise AssertionError("Later tools should not run after empty search.")

    monkeypatch.setattr(agent, "search_listings", fake_search)
    monkeypatch.setattr(agent, "suggest_outfit", should_not_run)
    monkeypatch.setattr(agent, "create_fit_card", should_not_run)

    session = run_agent("designer ballgown size XXS under $5", {"items": []})

    assert session["error"]
    assert session["search_results"] == []
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None


def test_run_agent_empty_query_returns_error(monkeypatch):
    def should_not_run(*args, **kwargs):
        raise AssertionError("Tools should not run for an empty query.")

    monkeypatch.setattr(agent, "search_listings", should_not_run)

    session = run_agent("   ", {"items": []})

    assert session["error"] == "Tell me what thrifted item you want to search for."
    assert session["parsed"] == {}
