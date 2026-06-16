import app
from app import handle_query


def test_handle_query_empty_input():
    listing, outfit, fit_card = handle_query("", "Example wardrobe")

    assert "Tell me what thrifted item" in listing
    assert outfit == ""
    assert fit_card == ""


def test_handle_query_formats_success(monkeypatch):
    selected_item = {
        "title": "Vintage Graphic Tee",
        "description": "Soft faded tee with a vintage graphic.",
        "size": "M",
        "condition": "good",
        "price": 24.0,
        "colors": ["black"],
        "brand": None,
        "platform": "depop",
        "style_tags": ["vintage", "graphic tee"],
    }

    def fake_run_agent(query, wardrobe):
        return {
            "query": query,
            "parsed": {},
            "search_results": [selected_item],
            "selected_item": selected_item,
            "wardrobe": wardrobe,
            "outfit_suggestion": "Pair it with baggy jeans.",
            "fit_card": "Depop tee fit card.",
            "error": None,
        }

    monkeypatch.setattr(app, "run_agent", fake_run_agent)

    listing, outfit, fit_card = handle_query("vintage graphic tee", "Example wardrobe")

    assert "Vintage Graphic Tee" in listing
    assert "Price: $24" in listing
    assert "Platform: depop" in listing
    assert outfit == "Pair it with baggy jeans."
    assert fit_card == "Depop tee fit card."


def test_handle_query_maps_error_to_first_panel(monkeypatch):
    monkeypatch.setattr(
        app,
        "run_agent",
        lambda query, wardrobe: {
            "selected_item": None,
            "outfit_suggestion": None,
            "fit_card": None,
            "error": "No listings found.",
        },
    )

    listing, outfit, fit_card = handle_query("designer ballgown", "Empty wardrobe (new user)")

    assert listing == "No listings found."
    assert outfit == ""
    assert fit_card == ""
