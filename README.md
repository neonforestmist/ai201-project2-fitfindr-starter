# FitFindr

FitFindr is a multi-tool AI agent for secondhand shopping. A user describes a thrifted item they want, FitFindr searches a mock listings dataset, suggests how to style the selected item with a wardrobe, compares the listing price, uses trend context, remembers style preferences across turns, and creates a short shareable fit-card caption.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Run the app:

```bash
python app.py
```

Open the local URL printed by Gradio. In local testing this ran at:

```text
http://127.0.0.1:7860
```

Run tests:

```bash
python -m pytest tests/
```

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]`

Purpose: Searches the mock secondhand listings in `data/listings.json`.

Inputs:
- `description` (`str`): Item or style terms from the user query, such as `"vintage graphic tee"`.
- `size` (`str | None`): Optional requested size, such as `"M"`, `"US 8"`, or `"XXS"`.
- `max_price` (`float | None`): Optional maximum budget.

Output: A list of matching listing dictionaries sorted by relevance. Each listing includes `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Failure behavior: Returns `[]` when nothing matches instead of raising an exception.

### `suggest_outfit(new_item: dict, wardrobe: dict, trend_context: str | None = None, style_profile: dict | None = None) -> str`

Purpose: Suggests one or two outfits that include the selected listing.

Inputs:
- `new_item` (`dict`): The selected listing returned by `search_listings`.
- `wardrobe` (`dict`): A wardrobe object with an `items` list. Each wardrobe item may include `id`, `name`, `category`, `colors`, `style_tags`, and `notes`.
- `trend_context` (`str | None`): Optional output from `get_trend_context`.
- `style_profile` (`dict | None`): Optional remembered style preferences from prior interactions.

Output: A non-empty styling suggestion string.

Failure behavior: If the wardrobe is empty, the tool returns general styling advice instead of crashing. If the Groq call fails, the tool returns a fallback outfit based on item category, colors, and style tags.

### `create_fit_card(outfit: str, new_item: dict) -> str`

Purpose: Turns the outfit suggestion into a short caption-style fit card.

Inputs:
- `outfit` (`str`): The output from `suggest_outfit`.
- `new_item` (`dict`): The selected listing.

Output: A 2-4 sentence caption that mentions the thrifted item, price, platform, and styling vibe.

Failure behavior: If `outfit` is empty, the tool returns a descriptive error string instead of raising an exception. If the Groq call fails, the tool returns a fallback caption.

### `compare_price(new_item: dict, listings: list[dict] | None = None) -> str`

Purpose: Stretch tool that assesses whether the selected listing price is a good deal.

Inputs:
- `new_item` (`dict`): The selected listing.
- `listings` (`list[dict] | None`): Optional comparison dataset. If omitted, the tool loads `data/listings.json`.

Output: A short assessment with the selected price, comparable listing count, average comparable price, range, verdict, and example comparable titles.

Failure behavior: Returns a clear message if no item, numeric price, or comparable listings are available.

### `get_trend_context(new_item: dict) -> str`

Purpose: Stretch tool that finds a relevant trend note for the selected listing.

Inputs:
- `new_item` (`dict`): The selected listing.

Output: A short trend note with a trend name, signal, and outfit influence.

Failure behavior: Returns a timeless styling note if no strong trend match is found.

## Planning Loop

The planning loop lives in `run_agent()` in `agent.py`. It does not blindly call every tool. It advances only when the previous step produced usable state.

1. Create a new session dictionary with `_new_session(query, wardrobe)`.
2. Parse the user query into `description`, `size`, and `max_price`.
3. Store the parsed values in `session["parsed"]`.
4. Call `search_listings(description, size, max_price)`.
5. Store the returned list in `session["search_results"]`.
6. If there are no search results and the query had size or price constraints, automatically retry once with those constraints removed.
7. Store retry metadata in `session["retry"]`. If the retry succeeds, store a user-facing `session["retry_note"]` and continue. If it still fails, set `session["error"]` and return before outfit generation.
8. If results exist, store the first result as `session["selected_item"]`.
9. Call `compare_price(selected_item)` and store the result in `session["price_assessment"]`.
10. Call `get_trend_context(selected_item)` and store the result in `session["trend_context"]`.
11. Call `suggest_outfit(selected_item, wardrobe, trend_context, style_profile_before)` and store the result in `session["outfit_suggestion"]`.
12. If the outfit text is missing or an error, set `session["error"]` and return.
13. Call `create_fit_card(outfit_suggestion, selected_item)` and store the result in `session["fit_card"]`.
14. Update `session["style_profile_after"]` with style tags, colors, and categories from the successful interaction.
15. Return the completed session.

Example no-results branch:

```text
designer ballgown size XXS under $5
```

first retries without the size and price filters. If the retry still fails, it returns a user-facing error and leaves `session["fit_card"]` as `None`.

Example retry branch:

```text
90s track jacket size XXS under $5
```

finds no exact match, retries as `"90s track jacket"` with no size or price cap, explains the adjustment, and then continues to price comparison, trend lookup, outfit suggestion, and fit-card creation.

## State Management

The session dictionary is the single source of truth for one interaction.

Session fields:
- `query`: Original user request.
- `parsed`: Extracted `description`, `size`, and `max_price`.
- `search_results`: List returned by `search_listings`.
- `selected_item`: First selected listing from the search results.
- `wardrobe`: Wardrobe selected by the UI.
- `price_assessment`: Output from `compare_price`.
- `trend_context`: Output from `get_trend_context`.
- `outfit_suggestion`: String returned by `suggest_outfit`.
- `fit_card`: String returned by `create_fit_card`.
- `retry`: Original and adjusted search parameters plus retry result count.
- `retry_note`: User-facing explanation of automatically loosened constraints.
- `style_profile_before`: Saved preferences passed into the current interaction.
- `style_profile_after`: Updated preferences returned to Gradio state.
- `error`: `None` on success, or a user-facing explanation when the flow stops early.

State passes directly from one tool to the next. For example, `session["selected_item"]` is the exact listing passed into `compare_price`, `get_trend_context`, and `suggest_outfit`. Then `session["trend_context"]` and `session["style_profile_before"]` influence `suggest_outfit`, and `session["outfit_suggestion"]` is the exact text passed into `create_fit_card`.

The Gradio app stores style memory in a hidden `gr.State` value. Each successful interaction returns `style_profile_after` to that state, so the next query can use saved tags, colors, and categories without the user re-entering them.

## Error Handling

| Tool | Failure mode | Response |
| --- | --- | --- |
| `search_listings` | No listings match the exact query | Returns `[]`; `run_agent()` retries once with size and price constraints removed, then either continues with a retry note or stops with a helpful error. |
| `suggest_outfit` | Wardrobe is empty | Returns general styling advice using item details instead of named wardrobe pieces. |
| `suggest_outfit` | Groq call fails | Returns a fallback outfit string. |
| `create_fit_card` | Empty outfit string | Returns `"I need an outfit suggestion before I can create a fit card."` |
| `create_fit_card` | Groq call fails | Returns a fallback caption using the selected item and outfit text. |
| `compare_price` | Selected item has no numeric price or no comparable listings | Returns a clear price-check message instead of crashing. |
| `get_trend_context` | No strong trend match | Returns a timeless styling note instead of blocking the outfit flow. |

Concrete tested example:

```bash
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
```

Output:

```text
[]
```

The full agent then returns:

```text
I couldn't find any listings for "designer ballgown" with size XXS and under $5. I also retried after removing size XXS and the $5 price cap, but still found no matches. Try using a broader search term like a style tag, color, or category.
```

Additional failure evidence is documented in `docs/milestone5_failure_modes.md`.

## Demo

Use this narration/script for the final 3-5 minute recording:

```text
docs/demo_script.md
```

The demo covers:
- A complete interaction from query to listing to outfit to fit card.
- State passing from `selected_item` into `suggest_outfit`, then `outfit_suggestion` into `create_fit_card`.
- A triggered no-results failure where the agent stops early and gives a helpful response.
- Stretch behavior: price comparison, trend context, saved style memory, and a loosened retry query such as `90s track jacket size XXS under $5`.

## Stretch Features

### Price Comparison Tool (+2)

Implemented by `compare_price(new_item, listings=None)` in `tools.py`.

The tool compares the selected item against listings from `data/listings.json`. Comparable listings are chosen by same category plus overlapping `style_tags` and `colors`. The output includes the selected price, number of comparable listings, average comparable price, range, verdict, and example comparable titles.

Source evidence:
- `tests/test_tools.py::test_compare_price_returns_reasoned_assessment`
- `agent.py` stores the result in `session["price_assessment"]`
- `app.py` displays it in the Price check panel

### Style Profile Memory (+2)

Implemented with `style_profile_before` and `style_profile_after` in `agent.py`, plus `gr.State` in `app.py`.

After a successful interaction, the agent saves style tags, colors, categories, and interaction count. On the next interaction, Gradio passes that profile back into `run_agent`, and `suggest_outfit` receives it as `style_profile` without the user re-entering those preferences.

Source evidence:
- `tests/test_agent.py::test_run_agent_uses_style_profile_from_previous_interaction`
- `app.py` displays the saved profile in the Style memory panel

### Trend Awareness Tool (+2)

Implemented by `get_trend_context(new_item)` in `tools.py`.

The data source is `data/trends.json`. The tool scores trends by matching category, style tags, and colors. `run_agent` stores the chosen note in `session["trend_context"]`, and `suggest_outfit` receives that note so the trend visibly influences the outfit recommendation.

Source evidence:
- `tests/test_tools.py::test_get_trend_context_returns_matching_trend`
- `tests/test_tools.py::test_suggest_outfit_uses_trend_and_style_profile_in_fallback`
- `app.py` displays the trend note in the Trend context panel

### Retry Logic with Fallback (+1)

Implemented in `run_agent()` in `agent.py`.

If `search_listings` returns zero results for a query with size or price constraints, the agent automatically retries once with those constraints removed. It stores the original and adjusted parameters in `session["retry"]` and explains the adjustment in `session["retry_note"]`.

Source evidence:
- `tests/test_agent.py::test_run_agent_retries_with_loosened_constraints`
- Demo query: `90s track jacket size XXS under $5`

## Spec Reflection

One way the spec helped: Writing the planning loop before implementation made the early-return behavior clear. The agent should not call every tool every time; it should stop after `search_listings` if there is no selected item to style.

One way implementation diverged from the spec: The original plan said the query parser would remove every search constraint cleanly before searching. In implementation, I kept the parser deterministic and simple with regex rules for size and price, then cleaned the remaining text. This is easier to test and debug for the starter project than asking the LLM to parse every query.

## AI Usage

### Instance 1: Planning loop implementation

Input given to AI: The Planning Loop, State Management, and Error Handling sections from `planning.md`, plus the starter notes in `agent.py`.

Output produced: A branch-based `run_agent()` implementation that parses the query, calls `search_listings`, stores session values, stops early on no results, and passes state into `suggest_outfit` and `create_fit_card`.

What I revised: I kept query parsing deterministic with regex instead of using the LLM, because the parsed values needed to be predictable for tests.

### Instance 2: Tool implementation and tests

Input given to AI: The tool specs from `planning.md`, the docstrings in `tools.py`, and the mock data schema from `data/listings.json` and `data/wardrobe_schema.json`.

Output produced: Implementations for `search_listings`, `suggest_outfit`, and `create_fit_card`, plus pytest tests for search results, empty search, price filters, size filters, empty wardrobe, LLM fallback, and empty fit-card input.

What I revised: I tightened search matching after seeing that broad terms like `"vintage"` returned too many loosely related listings. The final search requires stronger overlap for multi-word descriptions.

### Instance 3: Stretch evidence and demo prep

Input given to AI: The Project 2 grading rubric from the CodePath grading page, the running Gradio app, and the failure-mode test outputs.

Output produced: stretch implementations for price comparison, style memory, trend awareness, and retry fallback; tests that prove each behavior; README documentation; and an updated demo script for the final walkthrough.

What I revised: I kept the stretch features deterministic and visible in the UI, so the final demo can show them without relying on hidden state or a live LLM response.
