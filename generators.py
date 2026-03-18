from __future__ import annotations

import json
import os
import re

from anthropic import Anthropic

from models import SEOOutput, SEORequest
from validators import clean_tag, ensure_tag_count
from keyword_engine import build_keyword_plan

SYSTEM_PROMPT = """
You are an Etsy SEO expert.

Your job is to generate high-quality Etsy titles and tags from structured product data.

You must optimize for:
- buyer intent
- clarity
- readability
- strong keyword coverage without keyword stuffing

You are NOT allowed to generate titles that look like a pile of disconnected keywords.

## Core rules for titles
Generate exactly 5 Etsy title options.

Each title must:
- be 140 characters or fewer
- start with a strong primary keyword phrase when possible
- read like a real Etsy listing title, not a keyword dump
- contain 3 to 5 meaningful keyword segments max
- avoid repeating the same root words too many times
- avoid awkward phrases like:
  - gift from mom daughter
  - mother daughter
  - custom gift
  - personalized gift
  - special gift
  - unique item
  - thoughtful gift
- avoid filler and vague descriptors

Each title should follow one of these structures:

1. Primary Keyword, Recipient/Use Case, Occasion, Product Type
2. Recipient Product, Gift Angle, Occasion, Personalization Angle
3. Emotional Phrase/Product Theme, Recipient, Product Type, Occasion
4. Product Type, Recipient, Gift Intent, Occasion
5. Occasion Product, Recipient, Personalization/Product Detail

Each title must target a DIFFERENT buyer search intent.

Use these 5 distinct intents:

1. Core search phrase (highest volume keyword)
2. Recipient-focused search (e.g. daughter, mom, grandma)
3. Occasion-focused search (e.g. Mothers Day, pregnancy, baby announcement)
4. Personalization-focused search (e.g. custom name, personalized mug)
5. Emotional/message-driven search (based on visible text or sentiment)

Do NOT simply reorder the same keywords. Each title must feel like it could rank for a different search query.

## Keyword Expansion Rule

Do NOT limit keywords to the literal product description.

You must expand into adjacent high-intent search phrases that a buyer would realistically search.

Examples:
- "new mom gift" → also include "first time mom gift", "mom to be gift", "pregnancy gift"
- "daughter gift" → also include "gift for daughter", "daughter birthday gift"
- "mug" → also include "coffee mug", "ceramic mug", "tea cup"

Each title should introduce at least ONE new keyword angle that is NOT repeated across all titles.

Avoid making all 5 titles compete for the exact same search query.

## Core rules for tags
Generate exactly 13 Etsy tags.

Each tag must:
- be 20 characters or fewer
- be a real Etsy-style buyer search phrase
- avoid weak generic phrases
- avoid duplicates or near-duplicates
- avoid repeating the same root concept too many times
- not include banned broad words unless naturally part of a high-intent phrase
- Remove incomplete or awkward tag phrases. Every tag must read like a natural search query.
- Remove awkward or unnatural phrases (e.g., "new mom gift mom", "daughter new mom")
- Prefer clean, natural search phrases (e.g., "new mom gift", "gift from mom", "expecting mom gift")
- Tags must feel like real search queries, not word combinations

Do NOT use tags like:
- gift idea
- unique item
- special gift
- thoughtful gift
- aesthetic
- trendy
- awesome
- cute
- funny
- sentimental
- quote

## Tag Expansion Rule

At least 5 of the 13 tags must target adjacent or related search queries, not just direct variations.

Example:
Instead of repeating:
- new mom mug
- new mom coffee mug
- mom mug

Include:
- first time mom gift
- pregnancy gift
- baby announcement
- mom to be gift
- expecting mom gift

## Tag strategy
Build tags across these buckets:
1. product type
2. recipient
3. occasion
4. relationship/gift intent
5. personalization/theme

Try to cover different search angles instead of repeating the same exact idea.

## Seasonal logic
Use seasonal keywords only if they are highly relevant to BOTH:
- the launch timing
- the product itself

Do NOT force seasonal keywords if they are weak or unrelated.

Example:
- a grandma mug in April can use Mothers Day keywords
- do not inject Easter unless the product clearly fits Easter gifting

## Readability rules
Good title style:
- Daughter Mug, New Mom Gift from Mom, Personalized Coffee Cup, Mothers Day Gift

Bad title style:
- Daughter Mug Personalized New Mom Gift from Mom Watching You Be a Mom Coffee Mug Custom Name

## Banned weak words
Do not use these unless they are part of a clearly strong buyer phrase:
- funny
- cute
- sentimental
- quote
- unique
- perfect
- awesome
- gift idea
- trendy
- aesthetic
- thoughtful
- special

## Output format
Return valid JSON only in this exact shape:

{
  "titles": [
    "title 1",
    "title 2",
    "title 3",
    "title 4",
    "title 5"
  ],
  "tags": [
    "tag 1",
    "tag 2",
    "tag 3",
    "tag 4",
    "tag 5",
    "tag 6",
    "tag 7",
    "tag 8",
    "tag 9",
    "tag 10",
    "tag 11",
    "tag 12",
    "tag 13"
  ],
  "rationale": "2-3 sentences explaining the keyword strategy"
}
""".strip()


def _get_api_key() -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Missing ANTHROPIC_API_KEY.")
    return api_key


def _extract_text_from_response(response) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []):
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _extract_json(text: str) -> dict:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Claude did not return valid JSON.")

    return json.loads(match.group(0))


def _clean_title(title: str) -> str:
    if not title:
        return ""

    title = " ".join(str(title).split()).strip(" ,;-")

    weak_phrases = [
        "gift from mom daughter",
        "mother daughter",
        "custom gift",
        "personalized gift",
        "special gift",
        "unique item",
        "thoughtful gift",
    ]

    for phrase in weak_phrases:
        title = re.sub(rf"\b{re.escape(phrase)}\b", "", title, flags=re.IGNORECASE)

    title = re.sub(r"\s+", " ", title).strip(" ,;-")

    words = title.split()
    cleaned_words = []
    prev = None
    for word in words:
        if prev and prev.lower() == word.lower():
            continue
        cleaned_words.append(word)
        prev = word

    title = " ".join(cleaned_words).strip(" ,;-")

    if len(title) > 140:
        title = title[:140].rstrip(" ,;-")

    return title


def _bucketed_fallback_tags(req: SEORequest) -> list[str]:
    analysis = req.overrides.apply_to(req.analysis)
    seasonal = req.seasonal_context

    product_type = (analysis.product_type or "").strip().lower()
    recipient = (analysis.recipient or "").strip().lower()
    occasion = (analysis.occasion or "").strip().lower()
    theme = (analysis.theme or "").strip().lower()

    bucket_product: list[str] = []
    bucket_recipient: list[str] = []
    bucket_occasion: list[str] = []
    bucket_relationship: list[str] = []
    bucket_theme: list[str] = []

    if product_type:
        bucket_product.extend(
            [
                product_type,
                f"{product_type} gift",
            ]
        )

    if recipient:
        bucket_recipient.extend(
            [
                f"{recipient} gift",
                f"{recipient} {product_type}".strip(),
            ]
        )

    if occasion and occasion != "general":
        bucket_occasion.extend(
            [
                occasion,
                f"{occasion} gift",
                f"{occasion} {recipient}".strip(),
            ]
        )

    if recipient and "mom" in recipient:
        bucket_relationship.extend(["new mom gift", "mom mug", "mom to be gift"])
    if recipient == "daughter":
        bucket_relationship.extend(["daughter gift", "gift for daughter"])
    if recipient == "grandma":
        bucket_relationship.extend(["grandma gift", "nana gift"])

    if theme:
        bucket_theme.extend(
            [
                f"{theme} {product_type}".strip(),
                theme,
            ]
        )

    if seasonal.apply_seasonal:
        for kw in seasonal.seasonal_keywords:
            if kw:
                bucket_occasion.append(str(kw).strip().lower())

    combined = bucket_product + bucket_recipient + bucket_occasion + bucket_relationship + bucket_theme
    return combined


def _fallback_tags_from_request(req: SEORequest) -> list[str]:
    analysis = req.overrides.apply_to(req.analysis)
    seasonal = req.seasonal_context

    product_type = (analysis.product_type or "").strip().lower()
    recipient = (analysis.recipient or "").strip().lower()
    occasion = (analysis.occasion or "").strip().lower()
    theme = (analysis.theme or "").strip().lower()

    candidates: list[str] = _bucketed_fallback_tags(req)

    if recipient and product_type:
        candidates.append(f"{recipient} {product_type}")
    if recipient:
        candidates.append(f"{recipient} gift")
    if occasion and recipient and occasion != "general":
        candidates.append(f"{occasion} {recipient}")
    if occasion and product_type and occasion != "general":
        candidates.append(f"{occasion} {product_type}")
    if theme and product_type:
        candidates.append(f"{theme} {product_type}")

    for kw in analysis.keyword_candidates:
        if kw:
            candidates.append(str(kw).strip().lower())

    for kw in seasonal.seasonal_keywords:
        if kw:
            candidates.append(str(kw).strip().lower())

    if recipient == "grandma":
        candidates.extend(
            [
                "grandma mug",
                "grandma gift",
                "nana gift",
                "grandmother gift",
                "mothers day grandma",
            ]
        )

    if recipient in {"mom", "mother", "new mom"}:
        candidates.extend(
            [
                "new mom gift",
                "mom to be gift",
                "mom mug",
                "mothers day gift",
                "first time mom",
            ]
        )

    if recipient == "daughter":
        candidates.extend(
            [
                "daughter gift",
                "daughter mug",
                "pregnant daughter",
                "new mom gift",
            ]
        )

    if product_type == "mug":
        candidates.extend(["coffee mug", "ceramic mug", "gift mug"])
    elif product_type == "shirt":
        candidates.extend(["graphic tee", "gift shirt"])
    elif product_type == "bodysuit":
        candidates.extend(["baby bodysuit", "baby gift", "baby outfit"])

    return candidates


def _repair_titles(titles: list[str], req: SEORequest) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()

    for title in titles:
        title = _clean_title(title)
        if not title:
            continue

        key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(title)

    analysis = req.overrides.apply_to(req.analysis)

    product_type = (analysis.product_type or "gift").strip().title()
    recipient = (analysis.recipient or "").strip().title()
    occasion = (analysis.occasion or "").strip().title()
    theme = (analysis.theme or "").strip().title()

    visible_phrase = ""
    if analysis.visible_text:
        visible_phrase = analysis.visible_text[0].strip().title()

    fallback_pool = [
        ", ".join([x for x in [recipient, product_type, occasion] if x and x != "General"]),
        ", ".join([x for x in [recipient, "Gift", product_type] if x]),
        ", ".join([x for x in [occasion, recipient, product_type] if x and x != "General"]),
        ", ".join([x for x in [visible_phrase, recipient, product_type] if x]),
        ", ".join([x for x in [theme, recipient, product_type] if x]),
    ]

    for title in fallback_pool:
        title = _clean_title(title)
        if not title:
            continue

        key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(title)

        if len(cleaned) == 5:
            break

    while len(cleaned) < 5:
        cleaned.append(f"Listing Title {len(cleaned) + 1}")

    return cleaned[:5]


def _repair_output(seo, req: SEORequest) -> SEOOutput:
    repaired_titles = _repair_titles(list(getattr(seo, "titles", []) or []), req)

    fallback_tags = _fallback_tags_from_request(req)

    cleaned_input_tags = []
    for tag in list(getattr(seo, "tags", []) or []):
        cleaned = clean_tag(tag)
        if cleaned:
            cleaned_input_tags.append(cleaned)

    repaired_tags = ensure_tag_count(
        tags=cleaned_input_tags,
        fallback_tags=fallback_tags,
        required_count=13,
        max_len=20,
    )

    while len(repaired_tags) < 13:
        repaired_tags.append(f"tag{len(repaired_tags) + 1}")

    rationale = (getattr(seo, "rationale", "") or "").strip()
    if not rationale:
        rationale = "Keywords were generated from the image analysis, recipient, product type, and seasonal relevance."

    return SEOOutput(
        titles=repaired_titles,
        tags=repaired_tags[:13],
        rationale=rationale,
    )


def _build_user_prompt(req: SEORequest) -> str:
    analysis = req.overrides.apply_to(req.analysis)
    seasonal = req.seasonal_context
    keyword_plan = build_keyword_plan(req)

    payload = {
        "product_type": analysis.product_type,
        "recipient": analysis.recipient,
        "visible_text": analysis.visible_text,
        "theme": analysis.theme,
        "occasion": analysis.occasion,
        "gifting_intent": analysis.gifting_intent,
        "keyword_candidates": analysis.keyword_candidates,
        "season": seasonal.season,
        "upcoming_holidays": seasonal.upcoming_holidays,
        "seasonal_keywords": seasonal.seasonal_keywords,
        "apply_seasonal": seasonal.apply_seasonal,
        "extra_context": req.extra_context,
        "title_keyword_plan": keyword_plan["title_keyword_plan"],
        "recommended_tag_keywords": [k["phrase"] for k in keyword_plan["tag_keywords"]],
    }

    return f"""
Generate Etsy SEO output from this structured product context.

Structured context:
{json.dumps(payload, indent=2)}

Critical title rules:
- Generate exactly 5 titles.
- Each title MUST begin with its assigned primary keyword EXACTLY as written.
- Do not modify, reword, or replace the primary keyword.
- The primary keyword must appear at the start of the title.
- Each title must also use 2 to 3 supporting keywords from that title's supporting_keywords list.
- Do NOT reuse the same primary keyword across multiple titles.
- Each title must target a distinct buyer intent angle based on its assigned intent bucket.
- Each title must read naturally and cleanly, not like a keyword dump.
- Each title must include at least one strong buyer-intent phrase such as:
  "gift", "mothers day", "new mom", "first mothers day", "pregnancy", "mom to be", "baby shower"
- Avoid weak filler phrases like "ceramic cup", "sentimental", "quote", "special gift".
- Favor phrases that people actually search.
- Do NOT introduce new audiences or recipients that are not in the input.
- If the product is for "daughter", do NOT generate keywords like "grandma", "nana", etc.
- STRICTLY avoid filler phrases such as: "ceramic cup", "coffee cup", "spring gift", "sentimental", "quote" These do not add SEO value and must not be used unless absolutely necessary.
- Each title should follow this structure: [PRIMARY KEYWORD], [SUPPORTING KEYWORD 1], [SUPPORTING KEYWORD 2]

Do not exceed 3–4 meaningful segments.
Avoid stacking too many descriptors.

Critical tag rules:
- Generate exactly 13 tags.
- Each tag must be 20 characters or fewer.
- Prefer the recommended_tag_keywords list.
- Tags must be natural search phrases, not awkward word combinations.
- Avoid duplicate or near-duplicate tags.
- Avoid weak generic phrases.

Return valid JSON only.
""".strip()


def generate_seo(req: SEORequest) -> SEOOutput:
    client = Anthropic(api_key=_get_api_key())

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _build_user_prompt(req),
            }
        ],
    )

    raw_text = _extract_text_from_response(response)
    data = _extract_json(raw_text)

    raw_titles = data.get("titles", []) or []
    raw_tags = data.get("tags", []) or []
    raw_rationale = data.get("rationale", "") or ""

    class TempSEO:
        def __init__(self, titles, tags, rationale):
            self.titles = titles
            self.tags = tags
            self.rationale = rationale

    temp_seo = TempSEO(
        titles=raw_titles,
        tags=raw_tags,
        rationale=raw_rationale,
    )

    return _repair_output(temp_seo, req)