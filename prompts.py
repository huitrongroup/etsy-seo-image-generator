"""
Claude prompt templates for the two-step Etsy SEO pipeline.

Step 1 — IMAGE_ANALYSIS_SYSTEM / build_analysis_user_message:
  Claude Vision analyzes the product image and returns a structured ImageAnalysis.

Step 2 — build_seo_prompt:
  Claude generates 5 titles + 13 tags from the structured data plus hard rules.
"""

from __future__ import annotations

from models import SEORequest
from rules import BANNED_WORDS, ETSY_TAG_MAX, ETSY_TITLE_MAX, ETSY_TAG_COUNT, ETSY_TITLE_COUNT

# ---------------------------------------------------------------------------
# Step 1 — image analysis
# ---------------------------------------------------------------------------

IMAGE_ANALYSIS_SYSTEM = """\
You are an expert Etsy product analyst and SEO researcher.
Your job is to extract structured information from a product image so it can be
used to write high-converting Etsy titles and tags.

Be specific and literal — only describe what you can actually see or strongly infer.
Do NOT invent details. Do NOT use vague language.
"""

IMAGE_ANALYSIS_USER = """\
Analyze this product image and call the `submit_image_analysis` tool with:

• product_type — the exact physical product (e.g. "ceramic coffee mug", "canvas tote bag")
• recipient — who this is for (e.g. "dad", "nurse", "dog mom", "teacher", "new homeowner")
• visible_text — every word or phrase you can read on the design (empty list if none)
• theme — the overall concept or niche (e.g. "camping humor", "coffee lover", "dog dad")
• occasion — the specific occasion or holiday it is designed for; use "general" if none
• gifting_intent — the most likely reason someone buys this as a gift
  (e.g. "daughter buying for dad on Father's Day")
• keyword_candidates — exactly 12 buyer-intent search phrases a shopper might type on Etsy,
  based strictly on what is visible or strongly implied. Mix recipient-based, occasion-based,
  and product-based phrases. Use natural multi-word phrases (2–5 words).
"""


def build_analysis_user_message(extra_context: str = "") -> str:
    msg = IMAGE_ANALYSIS_USER
    if extra_context:
        msg += f"\n\nAdditional context from the seller: {extra_context}"
    return msg


# ---------------------------------------------------------------------------
# Step 2 — SEO generation
# ---------------------------------------------------------------------------

def build_seo_prompt(req: SEORequest) -> str:
    analysis = req.analysis
    seasonal = req.seasonal_context

    banned_str = ", ".join(sorted(BANNED_WORDS))

    # Build seasonal block only when relevant
    seasonal_block = ""
    if seasonal.apply_seasonal and seasonal.upcoming_holidays:
        holidays_str = ", ".join(seasonal.upcoming_holidays)
        kw_sample = ", ".join(seasonal.seasonal_keywords[:12])
        seasonal_block = f"""
SEASONAL CONTEXT (launch date is within 8 weeks of these holidays):
  Holidays: {holidays_str}
  Suggested seasonal phrases: {kw_sample}

  RULE: Only weave seasonal/holiday keywords in when they naturally fit this specific product.
  A generic mug or tote can carry most holiday phrases. A product that is already
  occasion-specific (e.g. graduation mug) should stick to its own occasion.
"""

    extra_block = ""
    if req.extra_context:
        extra_block = f"\nADDITIONAL SELLER CONTEXT:\n  {req.extra_context}\n"

    visible_text_str = (
        '  "' + '", "'.join(analysis.visible_text) + '"'
        if analysis.visible_text
        else "  (none)"
    )

    return f"""You are an expert Etsy SEO strategist with deep knowledge of buyer search behaviour.
Generate optimized titles and tags for the product described below.

━━━━━━━━━━━━━━━━━━━━━━━━
PRODUCT DATA
━━━━━━━━━━━━━━━━━━━━━━━━
  Product type   : {analysis.product_type}
  Recipient      : {analysis.recipient}
  Theme          : {analysis.theme}
  Occasion       : {analysis.occasion}
  Gifting intent : {analysis.gifting_intent}
  Visible text   :
{visible_text_str}
  Keyword candidates from image analysis:
    {", ".join(analysis.keyword_candidates)}
{seasonal_block}{extra_block}
━━━━━━━━━━━━━━━━━━━━━━━━
HARD RULES — violating any of these is a failure
━━━━━━━━━━━━━━━━━━━━━━━━
1. NEVER use these words anywhere: {banned_str}
2. Titles: each must be ≤ {ETSY_TITLE_MAX} characters
3. Tags  : each must be ≤ {ETSY_TAG_MAX} characters
4. Generate EXACTLY {ETSY_TITLE_COUNT} titles and EXACTLY {ETSY_TAG_COUNT} tags
5. No keyword stuffing — do not repeat the same root word more than twice in one title
6. Tags must be multi-word phrases (2–4 words) whenever possible; avoid single generic words

━━━━━━━━━━━━━━━━━━━━━━━━
TITLE STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━
• Lead each title with the highest-traffic keyword phrase for this product
• Include: product type + recipient + occasion where it reads naturally
• Vary the opening keyword and structure across all 5 options — do NOT just rearrange the same words
• Make every title a complete, natural-sounding phrase a buyer might scan
• Prioritise long-tail buyer-intent over short generic terms
• Include the design's phrase text when it adds search value
• Only include holiday/season keywords when they fit naturally for this product

━━━━━━━━━━━━━━━━━━━━━━━━
TAG STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━
• Cover: product type, recipient, relationship angle, occasion, use-case, gifting context
• No two tags should be near-duplicates of each other
• Mix broader reach tags with specific long-tail tags
• Tags are lowercase, no hashtags, no punctuation except hyphens

━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — return ONLY valid JSON, no markdown fences, no commentary
━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "titles": [
    "title option 1",
    "title option 2",
    "title option 3",
    "title option 4",
    "title option 5"
  ],
  "tags": [
    "tag 1", "tag 2", "tag 3", "tag 4", "tag 5",
    "tag 6", "tag 7", "tag 8", "tag 9", "tag 10",
    "tag 11", "tag 12", "tag 13"
  ],
  "rationale": "2-3 sentences explaining why these keywords were chosen and what buyer intent they target."
}}"""
