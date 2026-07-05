"""Shared UI components."""

from __future__ import annotations

import streamlit as st

from ssa_frontend.styles import CUSTOM_CSS

PIPELINE_STAGES = [
    "received",
    "extracting",
    "validating",
    "scoring",
    "recommending",
    "decided",
]


def inject_styles() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(
        """
        <div class="main-header">
            <h1>Social Support AI Portal</h1>
            <p>Automated eligibility assessment and economic enablement recommendations</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stepper(status: str) -> None:
    if status == "failed":
        st.error("Processing failed. See details below.")
        return

    steps_html = []
    active_idx = PIPELINE_STAGES.index(status) if status in PIPELINE_STAGES else 0
    labels = {
        "received": "Received",
        "extracting": "Extracting",
        "validating": "Validating",
        "scoring": "Scoring",
        "recommending": "Recommending",
        "decided": "Decided",
    }
    for idx, stage in enumerate(PIPELINE_STAGES):
        cls = "step"
        if idx < active_idx:
            cls += " done"
        elif idx == active_idx:
            cls += " active"
        steps_html.append(f'<div class="{cls}">{labels[stage]}</div>')

    st.markdown(f'<div class="stepper">{"".join(steps_html)}</div>', unsafe_allow_html=True)


def outcome_badge(outcome: str | None) -> str:
    if outcome == "approve":
        return '<span class="badge badge-approve">Approved</span>'
    if outcome == "soft_decline":
        return '<span class="badge badge-decline">Soft Decline</span>'
    if outcome == "needs_review":
        return '<span class="badge badge-review">Needs Review</span>'
    return '<span class="badge badge-processing">Processing</span>'
