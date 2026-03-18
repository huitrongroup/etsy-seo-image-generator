"""
Holiday detection and seasonal keyword mapping for Etsy SEO.

Given a launch date, surfaces which holidays fall within the next 8 weeks
and returns buyer-intent keyword phrases for each one.
"""

from __future__ import annotations

from datetime import date, timedelta

from models import SeasonalContext

# ---------------------------------------------------------------------------
# Keyword bank
# ---------------------------------------------------------------------------

HOLIDAY_KEYWORDS: dict[str, list[str]] = {
    "Valentine's Day": [
        "valentines day gift",
        "gift for wife",
        "gift for girlfriend",
        "gift for boyfriend",
        "gift for husband",
        "romantic gift for her",
        "romantic gift for him",
    ],
    "Mother's Day": [
        "mothers day gift",
        "gift for mom",
        "mom gift from daughter",
        "mom gift from son",
        "new mom gift",
        "gift for grandma",
    ],
    "Father's Day": [
        "fathers day gift",
        "gift for dad",
        "dad gift from daughter",
        "dad gift from son",
        "new dad gift",
        "gift for grandpa",
    ],
    "Christmas": [
        "christmas gift",
        "christmas present",
        "stocking stuffer",
        "secret santa gift",
        "white elephant gift",
        "holiday gift for him",
        "holiday gift for her",
    ],
    "Halloween": [
        "halloween gift",
        "halloween decor",
        "spooky season gift",
        "fall gift",
    ],
    "Thanksgiving": [
        "thanksgiving gift",
        "fall harvest gift",
        "thankful gift",
    ],
    "Easter": [
        "easter gift",
        "easter basket filler",
        "spring gift",
    ],
    "Hanukkah": [
        "hanukkah gift",
        "jewish holiday gift",
        "holiday gift",
    ],
    "New Year": [
        "new year gift",
        "new beginnings gift",
    ],
    "Graduation": [
        "graduation gift",
        "grad gift",
        "senior gift",
        "college grad gift",
        "high school grad gift",
    ],
    "4th of July": [
        "fourth of july gift",
        "patriotic gift",
        "independence day",
    ],
    "St. Patrick's Day": [
        "st patricks day gift",
        "irish gift",
        "lucky gift",
    ],
    "Back to School": [
        "back to school gift",
        "teacher gift",
        "student gift",
    ],
}

SEASON_KEYWORDS: dict[str, list[str]] = {
    "spring": ["spring gift", "spring decor"],
    "summer": ["summer gift", "summer fun gift"],
    "fall": ["fall gift", "fall decor", "autumn gift"],
    "winter": ["winter gift", "cozy gift"],
}

# How far ahead (in days) to look for upcoming holidays
HOLIDAY_WINDOW_DAYS = 56  # 8 weeks


# ---------------------------------------------------------------------------
# Holiday date calculators
# ---------------------------------------------------------------------------

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the nth occurrence of `weekday` (0=Mon … 6=Sun) in the given month/year."""
    first = date(year, month, 1)
    days_ahead = (weekday - first.weekday()) % 7
    return first + timedelta(days=days_ahead + (n - 1) * 7)


def _easter(year: int) -> date:
    """Compute Easter Sunday via the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month = (h + ll - 7 * m + 114) // 31
    day = (h + ll - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _all_holidays(year: int) -> dict[str, date]:
    return {
        "Valentine's Day": date(year, 2, 14),
        "St. Patrick's Day": date(year, 3, 17),
        "Easter": _easter(year),
        "Mother's Day": _nth_weekday(year, 5, 6, 2),   # 2nd Sunday in May
        "Father's Day": _nth_weekday(year, 6, 6, 3),   # 3rd Sunday in June
        "4th of July": date(year, 7, 4),
        "Back to School": date(year, 8, 20),            # approximate
        "Halloween": date(year, 10, 31),
        "Thanksgiving": _nth_weekday(year, 11, 3, 4),  # 4th Thursday in Nov
        "Hanukkah": date(year, 12, 1),                  # approximate; varies yearly
        "Christmas": date(year, 12, 25),
        "New Year": date(year, 1, 1),
        "Graduation": date(year, 5, 15),                # approximate window
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_season(d: date) -> str:
    month = d.month
    if month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    elif month in (9, 10, 11):
        return "fall"
    return "winter"


def get_upcoming_holidays(launch_date: date, window_days: int = HOLIDAY_WINDOW_DAYS) -> list[str]:
    """Return holiday names whose date falls within `window_days` after `launch_date`."""
    upcoming: list[str] = []
    for year in (launch_date.year, launch_date.year + 1):
        for name, hdate in _all_holidays(year).items():
            delta = (hdate - launch_date).days
            if 0 <= delta <= window_days:
                upcoming.append(name)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for h in upcoming:
        if h not in seen:
            seen.add(h)
            result.append(h)
    return result


def get_seasonal_context(launch_date: date) -> SeasonalContext:
    season = get_current_season(launch_date)
    holidays = get_upcoming_holidays(launch_date)

    keywords: list[str] = list(SEASON_KEYWORDS.get(season, []))
    for holiday in holidays:
        keywords.extend(HOLIDAY_KEYWORDS.get(holiday, []))

    # Deduplicate, preserve order
    seen_kw: set[str] = set()
    unique_keywords: list[str] = []
    for kw in keywords:
        if kw not in seen_kw:
            seen_kw.add(kw)
            unique_keywords.append(kw)

    return SeasonalContext(
        season=season,
        upcoming_holidays=holidays,
        seasonal_keywords=unique_keywords,
        apply_seasonal=bool(holidays),
    )
