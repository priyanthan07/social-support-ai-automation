"""Main Streamlit entrypoint with custom-themed multi-page navigation."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st

from ssa_frontend.api_client import ApiClient
from ssa_frontend.components import inject_styles, outcome_badge, render_header, render_stepper

st.set_page_config(
    page_title="Social Support AI",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
render_header()

api = ApiClient()

if "application_id" not in st.session_state:
    st.session_state.application_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    st.markdown("### Navigation")
    page = st.radio(
        "Go to",
        ["Apply", "Live Processing", "Decision", "Assistant", "Officer Dashboard"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Backend status**")
    try:
        health = api.health()
        st.success(f"{health.get('app', 'API')} — {health.get('env', 'dev')}")
    except Exception as exc:
        st.error(f"Backend unreachable: {exc}")
    if st.session_state.application_id:
        st.info(f"Active application:\n`{st.session_state.application_id}`")

# --------------------------------------------------------------------------- #
# Apply
# --------------------------------------------------------------------------- #
if page == "Apply":
    st.markdown('<div class="card"><div class="card-title">New Application</div></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        applicant_name = st.text_input("Full name *", placeholder="Aisha Abdullah Al Mansoori")
        emirates_id = st.text_input("Emirates ID", placeholder="784-1988-1234567-1")
        email = st.text_input("Email", placeholder="applicant@example.com")
        phone = st.text_input("Phone", placeholder="+971501234567")
    with col2:
        monthly_income = st.number_input("Monthly income (AED)", min_value=0.0, value=5000.0, step=500.0)
        family_size = st.number_input("Family size", min_value=1, max_value=15, value=4)
        num_dependents = st.number_input("Dependents", min_value=0, max_value=12, value=2)
        employment_status = st.selectbox(
            "Employment status",
            ["employed", "self_employed", "unemployed", "retired", "student"],
        )
        education_level = st.selectbox(
            "Education level",
            ["none", "high_school", "diploma", "bachelor", "postgraduate"],
        )
        housing_status = st.selectbox(
            "Housing status",
            ["owned", "rented", "family", "government_housing"],
        )
        has_disability = st.selectbox("Has disability", ["no", "yes"])
        address = st.text_input("Address", placeholder="Villa 12, Al Wathba, Abu Dhabi")

    st.markdown("#### Upload documents")
    doc_cols = st.columns(2)
    uploads = {
        "emirates_id": doc_cols[0].file_uploader("Emirates ID (image)", type=["png", "jpg", "jpeg"]),
        "bank_statement": doc_cols[1].file_uploader("Bank statement (PDF)", type=["pdf"]),
        "resume": doc_cols[0].file_uploader("Resume (PDF)", type=["pdf"]),
        "assets_liabilities": doc_cols[1].file_uploader("Assets/Liabilities (Excel)", type=["xlsx", "xls", "csv"]),
        "credit_report": st.file_uploader("Credit report (PDF)", type=["pdf"]),
    }

    if st.button("Submit Application", type="primary", use_container_width=True):
        if not applicant_name.strip():
            st.error("Applicant name is required.")
        else:
            form_data = {
                "monthly_income": monthly_income,
                "family_size": int(family_size),
                "num_dependents": int(num_dependents),
                "employment_status": employment_status,
                "education_level": education_level,
                "housing_status": housing_status,
                "marital_status": "married",
                "nationality_group": "citizen",
                "has_disability": has_disability,
                "address": address,
                "age": 35,
                "employment_years": 5,
                "months_employed_last_2yrs": 18,
                "total_assets": 50000,
                "total_liabilities": 30000,
                "net_worth": 20000,
                "credit_score": 620,
            }
            try:
                with st.spinner("Creating application..."):
                    app = api.create_application(
                        {
                            "applicant_name": applicant_name,
                            "emirates_id": emirates_id or None,
                            "email": email or None,
                            "phone": phone or None,
                            "form_data": form_data,
                        }
                    )
                    app_id = app["id"]
                    for doc_type, uploaded in uploads.items():
                        if uploaded is not None:
                            api.upload_document(app_id, doc_type, uploaded.getvalue(), uploaded.name)
                    api.process_application(app_id)
                    st.session_state.application_id = app_id
                    st.session_state.chat_history = []
                st.success(f"Application submitted and processing started. ID: `{app_id}`")
                st.info("Go to **Live Processing** to watch progress.")
            except Exception as exc:
                st.error(f"Submission failed: {exc}")

    demo_dir = Path("/data/synthetic/documents/aisha_eligible")
    if not demo_dir.exists():
        demo_dir = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "synthetic"
            / "documents"
            / "aisha_eligible"
        )
    if demo_dir.exists() and st.button("Load demo documents (Aisha - eligible)"):
        st.session_state.demo_dir = str(demo_dir)
        st.success(f"Demo path set: {demo_dir.name}. Fill the form and submit to use these files manually.")

# --------------------------------------------------------------------------- #
# Live Processing
# --------------------------------------------------------------------------- #
elif page == "Live Processing":
    st.markdown('<div class="card"><div class="card-title">Live Processing</div></div>', unsafe_allow_html=True)
    app_id = st.text_input("Application ID", value=st.session_state.application_id or "")

    if app_id:
        auto_refresh = st.checkbox("Auto-refresh while processing", value=True)
        if st.button("Refresh now"):
            st.rerun()
        try:
            app = api.get_application(app_id)
            st.session_state.application_id = app_id
            render_stepper(app["status"])
            st.markdown(f"**Status:** `{app['status']}`")
            if app.get("error"):
                st.error(app["error"])
            if app.get("audit"):
                st.markdown("#### Audit trail")
                for entry in app["audit"][-8:]:
                    st.caption(f"[{entry['stage']}] {entry['message']}")
            if app["status"] == "decided":
                st.success("Processing complete — view the **Decision** page.")
            elif auto_refresh and app["status"] not in {"decided", "failed"}:
                time.sleep(3)
                st.rerun()
        except Exception as exc:
            st.error(f"Could not load application: {exc}")

# --------------------------------------------------------------------------- #
# Decision
# --------------------------------------------------------------------------- #
elif page == "Decision":
    st.markdown('<div class="card"><div class="card-title">Decision & Recommendations</div></div>', unsafe_allow_html=True)
    app_id = st.text_input("Application ID", value=st.session_state.application_id or "")

    if app_id and st.button("Load decision", use_container_width=True):
        try:
            app = api.get_application(app_id)
            decision = app.get("decision")
            if not decision:
                st.warning("No decision yet. Processing may still be running.")
            else:
                st.markdown(outcome_badge(decision["outcome"]), unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.markdown(
                    f'<div class="metric-box"><div class="metric-value">AED {decision.get("support_amount", 0):,.0f}</div><div class="metric-label">Suggested support / month</div></div>',
                    unsafe_allow_html=True,
                )
                prob = decision.get("eligibility_probability")
                m2.markdown(
                    f'<div class="metric-box"><div class="metric-value">{prob:.0%}</div><div class="metric-label">Eligibility probability</div></div>'
                    if prob is not None
                    else '<div class="metric-box"><div class="metric-value">—</div><div class="metric-label">Eligibility probability</div></div>',
                    unsafe_allow_html=True,
                )
                conf = decision.get("confidence")
                m3.markdown(
                    f'<div class="metric-box"><div class="metric-value">{conf:.0%}</div><div class="metric-label">Confidence</div></div>'
                    if conf is not None
                    else '<div class="metric-box"><div class="metric-value">—</div><div class="metric-label">Confidence</div></div>',
                    unsafe_allow_html=True,
                )

                if decision.get("narrative"):
                    st.markdown("#### Explanation")
                    st.write(decision["narrative"])

                if decision.get("reasons"):
                    st.markdown("#### Key factors")
                    for reason in decision["reasons"]:
                        st.markdown(f"- {reason}")

                if decision.get("validation_flags"):
                    st.markdown("#### Validation flags")
                    for flag in decision["validation_flags"]:
                        st.warning(f"[{flag.get('severity', 'info')}] {flag.get('message')}")

                if decision.get("recommendations"):
                    st.markdown("#### Economic enablement recommendations")
                    for rec in decision["recommendations"]:
                        st.markdown(
                            f"**{rec.get('title', 'Program')}** ({rec.get('category', 'general')}) — "
                            f"{rec.get('rationale', '')}"
                        )
        except Exception as exc:
            st.error(f"Could not load decision: {exc}")

# --------------------------------------------------------------------------- #
# Assistant
# --------------------------------------------------------------------------- #
elif page == "Assistant":
    st.markdown('<div class="card"><div class="card-title">AI Assistant</div></div>', unsafe_allow_html=True)
    app_id = st.text_input("Application ID", value=st.session_state.application_id or "")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Ask about your application, documents, or enablement programs..."):
        if not app_id:
            st.error("Enter an application ID first.")
        else:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            try:
                with st.spinner("Thinking..."):
                    resp = api.chat(app_id, prompt)
                answer = resp["answer"]
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                with st.chat_message("assistant"):
                    st.write(answer)
            except Exception as exc:
                st.error(f"Chat failed: {exc}")

# --------------------------------------------------------------------------- #
# Officer Dashboard
# --------------------------------------------------------------------------- #
elif page == "Officer Dashboard":
    st.markdown('<div class="card"><div class="card-title">Case Officer Dashboard</div></div>', unsafe_allow_html=True)
    if st.button("Refresh applications", use_container_width=True):
        try:
            apps = api.list_applications()
            if not apps:
                st.info("No applications yet.")
            else:
                df = pd.DataFrame(
                    [
                        {
                            "ID": a["id"],
                            "Applicant": a["applicant_name"],
                            "Status": a["status"],
                            "Outcome": a.get("outcome") or "—",
                            "Submitted": a["created_at"],
                        }
                        for a in apps
                    ]
                )
                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Could not load dashboard: {exc}")
