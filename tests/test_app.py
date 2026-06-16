import app
from app import handle_query


def test_handle_query_empty_input():
    listing, price, trend, outfit, fit_card, profile_text, profile = handle_query("", "Example wardrobe")

    assert "Tell me what thrifted item" in listing
    assert price == ""
    assert trend == ""
    assert outfit == ""
    assert fit_card == ""
    assert "No saved preferences" in profile_text
    assert profile["interactions"] == 0


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

    def fake_run_agent(query, wardrobe, style_profile=None):
        return {
            "query": query,
            "parsed": {},
            "search_results": [selected_item],
            "selected_item": selected_item,
            "wardrobe": wardrobe,
            "price_assessment": "Price check: fair price.",
            "trend_context": "Trend: soft grunge revival.",
            "outfit_suggestion": "Pair it with baggy jeans.",
            "fit_card": "Depop tee fit card.",
            "retry": None,
            "retry_note": None,
            "style_profile_after": {
                "preferred_tags": ["vintage"],
                "preferred_colors": ["black"],
                "preferred_categories": ["tops"],
                "interactions": 1,
            },
            "error": None,
        }

    monkeypatch.setattr(app, "run_agent", fake_run_agent)

    listing, price, trend, outfit, fit_card, profile_text, profile = handle_query(
        "vintage graphic tee",
        "Example wardrobe",
    )

    assert "Vintage Graphic Tee" in listing
    assert "Price: $24" in listing
    assert "Platform: depop" in listing
    assert price == "Price check: fair price."
    assert trend == "Trend: soft grunge revival."
    assert outfit == "Pair it with baggy jeans."
    assert fit_card == "Depop tee fit card."
    assert "Preferred style tags: vintage" in profile_text
    assert profile["interactions"] == 1


def test_handle_query_maps_error_to_first_panel(monkeypatch):
    monkeypatch.setattr(
        app,
        "run_agent",
        lambda query, wardrobe, style_profile=None: {
            "selected_item": None,
            "outfit_suggestion": None,
            "fit_card": None,
            "style_profile_after": style_profile,
            "error": "No listings found.",
        },
    )

    listing, price, trend, outfit, fit_card, profile_text, profile = handle_query(
        "designer ballgown",
        "Empty wardrobe (new user)",
    )

    assert listing == "No listings found."
    assert price == ""
    assert trend == ""
    assert outfit == ""
    assert fit_card == ""
    assert "No saved preferences" in profile_text
    assert profile["interactions"] == 0
