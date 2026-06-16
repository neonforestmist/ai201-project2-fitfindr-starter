# FitFindr Demo Script

This is the narration script for `docs/fitfindr_demo.mp4`.

## Script

Hi, this is FitFindr, a multi-tool AI agent for secondhand shopping and outfit styling.

The goal of the project is not just to call a language model once. FitFindr has a planning loop that decides which tool to call next based on the state from the previous step. The three required tools are `search_listings`, `suggest_outfit`, and `create_fit_card`.

On the first screen, the user can type what they are looking for and choose either the example wardrobe or an empty wardrobe. For the happy-path demo, I am using the query: vintage graphic tee under thirty dollars.

When I submit this query, the agent first parses the natural-language request into structured search parameters. In this case, the parsed description is vintage graphic tee, the size is empty, and the max price is thirty dollars. Those parsed values are stored in `session["parsed"]`.

The planning loop then calls `search_listings(description, size, max_price)`. This tool loads the mock listing data, filters by price and size when those constraints exist, scores the remaining listings by keyword and style-tag relevance, and returns matching listing dictionaries sorted best first.

The top listing is saved in `session["selected_item"]`. This is the first important state handoff. The agent does not ask the user to re-enter the item. It passes the selected listing directly into the next tool.

Next, the planning loop calls `suggest_outfit(selected_item, wardrobe)`. Because the example wardrobe is selected, the tool receives the actual wardrobe items from `wardrobe_schema.json`. The output names real pieces from that wardrobe, such as baggy jeans, chunky sneakers, or boots, and explains how they work with the selected thrift listing.

That outfit text is then stored in `session["outfit_suggestion"]`. This is the second state handoff. The exact outfit suggestion becomes the input to `create_fit_card`.

Finally, the agent calls `create_fit_card(outfit_suggestion, selected_item)`. This tool uses the selected item, price, platform, and outfit suggestion to write a short caption-style fit card. At the end of the successful flow, the Gradio UI shows all three panels: the top listing, the outfit idea, and the fit card.

Now I will show an error path. I use an impossible query: designer ballgown size extra extra small under five dollars. This deliberately causes `search_listings` to return an empty list.

Because there is no selected item, the planning loop stops immediately. It does not call `suggest_outfit`, and it does not call `create_fit_card`. Instead, it sets `session["error"]` to a helpful message telling the user that no listings were found and suggesting ways to loosen the search, such as broadening the size, raising the budget, or using a broader search term.

That behavior matters because an agent should not keep going with invalid state. If search returns nothing, there is no item to style and no outfit to turn into a caption. FitFindr handles that failure gracefully and keeps the user oriented.

I also tested the other failure modes directly. If the wardrobe is empty, `suggest_outfit` returns general styling advice instead of crashing. If `create_fit_card` receives an empty outfit string, it returns a descriptive error message instead of raising a Python exception.

So the completed project demonstrates the full required agent workflow: tools with defined interfaces, state passing across tool calls, a planning loop with conditional branches, and deliberate error handling for the most important failure modes.
