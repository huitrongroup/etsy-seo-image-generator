from datetime import date
from models import Season

SEASONAL_KEYWORDS: dict[Season, list[str]] = {
    Season.SPRING: [
        "bloom", "renewal", "fresh", "growth", "rebirth", "blossom",
        "green", "rain", "warm", "Easter", "spring", "new beginnings",
    ],
    Season.SUMMER: [
        "sun", "heat", "beach", "vacation", "BBQ", "outdoor", "grill",
        "swim", "adventure", "bright", "summer", "freedom", "warm",
    ],
    Season.FALL: [
        "harvest", "cozy", "pumpkin", "crisp", "leaves", "autumn",
        "warm tones", "sweater", "Halloween", "Thanksgiving", "fall",
    ],
    Season.WINTER: [
        "snow", "cozy", "holiday", "Christmas", "cold", "warm",
        "festive", "New Year", "winter", "comfort", "celebration",
    ],
}

SEASONAL_THEMES: dict[Season, str] = {
    Season.SPRING: "renewal, growth, and fresh starts",
    Season.SUMMER: "energy, adventure, and outdoor experiences",
    Season.FALL: "harvest, comfort, and change",
    Season.WINTER: "warmth, celebration, and reflection",
}


def get_current_season() -> Season:
    month = date.today().month
    if month in (3, 4, 5):
        return Season.SPRING
    elif month in (6, 7, 8):
        return Season.SUMMER
    elif month in (9, 10, 11):
        return Season.FALL
    else:
        return Season.WINTER


def get_season_keywords(season: Season) -> list[str]:
    return SEASONAL_KEYWORDS.get(season, [])


def get_season_theme(season: Season) -> str:
    return SEASONAL_THEMES.get(season, "")


def detect_seasonal_keywords(text: str, season: Season) -> list[str]:
    keywords = get_season_keywords(season)
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def score_seasonal_relevance(text: str, season: Season) -> float:
    found = detect_seasonal_keywords(text, season)
    keywords = get_season_keywords(season)
    if not keywords:
        return 0.0
    return min(1.0, len(found) / max(3, len(keywords) * 0.3))
