from __future__ import annotations

BANNED_KEYWORDS = {
    "gift idea",
    "unique item",
    "special gift",
    "thoughtful gift",
    "cute mug",
    "funny mug",
    "sentimental gift",
    "quote mug",
    "aesthetic gift",
    "trendy gift",
}

WEAK_WORDS = {
    "cute",
    "funny",
    "sentimental",
    "quote",
    "unique",
    "perfect",
    "awesome",
    "gift idea",
    "trendy",
    "aesthetic",
    "thoughtful",
    "special",
}

HIGH_INTENT_TERMS = {
    "gift": 3,
    "mug": 2,
    "coffee mug": 3,
    "ceramic mug": 2,
    "personalized": 3,
    "custom": 3,
    "name": 2,
    "mothers day": 4,
    "new mom": 4,
    "mom to be": 4,
    "pregnancy": 4,
    "baby announcement": 4,
    "first mothers day": 5,
    "expecting mom": 4,
    "daughter": 3,
    "grandma": 3,
    "nana": 3,
}

INTENT_BUCKETS = {
    "product": {
        "mug", "coffee mug", "ceramic mug", "cup", "coffee cup", "tea cup", "floral mug"
    },
    "recipient": {
        "daughter", "mom", "mother", "new mom", "mom to be", "expecting mom", "grandma", "nana"
    },
    "occasion": {
        "mothers day", "first mothers day", "pregnancy", "baby announcement", "baby shower"
    },
    "personalization": {
        "personalized", "custom", "custom name", "name", "with name"
    },
    "relationship": {
        "gift from mom", "gift for daughter", "mother daughter", "to my daughter"
    },
}

AWKWARD_PATTERNS = {
    "mug mom daughter",
    "daughter becoming",
    "new mom gift mom",
    "personalized name",
    "watching you be mom",
    "mother daughter gift mug",
}