from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ImageAnalysis(BaseModel):
    product_type: str = Field(
        description="Specific physical product, e.g. 'ceramic coffee mug with C-handle'"
    )
    recipient: str = Field(
        description="Target recipient or audience, e.g. 'dad', 'nurse', 'dog mom', 'teacher'"
    )
    visible_text: list[str] = Field(
        default_factory=list,
        description="Exact words or phrases readable on the design (empty list if none)",
    )
    theme: str = Field(
        description="Overall product theme, e.g. 'camping', 'coffee lover', 'nursing humor'"
    )
    occasion: str = Field(
        description="Specific occasion or holiday. Use 'general' if none detected."
    )
    gifting_intent: str = Field(
        description="Most likely gifting scenario, e.g. 'daughter buying for dad on Fathers Day'"
    )
    keyword_candidates: list[str] = Field(
        description="10-15 buyer-intent keyword phrases derived from visible content or strong implication"
    )


class ManualOverrides(BaseModel):
    product_type: Optional[str] = None
    recipient: Optional[str] = None
    occasion: Optional[str] = None
    phrase_text: Optional[str] = None

    def apply_to(self, analysis: ImageAnalysis) -> ImageAnalysis:
        updates: dict = {}
        if self.product_type:
            updates["product_type"] = self.product_type
        if self.recipient:
            updates["recipient"] = self.recipient
        if self.occasion:
            updates["occasion"] = self.occasion
        if self.phrase_text and self.phrase_text not in analysis.visible_text:
            updates["visible_text"] = analysis.visible_text + [self.phrase_text]
        return analysis.model_copy(update=updates) if updates else analysis


class SeasonalContext(BaseModel):
    season: str
    upcoming_holidays: list[str]
    seasonal_keywords: list[str]
    apply_seasonal: bool


class SEORequest(BaseModel):
    analysis: ImageAnalysis
    seasonal_context: SeasonalContext
    extra_context: Optional[str] = None
    overrides: ManualOverrides = Field(default_factory=ManualOverrides)


class SEOOutput(BaseModel):
    titles: list[str] = Field(description="Exactly 5 Etsy title options, each <= 140 chars")
    tags: list[str] = Field(description="Exactly 13 Etsy tags, each <= 20 chars")
    rationale: str = Field(description="2-3 sentences explaining the keyword strategy")

    @field_validator("titles")
    @classmethod
    def check_titles(cls, v: list[str]) -> list[str]:
        if len(v) != 5:
            raise ValueError(f"Expected 5 titles, got {len(v)}")
        for t in v:
            if len(t) > 140:
                raise ValueError(f"Title too long ({len(t)} chars): {t[:60]}")
        return v

    @field_validator("tags")
    @classmethod
    def check_tags(cls, v: list[str]) -> list[str]:
        if len(v) != 13:
            raise ValueError(f"Expected 13 tags, got {len(v)}")
        for tag in v:
            if len(tag) > 20:
                raise ValueError(f"Tag '{tag}' is {len(tag)} chars (max 20)")
        return v
