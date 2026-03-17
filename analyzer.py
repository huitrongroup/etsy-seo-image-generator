import json
import os
import anthropic
from models import AnalysisReport, Season
from prompts import build_analysis_prompt
from validators import analyze_text

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


def analyze_with_ai(text: str, season: Season) -> dict:
    client = _get_client()
    prompt = build_analysis_prompt(text, season.value)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Failed to parse AI response", "raw": raw}


def analyze_content(text: str, season: Season, use_ai: bool = True) -> AnalysisReport:
    report = analyze_text(text, season)

    if use_ai:
        ai_data = analyze_with_ai(text, season)
        if "error" not in ai_data:
            ai_score = ai_data.get("score", report.score)
            ai_recs = ai_data.get("recommendations", [])
            report.score = round((report.score + ai_score) / 2, 2)
            report.recommendations = list(set(report.recommendations + ai_recs))

    return report


def batch_analyze(texts: list[str], season: Season, use_ai: bool = False) -> list[AnalysisReport]:
    return [analyze_content(t, season, use_ai=use_ai) for t in texts]
