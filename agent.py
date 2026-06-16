"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import (
    compare_price,
    create_fit_card,
    get_trend_context,
    search_listings,
    suggest_outfit,
)


_STYLE_TERMS = {
    "90s",
    "athletic",
    "classic",
    "cottagecore",
    "cozy",
    "grunge",
    "linen",
    "minimal",
    "oversized",
    "platform",
    "streetwear",
    "vintage",
    "western",
    "y2k",
}


def _dedupe_keep_order(values: list[str], limit: int = 8) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        cleaned = str(value).strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
        if len(deduped) == limit:
            break
    return deduped


def _normalize_style_profile(style_profile: dict | None) -> dict:
    if not isinstance(style_profile, dict):
        style_profile = {}
    return {
        "preferred_tags": _dedupe_keep_order(style_profile.get("preferred_tags", [])),
        "preferred_colors": _dedupe_keep_order(style_profile.get("preferred_colors", []), limit=6),
        "preferred_categories": _dedupe_keep_order(style_profile.get("preferred_categories", []), limit=6),
        "interactions": int(style_profile.get("interactions", 0) or 0),
    }


def _update_style_profile(style_profile: dict | None, query: str, selected_item: dict) -> dict:
    profile = _normalize_style_profile(style_profile)
    query_terms = {term.lower() for term in re.findall(r"[a-z0-9]+", query or "")}
    query_style_terms = sorted(query_terms & _STYLE_TERMS)

    profile["preferred_tags"] = _dedupe_keep_order(
        query_style_terms
        + selected_item.get("style_tags", [])
        + profile["preferred_tags"]
    )
    profile["preferred_colors"] = _dedupe_keep_order(
        selected_item.get("colors", []) + profile["preferred_colors"],
        limit=6,
    )
    profile["preferred_categories"] = _dedupe_keep_order(
        [selected_item.get("category", "")] + profile["preferred_categories"],
        limit=6,
    )
    profile["interactions"] += 1
    return profile


def _build_retry(parsed: dict) -> dict | None:
    if parsed.get("size") is None and parsed.get("max_price") is None:
        return None
    return {
        "description": parsed.get("description", ""),
        "size": None,
        "max_price": None,
    }


def _format_retry_adjustment(parsed: dict) -> str:
    changes = []
    if parsed.get("size"):
        changes.append(f"size {parsed['size']}")
    if parsed.get("max_price") is not None:
        changes.append(f"the ${parsed['max_price']:.0f} price cap")
    return " and ".join(changes)


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict, style_profile: dict | None = None) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "price_assessment": None,    # stretch price comparison output
        "trend_context": None,       # stretch trend-awareness output
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "retry": None,               # retry metadata when search is loosened
        "retry_note": None,          # user-facing explanation of retry changes
        "style_profile_before": _normalize_style_profile(style_profile),
        "style_profile_after": _normalize_style_profile(style_profile),
        "error": None,               # set if the interaction ended early
    }


def _parse_query(query: str) -> dict:
    """
    Extract search parameters from a natural-language thrift request.

    The parser is intentionally deterministic for Milestone 4: it uses simple
    regex rules for budget and size, then treats the remaining cleaned text as
    the item description.
    """
    raw_query = (query or "").strip()
    working = raw_query
    max_price = None
    size = None

    price_pattern = re.compile(
        r"\b(?:under|below|less than|up to|max(?:imum)?|budget(?: of)?)\s*\$?\s*(\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    price_match = price_pattern.search(working)
    if not price_match:
        price_pattern = re.compile(r"\$(\d+(?:\.\d+)?)", re.IGNORECASE)
        price_match = price_pattern.search(working)

    if price_match:
        max_price = float(price_match.group(1))
        working = price_pattern.sub(" ", working, count=1)

    size_patterns = [
        re.compile(
            r"\b(?:in\s+)?size\s+(us\s*\d+(?:\.5)?|w\d{2}(?:\s*l\d{2})?|xxs|xs|xl|xxl|s|m|l|\d+(?:\.5)?)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(us\s*\d+(?:\.5)?)\b", re.IGNORECASE),
        re.compile(r"\b(w\d{2}(?:\s*l\d{2})?)\b", re.IGNORECASE),
    ]

    for size_pattern in size_patterns:
        size_match = size_pattern.search(working)
        if size_match:
            size = re.sub(r"\s+", " ", size_match.group(1).upper()).strip()
            working = size_pattern.sub(" ", working, count=1)
            break

    description = re.split(
        r"\b(?:i mostly wear|my wardrobe|how would i style|how should i style|what'?s out there)\b",
        working,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    description = re.sub(
        r"\b(?:i'?m|i am|looking for|searching for|find me|show me|find|want|need|please)\b",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"[$,?.!]", " ", description)
    description = " ".join(description.split())

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


def _format_no_results_message(parsed: dict, retry: dict | None = None) -> str:
    description = parsed.get("description") or "that item"
    filters = []
    if parsed.get("size"):
        filters.append(f"size {parsed['size']}")
    if parsed.get("max_price") is not None:
        filters.append(f"under ${parsed['max_price']:.0f}")

    filter_text = f" with {' and '.join(filters)}" if filters else ""
    retry_text = ""
    if retry:
        retry_text = (
            f" I also retried after removing {_format_retry_adjustment(parsed)}, "
            "but still found no matches."
        )
    return (
        f"I couldn't find any listings for \"{description}\"{filter_text}."
        f"{retry_text} Try using a broader search term like a style tag, "
        "color, or category."
    )


def _looks_like_tool_error(value: str | None) -> bool:
    if not value or not value.strip():
        return True
    return value.strip().lower().startswith("i need ")


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict, style_profile: dict | None = None) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py
        style_profile: Optional saved preferences from earlier interactions.

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    The loop follows the Planning Loop section of planning.md: parse query,
    search, stop early if no listings are found, then pass selected_item into
    suggest_outfit and pass that result into create_fit_card.
    """
    session = _new_session(query, wardrobe, style_profile)

    if not query or not query.strip():
        session["error"] = "Tell me what thrifted item you want to search for."
        return session

    parsed = _parse_query(query)
    session["parsed"] = parsed

    if not parsed["description"]:
        session["error"] = "Tell me what thrifted item you want to search for."
        return session

    try:
        search_results = search_listings(
            parsed["description"],
            size=parsed["size"],
            max_price=parsed["max_price"],
        )
    except Exception as exc:
        session["error"] = f"Search failed before I could find listings: {exc}"
        return session

    session["search_results"] = search_results
    if not search_results:
        retry_parsed = _build_retry(parsed)
        if retry_parsed:
            try:
                retry_results = search_listings(
                    retry_parsed["description"],
                    size=retry_parsed["size"],
                    max_price=retry_parsed["max_price"],
                )
            except Exception as exc:
                session["error"] = f"Retry search failed before I could find listings: {exc}"
                return session

            session["retry"] = {
                "original": parsed,
                "adjusted": retry_parsed,
                "results_found": len(retry_results),
            }
            if retry_results:
                session["search_results"] = retry_results
                session["retry_note"] = (
                    "I found no exact matches, so I automatically retried and "
                    f"removed {_format_retry_adjustment(parsed)}."
                )
            else:
                session["error"] = _format_no_results_message(parsed, session["retry"])
                return session
        else:
            session["error"] = _format_no_results_message(parsed)
            return session

    session["selected_item"] = session["search_results"][0]

    try:
        session["price_assessment"] = compare_price(session["selected_item"])
    except Exception as exc:
        session["price_assessment"] = f"Price comparison unavailable: {exc}"

    try:
        session["trend_context"] = get_trend_context(session["selected_item"])
    except Exception as exc:
        session["trend_context"] = f"Trend lookup unavailable: {exc}"

    outfit = suggest_outfit(
        session["selected_item"],
        session["wardrobe"],
        trend_context=session["trend_context"],
        style_profile=session["style_profile_before"],
    )
    session["outfit_suggestion"] = outfit
    if _looks_like_tool_error(outfit):
        session["error"] = (
            "I found a listing, but I couldn't build a usable outfit suggestion."
        )
        return session

    fit_card = create_fit_card(session["outfit_suggestion"], session["selected_item"])
    session["fit_card"] = fit_card
    if _looks_like_tool_error(fit_card):
        session["error"] = "I made an outfit suggestion, but couldn't create a fit card."
        return session

    session["style_profile_after"] = _update_style_profile(
        session["style_profile_before"],
        query,
        session["selected_item"],
    )

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
