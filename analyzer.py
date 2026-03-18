"""
Step 1 of the pipeline: analyze the product image with Claude Vision.

Uses tool_use to guarantee a structured ImageAnalysis response.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import anthropic

from models import ImageAnalysis, ManualOverrides
from prompts import IMAGE_ANALYSIS_SYSTEM, build_analysis_user_message

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# ---------------------------------------------------------------------------
# Tool schema (mirrors ImageAnalysis fields)
# ---------------------------------------------------------------------------

_ANALYSIS_TOOL: dict = {
    "name": "submit_image_analysis",
    "description": "Submit the structured product image analysis for Etsy SEO generation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "product_type": {
                "type": "string",
                "description": "Specific physical product, e.g. 'ceramic coffee mug'",
            },
            "recipient": {
                "type": "string",
                "description": "Target recipient/audience, e.g. 'dad', 'nurse', 'dog mom'",
            },
            "visible_text": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Exact text/phrases visible on the design (empty list if none)",
            },
            "theme": {
                "type": "string",
                "description": "Overall product theme, e.g. 'camping humor', 'coffee lover'",
            },
            "occasion": {
                "type": "string",
                "description": "Specific occasion or holiday; 'general' if none",
            },
            "gifting_intent": {
                "type": "string",
                "description": "Most likely gifting scenario",
            },
            "keyword_candidates": {
                "type": "array",
                "items": {"type": "string"},
                "description": "12 buyer-intent keyword phrases",
            },
        },
        "required": [
            "product_type",
            "recipient",
            "visible_text",
            "theme",
            "occasion",
            "gifting_intent",
            "keyword_candidates",
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )
    return anthropic.Anthropic(api_key=api_key)


def _media_type(filename: str) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(Path(filename).suffix.lower(), "image/jpeg")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_image(
    image_bytes: bytes,
    filename: str,
    extra_context: str = "",
    overrides: ManualOverrides | None = None,
) -> ImageAnalysis:
    """
    Call Claude Vision to extract structured product information.

    Args:
        image_bytes: Raw bytes of the uploaded image.
        filename:    Original filename (used to infer MIME type).
        extra_context: Optional freeform text from the seller.
        overrides:   Optional manual field overrides applied after analysis.

    Returns:
        ImageAnalysis with overrides applied.
    """
    client = _get_client()
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    media = _media_type(filename)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=IMAGE_ANALYSIS_SYSTEM,
        tools=[_ANALYSIS_TOOL],
        tool_choice={"type": "any"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media,
                            "data": b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": build_analysis_user_message(extra_context),
                    },
                ],
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_image_analysis":
            analysis = ImageAnalysis(**block.input)
            if overrides:
                analysis = overrides.apply_to(analysis)
            return analysis

    raise RuntimeError(
        "Image analysis returned no structured output. Check the Claude API response."
    )
