# FitFindr Demo Script

Use this as a 3-5 minute narration guide for the final recording.

## Script

Hi, this is FitFindr, a multi-tool AI agent for secondhand shopping and outfit styling.

The three required tools are `search_listings`, `suggest_outfit`, and `create_fit_card`. I also added all four stretch features: price comparison, style profile memory, trend awareness, and retry logic with fallback.

For the happy path, I will search: vintage graphic tee under thirty dollars.

When I submit, the agent parses the natural-language query into `description`, `size`, and `max_price`, then stores those values in `session["parsed"]`. It calls `search_listings(description, size, max_price)`, which loads the mock listing dataset, filters by hard constraints, scores listings by keyword and style-tag overlap, and returns the best matches.

The top listing is saved as `session["selected_item"]`. That exact item is reused by the later tools without the user re-entering it.

Before styling, the stretch tools run. `compare_price(selected_item)` compares the item to similar listings from `data/listings.json` and writes the result to the Price check panel. `get_trend_context(selected_item)` reads `data/trends.json` and writes the matching trend note to the Trend context panel.

Next, the agent calls `suggest_outfit(selected_item, wardrobe, trend_context, style_profile)`. This uses the selected item, the chosen wardrobe, the trend note, and any saved style preferences. The outfit text is stored in `session["outfit_suggestion"]`.

Finally, the agent calls `create_fit_card(outfit_suggestion, selected_item)`. That creates the caption-style fit card. At this point, the UI shows the listing, price check, trend context, outfit idea, fit card, and saved style memory. The style memory is updated after the successful run.

To show the memory stretch point, I will run a second query without restating the first style preferences. The Style memory panel should show that the agent carried preferences such as vintage, graphic tee, colors, and categories forward into the next interaction.

Now I will show retry logic. I will search: 90s track jacket size extra extra small under five dollars. The exact search returns no results, so the agent automatically retries after removing the size and price constraints. It explains that adjustment in the listing panel, then continues through price comparison, trend lookup, outfit suggestion, and fit-card creation.

Finally, I will show a true failure path: designer ballgown size extra extra small under five dollars. The exact search fails, and the loosened retry still fails. Because there is no selected item, the agent stops before outfit generation and fit-card creation. The error message tells the user what failed and suggests using a broader search term.

That shows the required workflow and the stretch behavior: defined tool interfaces, state passing across calls, conditional planning, graceful failure handling, price comparison, style memory, trend-aware outfit suggestions, and automatic retry with an explanation.
