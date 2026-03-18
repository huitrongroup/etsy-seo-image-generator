# Etsy SEO Generator

AI-powered Etsy title and tag generator from product images, built with Claude and Streamlit.

## Features

- **Vision-based analysis** — Claude reads the product image and extracts product type, recipient, visible text, theme, occasion, and gifting intent
- **Two-step pipeline** — structured image analysis feeds directly into the SEO generation step, eliminating ambiguity
- **Seasonal intelligence** — detects holidays within 8 weeks of the launch date and adds relevant keyword phrases only when appropriate for the product
- **Hard rules enforced** — 10 banned words, 140-char title limit, 20-char tag limit, root-word repetition detection
- **Long-tail buyer-intent focus** — recipient + relationship + occasion + product phrasing over generic single words
- **Manual overrides** — correct the AI's detected product type, recipient, occasion, or phrase text without re-uploading
- **Regenerate without re-analysing** — rerun only the title/tag step after adjusting overrides

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your .env file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Launch the app
streamlit run app.py
```

## Project Structure

| File | Role |
|------|------|
| `app.py` | Streamlit UI — layout, pipeline orchestration, results rendering |
| `models.py` | Pydantic v2 data models (`ImageAnalysis`, `SEOOutput`, `SEORequest`, etc.) |
| `analyzer.py` | Step 1 — Claude Vision + tool_use → `ImageAnalysis` |
| `generators.py` | Step 2 — Claude text + tool_use → `SEOOutput` (titles, tags, rationale) |
| `seasonal.py` | Holiday calendar, seasonal keyword bank, `get_seasonal_context()` |
| `rules.py` | Banned-word list, length constants, root-repetition detection |
| `prompts.py` | Claude prompt templates for both pipeline steps |
| `validators.py` | Post-generation validation and sanitization helpers |

## Pipeline

```
Upload image
     │
     ▼
[Step 1 — analyzer.py]
Claude Vision + tool_use
     │
     ▼
ImageAnalysis
  product_type, recipient, visible_text,
  theme, occasion, gifting_intent,
  keyword_candidates
     │
     ├── seasonal.py  →  SeasonalContext (holidays, keywords)
     ├── overrides    →  applied to ImageAnalysis
     │
     ▼
[Step 2 — generators.py]
Claude text + tool_use + hard rules in prompt
     │
     ▼
SEOOutput
  5 titles  (≤ 140 chars each)
  13 tags   (≤ 20 chars each)
  rationale
     │
     ▼
validators.py  →  surface any rule violations in UI
```

## Banned Words

The following words are permanently blocked from all generated output:

> funny, cute, sentimental, quote, unique, perfect, awesome, gift idea, trendy, aesthetic

## Seasonal Logic

Given a launch date, the app looks for holidays within the next **8 weeks** and adds buyer-intent holiday phrases to the SEO generation prompt. Seasonal keywords are only woven into output when they fit the specific product — the prompt instructs Claude to exercise judgment rather than forcing holiday keywords onto every listing.

Supported holidays: Valentine's Day, St. Patrick's Day, Easter, Mother's Day, Father's Day, 4th of July, Back to School, Halloween, Thanksgiving, Hanukkah, Christmas, New Year, Graduation.

## Customising Rules

To add a banned word, edit `rules.py`:

```python
BANNED_WORDS: frozenset[str] = frozenset({
    ...
    "your-new-banned-word",
})
```

To add a holiday and its keywords, edit `seasonal.py`:

```python
HOLIDAY_KEYWORDS["My Holiday"] = [
    "my holiday gift",
    "gift for occasion",
]
```

And add its date calculator to `_all_holidays()` in the same file.
