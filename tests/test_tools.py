import tools
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def _sample_listing():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert results
    return results[0]


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all("title" in item for item in results)


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)

    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)

    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("track jacket", size="M", max_price=None)

    assert results
    assert all("m" in item["size"].lower() for item in results)


def test_suggest_outfit_empty_wardrobe(monkeypatch):
    monkeypatch.setattr(
        tools,
        "_call_groq",
        lambda *args, **kwargs: "Pair it with wide-leg denim, chunky sneakers, and a simple jacket.",
    )

    result = suggest_outfit(_sample_listing(), get_empty_wardrobe())

    assert isinstance(result, str)
    assert "wide-leg denim" in result


def test_suggest_outfit_llm_failure_returns_fallback(monkeypatch):
    def raise_error(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(tools, "_call_groq", raise_error)

    result = suggest_outfit(_sample_listing(), get_example_wardrobe())

    assert isinstance(result, str)
    assert result.strip()


def test_create_fit_card_empty_outfit():
    result = create_fit_card("", _sample_listing())

    assert isinstance(result, str)
    assert "outfit suggestion" in result.lower()


def test_create_fit_card_uses_llm(monkeypatch):
    monkeypatch.setattr(
        tools,
        "_call_groq",
        lambda *args, **kwargs: "Found this tee on Depop for $24 and built the whole look around it.",
    )

    result = create_fit_card("Pair it with baggy jeans and chunky sneakers.", _sample_listing())

    assert "Depop" in result
    assert "$24" in result


def test_create_fit_card_llm_failure_returns_fallback(monkeypatch):
    def raise_error(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(tools, "_call_groq", raise_error)

    result = create_fit_card("Pair it with baggy jeans and chunky sneakers.", _sample_listing())

    assert isinstance(result, str)
    assert result.strip()
