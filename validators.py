from models import ContentRequest, ContentResult, AnalysisReport, Season
from rules import apply_rules, DEFAULT_RULES
from seasonal import score_seasonal_relevance, detect_seasonal_keywords


def validate_request(req: ContentRequest) -> list[str]:
    errors: list[str] = []
    if not req.topic.strip():
        errors.append("Topic must not be empty")
    if req.max_length < 50:
        errors.append("max_length must be at least 50 characters")
    if req.max_length > 10_000:
        errors.append("max_length must not exceed 10,000 characters")
    return errors


def validate_content(result: ContentResult) -> ContentResult:
    violations = apply_rules(result.content, result.request)
    result.issues = violations
    result.score = _compute_score(result.content, result.request, violations)
    return result


def analyze_text(text: str, season: Season) -> AnalysisReport:
    from models import ContentRequest, ContentType
    dummy_req = ContentRequest(
        topic="",
        season=season,
        content_type=ContentType.BLOG,
    )
    violations = apply_rules(text, dummy_req)
    keywords_found = detect_seasonal_keywords(text, season)
    score = score_seasonal_relevance(text, season)

    recommendations: list[str] = []
    if score < 0.3:
        recommendations.append(f"Add more {season.value}-themed language to improve relevance.")
    if violations:
        recommendations.append("Address rule violations before publishing.")

    return AnalysisReport(
        original=text,
        season=season,
        score=round(score, 2),
        seasonal_keywords_found=keywords_found,
        rule_violations=violations,
        recommendations=recommendations,
        passed=len(violations) == 0,
    )


def _compute_score(text: str, req: ContentRequest, violations: list[str]) -> float:
    base = score_seasonal_relevance(text, req.season)
    penalty = len(violations) * 0.1
    return max(0.0, round(base - penalty, 2))
