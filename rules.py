from dataclasses import dataclass
from typing import Callable
from models import ContentRequest, Season


@dataclass
class Rule:
    name: str
    description: str
    check: Callable[[str, ContentRequest], list[str]]


def check_length(text: str, req: ContentRequest) -> list[str]:
    if len(text) > req.max_length:
        return [f"Content exceeds max length ({len(text)} > {req.max_length} chars)"]
    return []


def check_no_competitor_mentions(text: str, req: ContentRequest) -> list[str]:
    # Placeholder — populate with actual competitor names via config
    competitors: list[str] = []
    found = [c for c in competitors if c.lower() in text.lower()]
    return [f"Competitor mentioned: {c}" for c in found]


def check_seasonal_fit(text: str, req: ContentRequest) -> list[str]:
    from seasonal import score_seasonal_relevance
    score = score_seasonal_relevance(text, req.season)
    if score < 0.1:
        return [f"Content lacks seasonal relevance for {req.season.value}"]
    return []


def check_no_offensive_language(text: str, req: ContentRequest) -> list[str]:
    flagged = ["hate", "offensive_placeholder"]  # extend as needed
    found = [w for w in flagged if w in text.lower()]
    return [f"Potentially offensive term: '{w}'" for w in found]


def check_cta_present(text: str, req: ContentRequest) -> list[str]:
    cta_phrases = ["buy now", "learn more", "get started", "shop", "sign up", "click here", "discover"]
    if not any(phrase in text.lower() for phrase in cta_phrases):
        return ["No call-to-action detected"]
    return []


DEFAULT_RULES: list[Rule] = [
    Rule("length", "Content must not exceed max length", check_length),
    Rule("seasonal_fit", "Content should be seasonally relevant", check_seasonal_fit),
    Rule("no_offensive", "Content must not contain offensive language", check_no_offensive_language),
    Rule("cta", "Content should include a call-to-action", check_cta_present),
    Rule("no_competitors", "Content must not mention competitors", check_no_competitor_mentions),
]


def apply_rules(text: str, req: ContentRequest, rules: list[Rule] | None = None) -> list[str]:
    active_rules = rules if rules is not None else DEFAULT_RULES
    violations: list[str] = []
    for rule in active_rules:
        violations.extend(rule.check(text, req))
    return violations
