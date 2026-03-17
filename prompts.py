from models import ContentRequest
from seasonal import get_season_theme, get_season_keywords


def build_generation_prompt(req: ContentRequest) -> str:
    theme = get_season_theme(req.season)
    keywords = ", ".join(get_season_keywords(req.season)[:6])
    kw_line = f"Incorporate keywords like: {keywords}." if req.keywords else ""
    user_keywords = f"Also weave in these specific keywords: {', '.join(req.keywords)}." if req.keywords else ""

    return f"""You are a creative marketing copywriter specializing in seasonal content.

Write {req.content_type.value} content for the following:

Topic: {req.topic}
Season: {req.season.value.capitalize()}
Seasonal theme: {theme}
Tone: {req.tone}
Max length: {req.max_length} characters

Guidelines:
- {kw_line}
- {user_keywords}
- Include a clear call-to-action.
- Keep the content engaging and on-brand for the season.
- Do not exceed {req.max_length} characters.

Respond with only the final content, no commentary or labels."""


def build_analysis_prompt(text: str, season: str) -> str:
    return f"""You are a content quality analyst. Analyze the following marketing content for its seasonal relevance and quality.

Season context: {season}

Content to analyze:
\"\"\"
{text}
\"\"\"

Provide your analysis as JSON with these keys:
- "score": float 0-1 representing overall quality and seasonal fit
- "seasonal_keywords": list of season-relevant words found
- "strengths": list of positive aspects
- "weaknesses": list of areas for improvement
- "recommendations": list of specific improvements

Respond with valid JSON only."""


def build_improve_prompt(text: str, issues: list[str], season: str) -> str:
    issues_str = "\n".join(f"- {i}" for i in issues)
    return f"""You are a marketing editor. Improve the following content to address these issues while maintaining the {season} seasonal theme.

Issues to fix:
{issues_str}

Original content:
\"\"\"
{text}
\"\"\"

Respond with only the improved content, no commentary."""
