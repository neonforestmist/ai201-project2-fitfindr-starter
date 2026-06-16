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
        "style_tags": ["vintage", "graphic tee"],
        "colors": ["black"],
        "category": "tops",
    }
    wardrobe = {"items": [{"name": "Baggy jeans", "category": "bottoms"}]}
    calls = {}

    def fake_search(description, size, max_price):
        calls["search"] = (description, size, max_price)
        return [selected_item]

    def fake_outfit(new_item, passed_wardrobe, trend_context=None, style_profile=None):
        calls["outfit"] = (new_item, passed_wardrobe, trend_context, style_profile)
        return "Pair it with Baggy jeans and chunky sneakers."

    def fake_fit_card(outfit, new_item):
        calls["fit_card"] = (outfit, new_item)
        return "Thrifted tee fit card."

    monkeypatch.setattr(agent, "search_listings", fake_search)
    monkeypatch.setattr(agent, "suggest_outfit", fake_outfit)
    monkeypatch.setattr(agent, "create_fit_card", fake_fit_card)
    monkeypatch.setattr(agent, "compare_price", lambda new_item: "fair price")
    monkeypatch.setattr(agent, "get_trend_context", lambda new_item: "Trend: soft grunge")

    session = run_agent("vintage graphic tee under $30", wardrobe)

    assert session["error"] is None
    assert calls["search"] == ("vintage graphic tee", None, 30.0)
    assert session["selected_item"] is selected_item
    assert calls["outfit"] == (selected_item, wardrobe, "Trend: soft grunge", session["style_profile_before"])
    assert calls["fit_card"] == (session["outfit_suggestion"], selected_item)
    assert session["fit_card"] == "Thrifted tee fit card."
    assert session["price_assessment"] == "fair price"
    assert session["trend_context"] == "Trend: soft grunge"
    assert "vintage" in session["style_profile_after"]["preferred_tags"]


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


def test_run_agent_retries_with_loosened_constraints(monkeypatch):
    selected_item = {
        "title": "90s Track Jacket",
        "price": 45.0,
        "platform": "poshmark",
        "style_tags": ["90s", "athletic"],
        "colors": ["navy"],
        "category": "outerwear",
    }
    calls = []

    def fake_search(description, size, max_price):
        calls.append((description, size, max_price))
        if len(calls) == 1:
            return []
        return [selected_item]

    monkeypatch.setattr(agent, "search_listings", fake_search)
    monkeypatch.setattr(agent, "suggest_outfit", lambda *args, **kwargs: "Layer it over a plain tee.")
    monkeypatch.setattr(agent, "create_fit_card", lambda *args, **kwargs: "Track jacket fit card.")
    monkeypatch.setattr(agent, "compare_price", lambda new_item: "fair price")
    monkeypatch.setattr(agent, "get_trend_context", lambda new_item: "Trend: track-layer nostalgia")

    session = run_agent("90s track jacket size XXS under $5", {"items": []})

    assert session["error"] is None
    assert calls == [
        ("90s track jacket", "XXS", 5.0),
        ("90s track jacket", None, None),
    ]
    assert session["retry"]["results_found"] == 1
    assert "automatically retried" in session["retry_note"]
    assert session["selected_item"] is selected_item
    assert session["fit_card"] == "Track jacket fit card."


def test_run_agent_uses_style_profile_from_previous_interaction(monkeypatch):
    selected_item = {
        "title": "Classic Canvas Sneakers",
        "price": 20.0,
        "platform": "depop",
        "style_tags": ["classic", "streetwear"],
        "colors": ["white"],
        "category": "shoes",
    }
    seen_profile = {}

    monkeypatch.setattr(agent, "search_listings", lambda *args, **kwargs: [selected_item])
    monkeypatch.setattr(agent, "compare_price", lambda new_item: "good deal")
    monkeypatch.setattr(agent, "get_trend_context", lambda new_item: "Trend: chunky shoe comeback")

    def fake_outfit(new_item, wardrobe, trend_context=None, style_profile=None):
        seen_profile.update(style_profile)
        return "Use the saved vintage preference with cuffed denim."

    monkeypatch.setattr(agent, "suggest_outfit", fake_outfit)
    monkeypatch.setattr(agent, "create_fit_card", lambda *args, **kwargs: "Sneaker fit card.")

    first_profile = {
        "preferred_tags": ["vintage", "streetwear"],
        "preferred_colors": ["black"],
        "preferred_categories": ["tops"],
        "interactions": 1,
    }
    session = run_agent("canvas sneakers under $30", {"items": []}, style_profile=first_profile)

    assert seen_profile["preferred_tags"] == ["vintage", "streetwear"]
    assert session["style_profile_after"]["interactions"] == 2
    assert "shoes" in session["style_profile_after"]["preferred_categories"]


def test_run_agent_empty_query_returns_error(monkeypatch):
    def should_not_run(*args, **kwargs):
        raise AssertionError("Tools should not run for an empty query.")

    monkeypatch.setattr(agent, "search_listings", should_not_run)

    session = run_agent("   ", {"items": []})

    assert session["error"] == "Tell me what thrifted item you want to search for."
    assert session["parsed"] == {}
