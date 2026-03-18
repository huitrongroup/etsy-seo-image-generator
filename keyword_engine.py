from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from models import SEORequest
from keyword_rules import (
    AWKWARD_PATTERNS,
    BANNED_KEYWORDS,
    HIGH_INTENT_TERMS,
    INTENT_BUCKETS,
    WEAK_WORDS,
)
from keyword_sources import collect_keyword_candidates


TITLE_BUCKET_ORDER = [
    "relationship",     # title 1: emotional/core phrase
    "recipient",        # title 2: recipient angle
    "occasion",         # title 3: seasonal/occasion angle
    "personalization",  # title 4: personalization angle
    "general",          # title 5: adjacent/expansion angle
]


@dataclass
class ScoredKeyword:
    phrase: str
    score: int
    bucket: str
    reasons: list[str]


def normalize_keyword(keyword: str) -> str:
    keyword = keyword.lower().strip()
    keyword = re.sub(r"[/|,_\-]+", " ", keyword)
    keyword = re.sub(r"[^a-z0-9' ]+", "", keyword)
    keyword = re.sub(r"\s+", " ", keyword).strip()
    return keyword


def is_banned_keyword(keyword: str) -> bool:
    return keyword in BANNED_KEYWORDS


def detect_bucket(keyword: str) -> str:
    for bucket, terms in INTENT_BUCKETS.items():
        for term in terms:
            if term in keyword:
                return bucket
    return "general"


def keyword_root_key(keyword: str) -> str:
    """
    Used to prevent near-duplicate primary keywords across titles.
    """
    keyword = normalize_keyword(keyword)
    words = keyword.split()

    # remove common filler
    filler = {
        "gift", "mug", "cup", "coffee", "ceramic", "personalized",
        "custom", "name", "for", "from", "day", "with"
    }
    core = [w for w in words if w not in filler]

    if not core:
        core = words[:2]

    return " ".join(core[:3]).strip()


def score_keyword(keyword: str, req: SEORequest) -> ScoredKeyword | None:
    keyword = normalize_keyword(keyword)
    if not keyword:
        return None

    if is_banned_keyword(keyword):
        return None

    analysis = req.overrides.apply_to(req.analysis)
    recipient = (analysis.recipient or "").strip().lower()
    product_type = (analysis.product_type or "").strip().lower()
    occasion = (analysis.occasion or "").strip().lower()
    theme = (analysis.theme or "").strip().lower()

    score = 0
    reasons: list[str] = []

    if recipient and recipient in keyword:
        score += 4
        reasons.append("matches recipient")

    if product_type and any(part in keyword for part in product_type.split()):
        score += 4
        reasons.append("matches product")

    if occasion and occasion != "general" and occasion in keyword:
        score += 4
        reasons.append("matches occasion")

    if theme and theme in keyword:
        score += 2
        reasons.append("matches theme")

    for term, pts in HIGH_INTENT_TERMS.items():
        if term in keyword:
            score += pts
            reasons.append(f"contains high-intent term: {term}")

    word_count = len(keyword.split())
    if 2 <= word_count <= 4:
        score += 3
        reasons.append("good phrase length")
    elif word_count == 1:
        score -= 1
        reasons.append("too broad")
    elif word_count > 5:
        score -= 3
        reasons.append("too long")

    if keyword in AWKWARD_PATTERNS:
        score -= 5
        reasons.append("awkward phrase")

    for weak in WEAK_WORDS:
        if weak in keyword:
            score -= 4
            reasons.append(f"contains weak word: {weak}")

    if any(
        phrase in keyword
        for phrase in [
            "first mothers day",
            "expecting mom",
            "mom to be",
            "baby announcement",
            "pregnancy",
            "baby shower",
        ]
    ):
        score += 3
        reasons.append("expands adjacent search intent")

    # Extra boost for emotionally strong direct phrases
    if any(
        phrase in keyword
        for phrase in [
            "to my daughter",
            "gift from mom",
            "watching you be a mom",
        ]
    ):
        score += 4
        reasons.append("strong emotional/core phrase")

    bucket = detect_bucket(keyword)
    return ScoredKeyword(phrase=keyword, score=score, bucket=bucket, reasons=reasons)


def dedupe_keywords(scored: list[ScoredKeyword]) -> list[ScoredKeyword]:
    seen: set[str] = set()
    result: list[ScoredKeyword] = []

    for item in sorted(scored, key=lambda x: x.score, reverse=True):
        key = item.phrase
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def choose_primary_keywords_by_bucket(
    buckets: dict[str, list[ScoredKeyword]],
    max_titles: int = 5,
) -> list[ScoredKeyword]:
    """
    Select exactly one strong primary keyword per title bucket.
    Prevents repeated keyword clusters across titles.
    """
    chosen: list[ScoredKeyword] = []
    used_roots: set[str] = set()

    for bucket_name in TITLE_BUCKET_ORDER:
        for item in buckets.get(bucket_name, []):
            root = keyword_root_key(item.phrase)
            if root in used_roots:
                continue
            chosen.append(item)
            used_roots.add(root)
            break

        if len(chosen) == max_titles:
            return chosen

    # Fill remaining from best overall leftovers
    leftovers: list[ScoredKeyword] = []
    for bucket_items in buckets.values():
        leftovers.extend(bucket_items)

    for item in dedupe_keywords(leftovers):
        root = keyword_root_key(item.phrase)
        if root in used_roots:
            continue
        chosen.append(item)
        used_roots.add(root)
        if len(chosen) == max_titles:
            break

    return chosen[:max_titles]


def build_secondary_keywords(
    buckets: dict[str, list[ScoredKeyword]],
    primaries: list[ScoredKeyword],
    per_title: int = 3,
) -> dict[str, list[ScoredKeyword]]:
    """
    For each primary keyword, assign supporting keywords that do NOT duplicate the same root.
    """
    all_items: list[ScoredKeyword] = []
    for bucket_items in buckets.values():
        all_items.extend(bucket_items)

    all_items = dedupe_keywords(all_items)
    primary_roots = {keyword_root_key(p.phrase) for p in primaries}

    support_map: dict[str, list[ScoredKeyword]] = {}

    for primary in primaries:
        primary_root = keyword_root_key(primary.phrase)
        picked: list[ScoredKeyword] = []
        used_roots = {primary_root}

        # Prefer support from different buckets
        for item in all_items:
            item_root = keyword_root_key(item.phrase)
            if item_root in used_roots:
                continue
            if item_root in primary_roots and item.phrase != primary.phrase:
                continue
            if item.bucket == primary.bucket:
                continue

            picked.append(item)
            used_roots.add(item_root)

            if len(picked) == per_title:
                break

        support_map[primary.phrase] = picked

    return support_map


def build_keyword_plan(req: SEORequest) -> dict:
    raw_keywords = collect_keyword_candidates(req)

    scored: list[ScoredKeyword] = []
    for kw in raw_keywords:
        item = score_keyword(kw, req)
        if item and item.score > 0:
            scored.append(item)

    ranked = dedupe_keywords(scored)

    buckets = {
        "product": [],
        "recipient": [],
        "occasion": [],
        "personalization": [],
        "relationship": [],
        "general": [],
    }

    for item in ranked:
        buckets[item.bucket].append(item)

    primaries = choose_primary_keywords_by_bucket(buckets, max_titles=5)
    support_map = build_secondary_keywords(buckets, primaries, per_title=3)

    title_keyword_plan = []
    for idx, primary in enumerate(primaries, start=1):
        support = support_map.get(primary.phrase, [])
        title_keyword_plan.append(
            {
                "title_number": idx,
                "intent_bucket": primary.bucket,
                "primary_keyword": asdict(primary),
                "supporting_keywords": [asdict(s) for s in support],
            }
        )

    tag_keywords: list[ScoredKeyword] = []
    for bucket_name in ["product", "recipient", "occasion", "personalization", "relationship", "general"]:
        tag_keywords.extend(buckets[bucket_name][:4])

    tag_keywords = dedupe_keywords(tag_keywords)[:25]

    return {
        "ranked_keywords": [asdict(k) for k in ranked],
        "title_keyword_plan": title_keyword_plan,
        "tag_keywords": [asdict(k) for k in tag_keywords],
        "bucket_summary": {
            bucket: [asdict(k) for k in items]
            for bucket, items in buckets.items()
        },
    }