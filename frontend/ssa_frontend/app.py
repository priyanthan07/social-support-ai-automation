"""Main Streamlit entrypoint with custom-themed multi-page navigation."""

from __future__ import annotations

import json
import time
from datetime import date, datetime
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

FAMILY_RELATIONS = ["spouse", "child", "parent", "sibling", "other"]
DEMO_DOC_MAP = {
    "emirates_id": ("emirates_id.png", "emirates_id"),
    "bank_statement": ("bank_statement.pdf", "bank_statement"),
    "resume": ("resume.pdf", "resume"),
    "assets_liabilities": ("assets_liabilities.xlsx", "assets_liabilities"),
    "credit_report": ("credit_report.pdf", "credit_report"),
}

if "application_id" not in st.session_state:
    st.session_state.application_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "demo_files" not in st.session_state:
    st.session_state.demo_files = {}
if "demo_form_defaults" not in st.session_state:
    st.session_state.demo_form_defaults = {}
if "chat_loaded_for" not in st.session_state:
    st.session_state.chat_loaded_for = None


def _demo_dir_path() -> Path:
    demo_dir = Path("/data/synthetic/documents/aisha_eligible")
    if not demo_dir.exists():
        demo_dir = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "synthetic"
            / "documents"
            / "aisha_eligible"
        )
    return demo_dir


def _age_from_dob_str(dob: str | None) -> int | None:
    if not dob:
        return None
    try:
        parsed = datetime.strptime(str(dob)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    years = today.year - parsed.year
    if (today.month, today.day) < (parsed.month, parsed.day):
        years -= 1
    return years if years >= 0 else None


def _nationality_group(nationality: str | None) -> str:
    if nationality and "united arab emirates" in nationality.lower():
        return "citizen"
    return "resident"


def _employment_years_from_history(history: list) -> float:
    if not history:
        return 0.0
    total = 0.0
    for entry in history:
        if isinstance(entry, list) and len(entry) >= 3:
            period = str(entry[2])
            if "-" in period:
                parts = period.split("-")
                try:
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    total += max(0, end - start)
                except ValueError:
                    continue
    return float(total)


def _load_demo_assets() -> None:
    demo_dir = _demo_dir_path()
    if not demo_dir.exists():
        st.error(f"Demo directory not found: {demo_dir}")
        return

    persona_path = demo_dir / "persona.json"
    if persona_path.exists():
        persona = json.loads(persona_path.read_text(encoding="utf-8"))
        employment_years = _employment_years_from_history(persona.get("employment_history", []))
        st.session_state.demo_form_defaults = {
            "applicant_name": persona.get("full_name", ""),
            "emirates_id": persona.get("emirates_id", ""),
            "monthly_income": float(persona.get("stated_monthly_income", 1800)),
            "family_size": int(persona.get("family_size", 4)),
            "num_dependents": int(persona.get("num_dependents", 2)),
            "employment_status": persona.get("employment_status", "unemployed"),
            "education_level": "high_school",
            "address": persona.get("address_id", ""),
            "age": _age_from_dob_str(persona.get("dob")) or 35,
            "nationality_group": _nationality_group(persona.get("nationality")),
            "employment_years": employment_years,
            "months_employed_last_2yrs": min(24, int(round(min(employment_years, 2.0) * 12))),
            "family_member_rows": int(persona.get("num_dependents", 2)),
        }

    demo_files: dict[str, tuple[bytes, str]] = {}
    for doc_type, (filename, _) in DEMO_DOC_MAP.items():
        path = demo_dir / filename
        if path.exists():
            demo_files[doc_type] = (path.read_bytes(), filename)
    st.session_state.demo_files = demo_files


def _resolve_upload(doc_type: str, uploaded, demo_files: dict) -> tuple[bytes, str] | None:
    if uploaded is not None:
        return uploaded.getvalue(), uploaded.name
    if doc_type in demo_files:
        return demo_files[doc_type]
    return None


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

    defaults = st.session_state.demo_form_defaults

    col1, col2 = st.columns(2)
    with col1:
        applicant_name = st.text_input(
            "Full name *",
            value=defaults.get("applicant_name", ""),
            placeholder="Aisha Abdullah Al Mansoori",
        )
        emirates_id = st.text_input(
            "Emirates ID",
            value=defaults.get("emirates_id", ""),
            placeholder="784-1988-1234567-1",
        )
        email = st.text_input("Email", placeholder="applicant@example.com")
        phone = st.text_input("Phone", placeholder="+971501234567")
        age = st.number_input("Age", min_value=18, max_value=100, value=int(defaults.get("age", 35)))
        marital_status = st.selectbox(
            "Marital status",
            ["single", "married", "divorced", "widowed"],
            index=["single", "married", "divorced", "widowed"].index(
                defaults.get("marital_status", "married")
            )
            if defaults.get("marital_status") in {"single", "married", "divorced", "widowed"}
            else 1,
        )
        nationality_group = st.selectbox(
            "Nationality group",
            ["citizen", "resident"],
            index=0 if defaults.get("nationality_group", "citizen") == "citizen" else 1,
        )
    with col2:
        monthly_income = st.number_input(
            "Monthly income (AED)",
            min_value=0.0,
            value=float(defaults.get("monthly_income", 5000.0)),
            step=500.0,
        )
        family_size = st.number_input(
            "Family size",
            min_value=1,
            max_value=15,
            value=int(defaults.get("family_size", 4)),
        )
        num_dependents = st.number_input(
            "Dependents",
            min_value=0,
            max_value=12,
            value=int(defaults.get("num_dependents", 2)),
        )
        employment_status = st.selectbox(
            "Employment status",
            ["employed", "self_employed", "unemployed", "retired", "student"],
            index=["employed", "self_employed", "unemployed", "retired", "student"].index(
                defaults.get("employment_status", "employed")
            )
            if defaults.get("employment_status") in {"employed", "self_employed", "unemployed", "retired", "student"}
            else 0,
        )
        education_level = st.selectbox(
            "Education level",
            ["none", "high_school", "diploma", "bachelor", "postgraduate"],
            index=["none", "high_school", "diploma", "bachelor", "postgraduate"].index(
                defaults.get("education_level", "high_school")
            )
            if defaults.get("education_level") in {"none", "high_school", "diploma", "bachelor", "postgraduate"}
            else 1,
        )
        housing_status = st.selectbox(
            "Housing status",
            ["owned", "rented", "family", "government_housing"],
        )
        has_disability = st.selectbox("Has disability", ["no", "yes"])
        employment_years = st.number_input(
            "Years of employment (total)",
            min_value=0.0,
            max_value=50.0,
            value=float(defaults.get("employment_years", 0.0)),
            step=0.5,
        )
        months_employed_last_2yrs = st.number_input(
            "Months employed (last 2 years)",
            min_value=0,
            max_value=24,
            value=int(defaults.get("months_employed_last_2yrs", 0)),
        )
        address = st.text_input(
            "Address",
            value=defaults.get("address", ""),
            placeholder="Villa 12, Al Wathba, Abu Dhabi",
        )

    st.markdown("#### Household members")
    st.caption("List other household members (used for the household graph in validation).")
    num_family_rows = st.number_input(
        "Number of household members to list",
        min_value=0,
        max_value=8,
        value=int(defaults.get("family_member_rows", 2)),
    )
    family_members: list[dict[str, str]] = []
    for i in range(int(num_family_rows)):
        fc1, fc2 = st.columns(2)
        member_name = fc1.text_input(f"Member {i + 1} name", key=f"family_member_name_{i}")
        relation = fc2.selectbox(
            f"Member {i + 1} relation",
            FAMILY_RELATIONS,
            key=f"family_member_relation_{i}",
        )
        if member_name.strip():
            family_members.append({"name": member_name.strip(), "relation": relation})

    st.markdown("#### Upload documents")
    doc_cols = st.columns(2)
    uploads = {
        "emirates_id": doc_cols[0].file_uploader("Emirates ID (image)", type=["png", "jpg", "jpeg"]),
        "bank_statement": doc_cols[1].file_uploader("Bank statement (PDF)", type=["pdf"]),
        "resume": doc_cols[0].file_uploader("Resume (PDF)", type=["pdf"]),
        "assets_liabilities": doc_cols[1].file_uploader(
            "Assets/Liabilities (Excel)", type=["xlsx", "xls", "csv"]
        ),
        "credit_report": st.file_uploader("Credit report (PDF)", type=["pdf"]),
    }

    if st.session_state.demo_files:
        loaded = ", ".join(st.session_state.demo_files.keys())
        st.info(f"Demo files loaded in session (used on submit if upload empty): {loaded}")

    demo_dir = _demo_dir_path()
    if demo_dir.exists():
        if st.button("Load demo (Aisha — eligible persona + files)"):
            _load_demo_assets()
            if st.session_state.demo_files:
                loaded = ", ".join(st.session_state.demo_files.keys())
                st.success(
                    f"Demo persona and documents loaded ({loaded}). Review the form and submit."
                )
            else:
                st.warning(
                    "Demo persona loaded, but no document files found. "
                    "Run `uv run python -m ssa_ml.generate_documents` in the ml/ folder, "
                    "or upload documents manually before submitting."
                )
            st.rerun()

    if st.button("Submit Application", type="primary", use_container_width=True):
        if not applicant_name.strip():
            st.error("Applicant name is required.")
        else:
            if num_dependents != len(family_members) and family_members:
                st.warning(
                    f"Dependents ({num_dependents}) differs from listed household members "
                    f"({len(family_members)}). Submission will continue."
                )

            form_data = {
                "monthly_income": monthly_income,
                "family_size": int(family_size),
                "num_dependents": int(num_dependents),
                "employment_status": employment_status,
                "education_level": education_level,
                "housing_status": housing_status,
                "marital_status": marital_status,
                "nationality_group": nationality_group,
                "has_disability": has_disability,
                "address": address,
                "age": int(age),
                "employment_years": float(employment_years),
                "months_employed_last_2yrs": int(months_employed_last_2yrs),
                "family_members": family_members,
            }

            demo_files = st.session_state.demo_files
            resolved: dict[str, tuple[bytes, str]] = {}
            for doc_type, uploaded in uploads.items():
                payload = _resolve_upload(doc_type, uploaded, demo_files)
                if payload:
                    resolved[doc_type] = payload

            if not resolved:
                st.error("Upload at least one document (or load the demo with generated files).")
            else:
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
                        for doc_type, (file_bytes, filename) in resolved.items():
                            api.upload_document(app_id, doc_type, file_bytes, filename)
                        api.process_application(app_id)
                        st.session_state.application_id = app_id
                        st.session_state.chat_history = []
                        st.session_state.chat_loaded_for = None
                    st.success(f"Application submitted and processing started. ID: `{app_id}`")
                    st.info("Go to **Live Processing** to watch progress.")
                except Exception as exc:
                    st.error(f"Submission failed: {exc}")

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

    if app_id and st.session_state.get("chat_loaded_for") != app_id:
        try:
            turns = api.get_chat_history(app_id)
            st.session_state.chat_history = turns
            st.session_state.chat_loaded_for = app_id
        except Exception:
            st.session_state.chat_history = []
            st.session_state.chat_loaded_for = app_id

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
