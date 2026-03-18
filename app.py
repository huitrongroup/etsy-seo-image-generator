"""
Etsy SEO Generator — Streamlit app

Two-step pipeline:
  1. Claude Vision → structured ImageAnalysis
  2. Claude text  → 5 Etsy titles + 13 tags + rationale
"""

from __future__ import annotations

import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from analyzer import analyze_image
from generators import generate_seo
from models import ManualOverrides, SEOOutput, SEORequest, ImageAnalysis
from seasonal import get_seasonal_context
from validators import tag_char_summary, validate_seo_output

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Etsy SEO Generator",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    /* Tag chips */
    .tag-chip {
        display: inline-block;
        background: #f0f2f6;
        border: 1px solid #ced4da;
        border-radius: 16px;
        padding: 3px 11px;
        margin: 3px;
        font-size: 13px;
        color: #333;
        font-family: monospace;
    }
    .tag-chip.over { background: #ffe0e0; border-color: #e74c3c; color: #c0392b; }

    /* Title card */
    .title-card {
        background: #f8f9fa;
        border-left: 4px solid #4f8ef7;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 10px;
        font-size: 15px;
        line-height: 1.5;
    }
    .title-meta {
        font-size: 11px;
        color: #888;
        margin-top: 4px;
    }
    .ok   { color: #27ae60; font-weight: bold; }
    .warn { color: #e67e22; font-weight: bold; }
    .err  { color: #e74c3c; font-weight: bold; }

    /* Section divider */
    .section-header {
        font-size: 18px;
        font-weight: 700;
        margin-top: 28px;
        margin-bottom: 6px;
        color: #1a1a2e;
    }

    /* Keyword chips inside analysis */
    .kw-chip {
        display: inline-block;
        background: #e8f4f8;
        border: 1px solid #acd;
        border-radius: 12px;
        padding: 2px 9px;
        margin: 2px;
        font-size: 12px;
        color: #2c5f7a;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session state keys
# ---------------------------------------------------------------------------

def _init_state() -> None:
    for key in ("analysis", "seo_output", "seasonal_ctx", "issues"):
        if key not in st.session_state:
            st.session_state[key] = None


_init_state()


# ---------------------------------------------------------------------------
# Sidebar — API key guard
# ---------------------------------------------------------------------------

def _check_api_key() -> bool:
    if os.getenv("ANTHROPIC_API_KEY"):
        return True
    with st.sidebar:
        st.error("ANTHROPIC_API_KEY not found.")
        key_input = st.text_input("Paste your API key", type="password", key="api_key_input")
        if key_input:
            os.environ["ANTHROPIC_API_KEY"] = key_input
            st.success("Key set for this session.")
            return True
    st.info("Add your Anthropic API key in the sidebar to get started.")
    return False


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _char_badge(n: int, limit: int) -> str:
    if n <= limit * 0.85:
        cls = "ok"
    elif n <= limit:
        cls = "warn"
    else:
        cls = "err"
    return f'<span class="{cls}">{n}/{limit}</span>'


def _render_analysis(analysis: ImageAnalysis) -> None:
    with st.expander("🔎 Image Analysis (expand to inspect)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Product type:** {analysis.product_type}")
            st.markdown(f"**Recipient:** {analysis.recipient}")
            st.markdown(f"**Theme:** {analysis.theme}")
        with c2:
            st.markdown(f"**Occasion:** {analysis.occasion}")
            st.markdown(f"**Gifting intent:** {analysis.gifting_intent}")

        if analysis.visible_text:
            st.markdown("**Visible text on design:**")
            for t in analysis.visible_text:
                st.code(t, language=None)

        st.markdown("**Keyword candidates:**")
        chips = "".join(f'<span class="kw-chip">{kw}</span>' for kw in analysis.keyword_candidates)
        st.markdown(chips, unsafe_allow_html=True)


def _render_titles(titles: list[str]) -> None:
    st.markdown('<div class="section-header">📝 Title Options</div>', unsafe_allow_html=True)
    st.caption("Etsy allows up to 140 characters per title. Pick one or mix elements.")

    for i, title in enumerate(titles, 1):
        n = len(title)
        badge = _char_badge(n, 140)
        st.markdown(
            f'<div class="title-card">'
            f"<strong>Option {i}</strong>&nbsp;&nbsp;{title}"
            f'<div class="title-meta">{badge} chars</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    # Copyable block
    with st.expander("Copy all titles as plain text"):
        st.code("\n\n".join(f"{i}. {t}" for i, t in enumerate(titles, 1)), language=None)


def _render_tags(tags: list[str]) -> None:
    st.markdown('<div class="section-header">🏷️ Tags (13)</div>', unsafe_allow_html=True)
    st.caption("Each tag is ≤ 20 characters. Etsy searches within multi-word tags.")

    summary = tag_char_summary(tags)
    chips = "".join(
        f'<span class="tag-chip{" over" if not t["ok"] else ""}" title="{t["length"]} chars">{t["tag"]}</span>'
        for t in summary
    )
    st.markdown(chips, unsafe_allow_html=True)

    with st.expander("Copy tags — comma-separated (paste into Etsy)"):
        st.code(", ".join(tags), language=None)

    with st.expander("Tag character counts"):
        for t in summary:
            icon = "🟢" if t["ok"] else "🔴"
            st.markdown(f"{icon} `{t['tag']}` — {t['length']}/20 chars")


def _render_rationale(rationale: str) -> None:
    st.markdown('<div class="section-header">💡 Keyword Strategy</div>', unsafe_allow_html=True)
    st.markdown(rationale)


def _render_issues(issues: list[str]) -> None:
    if not issues:
        st.success("All titles and tags passed validation.")
    else:
        st.warning(f"⚠️ {len(issues)} validation issue(s) detected:")
        for issue in issues:
            st.markdown(f"- {issue}")


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def _run_pipeline(
    image_bytes: bytes,
    filename: str,
    launch_date: date,
    extra_context: str,
    overrides: ManualOverrides,
) -> None:
    # Step 1: image analysis
    with st.spinner("🔍 Analyzing product image…"):
        try:
            analysis = analyze_image(
                image_bytes=image_bytes,
                filename=filename,
                extra_context=extra_context,
                overrides=overrides,
            )
        except Exception as exc:
            st.error(f"Image analysis failed: {exc}")
            return

    st.session_state.analysis = analysis

    # Seasonal context
    seasonal_ctx = get_seasonal_context(launch_date)
    st.session_state.seasonal_ctx = seasonal_ctx

    if seasonal_ctx.upcoming_holidays:
        st.info(
            "🗓️ **Seasonal keywords active** — holidays within 8 weeks of launch date: "
            + ", ".join(f"**{h}**" for h in seasonal_ctx.upcoming_holidays)
        )

    # Step 2: SEO generation
    req = SEORequest(
        analysis=analysis,
        seasonal_context=seasonal_ctx,
        extra_context=extra_context or None,
        overrides=overrides,
    )

    with st.spinner("✍️ Generating titles and tags…"):
        try:
            seo_output = generate_seo(req)
        except Exception as exc:
            st.error(f"SEO generation failed: {exc}")
            return

    st.session_state.seo_output = seo_output
    st.session_state.issues = validate_seo_output(seo_output)


def _run_regenerate(overrides: ManualOverrides, extra_context: str) -> None:
    """Re-run only step 2 using the cached analysis."""
    analysis: ImageAnalysis = st.session_state.analysis
    seasonal_ctx = st.session_state.seasonal_ctx

    # Apply any new overrides
    analysis = overrides.apply_to(analysis)

    req = SEORequest(
        analysis=analysis,
        seasonal_context=seasonal_ctx,
        extra_context=extra_context or None,
        overrides=overrides,
    )

    with st.spinner("🔄 Regenerating titles and tags…"):
        try:
            seo_output = generate_seo(req)
        except Exception as exc:
            st.error(f"Regeneration failed: {exc}")
            return

    st.session_state.seo_output = seo_output
    st.session_state.issues = validate_seo_output(seo_output)


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("🛍️ Etsy SEO Generator")
    st.markdown(
        "Upload a product image to generate optimised titles and tags using a two-step AI pipeline."
    )
    st.markdown("---")

    if not _check_api_key():
        return

    # ── Input columns ──────────────────────────────────────────────────────
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.subheader("📸 Product Image")
        uploaded = st.file_uploader(
            "Upload image",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
        if uploaded:
            st.image(uploaded, use_container_width=True)

    with right:
        st.subheader("⚙️ Settings")

        launch_date: date = st.date_input(
            "Launch date",
            value=date.today(),
            help="The date you plan to list this product. Used to apply holiday/seasonal keywords.",
        )

        extra_context: str = st.text_area(
            "Extra context (optional)",
            placeholder=(
                "E.g. 'This is a black ceramic mug with the phrase \"Dog Dad\" "
                "targeted at German Shepherd owners.'"
            ),
            height=90,
            help="Any details the image alone won't convey: niche, audience, phrasing, etc.",
        )

        with st.expander("🔧 Manual Overrides", expanded=False):
            st.caption(
                "Override the AI's detected values if they are inaccurate. "
                "Leave blank to use the AI result."
            )
            ov_product = st.text_input(
                "Product type", placeholder="e.g. ceramic coffee mug"
            )
            ov_recipient = st.text_input(
                "Recipient", placeholder="e.g. dog dad, nurse, teacher"
            )
            ov_occasion = st.text_input(
                "Occasion", placeholder="e.g. Father's Day, birthday, graduation"
            )
            ov_phrase = st.text_input(
                "Phrase text on design",
                placeholder='e.g. "World\'s Best Dog Dad"',
            )

        overrides = ManualOverrides(
            product_type=ov_product.strip() or None,
            recipient=ov_recipient.strip() or None,
            occasion=ov_occasion.strip() or None,
            phrase_text=ov_phrase.strip() or None,
        )

    # ── Action buttons ──────────────────────────────────────────────────────
    st.markdown("")
    btn_col1, btn_col2, _ = st.columns([1, 1, 3])

    with btn_col1:
        generate_btn = st.button(
            "🚀 Generate SEO",
            type="primary",
            disabled=not uploaded,
            use_container_width=True,
        )

    with btn_col2:
        regen_btn = st.button(
            "🔄 Regenerate Titles/Tags",
            disabled=st.session_state.analysis is None,
            use_container_width=True,
            help="Re-run only the title/tag step using the cached image analysis.",
        )

    if not uploaded:
        st.info("Upload a product image above to get started.")
        return

    # ── Run pipeline ────────────────────────────────────────────────────────
    if generate_btn:
        image_bytes = uploaded.read()
        _run_pipeline(
            image_bytes=image_bytes,
            filename=uploaded.name,
            launch_date=launch_date,
            extra_context=extra_context.strip(),
            overrides=overrides,
        )

    if regen_btn and st.session_state.analysis is not None:
        _run_regenerate(overrides=overrides, extra_context=extra_context.strip())

    # ── Results ─────────────────────────────────────────────────────────────
    if st.session_state.seo_output is None:
        return

    seo: SEOOutput = st.session_state.seo_output
    analysis: ImageAnalysis = st.session_state.analysis

    st.markdown("---")
    st.subheader("✅ Results")

    _render_issues(st.session_state.issues or [])
    _render_analysis(analysis)
    _render_titles(seo.titles)
    _render_tags(seo.tags)
    _render_rationale(seo.rationale)


if __name__ == "__main__":
    main()
