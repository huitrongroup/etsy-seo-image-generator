"""
Hard rules for Etsy SEO output:
- Banned words that must never appear in titles or tags
- Length limits (Etsy platform constraints)
- Root-word repetition detection (anti-stuffing)
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Platform limits
# ---------------------------------------------------------------------------

ETSY_TITLE_MAX = 140
ETSY_TAG_MAX = 20
ETSY_TAG_COUNT = 13
ETSY_TITLE_COUNT = 5

# ---------------------------------------------------------------------------
# Banned words (must never appear in generated output)
# ---------------------------------------------------------------------------

BANNED_WORDS: frozenset[str] = frozenset({
    "funny",
    "cute",
    "sentimental",
    "quote",
    "unique",
    "perfect",
    "awesome",
    "gift idea",
    "trendy",
    "aesthetic",
})

# ---------------------------------------------------------------------------
# Banned-word checking
# ---------------------------------------------------------------------------

def find_banned_words(text: str) -> list[str]:
    """Return any banned words/phrases found in `text` (case-insensitive, whole-word)."""
    text_lower = text.lower()
    found: list[str] = []
    for word in BANNED_WORDS:
        # Multi-word banned phrases need a simple substring check
        if " " in word:
            if word in text_lower:
                found.append(word)
        else:
            if re.search(r"\b" + re.escape(word) + r"\b", text_lower):
                found.append(word)
    return found


# ---------------------------------------------------------------------------
# Root-word repetition (anti-stuffing)
# ---------------------------------------------------------------------------

# Common suffixes to strip for basic stemming
_SUFFIXES = ("ing", "tion", "ness", "ment", "ful", "less", "ers", "er", "ed", "es", "ly", "s")


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def get_root_counts(text: str) -> dict[str, int]:
    """Map each stemmed root to how many times it appears in `text`."""
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    # Skip very common stop-words that inflate counts meaninglessly
    stop = {"for", "and", "the", "with", "from", "gift", "your", "that", "this", "has", "are"}
    counts: dict[str, int] = {}
    for w in words:
        if w in stop:
            continue
        root = _stem(w)
        counts[root] = counts.get(root, 0) + 1
    return counts


def detect_root_repetition(title: str, threshold: int = 2) -> list[str]:
    """Return root words that appear more than `threshold` times in one title."""
    return [r for r, n in get_root_counts(title).items() if n > threshold]


# ---------------------------------------------------------------------------
# Per-item validators
# ---------------------------------------------------------------------------

def validate_title(title: str) -> list[str]:
    issues: list[str] = []
    if len(title) > ETSY_TITLE_MAX:
        issues.append(f"Too long: {len(title)} chars (max {ETSY_TITLE_MAX})")
    banned = find_banned_words(title)
    if banned:
        issues.append(f"Banned words: {', '.join(banned)}")
    repeated = detect_root_repetition(title)
    if repeated:
        issues.append(f"Root words repeated >2x: {', '.join(repeated)}")
    return issues


def validate_tag(tag: str) -> list[str]:
    issues: list[str] = []
    if len(tag) > ETSY_TAG_MAX:
        issues.append(f"Too long: {len(tag)} chars (max {ETSY_TAG_MAX})")
    banned = find_banned_words(tag)
    if banned:
        issues.append(f"Banned words: {', '.join(banned)}")
    return issues


# ---------------------------------------------------------------------------
# Sanitization helpers (use only as last resort — prefer correct generation)
# ---------------------------------------------------------------------------

def sanitize_title(title: str) -> str:
    return title.strip()[:ETSY_TITLE_MAX]


def sanitize_tag(tag: str) -> str:
    return tag.strip().lower()[:ETSY_TAG_MAX]
