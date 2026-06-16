# Milestone 5 Failure Mode Evidence

Milestone 5 asks us to deliberately trigger each failure mode and confirm the agent returns useful output instead of crashing.

## 1. No listings found

Command:

```bash
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
```

Observed output:

```text
[]
```

Full agent check:

```bash
python -c "from agent import run_agent; from utils.data_loader import get_example_wardrobe; session = run_agent('designer ballgown size XXS under \$5', get_example_wardrobe()); print(session['error']); print('fit_card:', session['fit_card'])"
```

Observed output:

```text
I couldn't find any listings for "designer ballgown" with size XXS and under $5. I also retried after removing size XXS and the $5 price cap, but still found no matches. Try using a broader search term like a style tag, color, or category.
fit_card: None
```

## 2. Empty wardrobe

Command:

```bash
python -c "from tools import search_listings, suggest_outfit; from utils.data_loader import get_empty_wardrobe; results = search_listings('vintage graphic tee', size=None, max_price=50); print(suggest_outfit(results[0], get_empty_wardrobe()))"
```

Observed output:

```text
Pair the Y2K Baby Tee with high-waisted jeans or a flowy skirt for a cute, nostalgic look. Add some neutral sneakers or sandals and finish with a denim jacket or cardigan for a chic, laid-back outfit.
```

## 3. Empty outfit input

Command:

```bash
python -c "from tools import search_listings, create_fit_card; results = search_listings('vintage graphic tee', size=None, max_price=50); print(create_fit_card('', results[0]))"
```

Observed output:

```text
I need an outfit suggestion before I can create a fit card.
```

## Demo evidence

Screenshot captured at:

```text
docs/milestone5_no_results.jpg
```

This screenshot shows the impossible search query in the Gradio UI, the helpful no-results message in the first output panel, and blank outfit/fit-card panels. The current stretch version also documents the automatic loosened retry before stopping.
