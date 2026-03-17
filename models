from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"


class ContentType(str, Enum):
    BLOG = "blog"
    SOCIAL = "social"
    EMAIL = "email"
    AD = "ad"


@dataclass
class ContentRequest:
    topic: str
    season: Season
    content_type: ContentType
    tone: str = "neutral"
    keywords: list[str] = field(default_factory=list)
    max_length: int = 500


@dataclass
class ContentResult:
    request: ContentRequest
    content: str
    score: float
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    original: str
    season: Season
    score: float
    seasonal_keywords_found: list[str]
    rule_violations: list[str]
    recommendations: list[str]
    passed: bool
