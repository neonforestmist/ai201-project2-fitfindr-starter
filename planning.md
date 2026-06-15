# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): ...
- `size` (str): ...
- `max_price` (float): ...

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): ...
- `wardrobe` (dict): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Milestone 1 summary:** FitFindr needs to turn a natural-language thrift request into a tool-driven styling flow: `search_listings` is triggered first from the requested item description, size, and budget; `suggest_outfit` is triggered only after a real listing is selected; and `create_fit_card` is triggered only after there is a complete outfit suggestion to summarize. The listings data includes fields like `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`, while the wardrobe input is an `items` list of closet pieces with `name`, `category`, `colors`, `style_tags`, and optional `notes`. If a tool cannot return useful data, the agent should explain the failure, stop or ask for better information when needed, and avoid passing empty or incomplete results into the next tool.

**Step 1:**
The agent parses the query into a search request and calls `search_listings(description="vintage graphic tee", size=None, max_price=30.0)`. It filters the mock listings by the user's requested item and budget, then looks for style matches such as `graphic tee`, `vintage`, `streetwear`, or `grunge`.

**Step 2:**
If `search_listings` returns matching listings, the agent stores the best match in session state as `selected_item`; for this query, that could be "Graphic Tee — 2003 Tour Bootleg Style" at `$24.00` from Depop. The agent then calls `suggest_outfit(new_item=selected_item, wardrobe=get_example_wardrobe())`, using the user's wardrobe clues plus the example wardrobe structure to find pieces like baggy jeans, chunky white sneakers, a black denim jacket, or combat boots.

**Step 3:**
After `suggest_outfit` returns a complete outfit idea, the agent stores it as `outfit_suggestion` and calls `create_fit_card(outfit=outfit_suggestion, new_item=selected_item)`. This final tool turns the listing and styling recommendation into a short, shareable caption.

**Final output to user:**
The user sees the selected thrift listing, a short explanation of why it fits their style, a complete outfit suggestion using their wardrobe, and a caption-style fit card. If no matching listing is found, the user instead sees a clear message like: "I couldn't find a vintage graphic tee under $30 with those constraints; try raising the budget, broadening the size, or searching for 'band tee' or 'bootleg tee' instead."
