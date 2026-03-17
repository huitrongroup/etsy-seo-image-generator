# Seasonal Content Generator & Analyzer

An AI-powered tool for generating and analyzing seasonal marketing content using Claude.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Usage

### Generate content

```bash
# Generate a blog post for the current season
python app.py generate "summer sale promotion"

# Specify season and content type
python app.py generate "holiday gift guide" --season winter --type email

# Generate 3 variants with auto-improvement
python app.py generate "back to school" --season fall --variants 3 --auto-improve

# Custom tone and keywords
python app.py generate "spring skincare" --season spring --tone friendly --keywords glow refresh renew
```

### Analyze content

```bash
# Analyze inline text
python app.py analyze --text "Shop our summer deals now! Beat the heat with cool savings."

# Analyze a file
python app.py analyze --file my_copy.txt --season summer

# Rules-only analysis (no API call)
python app.py analyze --text "..." --no-ai

# JSON output
python app.py analyze --text "..." --json
```

## Project Structure

| File | Description |
|------|-------------|
| `app.py` | CLI entry point |
| `models.py` | Data classes (`ContentRequest`, `ContentResult`, `AnalysisReport`) |
| `seasonal.py` | Season detection, keywords, and themes |
| `rules.py` | Rule definitions and validation engine |
| `validators.py` | Content validation and scoring |
| `prompts.py` | Claude prompt templates |
| `generators.py` | Content generation via Claude API |
| `analyzer.py` | Content analysis via Claude API |

## Scoring

Content is scored 0–1 based on:
- Seasonal keyword density
- Rule compliance (violations reduce score by 0.1 each)
- AI quality assessment (when `--no-ai` is not set)

## Adding Custom Rules

Edit `rules.py` and add a new `Rule` to `DEFAULT_RULES`:

```python
def check_my_rule(text: str, req: ContentRequest) -> list[str]:
    if "forbidden_word" in text.lower():
        return ["Found forbidden word"]
    return []

DEFAULT_RULES.append(Rule("my_rule", "Description", check_my_rule))
```
