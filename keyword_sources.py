from __future__ import annotations

from models import SEORequest


def collect_keyword_candidates(req: SEORequest) -> list[str]:
    analysis = req.overrides.apply_to(req.analysis)
    seasonal = req.seasonal_context

    product_type = (analysis.product_type or "").strip().lower()
    recipient = (analysis.recipient or "").strip().lower()
    theme = (analysis.theme or "").strip().lower()
    occasion = (analysis.occasion or "").strip().lower()

    keywords: list[str] = []

    # From model analysis
    keywords.extend([k.strip().lower() for k in analysis.keyword_candidates if k])

    # From visible text
    for text in analysis.visible_text:
        t = text.strip().lower()
        if t:
            keywords.append(t)

    # From base product logic
    if recipient and product_type:
        keywords.append(f"{recipient} {product_type}")
    if recipient:
        keywords.append(f"{recipient} gift")
    if product_type:
        keywords.append(product_type)

    if occasion and occasion != "general":
        keywords.append(occasion)
        if recipient:
            keywords.append(f"{occasion} {recipient}")
        if product_type:
            keywords.append(f"{occasion} {product_type}")

    if theme and product_type:
        keywords.append(f"{theme} {product_type}")

    # Seasonal
    if seasonal.apply_seasonal:
        keywords.extend([k.strip().lower() for k in seasonal.seasonal_keywords if k])

    # Expansion ideas
    if recipient == "daughter":
        keywords.extend([
            "gift for daughter",
            "daughter mug",
            "daughter coffee mug",
        ])

    if recipient in {"mom", "mother", "new mom"}:
        keywords.extend([
            "new mom gift",
            "new mom mug",
            "first mothers day",
            "mom to be gift",
            "expecting mom gift",
            "pregnancy gift",
            "baby announcement",
        ])

    if product_type == "mug":
        keywords.extend([
            "coffee mug",
            "ceramic mug",
            "floral coffee mug",
            "custom name mug",
            "personalized mug",
        ])

    return keywords