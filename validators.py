from __future__ import annotations

import re
from typing import Iterable


ETSY_TAG_MAX_LEN = 20
DEFAULT_TAG_COUNT = 13

# Hard replacements for phrases that frequently run too long or are weak.
TAG_REPLACEMENTS = {
    "daughter becoming mom": "new mom gift",
    "gift for daughter": "daughter gift",
    "mother to be gift": "mom to be gift",
    "first time mom gift": "new mom gift",
    "daughter pregnancy": "pregnant daughter",
    "gift for grandmother": "grandma gift",
    "gift for new mother": "new mom gift",
    "mothers day for grandma": "grandma mothers day",
    "grandma mothers day gift": "mothers day grandma",
    "mother's day grandma gift": "mothers day grandma",
}

# Remove weak filler or noisy terms if they appear as standalone words.
FILLER_WORDS = {
    "gift idea",
    "unique",
    "awesome",
    "perfect",
    "trendy",
    "aesthetic",
    "quote",
    "sentimental",
    "cute",
    "funny",
}

STOP_WORDS = {
    "a",
    "an",
    "the",
    "for",
    "to",
    "and",
    "with",
    "of",
    "from",
}


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_quotes(text: str) -> str:
    return text.replace("’", "'").replace("“", '"').replace("”", '"')


def clean_tag(tag: str, max_len: int = ETSY_TAG_MAX_LEN) -> str:
    """
    Normalizes a tag, applies replacements, removes junk, and shortens safely.
    """
    if not tag:
        return ""

    tag = _normalize_quotes(tag).lower().strip()
    tag = re.sub(r"[/|,_\-]+", " ", tag)
    tag = re.sub(r"[^a-z0-9' ]+", "", tag)
    tag = _normalize_spaces(tag)

    if not tag:
        return ""

    # Apply exact replacements first.
    if tag in TAG_REPLACEMENTS:
        tag = TAG_REPLACEMENTS[tag]

    # Remove filler phrases if present.
    for filler in sorted(FILLER_WORDS, key=len, reverse=True):
        tag = re.sub(rf"\b{re.escape(filler)}\b", "", tag)
    tag = _normalize_spaces(tag)

    if not tag:
        return ""

    # Re-apply replacements after cleanup.
    if tag in TAG_REPLACEMENTS:
        tag = TAG_REPLACEMENTS[tag]

    if len(tag) <= max_len:
        return tag

    # Try removing stop words first.
    words = [w for w in tag.split() if w not in STOP_WORDS]
    candidate = _normalize_spaces(" ".join(words))
    if candidate and len(candidate) <= max_len:
        return candidate

    # Build the longest phrase <= max_len.
    kept: list[str] = []
    current = ""
    for word in words or tag.split():
        test = f"{current} {word}".strip()
        if len(test) <= max_len:
            kept.append(word)
            current = test
        else:
            break

    candidate = _normalize_spaces(" ".join(kept))
    if candidate:
        return candidate

    # Last resort: hard cut.
    return tag[:max_len].rstrip()


def is_valid_tag(tag: str, max_len: int = ETSY_TAG_MAX_LEN) -> bool:
    if not tag:
        return False
    if len(tag) > max_len:
        return False
    return True


def normalize_tags(
    tags: Iterable[str],
    required_count: int = DEFAULT_TAG_COUNT,
    max_len: int = ETSY_TAG_MAX_LEN,
) -> list[str]:
    """
    Cleans, dedupes, and trims tags to Etsy-safe output.
    """
    cleaned: list[str] = []
    seen: set[str] = set()

    for raw_tag in tags:
        tag = clean_tag(raw_tag, max_len=max_len)

        if not is_valid_tag(tag, max_len=max_len):
            continue

        # Near-duplicate normalization
        dedupe_key = tag.replace("'", "")
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        cleaned.append(tag)

        if len(cleaned) == required_count:
            break

    return cleaned


def ensure_tag_count(
    tags: list[str],
    fallback_tags: Iterable[str],
    required_count: int = DEFAULT_TAG_COUNT,
    max_len: int = ETSY_TAG_MAX_LEN,
) -> list[str]:
    """
    Tops up tag list with fallback tags if generation came back short after cleanup.
    """
    result = normalize_tags(tags, required_count=required_count, max_len=max_len)

    if len(result) >= required_count:
        return result[:required_count]

    seen = {t.replace("'", "") for t in result}

    for raw_tag in fallback_tags:
        tag = clean_tag(raw_tag, max_len=max_len)
        if not is_valid_tag(tag, max_len=max_len):
            continue
        key = tag.replace("'", "")
        if key in seen:
            continue
        seen.add(key)
        result.append(tag)
        if len(result) == required_count:
            break

    return result[:required_count]

def tag_char_summary(tags: list[str]) -> list[dict]:
    """
    Returns tag metadata in the shape expected by app.py.
    """
    summary = []

    for tag in tags:
        length = len(tag)
        summary.append(
            {
                "tag": tag,
                "length": length,
                "ok": length <= 20,
            }
        )

    return summary


def validate_seo_output(seo_output):
    """
    Returns a list of human-readable issues for the UI.
    Empty list means no issues.
    """
    issues = []

    titles = getattr(seo_output, "titles", []) or []
    tags = getattr(seo_output, "tags", []) or []

    if not titles:
        issues.append("No titles were generated.")

    if not tags:
        issues.append("No tags were generated.")

    if len(tags) != 13:
        issues.append(f"Expected 13 tags, got {len(tags)}.")

    for tag in tags:
        if len(tag) > 20:
            issues.append(f"Tag '{tag}' is {len(tag)} chars (max 20).")

    return issues
    return True