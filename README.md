# FitFindr

FitFindr is a multi-tool AI agent for secondhand shopping. A user describes a thrifted item they want, FitFindr searches a mock listings dataset, suggests how to style the selected item with a wardrobe, and creates a short shareable fit-card caption.

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

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

Purpose: Suggests one or two outfits that include the selected listing.

Inputs:
- `new_item` (`dict`): The selected listing returned by `search_listings`.
- `wardrobe` (`dict`): A wardrobe object with an `items` list. Each wardrobe item may include `id`, `name`, `category`, `colors`, `style_tags`, and `notes`.

Output: A non-empty styling suggestion string.

Failure behavior: If the wardrobe is empty, the tool returns general styling advice instead of crashing. If the Groq call fails, the tool returns a fallback outfit based on item category, colors, and style tags.

### `create_fit_card(outfit: str, new_item: dict) -> str`

Purpose: Turns the outfit suggestion into a short caption-style fit card.

Inputs:
- `outfit` (`str`): The output from `suggest_outfit`.
- `new_item` (`dict`): The selected listing.

Output: A 2-4 sentence caption that mentions the thrifted item, price, platform, and styling vibe.

Failure behavior: If `outfit` is empty, the tool returns a descriptive error string instead of raising an exception. If the Groq call fails, the tool returns a fallback caption.

## Planning Loop

The planning loop lives in `run_agent()` in `agent.py`. It does not blindly call every tool. It advances only when the previous step produced usable state.

1. Create a new session dictionary with `_new_session(query, wardrobe)`.
2. Parse the user query into `description`, `size`, and `max_price`.
3. Store the parsed values in `session["parsed"]`.
4. Call `search_listings(description, size, max_price)`.
5. Store the returned list in `session["search_results"]`.
6. If there are no search results, set `session["error"]` to a helpful no-results message and return early. The agent does not call `suggest_outfit` or `create_fit_card`.
7. If results exist, store the first result as `session["selected_item"]`.
8. Call `suggest_outfit(selected_item, wardrobe)` and store the result in `session["outfit_suggestion"]`.
9. If the outfit text is missing or an error, set `session["error"]` and return.
10. Call `create_fit_card(outfit_suggestion, selected_item)` and store the result in `session["fit_card"]`.
11. Return the completed session.

Example no-results branch:

```text
designer ballgown size XXS under $5
```

returns a user-facing error and leaves `session["fit_card"]` as `None`.

## State Management

The session dictionary is the single source of truth for one interaction.

Session fields:
- `query`: Original user request.
- `parsed`: Extracted `description`, `size`, and `max_price`.
- `search_results`: List returned by `search_listings`.
- `selected_item`: First selected listing from the search results.
- `wardrobe`: Wardrobe selected by the UI.
- `outfit_suggestion`: String returned by `suggest_outfit`.
- `fit_card`: String returned by `create_fit_card`.
- `error`: `None` on success, or a user-facing explanation when the flow stops early.

State passes directly from one tool to the next. For example, `session["selected_item"]` is the exact listing passed into `suggest_outfit`, and `session["outfit_suggestion"]` is the exact text passed into `create_fit_card`.

## Error Handling

| Tool | Failure mode | Response |
| --- | --- | --- |
| `search_listings` | No listings match the query | Returns `[]`; `run_agent()` sets a helpful error and stops before outfit generation. |
| `suggest_outfit` | Wardrobe is empty | Returns general styling advice using item details instead of named wardrobe pieces. |
| `suggest_outfit` | Groq call fails | Returns a fallback outfit string. |
| `create_fit_card` | Empty outfit string | Returns `"I need an outfit suggestion before I can create a fit card."` |
| `create_fit_card` | Groq call fails | Returns a fallback caption using the selected item and outfit text. |

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
I couldn't find any listings for "designer ballgown" with size XXS and under $5. Try loosening the size, raising the budget, or using a broader search term like a style tag, color, or category.
```

Additional failure evidence is documented in `docs/milestone5_failure_modes.md`.

## Demo

Demo assets are in `docs/demo_assets/`.

Demo video artifact:

```text
docs/fitfindr_demo.mp4
```

Demo narration/script:

```text
docs/demo_script.md
```

The demo covers:
- A complete interaction from query to listing to outfit to fit card.
- State passing from `selected_item` into `suggest_outfit`, then `outfit_suggestion` into `create_fit_card`.
- A triggered no-results failure where the agent stops early and gives a helpful response.

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

### Instance 3: Demo evidence

Input given to AI: Milestone 5 and 6 instructions from the CodePath page, the running Gradio app, and the failure-mode test outputs.

Output produced: `docs/milestone5_failure_modes.md`, screenshot evidence for the no-results path, and demo materials for the final walkthrough.

What I revised: I kept the demo focused on the required agent behavior rather than adding stretch features, so the video shows the required tools, state passing, and failure handling clearly.
