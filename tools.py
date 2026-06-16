"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"

_PLACEHOLDER_KEYS = {
    "",
    "your_key_here",
    "your_groq_api_key_here",
}

_STOPWORDS = {
    "a",
    "an",
    "and",
    "any",
    "for",
    "i",
    "in",
    "is",
    "it",
    "looking",
    "me",
    "of",
    "or",
    "the",
    "to",
    "under",
    "want",
    "with",
}


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if api_key in _PLACEHOLDER_KEYS:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _call_groq(messages: list[dict], temperature: float = 0.7, max_tokens: int = 300) -> str:
    """Call Groq and return stripped response text."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise ValueError("Groq returned an empty response.")
    return content.strip()


def _tokenize(text: str) -> set[str]:
    """Lowercase, split, and remove filler words from search text."""
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in _STOPWORDS and len(token) > 1
    }


def _normalized_text(value) -> str:
    """Flatten listing fields into searchable lowercase text."""
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _listing_text(listing: dict) -> str:
    fields = [
        listing.get("title"),
        listing.get("description"),
        listing.get("category"),
        listing.get("style_tags", []),
        listing.get("size"),
        listing.get("condition"),
        listing.get("colors", []),
        listing.get("brand"),
        listing.get("platform"),
    ]
    return " ".join(_normalized_text(field) for field in fields).lower()


def _size_matches(listing_size: str, requested_size: str | None) -> bool:
    if not requested_size:
        return True

    listing_size = listing_size.lower().replace(" ", "")
    requested_size = requested_size.lower().replace(" ", "")
    return requested_size in listing_size


def _score_listing(listing: dict, query: str, query_terms: set[str]) -> int:
    searchable_text = _listing_text(listing)
    searchable_terms = _tokenize(searchable_text)
    score = 0

    if query.strip().lower() in searchable_text:
        score += 6

    title_terms = _tokenize(_normalized_text(listing.get("title")))
    description_terms = _tokenize(_normalized_text(listing.get("description")))
    category_terms = _tokenize(_normalized_text(listing.get("category")))
    style_terms = _tokenize(_normalized_text(listing.get("style_tags", [])))
    color_terms = _tokenize(_normalized_text(listing.get("colors", [])))
    brand_terms = _tokenize(_normalized_text(listing.get("brand")))
    platform_terms = _tokenize(_normalized_text(listing.get("platform")))

    for term in query_terms:
        if term in title_terms:
            score += 4
        if term in style_terms:
            score += 3
        if term in category_terms:
            score += 2
        if term in description_terms:
            score += 2
        if term in color_terms:
            score += 1
        if term in brand_terms or term in platform_terms:
            score += 1
        if term in searchable_terms:
            score += 1

    return score


def _format_price(price) -> str:
    try:
        return f"${float(price):.0f}" if float(price).is_integer() else f"${float(price):.2f}"
    except (TypeError, ValueError):
        return "a good price"


def _item_summary(item: dict) -> str:
    title = item.get("title", "Selected item")
    price = _format_price(item.get("price"))
    platform = item.get("platform", "a secondhand platform")
    condition = item.get("condition", "pre-loved")
    colors = ", ".join(item.get("colors", [])) or "versatile colors"
    tags = ", ".join(item.get("style_tags", [])) or "everyday"
    return (
        f"{title} ({item.get('category', 'item')}, {condition}, {price} on "
        f"{platform}; colors: {colors}; style tags: {tags})"
    )


def _format_wardrobe_items(items: list[dict]) -> str:
    lines = []
    for item in items:
        colors = ", ".join(item.get("colors", [])) or "unknown colors"
        tags = ", ".join(item.get("style_tags", [])) or "no style tags"
        notes = item.get("notes") or "no notes"
        lines.append(
            f"- {item.get('name', 'Unnamed item')} "
            f"({item.get('category', 'item')}; colors: {colors}; "
            f"tags: {tags}; notes: {notes})"
        )
    return "\n".join(lines)


def _choose_wardrobe_piece(items: list[dict], category: str) -> dict | None:
    for item in items:
        if item.get("category") == category:
            return item
    return None


def _fallback_outfit(new_item: dict, wardrobe: dict | None = None) -> str:
    title = new_item.get("title", "this find")
    category = new_item.get("category", "item")
    tags = ", ".join(new_item.get("style_tags", [])[:3]) or "thrifted"
    colors = ", ".join(new_item.get("colors", [])[:2]) or "neutral"
    items = (wardrobe or {}).get("items", []) if isinstance(wardrobe, dict) else []

    if items:
        pieces = []
        for needed_category in ("bottoms", "tops", "outerwear", "shoes", "accessories"):
            if needed_category == category:
                continue
            piece = _choose_wardrobe_piece(items, needed_category)
            if piece:
                pieces.append(piece["name"])
            if len(pieces) == 3:
                break

        if pieces:
            return (
                f"Style {title} with {', '.join(pieces)} for a {tags} look. "
                f"Keep the {colors} tones visible and balance the thrifted piece "
                "with one clean basic so the outfit feels intentional."
            )

    category_advice = {
        "tops": "relaxed denim or wide-leg trousers, then finish with sneakers or boots",
        "bottoms": "a fitted tank or cropped tee, a simple jacket, and low-profile shoes",
        "outerwear": "a plain base layer, straight-leg denim, and a shoe that matches the jacket's vibe",
        "shoes": "cuffed jeans or a midi skirt, plus a simple top so the shoes stand out",
        "accessories": "a simple base outfit and one matching color elsewhere in the look",
    }
    advice = category_advice.get(category, "closet basics that repeat one color from the piece")
    return (
        f"For {title}, build around its {tags} feel and {colors} palette: pair it "
        f"with {advice}. Add one contrasting texture so the look feels styled, not random."
    )


def _fallback_fit_card(outfit: str, new_item: dict) -> str:
    title = new_item.get("title", "this thrift find")
    price = _format_price(new_item.get("price"))
    platform = new_item.get("platform", "secondhand")
    tags = ", ".join(new_item.get("style_tags", [])[:2]) or "easy thrifted"
    return (
        f"Found {title} on {platform} for {price}, and it is doing all the "
        f"{tags} work. Styled it with {outfit.strip()}."
    )


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    Implementation:
        Loads listings with load_listings(), filters by hard constraints,
        scores keyword overlap, drops irrelevant listings, and returns results
        sorted by score.
    """
    if not description or not description.strip():
        return []

    query = description.strip()
    query_terms = _tokenize(query)
    if not query_terms:
        return []

    scored_listings = []
    minimum_matches = 1 if len(query_terms) == 1 else min(2, len(query_terms))
    for listing in load_listings():
        if max_price is not None and listing.get("price", 0) > max_price:
            continue
        if not _size_matches(listing.get("size", ""), size):
            continue
        if len(query_terms & _tokenize(_listing_text(listing))) < minimum_matches:
            continue

        score = _score_listing(listing, query, query_terms)
        if score > 0:
            scored_listings.append((score, listing))

    scored_listings.sort(
        key=lambda scored: (-scored[0], scored[1].get("price", float("inf")))
    )
    return [listing for _, listing in scored_listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    Implementation:
        Handles empty wardrobes with general advice, otherwise formats the
        user's wardrobe into an LLM prompt and asks for specific combinations.
        Falls back to deterministic styling text if the LLM call fails.
    """
    if not new_item:
        return "I need a selected listing before I can suggest an outfit."

    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    item_summary = _item_summary(new_item)

    if not wardrobe_items:
        prompt = (
            "Suggest one complete outfit for this thrifted item. The user has "
            "not entered their wardrobe yet, so give general styling advice by "
            "naming the kinds of pieces to pair with it. Be specific, concise, "
            "and practical.\n\n"
            f"Item: {item_summary}"
        )
    else:
        prompt = (
            "Suggest one or two complete outfits using the thrifted item and "
            "specific named pieces from the user's wardrobe. Mention why the "
            "pieces work together, keep it concise, and do not invent wardrobe "
            "items.\n\n"
            f"Thrifted item: {item_summary}\n\n"
            f"User wardrobe:\n{_format_wardrobe_items(wardrobe_items)}"
        )

    try:
        return _call_groq(
            [
                {
                    "role": "system",
                    "content": "You are FitFindr, a practical secondhand fashion stylist.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=260,
        )
    except Exception:
        return _fallback_outfit(new_item, wardrobe)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    Implementation:
        Guards against missing outfit text, prompts the LLM with item and outfit
        details, and falls back to a deterministic caption if the LLM call fails.
    """
    if not outfit or not outfit.strip():
        return "I need an outfit suggestion before I can create a fit card."
    if not new_item:
        return "I need a selected listing before I can create a fit card."

    prompt = (
        "Write a short outfit caption for a thrifted find. Make it sound like "
        "a real casual outfit post, not a product description. Use 2-4 "
        "sentences. Mention the item, price, and platform once each. Capture "
        "the outfit vibe in specific terms.\n\n"
        f"Item: {_item_summary(new_item)}\n\n"
        f"Outfit suggestion: {outfit.strip()}"
    )

    try:
        return _call_groq(
            [
                {
                    "role": "system",
                    "content": "You write natural, shareable OOTD captions.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.95,
            max_tokens=180,
        )
    except Exception:
        return _fallback_fit_card(outfit, new_item)
